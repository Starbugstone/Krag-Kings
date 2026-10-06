"""Replace separated forearm rings with surface-fitted, overlapping cloth strips.

Works on a saved coherent source and preserves all skeleton/actions. Original
rings remain archived. Geometry follows actual anatomical body triangles;
the wrist seam is bridged by a bounded convex envelope of actual skin slices.
Weights interpolate from its measured support vertices with at most four influences. Native neutral
and action renders are required before export or artistic acceptance.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree
from bpy_extras.anim_utils import action_get_channelbag_for_slot

sys.path.insert(0, str(Path(__file__).parent))
from export_contract import CLIPS, select_action

p = argparse.ArgumentParser()
p.add_argument('--source', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args(sys.argv[sys.argv.index('--')+1:])
if a.output.exists():
    raise RuntimeError('Preserve earlier wrap study output')
a.output.mkdir(parents=True)
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
input_sha = sha(a.source)
bpy.ops.wm.open_mainfile(filepath=str(a.source), load_ui=False)
rig = bpy.data.objects['Nib_Rig']
collection = bpy.data.collections['Nib_Authored_Components']
body = bpy.data.objects['Continuous Nib anatomy organic']
source_bind = {b.name: [list(row) for row in b.matrix_local] for b in rig.data.bones}


def actions_digest():
    result = {}
    for name in CLIPS:
        action = bpy.data.actions[name]
        select_action(bpy, rig, action)
        bag = action_get_channelbag_for_slot(action, rig.animation_data.action_slot)
        rows = [(c.data_path, c.array_index,
                 [(list(k.co), list(k.handle_left), list(k.handle_right),
                   k.interpolation, k.handle_left_type, k.handle_right_type)
                  for k in c.keyframe_points]) for c in bag.fcurves]
        result[name] = hashlib.sha256(json.dumps(sorted(rows), sort_keys=True).encode()).hexdigest()
    return result


source_actions = actions_digest()
select_action(bpy, rig, None)
for track in rig.animation_data.nla_tracks:
    track.mute = True
bpy.context.scene.frame_set(1)
bpy.context.view_layer.update()
points, all_triangles, supporting_weights = [], [], []
for surface in [body]+[bpy.data.objects['Nib v5 coherent hand '+side] for side in ['L', 'R']]:
    surface.data.calc_loop_triangles()
    start = len(points)
    points.extend(surface.matrix_world@v.co for v in surface.data.vertices)
    all_triangles.extend(tuple(start+i for i in t.vertices) for t in surface.data.loop_triangles)
    names = [g.name for g in surface.vertex_groups]
    supporting_weights.extend([(names[g.group], g.weight) for g in v.groups]
                              for v in surface.data.vertices)


def mix_weights(entries):
    weights = {}
    total = sum(factor for vertex, factor in entries)
    for vertex, factor in entries:
        for name, value in supporting_weights[vertex]:
            weights[name] = weights.get(name, 0.)+value*factor/total
    ranked = sorted(weights.items(), key=lambda item: -item[1])[:4]
    total = sum(w for name, w in ranked)
    if total <= 1e-8:
        raise RuntimeError('Wrap hit unweighted anatomy')
    return [(name, w/total) for name, w in ranked]


def cross2(a, b):
    return a[0]*b[1]-a[1]*b[0]


def convex_hull(rows):
    ordered = sorted(rows)
    if len(ordered) < 12:
        raise RuntimeError('Insufficient measured skin support for cloth slice')
    def half(values):
        out = []
        for point in values:
            while len(out) >= 2 and cross2(
                    (out[-1][0]-out[-2][0], out[-1][1]-out[-2][1]),
                    (point[0]-out[-1][0], point[1]-out[-1][1])) <= 0:
                out.pop()
            out.append(point)
        return out
    return half(ordered)[:-1]+half(list(reversed(ordered)))[:-1]


def sample_hull(hull, direction):
    candidates = []
    for p, q in zip(hull, hull[1:]+hull[:1]):
        edge = (q[0]-p[0], q[1]-p[1])
        denominator = cross2(direction, edge)
        if abs(denominator) < 1e-12:
            continue
        radius = cross2(p, edge)/denominator
        along = cross2(p, direction)/denominator
        if radius > 0 and -1e-6 <= along <= 1+1e-6:
            along = max(0., min(1., along))
            candidates.append((radius, [(p[2], 1-along), (q[2], along)]))
    if not candidates:
        raise RuntimeError('Forearm axis lies outside measured cloth support slice')
    return max(candidates, key=lambda item: item[0])


archive = bpy.data.collections.new('PRESERVED separate forearm binding rings')
bpy.context.scene.collection.children.link(archive)
archive.hide_render = True
archive.hide_viewport = True
report = {'source': str(a.source), 'sourceSha256': input_sha,
          'recipeSha256': sha(Path(__file__)),
          'status': 'Actual cloth-strip source; native pose/material review required',
          'sharedAssetsChanged': False, 'engineExported': False,
          'artisticAcceptance': False, 'wraps': {}}
for side, sign in [('L', 1), ('R', -1)]:
    legacy = [obj for obj in collection.objects if obj.name.startswith('Forearm desert wrap '+side)]
    if len(legacy) != 10:
        raise RuntimeError('Expected ten separated source rings for '+side)
    elbow = rig.matrix_world@rig.data.bones['LowerArm_'+side].head_local
    wrist = rig.matrix_world@rig.data.bones['Hand_'+side].head_local
    axis = (wrist-elbow).normalized()
    length = (wrist-elbow).length
    lateral = Vector((sign, 0, 0))
    lateral -= axis*lateral.dot(axis)
    lateral.normalize()
    front = axis.cross(lateral).normalized()
    allowed = {'LowerArm_'+side, 'ForearmTwist_'+side, 'Hand_'+side}
    influence = [sum(value for name, value in row if name in allowed)
                 for row in supporting_weights]
    triangles = []
    for triangle in all_triangles:
        center = sum((points[i] for i in triangle), Vector())/3
        t = (center-elbow).dot(axis)/length
        radius = (center-elbow-axis*((center-elbow).dot(axis))).length
        if (.15 < t < 1.12 and radius < .06 and
                sum(influence[i] for i in triangle)/3 > .92):
            triangles.append(triangle)
    if not triangles:
        raise RuntimeError('No actual forearm/hand supporting surface')
    tree = BVHTree.FromPolygons(points, triangles, all_triangles=True)
    supported = sorted({i for triangle in triangles for i in triangle})
    # Cross-section hulls approximate taut cloth spanning the oblique body /
    # hand overlap. They must stay near actual anatomy; no invented base tube.
    projected = [(float((points[i]-elbow).dot(axis)),
                  float((points[i]-elbow).dot(lateral)),
                  float((points[i]-elbow).dot(front)), i) for i in supported]
    minimum_t, maximum_t, slice_count = .26, 1.03, 100
    hulls = []
    for station in range(slice_count+1):
        at_t = minimum_t+(maximum_t-minimum_t)*station/slice_count
        rows = [(x, y, i) for distance, x, y, i in projected
                if abs(distance-at_t*length) <= .005]
        hulls.append(convex_hull(rows))
    maximum_support_gap = 0.
    measured_radii = []
    turns = 5
    segments = turns*80
    columns = 12
    vertices, faces, weights, uv, distances = [], [], [], [], []
    for j in range(segments+1):
        s = j/segments
        theta = math.tau*turns*s + sign*.6
        outward = lateral*math.cos(theta)+front*math.sin(theta)
        # A continuous strip, wider than its pitch, overlaps the previous turn.
        center_t = .40+.51*s
        width = .0225*(1+.07*math.sin(theta*.43+1.1))
        for i in range(columns+1):
            u = i/columns
            # Small edge variation reads as handled fabric; never torn spikes.
            edge = .00038*math.sin(theta*3.1+.7)*(abs(2*u-1)**6)
            t = center_t+((u-.5)*width+edge)/length
            center = elbow+(wrist-elbow)*t
            station = (t-minimum_t)/(maximum_t-minimum_t)*slice_count
            if not 0 <= station <= slice_count:
                raise RuntimeError('Cloth extends beyond measured support stations')
            first = min(slice_count-1, int(station)); blend = station-first
            r0, w0 = sample_hull(hulls[first], (math.cos(theta), math.sin(theta)))
            r1, w1 = sample_hull(hulls[first+1], (math.cos(theta), math.sin(theta)))
            radius = r0+(r1-r0)*blend
            if not math.isfinite(radius) or not 0 < radius <= .048:
                raise RuntimeError('Invalid measured cloth radius '+str({'side': side, 'row': j, 'column': i, 'radius': radius}))
            measured_radii.append(radius)
            point = center+outward*radius
            normal = outward
            skin = mix_weights([(vertex, factor*(1-blend)) for vertex, factor in w0]+
                               [(vertex, factor*blend) for vertex, factor in w1])
            nearest, _, _, gap = tree.find_nearest(point)
            if nearest is None or gap > .012:
                raise RuntimeError('Cloth envelope has an unsupported span '+str(gap))
            maximum_support_gap = max(maximum_support_gap, gap)
            if sum(value for name, value in skin if name in allowed) < .97:
                raise RuntimeError('Forearm wrap picked non-forearm support weights')
            # Each overlapping revolution rises1mm, enough for0.6mm fabric.
            stack = .0016+.005*s
            wrinkle = .00032*math.sin(theta*2.7+u*5.2)*math.sin(math.pi*u)**2
            hem = .00035*(math.exp(-((u-.035)/.055)**2)+math.exp(-((u-.965)/.055)**2))
            offset = stack+wrinkle+hem
            vertices.append(tuple(point+normal*offset))
            distances.append(offset)
            weights.append(skin)
            uv.append((s*turns*math.tau*.023/.35, u*width/.35))
    for j in range(segments):
        for i in range(columns):
            k = j*(columns+1)+i
            faces.append((k, k+1, k+columns+2, k+columns+1))
    mesh = bpy.data.meshes.new('Continuous overlapping linen wrap '+side)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(mesh.name, mesh)
    collection.objects.link(obj)
    mesh.materials.append(bpy.data.materials['Nib_Cloth'])
    layer = mesh.uv_layers.new(name='UVMap')
    for loop in mesh.loops:
        layer.data[loop.index].uv = uv[loop.vertex_index]
    for name in sorted({name for row in weights for name, value in row}):
        obj.vertex_groups.new(name=name)
    for vertex, row in enumerate(weights):
        for name, value in row:
            obj.vertex_groups[name].add([vertex], value, 'REPLACE')
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(mesh)
    bm.free()
    # Check the outward shell orientation before adding physical thickness.
    mesh.update()
    oriented = 0
    for polygon in mesh.polygons:
        d = polygon.center-elbow
        radial = d-axis*d.dot(axis)
        oriented += polygon.normal.dot(radial)
    if oriented < 0:
        bm = bmesh.new(); bm.from_mesh(mesh)
        bmesh.ops.reverse_faces(bm, faces=list(bm.faces))
        bm.to_mesh(mesh); bm.free()
    for polygon in mesh.polygons:
        polygon.use_smooth = True
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True); bpy.context.view_layer.objects.active = obj
    solid = obj.modifiers.new('Woven cloth thickness', 'SOLIDIFY')
    solid.thickness = .0006; solid.offset = 0
    bpy.ops.object.modifier_apply(modifier=solid.name)
    obj.parent = rig; obj.matrix_world = Matrix.Identity(4)
    obj['bone'] = 'LowerArm_'+side
    obj['variant'] = 'natural' if side == 'L' else 'all'
    modifier = obj.modifiers.new('Actual supporting forearm weights', 'ARMATURE')
    modifier.object = rig; modifier.use_deform_preserve_volume = False
    archived = []
    for old in legacy:
        archived.append(old.name)
        collection.objects.unlink(old); archive.objects.link(old)
        old.hide_render = True; old.hide_viewport = True
        old.name = 'PRESERVED separate ring '+old.name
    report['wraps'][side] = {'object': obj.name, 'vertices': len(mesh.vertices),
        'triangles': sum(len(poly.vertices)-2 for poly in mesh.polygons),
        'archived': archived, 'turns': turns, 'fabricThicknessMeters': .0006,
        'skinNormalOffsetRangeMeters': [min(distances), max(distances)],
        'support': 'Convex cross-sections of actual forearm/proximal-hand vertices within5mm axial slices; support-edge weight interpolation, at most4 influences',
        'supportSliceCount': slice_count+1,
        'actualSupportRadiusRangeMeters': [min(measured_radii), max(measured_radii)],
        'maximumEnvelopeToActualSkinDistanceMeters': maximum_support_gap,
        'envelopeDistanceLimitMeters': .012,
        'supportTriangles': len(triangles),
        'material': 'Existing Nib_Cloth, no new texture bake'}
select_action(bpy, rig, bpy.data.actions['Idle'])
bpy.context.scene.frame_set(1)
output = a.output/'Nib_ContinuousWraps_Study_v1.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(output), compress=True)
bpy.ops.wm.open_mainfile(filepath=str(output), load_ui=False)
rig = bpy.data.objects['Nib_Rig']
if source_bind != {b.name: [list(row) for row in b.matrix_local] for b in rig.data.bones}:
    raise RuntimeError('Wrap patch changed bind')
if source_actions != actions_digest():
    raise RuntimeError('Wrap patch changed canonical actions')
if any(not bpy.data.actions[name].use_fake_user for name in CLIPS):
    raise RuntimeError('Canonical actions are not retained')
if sha(a.source) != input_sha:
    raise RuntimeError('Wrap patch changed its input source')
report.update({'output': str(output), 'outputSha256': sha(output),
               'reopenedSavedFile': True, 'exactBindPreserved': True,
               'canonicalActionHashes': source_actions})
(a.output/'wrap-fit.json').write_text(json.dumps(report, indent=2)+'\n')
print('NIB_CONTINUOUS_WRAPS_COMPLETE', flush=True)
