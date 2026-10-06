"""Fit original licensed hand topology using digit domains before deformation.

The prior fit blended nearby finger transforms through empty space. This fresh
source retains the current bone bindings and clips but derives shape and skin
from connected original digit domains. It needs actual rest and action review.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).parent))
import hand_skin_domains
from export_contract import select_action
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'tools/nib/v5_wip'))
from nib_hand_v5 import SOURCE_CHAINS

parser = argparse.ArgumentParser()
parser.add_argument('--source', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
if args.output.exists():
    raise RuntimeError('Preserve previous hand-fit source')
args.output.mkdir(parents=True)
library = ROOT/'art/reference-anatomy/blender-studio-human-base-meshes/source/human-base-meshes-bundle-v1.4.1/human_base_meshes_bundle.blend'
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
inputs = {str(path): sha(path) for path in [args.source, library]}
bpy.ops.wm.open_mainfile(filepath=str(args.source), load_ui=False)
rig = bpy.data.objects['Nib_Rig']
collection = bpy.data.collections['Nib_Authored_Components']
bind_before = {b.name: [list(row) for row in b.matrix_local] for b in rig.data.bones}
select_action(bpy, rig, None)
for track in rig.animation_data.nla_tracks:
    track.mute = True
bpy.context.scene.frame_set(1); bpy.context.view_layer.update()
old = bpy.data.objects['Nib v5 coherent hand L']
if old.data.shape_keys:
    raise RuntimeError('Existing hand morphs need an explicit transfer before replacement')
materials = list(old.data.materials)
with bpy.data.libraries.load(str(library), link=False) as (available, requested):
    requested.objects = ['Hand  - Realistic']
hand = requested.objects[0]
for owner in list(hand.users_collection):
    owner.objects.unlink(hand)
collection.objects.link(hand)
hand.parent = None; hand.matrix_parent_inverse = Matrix.Identity(4); hand.matrix_world = Matrix.Identity(4)
hand.modifiers.clear(); hand.vertex_groups.clear(); hand.data.materials.clear()
for material in materials:
    hand.data.materials.append(material)
points = np.array([v.co[:] for v in hand.data.vertices])
faces = [list(p.vertices) for p in hand.data.polygons]
domains, field_report = hand_skin_domains.solve(points, faces, source_cage=True)
names, weights, weight_report = hand_skin_domains.weights(points, domains, SOURCE_CHAINS,
                                                          joint_half_width=.008)
mapped = np.zeros_like(points)
transforms = {}
for index, name in enumerate(names):
    if name == 'Hand_L':
        candidate = np.column_stack([.227-(points[:, 0]-.008)*.43,
                                     -.043-points[:, 1]*.43, .610+points[:, 2]*.39])
    else:
        digit = next(d for d in hand_skin_domains.DIGITS if name.startswith(d))
        segment = int(name[len(digit):].split('_')[0])-1
        a, b = [Vector(v) for v in SOURCE_CHAINS[digit][segment:segment+2]]
        target = rig.data.bones[name]
        source_axis = (b-a).normalized()
        pre = Matrix.Diagonal(Vector((-1, -1, 1)))
        turn = (pre@source_axis).rotation_difference((target.tail_local-target.head_local).normalized()).to_matrix()
        axis = np.array(source_axis); offset = points-np.array(a)
        along = (offset@axis)[:, None]*axis
        across = offset-along
        candidate = (along*(target.length/(b-a).length)+across*.43) @ np.array(turn@pre).T+np.array(target.head_local)
        transforms[name] = {'sourceHead': list(a), 'sourceTail': list(b),
                            'targetHead': list(target.head_local), 'targetTail': list(target.tail_local)}
    mapped += candidate*weights[:, index, None]
hand.data.vertices.foreach_set('co', np.asarray(mapped, dtype=np.float32).ravel())
for name in names:
    hand.vertex_groups.new(name=name)
for vertex, row in enumerate(weights):
    for index in np.flatnonzero(row > 1e-8):
        hand.vertex_groups[int(index)].add([vertex], float(row[index]), 'REPLACE')
original = hand.data.attributes.new('Nib_OriginalHandCoordinate', 'FLOAT_VECTOR', 'POINT')
original.data.foreach_set('vector', np.asarray(points, dtype=np.float32).ravel())
for index, digit in enumerate(hand_skin_domains.DIGITS+['Palm']):
    attribute = hand.data.attributes.new('Nib_HandDomain_'+digit, 'FLOAT', 'POINT')
    attribute.data.foreach_set('value', np.asarray(domains[:, index], dtype=np.float32))
for polygon in hand.data.polygons:
    z = float(points[list(polygon.vertices), 2].mean())
    x = float(points[list(polygon.vertices), 0].mean())
    polygon.material_index = 1 if z > -.123 and not (x > .063 and z < -.073) else 0
    polygon.use_smooth = True
bm = bmesh.new(); bm.from_mesh(hand.data)
bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces)); bm.to_mesh(hand.data); bm.free()
bpy.ops.object.select_all(action='DESELECT'); hand.select_set(True)
bpy.context.view_layer.objects.active = hand
sub = hand.modifiers.new('Coherent anatomical hand surface', 'SUBSURF'); sub.levels = 2
bpy.ops.object.modifier_apply(modifier=sub.name)
rows = []
for vertex in hand.data.vertices:
    row = sorted([(hand.vertex_groups[g.group].name, g.weight) for g in vertex.groups if g.weight > 1e-8],
                 key=lambda entry: -entry[1])[:4]
    total = sum(value for name, value in row)
    if total < 1e-8:
        raise RuntimeError('Unweighted fitted hand vertex')
    rows.append([(name, value/total) for name, value in row])
hand.vertex_groups.clear()
for name in names:
    hand.vertex_groups.new(name=name)
for index, row in enumerate(rows):
    for name, value in row:
        hand.vertex_groups[name].add([index], value, 'REPLACE')
archive = bpy.data.collections.new('PRESERVED prior Nib hand fit')
bpy.context.scene.collection.children.link(archive); archive.hide_render = True; archive.hide_viewport = True
collection.objects.unlink(old); archive.objects.link(old)
old.hide_render = True; old.hide_viewport = True; old.name = 'PRESERVED before domain fit '+old.name
hand.name = 'Nib v5 coherent hand L'; hand.parent = rig
hand['bone'] = 'Hand_L'; hand['variant'] = 'natural'
armature = hand.modifiers.new('Portable Nib hand skinning', 'ARMATURE'); armature.object = rig
armature.use_deform_preserve_volume = False
if bind_before != {b.name: [list(row) for row in b.matrix_local] for b in rig.data.bones}:
    raise RuntimeError('Hand fit changed existing skeletal bind')
select_action(bpy, rig, bpy.data.actions['Idle']); bpy.context.scene.frame_set(1)
output = args.output/'Nib_HandFit_Study_v1.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(output), compress=True)
if any(sha(Path(path)) != expected for path, expected in inputs.items()):
    raise RuntimeError('Input source changed')
report = {'status': 'Actual isolated left-hand fit; visual/contact review required',
          'inputs': inputs, 'output': str(output), 'outputSha256': sha(output),
          'recipeSha256': sha(Path(__file__)), 'domainRecipeSha256': sha(Path(hand_skin_domains.__file__)),
          'sourceCageVertices': len(points), 'sourceCageFaces': len(faces),
          'outputVertices': len(hand.data.vertices), 'outputFaces': len(hand.data.polygons),
          'harmonicDomains': field_report, 'weightLimits': weight_report,
          'digitTransforms': transforms, 'bindPreserved': True, 'actionsChanged': False,
          'referenceLicense': 'CC0; see art/reference-anatomy/blender-studio-human-base-meshes/source.json',
          'sharedAssetsChanged': False, 'engineExported': False, 'artisticAcceptance': False}
(args.output/'hand-fit.json').write_text(json.dumps(report, indent=2)+'\n', newline='\n')
print('NIB_HAND_FIT_STUDY_COMPLETE', flush=True)
