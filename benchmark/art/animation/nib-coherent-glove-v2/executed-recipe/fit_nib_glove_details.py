"""Fit the natural left glove's details to its actual anatomical hand surface.

Replaces old floating palmar rivets and the box wrist strap with a conforming
dorsal leather reinforcement, supported rivets, and a coherent wrist band.
Skin weights follow exact supporting triangles; no skeleton/action changes.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).parent))
from export_contract import CLIPS, select_action

p = argparse.ArgumentParser()
p.add_argument('--source', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
p.add_argument('--panel-width', type=float, default=.036)
a = p.parse_args(sys.argv[sys.argv.index('--')+1:])
if not .020 <= a.panel_width <= .050:
    raise ValueError('Dorsal panel width must remain within the authored hand')
if a.output.exists():
    raise RuntimeError('Preserve previous fitted glove source')
a.output.mkdir(parents=True)
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
input_hash = sha(a.source)
bpy.ops.wm.open_mainfile(filepath=str(a.source), load_ui=False)
rig = bpy.data.objects['Nib_Rig']; hand = bpy.data.objects['Nib v5 coherent hand L']
source_bind = {bone.name: [list(row) for row in bone.matrix_local] for bone in rig.data.bones}
source_clips = {name: list(bpy.data.actions[name].frame_range) for name in CLIPS}
collection = bpy.data.collections['Nib_Authored_Components']
select_action(bpy, rig, None)
for track in rig.animation_data.nla_tracks:
    track.mute = True
bpy.context.scene.frame_set(1); bpy.context.view_layer.update()
hand.data.calc_loop_triangles()
points = [hand.matrix_world@v.co for v in hand.data.vertices]
triangles = [tuple(t.vertices) for t in hand.data.loop_triangles]
tree = BVHTree.FromPolygons(points, triangles, all_triangles=True)
group_names = [g.name for g in hand.vertex_groups]


def hit_surface(origin, direction):
    point, normal, index, distance = tree.ray_cast(Vector(origin), Vector(direction), .2)
    if point is None:
        raise RuntimeError('Glove fit missed actual hand surface '+str(tuple(origin)))
    return point, normal, index


def support_weights(point, index):
    ids = triangles[index]
    origin, b, c = [points[i] for i in ids]
    v0, v1, v2 = b-origin, c-origin, point-origin
    aa, ab, bb, pa, pb = v0.dot(v0), v0.dot(v1), v1.dot(v1), v2.dot(v0), v2.dot(v1)
    determinant = aa*bb-ab*ab
    if determinant <= 1e-18:
        raise RuntimeError('Degenerate supporting hand triangle')
    u = (bb*pa-ab*pb)/determinant; v = (aa*pb-ab*pa)/determinant
    bary = [max(0., 1-u-v), max(0., u), max(0., v)]
    total = sum(bary); result = {}
    for vertex, factor in zip(ids, bary):
        for group in hand.data.vertices[vertex].groups:
            name = group_names[group.group]
            result[name] = result.get(name, 0.)+factor/total*group.weight
    ranked = sorted(result.items(), key=lambda row: -row[1])[:4]
    total = sum(value for name, value in ranked)
    return [(name, value/total) for name, value in ranked]


def mesh_object(name, vertices, faces, uv, weights, material, thickness=0):
    mesh = bpy.data.meshes.new(name); mesh.from_pydata(vertices, [], faces); mesh.update()
    obj = bpy.data.objects.new(name, mesh); collection.objects.link(obj)
    mesh.materials.append(material)
    layer = mesh.uv_layers.new(name='UVMap')
    for loop in mesh.loops:
        layer.data[loop.index].uv = uv[loop.vertex_index]
    for name in sorted({name for row in weights for name, value in row}):
        obj.vertex_groups.new(name=name)
    for index, row in enumerate(weights):
        for name, value in row:
            obj.vertex_groups[name].add([index], value, 'REPLACE')
    for face in mesh.polygons:
        face.use_smooth = True
    bpy.ops.object.select_all(action='DESELECT'); obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    if thickness:
        solid = obj.modifiers.new('Actual leather thickness', 'SOLIDIFY')
        solid.thickness = thickness; solid.offset = 1
        bpy.ops.object.modifier_apply(modifier=solid.name)
    obj.parent = rig; obj.matrix_world = Matrix.Identity(4)
    obj['bone'] = 'Hand_L'; obj['variant'] = 'natural'
    modifier = obj.modifiers.new('Portable fitted glove skinning', 'ARMATURE'); modifier.object = rig
    modifier.use_deform_preserve_volume = False
    return obj


archive = bpy.data.collections.new('PRESERVED unfitted left glove details')
bpy.context.scene.collection.children.link(archive); archive.hide_render = True; archive.hide_viewport = True
removed = []
for obj in list(collection.objects):
    if obj.get('bone') == 'Hand_L' and obj.get('variant') == 'natural' and (
            obj.name.startswith('Set rivet') or obj.name == 'Glove wrist strap L'):
        collection.objects.unlink(obj); archive.objects.link(obj)
        obj.hide_render = True; obj.hide_viewport = True
        removed.append(obj.name); obj.name = 'PRESERVED unfitted '+obj.name
if len(removed) != 5:
    raise RuntimeError('Expected four legacy rivets and one box wrist strap; got '+str(removed))
leather = bpy.data.materials['Nib_Leather']; brass = bpy.data.materials['Nib_Brass']
# Rounded rectangle parameterization, smoothly narrowing its top/bottom corners.
vertices, faces, uv, weights = [], [], [], []
width = a.panel_width; height = .018; center_x = .2265; center_z = .586
columns, rows = 20, 10
for j in range(rows+1):
    t = j/rows; inset = .003*(abs(2*t-1)**6)
    for i in range(columns+1):
        s = i/columns
        x = center_x+(s-.5)*(width-2*inset); z = center_z+(t-.5)*height
        point, normal, triangle = hit_surface((x, .04, z), (0, -1, 0))
        if normal.y < .15:
            raise RuntimeError('Dorsal reinforcement hit a non-dorsal surface')
        vertices.append(tuple(point+normal*.0007)); weights.append(support_weights(point, triangle)); uv.append((s, t))
for j in range(rows):
    for i in range(columns):
        k = j*(columns+1)+i; faces.append((k, k+columns+1, k+columns+2, k+1))
panel = mesh_object('Anatomical dorsal glove reinforcement L', vertices, faces, uv, weights, leather, .0007)
# Wrap the whole wrist, fitting every row to the actual hand rather than a box.
vertices, faces, uv, weights = [], [], [], []
for j in range(5):
    z = .607+j*.0025
    for i in range(64):
        angle = math.tau*i/64; outward = Vector((math.cos(angle), math.sin(angle), 0))
        center = Vector((.220, -.040, z))
        point, normal, triangle = hit_surface(center+outward*.09, -outward)
        vertices.append(tuple(point+normal*.0008)); weights.append(support_weights(point, triangle)); uv.append((i/64, j/4))
for j in range(4):
    for i in range(64):
        k = j*64+i; next_i = j*64+(i+1)%64
        faces.append((k, next_i, next_i+64, k+64))
band = mesh_object('Fitted leather wrist band L', vertices, faces, uv, weights, leather, .0011)
rivets = []
for index, (x, z) in enumerate([(center_x-.014, center_z-.004), (center_x+.014, center_z-.004),
                              (center_x-.014, center_z+.004), (center_x+.014, center_z+.004)]):
    point, normal, triangle = hit_surface((x, .04, z), (0, -1, 0))
    basis = normal.to_track_quat('Z', 'Y').to_matrix()
    center = point+normal*.0018
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=6, radius=1)
    obj = bpy.context.object
    for owner in list(obj.users_collection):
        owner.objects.unlink(obj)
    collection.objects.link(obj)
    obj.name = 'Fitted dorsal glove rivet L '+str(index)
    for vertex in obj.data.vertices:
        vertex.co = center+basis@Vector((vertex.co.x*.0012, vertex.co.y*.0012, vertex.co.z*.00055))
    obj.data.materials.append(brass)
    for name, value in support_weights(point, triangle):
        group = obj.vertex_groups.new(name=name); group.add(list(range(len(obj.data.vertices))), value, 'REPLACE')
    obj.parent = rig; obj.matrix_world = Matrix.Identity(4); obj['bone'] = 'Hand_L'; obj['variant'] = 'natural'
    modifier = obj.modifiers.new('Portable supported rivet', 'ARMATURE'); modifier.object = rig
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    rivets.append(obj)
select_action(bpy, rig, bpy.data.actions['Idle']); bpy.context.scene.frame_set(1)
output = a.output/'Nib_FittedGlove_Study_v1.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(output), compress=True)
if sha(a.source) != input_hash:
    raise RuntimeError('Input source changed')
report = {'status': 'Actual fitted left glove details; posed review required',
          'source': str(a.source), 'sourceSha256': input_hash, 'output': str(output),
          'outputSha256': sha(output), 'recipeSha256': sha(Path(__file__)),
          'archivedLegacyDetails': removed,
          'panelWidthMeters': a.panel_width,
          'added': [{'name': obj.name, 'vertices': len(obj.data.vertices)} for obj in [panel, band]+rivets],
          'geometryFit': 'Directional actual-hand triangle rays; barycentric skin-weight transfer',
          'remaining': ['Actual posed contact', 'Right-hand equipment fit', 'Forearm cloth wrap reconstruction'],
          'sharedAssetsChanged': False, 'engineExported': False, 'artisticAcceptance': False}
bpy.ops.wm.open_mainfile(filepath=str(output), load_ui=False)
rig = bpy.data.objects['Nib_Rig']
if source_bind != {bone.name: [list(row) for row in bone.matrix_local] for bone in rig.data.bones}:
    raise RuntimeError('Saved glove source changed skeletal bind')
retained_clips = {}
for name, frames in source_clips.items():
    action = bpy.data.actions.get(name)
    if action is None or not action.use_fake_user or list(action.frame_range) != frames:
        raise RuntimeError('Saved glove source did not retain canonical clip '+name)
    retained_clips[name] = {'frameRange': frames, 'fakeUser': action.use_fake_user}
report['reopenedSavedFile'] = True
report['persistedCanonicalActions'] = retained_clips
(a.output/'glove-fit.json').write_text(json.dumps(report, indent=2)+'\n', newline='\n')
print('NIB_GLOVE_FIT_STUDY_COMPLETE', flush=True)
