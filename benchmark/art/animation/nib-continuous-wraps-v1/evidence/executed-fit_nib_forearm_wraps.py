"""Replace separated forearm rings with surface-fitted, overlapping cloth strips.

Works on a saved coherent source and preserves all skeleton/actions. Original
rings remain archived. Geometry follows actual anatomical body triangles;
weights transfer barycentrically with at most four influences. Native neutral
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
body.data.calc_loop_triangles()
points = [body.matrix_world@v.co for v in body.data.vertices]
triangles = [tuple(t.vertices) for t in body.data.loop_triangles]
tree = BVHTree.FromPolygons(points, triangles, all_triangles=True)
group_names = [g.name for g in body.vertex_groups]


def fit_ray(origin, direction):
    point, normal, index, distance = tree.ray_cast(origin, direction, .24)
    if point is None:
        raise RuntimeError('Wrap fit missed body '+str(list(origin)))
    ids = triangles[index]
    aa, bb, cc = [points[i] for i in ids]
    v0, v1, v2 = bb-aa, cc-aa, point-aa
    d00, d01, d11 = v0.dot(v0), v0.dot(v1), v1.dot(v1)
    denom = d00*d11-d01*d01
    if denom <= 1e-18:
        raise RuntimeError('Degenerate support triangle')
    u = (d11*v2.dot(v0)-d01*v2.dot(v1))/denom
    v = (d00*v2.dot(v1)-d01*v2.dot(v0))/denom
    bary = [max(0., 1-u-v), max(0., u), max(0., v)]
    total = sum(bary)
    weights = {}
    for vertex, factor in zip(ids, bary):
        for g in body.data.vertices[vertex].groups:
            name = group_names[g.group]
            weights[name] = weights.get(name, 0.)+g.weight*factor/total
    ranked = sorted(weights.items(), key=lambda item: -item[1])[:4]
    total = sum(w for name, w in ranked)
    if total <= 1e-8:
        raise RuntimeError('Wrap hit unweighted anatomy')
    return point, normal, [(name, w/total) for name, w in ranked]


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
            point, normal, skin = fit_ray(center+outward*.10, -outward)
            if normal.dot(outward) < .25 or (point-center).length > .048:
                raise RuntimeError('Wrap support is outside the actual forearm domain')
            allowed = {'LowerArm_'+side, 'ForearmTwist_'+side, 'Hand_'+side}
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
        'support': 'Actual body triangle rays with barycentric skin weights; at most4 influences',
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
