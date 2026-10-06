"""Prepared visible-surface native flow derivative; requires the actual audit.

No density, rig, skin or material change. Runtime ABC export is deliberately
deferred until actual Neutral/Profile review. This does not edit the pilot.
"""
import argparse
import copy
import json
import math
import random
import shutil
import sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent), str(HERE.parents[1] / 'restorative_wip'),
               str(HERE.parents[1] / 'v5_wip')]
from contracts import rig_contract, surface_hash
from flow_recipe import make, strand_point, ear_selector
from native_surface import surface_copy, Sampler
from strand_contract import sha, write_region
from nib_groom_v5 import configure_goggle_envelopes, avoid_goggles


def tree_for(objects):
    vertices, triangles, owners = [], [], []
    for obj in objects:
        obj.data.calc_loop_triangles()
        start = len(vertices)
        vertices.extend(obj.matrix_world @ v.co for v in obj.data.vertices)
        triangles.extend(tuple(start + i for i in t.vertices) for t in obj.data.loop_triangles)
        owners.extend(obj.name for t in obj.data.loop_triangles)
    class Envelope:
        def __init__(self):
            self.tree = BVHTree.FromPolygons(vertices, triangles, all_triangles=True)
            self.owners = owners
        def ray_cast(self, *args):
            return self.tree.ray_cast(*args)
    return Envelope()


class PathClearanceError(RuntimeError):
    def __init__(self, message, detail):
        super().__init__(message)
        self.detail = detail


def lift_ear_path(points, outward, tree):
    """One smooth whole-path lift, not independent nearest-surface snapping."""
    front = outward.y < 0
    ray = Vector((0, 1 if front else -1, 0))
    direction = -ray
    # Tangent-plane guides can re-enter the cup as the actual surface curves.
    # A single smooth displacement clears that measured surface while keeping
    # the root exact. A buried root needs re-rooting, so this recipe refuses it.
    lift = 0.
    intersections = []
    for j, point in enumerate(points):
        location, hit_normal, triangle, hit_distance = tree.ray_cast(point + direction * .4, ray, .6)
        if location is None:
            continue
        depth = (location - point).dot(direction)
        entry = {'pointIndex': j, 'point': list(point), 'hit': list(location),
            'hitNormal': list(hit_normal), 'hitNormalDotOutwardRayOrigin': float(hit_normal.dot(direction)),
            'hitSource': tree.owners[triangle], 'hitTriangle': triangle,
            'depthMeters': depth, 'hitDistanceMeters': hit_distance}
        intersections.append(entry)
        if j == 0:
            if depth > .0005:
                raise PathClearanceError('Proposed root lies under another skin surface',
                    {'front': front, 'rootNormal': list(outward), 'intersections': intersections})
            continue
        margin = .00035 + .0015 * math.sin(math.pi * j / 16)
        envelope = math.sin(math.pi * j / 16)
        entry['clearanceMarginMeters'] = margin
        entry['smoothLiftEnvelope'] = envelope
        entry['requiredWholePathLiftMeters'] = (depth + margin) / envelope
        lift = max(lift, entry['requiredWholePathLiftMeters'])
    lift = max(0., lift)
    if lift > .025:
        raise PathClearanceError('Ear path requires more than the bounded 25mm coherent lift',
            {'front': front, 'rootNormal': list(outward), 'requiredLiftMeters': lift, 'intersections': intersections})
    result = [p + direction * lift * math.sin(math.pi * j / 16) for j, p in enumerate(points)]
    for j, point in enumerate(result[1:], 1):
        location, _, _, _ = tree.ray_cast(point + direction * .4, ray, .6)
        if location is not None and (location - point).dot(direction) > -.00025:
            raise PathClearanceError('Ear guide still enters the actual visible skin envelope',
                {'front': front, 'rootNormal': list(outward), 'requiredLiftMeters': lift,
                 'intersections': intersections, 'liftedPoints': [list(p) for p in result]})
    return result, lift


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--audit', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--diagnostic-only', action='store_true')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    source_sha = sha(args.source)
    old = json.loads(args.report.read_text())
    audit = json.loads(args.audit.read_text())
    if source_sha != '0e60a9dbd59a88c64befbf3f05bd543d051d47d23857e31478f3bce8f9ab0cf7':
        raise RuntimeError('Wrong frozen native pilot')
    if old['candidateSha256'] != source_sha or audit['sourceSha256'] != source_sha:
        raise RuntimeError('Require the actual matching source audit')
    if sha(args.audit) != 'df9122174dddfde672309dea2d93fedeae66f39c092f2dfb047153c7b2d0e3d6':
        raise RuntimeError('Actual reviewed occlusion audit changed')
    if old['curveCount'] != 26000 or old['pointCount'] != 234000 or len(old['regions']) != 5:
        raise RuntimeError('Fixed native groom budget differs')
    if args.output_dir.exists():
        raise RuntimeError('Preserve prior appearance result')
    if not any(region['name'].startswith('EarInner') and any(
            part['rootFrontOccluderCounts'] for part in region['parts']) for region in audit['regions']):
        raise RuntimeError('This revision requires the diagnosed actual inner-ear root-domain failure')
    args.output_dir.mkdir(parents=True)
    bpy.ops.wm.open_mainfile(filepath=str(args.source), load_ui=False)
    rig = bpy.data.objects['Nib_Rig']
    before_rig = rig_contract(rig)
    mesh_hashes = {o.name: surface_hash(o) for o in bpy.data.objects if o.type == 'MESH'}
    visibility_exclusions = []
    for name in ['Auricle basal cartilage fold', 'Auricle basal cartilage fold.001']:
        obj = bpy.data.objects.get(name)
        if obj is None or obj.type != 'MESH' or obj.get('bone') not in ['Ear_L', 'Ear_R']:
            raise RuntimeError('Expected the two actually diagnosed basal artifacts')
        visibility_exclusions.append({'name': name, 'previousHideRender': obj.hide_render,
            'previousHideViewport': obj.hide_get(), 'preservedMeshHash': mesh_hashes[name],
            'reason': 'Non-concept hard tan basal crossbar; actual curve41 intersects its front-facing surface. Preserve geometry but explicitly exclude it from this isolated appearance.'})
        obj.hide_render = True; obj.hide_set(True)
        obj['native_groom_artifact_excluded'] = True
    rig.animation_data.action = None
    for track in rig.animation_data.nla_tracks:
        track.mute = True
    for bone in rig.pose.bones:
        bone.matrix_basis = Matrix.Identity(4)
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()
    configure_goggle_envelopes(bpy.data.collections['Nib_Authored_Components'])
    report = copy.deepcopy(old)
    report['hiddenControlGroom'] += visibility_exclusions
    target_arrays = {}
    changes = []
    seed = 701620
    strand_dir = args.output_dir / 'strands'
    shutil.copytree(args.report.parent / 'strands', strand_dir)
    for region in report['regions']:
        curves = bpy.data.objects['Nib native ' + region['name']]
        surface = bpy.data.objects[region['sourceSurfaceObject']]
        old_surface_name = surface.name
        ear = region['name'].startswith('Ear')
        inner = region['name'].startswith('EarInner')
        side = 'L' if region['name'].endswith('_L') else 'R'
        authored = bpy.data.collections['Nib_Authored_Components']
        ear_surfaces = [o for o in authored.objects if o.type == 'MESH'
            and o.get('bone') == 'Ear_' + side and o.name.startswith(
                ('Fennec cupped ear', 'Ear inner velvet', 'Rounded auricle cartilage rim', 'Auricle basal cartilage fold'))
            and not o.get('native_groom_artifact_excluded', False)]
        if inner:
            matches = [o for o in ear_surfaces if o.name.startswith('Ear inner velvet')]
            if len(matches) != 1:
                raise RuntimeError('Expected one actual visible pink ear surface')
            surface = matches[0]
            support = surface_copy(surface, bpy.data.collections['Nib_Native_Groom_Attachment'])
            curves.data.surface = support
            curves.data.surface_uv_map = 'NativeGroomAttachment'
            bpy.context.view_layer.update()
        else:
            support = curves.data.surface
        tree = tree_for(ear_surfaces) if ear else None
        matrix = surface.matrix_world
        normal_matrix = matrix.to_3x3().inverted().transposed()
        def array(field, dtype):
            spec = region['files'][field]
            path = args.report.parent / region['dataDirectory'] / spec['path']
            if sha(path) != spec['sha256']:
                raise RuntimeError('Frozen strand sidecar changed')
            return np.fromfile(path, dtype=dtype).reshape(spec['shape'])
        positions = array('positions', '<f4').reshape(-1, 9, 3)
        ids = array('rootTriangleVertexIndices', '<i4')
        bary = array('rootBarycentrics', '<f4')
        roots, normals, hints = [], [], []
        root_records = []
        sampling = []
        hint_attr = surface.data.attributes.get('nib_source_position')
        if ear:
            def visible(point):
                direction = Vector((0, -1 if inner else 1, 0))
                hit, _, _, _ = tree.ray_cast(point + direction * .4, -direction, .6)
                return hit is not None and abs((hit - point).dot(direction)) < .0005
            for part in region['parts']:
                name, count = part['region'], part['rootSamples']
                if inner:
                    selector = lambda point, normal, hint: ear_selector(name, point, normal, hint)
                    sampler = Sampler(surface, support, selector)
                    records, measurement = sampler.sample(count, seed + 841, visible)
                    sampling.append({'part': name, **measurement})
                    root_records.extend(records)
                else:
                    # Same4500 regional budget: restore short nap around the
                    # visible silhouette using 1200 outer-margin roots, with
                    # 3300 remaining rear-surface roots. No front buried roots.
                    from flow_guides import ear_frame
                    for margin, number in [(False, count - 1200), (True, 1200)]:
                        def selector(point, normal, hint):
                            along, across, _, _, _ = ear_frame(point, 1 if side == 'L' else -1)
                            return normal.y > .12 and .045 < along < .975 and (not margin or abs(across) > .72)
                        sampler = Sampler(surface, support, selector)
                        records, measurement = sampler.sample(number, seed + (940 if margin else 841), visible)
                        sampling.append({'part': name, 'outerMargin': margin, **measurement})
                        root_records.extend(records)
                seed += 1000
            roots = [Vector(r['point']) for r in root_records]
            normals = [Vector(r['normal']) for r in root_records]
            hints = [Vector(r['sourceHint']) for r in root_records]
        else:
            for indices, weights in zip(ids, bary):
                point = sum((matrix @ surface.data.vertices[int(i)].co * float(w) for i, w in zip(indices, weights)), Vector())
                normal = sum((normal_matrix @ surface.data.vertices[int(i)].normal * float(w) for i, w in zip(indices, weights)), Vector()).normalized()
                hint = sum((Vector(hint_attr.data[int(i)].vector) * float(w) for i, w in zip(indices, weights)), Vector()) if hint_attr else point.copy()
                roots.append(point); normals.append(normal); hints.append(hint)
            if np.max(np.linalg.norm(np.asarray(roots) - positions[:, 0], axis=1)) > 1e-6:
                raise RuntimeError('Exact retained scalp root correspondence changed')
        result = np.empty_like(positions)
        offset = 0
        maximum_lift = 0.
        for part in region['parts']:
            count = part['rootSamples']; name = part['region']
            rng = random.Random(seed)
            guide_ids = rng.sample(range(offset, offset + count), min(count, max(50, count // 18)))
            guides = [make(name, roots[i], normals[i], hints[i], seed + i, 1 if side == 'L' else -1) for i in guide_ids]
            part['guides'] = len(guides)
            xyz = np.asarray([roots[i] for i in guide_ids])
            for i in range(offset, offset + count):
                generator = random.Random(seed * 100003 + i)
                index = int(np.argmin(np.sum((xyz - np.asarray(roots[i])) ** 2, axis=1)))
                guide = guides[index]
                length = generator.uniform(.62, 1.10)
                phase = generator.uniform(0, math.tau)
                points = [strand_point(roots[i], normals[i], guide, j / 8, length, phase, guide['undercoat']) for j in range(9)]
                if ear:
                    try:
                        points, lift = lift_ear_path(points, normals[i], tree)
                    except PathClearanceError as error:
                        detail = {'status': 'Actual isolated path attribution; no source save or geometric gate relaxation',
                            'sourceSha256': source_sha, 'region': region['name'], 'part': name,
                            'curveIndex': i, 'sourceSurface': surface.name, 'root': root_records[i],
                            'guideIndex': guide_ids[index], 'guide': guide, 'lengthScale': length,
                            'curlPhase': phase, 'exception': str(error), 'path': error.detail,
                            'recipeSha256': sha(Path(__file__)), 'flowRecipeSha256': sha(HERE / 'flow_recipe.py'),
                            'sourceChanged': sha(args.source) != source_sha, 'artisticAcceptance': False}
                        (args.output_dir / 'flow-failure.json').write_text(json.dumps(detail, indent=2) + '\n', newline='\n')
                        if args.diagnostic_only and not detail['sourceChanged']:
                            print('NIB_NATIVE_FLOW_DIAGNOSTIC_COMPLETE', flush=True)
                            return
                        raise
                    maximum_lift = max(maximum_lift, lift)
                else:
                    points = [points[0]] + [avoid_goggles(p) for p in points[1:]]
                result[i] = points
            offset += count; seed += 10000
        # Preserve exact original root float32 values, including the tiny source
        # interpolation rounding, rather than claiming a regenerated root exact.
        result[:, 0] = np.asarray(roots, np.float32) if ear else positions[:, 0]
        if not np.isfinite(result).all() or np.min(np.linalg.norm(np.diff(result, axis=1), axis=2)) < 1e-7:
            raise RuntimeError('Invalid native flow segments')
        curves.data.attributes['position'].data.foreach_set('vector', result.ravel())
        if ear:
            for name, values in [('surface_uv_coordinate', [r['attachmentUv'] for r in root_records]),
                                 ('groom_root_uv', [r['sourceUv'] for r in root_records])]:
                curves.data.attributes[name].data.foreach_set('vector', np.asarray(values, np.float32).ravel())
            colors = array('colorLinearRgb', '<f4')
            radii = array('radii', '<f4')
            replacement = write_region(strand_dir, region['name'], result.reshape(-1, 3), radii,
                [9] * len(result), root_records, colors, surface.name, support.name, report['boneNames'])
            region.update(replacement)
            region['rootSampling'] = sampling
            region['parts'] = [{'region': p['region'], 'rootSamples': p['rootSamples'],
                                'guides': p['guides'], 'sampling': [s for s in sampling if s['part'] == p['region']]}
                               for p in region['parts']]
            curves['surfaceSource'] = surface.name
        path = strand_dir / region['files']['positions']['path']
        result.reshape(-1, 3).astype('<f4').tofile(path)
        region['files']['positions'].update(sha256=sha(path), bytes=path.stat().st_size)
        target_arrays[region['name']] = result
        changes.append({'region': region['name'], 'rootsByteExact': not ear,
            'rootDomainReauthored': ear, 'oldSourceSurface': old_surface_name,
            'newSourceSurface': surface.name, 'rootSampling': sampling,
            'strandCount': len(result), 'maximumPointDisplacementMeters': float(np.linalg.norm(result - positions, axis=2).max()),
            'maximumCoherentEarLiftMeters': maximum_lift})
    for name, digest in mesh_hashes.items():
        if surface_hash(bpy.data.objects[name]) != digest:
            raise RuntimeError('Flow revision changed skin or other original geometry')
    if rig_contract(rig) != before_rig:
        raise RuntimeError('Flow revision changed bind or actions')
    if sum(len(v) for v in target_arrays.values()) != 26000:
        raise RuntimeError('Appearance revision changed native strand count')
    if args.diagnostic_only:
        raise RuntimeError('Diagnostic did not reproduce the preserved path failure; do not save a source')
    rig.animation_data.action = bpy.data.actions['Idle']; bpy.context.scene.frame_set(1)
    target = args.output_dir / 'Nib_NativeFlow_Study_v2b.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(target), compress=True)
    bpy.ops.wm.open_mainfile(filepath=str(target), load_ui=False)
    if rig_contract(bpy.data.objects['Nib_Rig']) != before_rig:
        raise RuntimeError('Reopened flow source lost rig/actions')
    for name, digest in mesh_hashes.items():
        if surface_hash(bpy.data.objects[name]) != digest:
            raise RuntimeError('Reopened flow source changed original geometry')
    for item in visibility_exclusions:
        obj = bpy.data.objects[item['name']]
        if not obj.hide_render or not obj.hide_get() or surface_hash(obj) != item['preservedMeshHash']:
            raise RuntimeError('Reopened basal-artifact exclusion or preserved mesh differs')
    for name, expected in target_arrays.items():
        data = bpy.data.objects['Nib native ' + name].data
        actual = np.empty(expected.size, np.float32)
        data.attributes['position'].data.foreach_get('vector', actual)
        if not np.array_equal(actual.reshape(expected.shape), expected):
            raise RuntimeError('Reopened native flow differs')
    rig = bpy.data.objects['Nib_Rig']
    scene = bpy.context.scene
    def reset_pose():
        rig.animation_data.action = None
        for track in rig.animation_data.nla_tracks:
            track.mute = True
        for bone in rig.pose.bones:
            bone.matrix_basis = Matrix.Identity(4)
        scene.frame_set(1)
        bpy.context.view_layer.update()
    def inspect_roots(label):
        bpy.context.view_layer.update()
        depsgraph = bpy.context.evaluated_depsgraph_get()
        rows = []
        for group in report['regions']:
            curves = bpy.data.objects['Nib native ' + group['name']]
            support = curves.data.surface
            evaluated = support.evaluated_get(depsgraph)
            mesh = evaluated.to_mesh()
            xyz = np.asarray([support.matrix_world @ v.co for v in mesh.vertices], float)
            evaluated.to_mesh_clear()
            def load(key, dtype):
                entry = group['files'][key]
                return np.fromfile(strand_dir / entry['path'], dtype=dtype).reshape(entry['shape'])
            indices = load('rootTriangleVertexIndices', '<i4')
            weights = load('rootBarycentrics', '<f4')
            expected = np.einsum('nij,ni->nj', xyz[indices], weights)
            data = curves.evaluated_get(depsgraph).data
            actual = np.empty(len(data.points) * 3, np.float32)
            data.attributes['position'].data.foreach_get('vector', actual)
            actual = actual.reshape(-1, 9, 3)[:, 0]
            error = np.linalg.norm(actual - expected, axis=1)
            movement = np.linalg.norm(actual - target_arrays[group['name']][:, 0], axis=1)
            if error.max() > 1e-5:
                raise RuntimeError('Revised native attachment differs ' + str((label, group['name'], float(error.max()))))
            rows.append({'region': group['name'], 'rootCount': len(actual),
                'maximumRootErrorMeters': float(error.max()), 'maximumRootMovementMeters': float(movement.max())})
        return {'pose': label, 'regions': rows}
    posed = []
    reset_pose(); posed.append(inspect_roots('BindRest'))
    for name, frame in [('Idle', 45), ('Run', 8), ('FacePerformance', 16), ('FacePerformance', 103)]:
        reset_pose(); rig.animation_data.action = bpy.data.actions[name]
        scene.frame_set(frame); posed.append(inspect_roots(name + ':' + str(frame)))
    reset_pose(); rig.pose.bones['EarTip_L'].rotation_euler.z = .18
    posed.append(inspect_roots('Diagnostic EarTip_L +0.18rad; source action unchanged'))
    if max(row['maximumRootMovementMeters'] for row in posed[-1]['regions'] if row['region'] == 'EarInnerCream_L') < .0005:
        raise RuntimeError('New visible inner-ear support failed actual ear-tip motion')
    if sha(args.source) != source_sha:
        raise RuntimeError('Frozen pilot source changed')
    report.update(status='Actual fixed-count visible-surface flow study; matched appearance review pending',
        source=str(args.source), sourceSha256=source_sha, candidate=str(target), candidateSha256=sha(target),
        savedSourceReopened=True, flowChanges=changes, inputAuditSha256=sha(args.audit),
        exports=[], nativeAlembicRoundtrips=[], posedRootChecks=posed,
        runtimeExportReady=False, artisticAcceptance=False, engineImported=False, sharedChanged=False,
        retainedAllMeshHashes=mesh_hashes,
        appearanceVisibilityExclusions=visibility_exclusions,
        futureExplicitMeshExportExclusions=[x['name'] for x in report['hiddenControlGroom']],
        futureBindingEligibleObjects=sorted({r['sourceSurfaceObject'] for r in report['regions']}),
        codeSha256={p.name: sha(p) for p in [Path(__file__), HERE / 'flow_recipe.py']})
    (args.output_dir / 'source.json').write_text(json.dumps(report, indent=2) + '\n', newline='\n')
    print('NIB_NATIVE_FLOW_SOURCE_SAVED_AND_REOPENED', flush=True)


if __name__ == '__main__':
    main()
