"""Inspect one actual full-mesh FBX in a fresh Blender process.

Checks the full pinned bind/hierarchy and all seven embedded takes against
source samples, plus material/UV/skin/morph contracts. No art acceptance claim.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector


def sha(path):
    # Large source/FBX files must not allocate a second full payload just to hash.
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def angle(a, b):
    dot = abs(sum(float(a[i]) * float(b[i]) for i in range(4)))
    norm = math.sqrt(sum(float(x)**2 for x in a) * sum(float(x)**2 for x in b))
    if norm < 1e-15:
        raise RuntimeError('Zero quaternion')
    return math.degrees(2 * math.acos(min(1., dot / norm)))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--source-contract', type=Path, required=True)
    parser.add_argument('--variant', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--expected-bones', type=int, default=79)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    if args.output.exists():
        raise RuntimeError('Preserve previous variant validation')
    directory = args.directory
    manifest = json.loads((directory / 'manifest.json').read_text())
    source = json.loads(args.source_contract.read_text())
    item = next(v for v in manifest['variants'] if v['name'] == args.variant)
    path = directory / item['fbx']
    before_hash = sha(path)
    errors = []
    if manifest['sourceSha256'] != source['sourceSha256']:
        raise RuntimeError('FBX manifest does not match baked source contract')
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(path), use_anim=True)
    rigs = [o for o in bpy.data.objects if o.type == 'ARMATURE']
    meshes = [o for o in bpy.data.objects if o.type == 'MESH']
    if len(rigs) != 1 or len(meshes) != 1:
        raise RuntimeError('Expected exactly one full mesh and one rig')
    rig, mesh = rigs[0], meshes[0]
    bones = {b.name for b in rig.data.bones}
    missing = sorted(set(source['bones']) - bones)
    extra = sorted(bones - set(source['bones']))
    parents = {b.name: b.parent.name if b.parent else None for b in rig.data.bones}
    if missing or extra or len(bones) != args.expected_bones or len(source['bones']) != args.expected_bones:
        errors.append('Full '+str(args.expected_bones)+'-bone set differs from source')
    if parents != source['sourceParents']:
        errors.append('Full hierarchy differs from source')
    rest = {b.name: (rig.matrix_world @ b.matrix_local).copy() for b in rig.data.bones}
    bind_error = max((max(abs(rest[n][i][j] - Matrix(m)[i][j]) for i in range(4) for j in range(4))
        for n, m in source['sourceRest'].items() if n in rest), default=float('inf'))
    if bind_error > 1e-4:
        errors.append('Full-mesh world bind differs from saved source')
    # Blender infers edit-bone connection and suppresses valid FBX translation.
    # Restore only source use_connect flags; assert no bind/hierarchy changes.
    before = {b.name: b.matrix_local.copy() for b in rig.data.bones}
    changed = [b.name for b in rig.data.bones if b.name in source['sourceConnected']
               and b.use_connect != source['sourceConnected'][b.name]]
    if changed:
        bpy.context.view_layer.objects.active = rig; rig.select_set(True)
        bpy.ops.object.mode_set(mode='EDIT')
        for name in changed:
            rig.data.edit_bones[name].use_connect = source['sourceConnected'][name]
        bpy.ops.object.mode_set(mode='OBJECT')
    connect_drift = max(max(abs(b.matrix_local[i][j] - before[b.name][i][j])
                           for i in range(4) for j in range(4)) for b in rig.data.bones)
    if connect_drift > 1e-6:
        errors.append('Connection-flag restoration changed bind')
    data = mesh.data
    all_triangles = all(len(p.vertices) == 3 for p in data.polygons)
    if not all_triangles:
        errors.append('Final FBX is not fully triangular')
    if len(data.vertices) != item['vertices'] or len(data.polygons) != item['triangles']:
        errors.append('Actual vertex/triangle counts differ from manifest')
    coordinates = np.empty(len(data.vertices) * 3, dtype=np.float32)
    data.vertices.foreach_get('co', coordinates)
    transform = np.array(mesh.matrix_world, dtype=np.float64)
    world_positions = coordinates.reshape((-1, 3)) @ transform[:3, :3].T + transform[:3, 3]
    bounds = {'min': world_positions.min(axis=0).tolist(), 'max': world_positions.max(axis=0).tolist()}
    bounds_error = max(abs(a-b) for side in ['min', 'max']
        for a, b in zip(bounds[side], item['sourceRestBoundsMeters'][side]))
    if not np.isfinite(world_positions).all() or bounds_error > 1e-4:
        errors.append('Rest mesh bounds/units differ from source export')
    invalid_weights = 0
    for vertex in data.vertices:
        if (not vertex.groups or len(vertex.groups) > 8
            or any(not math.isfinite(g.weight) or g.weight < 0 or
                   mesh.vertex_groups[g.group].name not in bones for g in vertex.groups)
            or abs(sum(g.weight for g in vertex.groups) - 1.) > .005):
            invalid_weights += 1
    if invalid_weights:
        errors.append('Invalid vertex skin weights')
    if not data.uv_layers:
        errors.append('Missing UV layer')
    else:
        uvs = np.empty(len(data.uv_layers.active.data) * 2, dtype=np.float32)
        data.uv_layers.active.data.foreach_get('uv', uvs)
        if not np.isfinite(uvs).all():
            errors.append('Nonfinite UV coordinates')
    actual_materials = [m.name if m else None for m in data.materials]
    declared_materials = {m['name'] for m in manifest['materials']}
    if None in actual_materials or not set(actual_materials).issubset(declared_materials):
        errors.append('Missing or undeclared material slots')
    if len(actual_materials) != item['materialSlots']:
        errors.append('Material slot count differs from exported manifest')
    morphs = {}
    if data.shape_keys:
        basis = np.empty(len(data.vertices) * 3, dtype=np.float32)
        data.shape_keys.key_blocks[0].data.foreach_get('co', basis)
        for key in list(data.shape_keys.key_blocks)[1:]:
            values = np.empty_like(basis); key.data.foreach_get('co', values)
            name = key.name.rsplit('.', 1)[-1]
            morphs[name] = float(np.max(np.abs(values - basis)))
            if not np.isfinite(values).all():
                errors.append('Nonfinite morph ' + name)
    required_morphs = set(item['morphs'])
    if any(morphs.get(name, 0) <= 1e-7 for name in required_morphs):
        errors.append('Required nonzero morph lost on import')
    deformation = item.get('deformation', manifest['deformation'])
    for driver in deformation['drivers']:
        if driver['bone'] not in bones or driver['morph'] not in required_morphs:
            errors.append('Invalid per-variant deformation driver')
    canonical = set(source['clips'])
    compatible = [a for a in bpy.data.actions if any(s.target_id_type == 'OBJECT' for s in a.slots)]
    action_map = {}
    for action in compatible:
        name = action.name.rsplit('|', 1)[-1]
        if name in action_map:
            errors.append('Duplicate compatible embedded take: ' + name)
        action_map[name] = action
    if set(action_map) != canonical:
        errors.append('Embedded object actions are not exactly the seven canonical takes')
    results = {}
    if not missing and not extra:
        controls = [b.name for b in rig.pose.bones if b.name == 'FaceRoot'
                    or any(p.name == 'FaceRoot' for p in b.parent_recursive)]
        for name, entry in source['clips'].items():
            if name not in action_map:
                continue
            action = action_map[name]
            rig.animation_data_create(); rig.animation_data.action = None
            for bone in rig.pose.bones:
                bone.matrix_basis = Matrix.Identity(4)
            rig.animation_data.action = action
            slots = [s for s in action.slots if s.target_id_type == 'OBJECT']
            if len(slots) != 1:
                errors.append(name + ' ambiguous object action slot'); continue
            rig.animation_data.action_slot = slots[0]
            for track in rig.animation_data.nla_tracks:
                track.mute = True
            scene = bpy.context.scene; fps = scene.render.fps / scene.render.fps_base
            first, last = action.frame_range
            source_first, source_last = entry['frameRange']
            duration = (last - first) / fps
            expected_duration = (source_last - source_first) / entry['fps']
            maximum_position = maximum_rotation = maximum_scale = 0.
            facial = {n: [] for n in controls}; worst = None
            for sample in entry['sourceSamples']:
                at = first + (sample['frame'] - source_first) / entry['fps'] * fps
                scene.frame_set(math.floor(at), subframe=at - math.floor(at))
                bpy.context.view_layer.update()
                for bone, expected in sample['bones'].items():
                    world = rig.matrix_world @ rig.pose.bones[bone].matrix
                    position_error = (world.translation - Vector(expected['head'])).length
                    rotation_error = angle((world @ rest[bone].inverted()).to_quaternion(),
                                           Quaternion(expected['deformationQuaternion']))
                    scale_error = max(abs(a-b) for a, b in zip(world.to_scale(), expected['worldScale']))
                    if position_error > maximum_position:
                        maximum_position = position_error; worst = {'bone': bone, 'sourceFrame': sample['frame']}
                    maximum_rotation = max(maximum_rotation, rotation_error)
                    maximum_scale = max(maximum_scale, scale_error)
                for bone in controls:
                    facial[bone].append(rig.pose.bones[bone].matrix_basis.copy())
            varying = [bone for bone, values in facial.items() if any(
                (values[0].translation - v.translation).length > 1e-6
                or angle(values[0].to_quaternion(), v.to_quaternion()) > .001 for v in values[1:])]
            if len(entry['sourceSamples']) != 17 or abs(duration - expected_duration) > 1e-4:
                errors.append(name + ' source sample coverage/duration mismatch')
            if maximum_position > 1e-4 or maximum_rotation > .05 or maximum_scale > 1e-4:
                errors.append(name + ' embedded skeletal motion differs from source')
            if not varying:
                errors.append(name + ' no varying local facial control')
            results[name] = {'action': action.name, 'durationSeconds': duration,
                'expectedDurationSeconds': expected_duration, 'sampledFrames': len(entry['sourceSamples']),
                'maximumPosePositionErrorMeters': maximum_position,
                'maximumPoseRotationErrorDegrees': maximum_rotation, 'maximumScaleError': maximum_scale,
                'worstPosition': worst, 'varyingLocalFacialControls': varying}
    if sha(path) != before_hash:
        errors.append('Read-only validation changed FBX')
    report = {'variant': args.variant, 'file': str(path), 'sha256': before_hash,
        'sourceContractSha256': sha(args.source_contract), 'manifestSha256': sha(directory/'manifest.json'),
        'recipeSha256': sha(__file__), 'passed': not errors, 'errors': errors,
        'boneCount': len(bones), 'missingBones': missing, 'extraBones': extra,
        'hierarchyMatchesSource': parents == source['sourceParents'], 'maxSourceBindMatrixError': bind_error,
        'connectionFlagsRestoredForBlenderPlayback': changed, 'connectionNormalizationBindDrift': connect_drift,
        'vertices': len(data.vertices), 'triangles': len(data.polygons), 'allPolygonsTriangular': all_triangles,
        'worldRestBoundsMeters': bounds, 'maximumRestBoundsErrorMeters': bounds_error,
        'invalidWeightCount': invalid_weights, 'materialNames': actual_materials,
        'morphMaximumAbsoluteDeltaMeters': morphs, 'clips': results,
        'artisticAcceptance': False, 'engineImportVerified': False,
        'limits': '17 skeletal samples per embedded take; not full-cycle mesh collision or artistic validation'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n', newline='\n')
    if errors:
        raise RuntimeError('; '.join(errors))
    print('NIB_COHERENT_VARIANT_ROUNDTRIP_COMPLETE', args.variant, flush=True)


if __name__ == '__main__':
    main()
