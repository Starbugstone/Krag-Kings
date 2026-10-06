"""Combine reviewed motion and revised art only when their bind contracts match.

Keeps an editable fresh output, preserves replaced actions, and verifies actual
evaluated skeletal poses after appending the seven canonical actions. Geometry,
UVs, skin weights, morph coordinates, and material assignments must stay exact.
No engine assets are written. Render the combined source before exporting it.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy
import numpy as np
from bpy_extras.anim_utils import action_get_channelbag_for_slot

sys.path.insert(0, str(Path(__file__).parent))
from export_contract import CLIPS, select_action

parser = argparse.ArgumentParser()
parser.add_argument('--art-source', type=Path, required=True)
parser.add_argument('--motion-source', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
if args.output.exists():
    raise RuntimeError('Preserve previous integrated source')
args.output.mkdir(parents=True)
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
inputs = {str(path): sha(path) for path in [args.art_source, args.motion_source]}


def current_rig():
    rigs = [obj for obj in bpy.data.objects
            if obj.type == 'ARMATURE' and 'Pelvis' in obj.data.bones]
    if len(rigs) != 1:
        raise RuntimeError('Expected exactly one character rig')
    rig = rigs[0]
    for track in rig.animation_data.nla_tracks:
        track.mute = True
    if rig.constraints or any(bone.constraints for bone in rig.pose.bones):
        raise RuntimeError('Constraint-driven rig requires a separate bake/merge review')
    return rig


def bind_contract(rig):
    return {'world': [list(row) for row in rig.matrix_world],
            'bones': {bone.name: {'matrix': [list(row) for row in bone.matrix_local],
                                 'parent': bone.parent.name if bone.parent else None,
                                 'connected': bone.use_connect,
                                 'rotationMode': rig.pose.bones[bone.name].rotation_mode}
                      for bone in rig.data.bones}}


def action_digest(rig, action):
    select_action(bpy, rig, action)
    bag = action_get_channelbag_for_slot(action, rig.animation_data.action_slot)
    if bag is None:
        raise RuntimeError('Missing action channel bag')
    curves = []
    for curve in bag.fcurves:
        if curve.modifiers:
            raise RuntimeError('Action modifiers require explicit merge validation')
        curves.append((curve.data_path, curve.array_index, curve.extrapolation,
                       [(tuple(key.co), tuple(key.handle_left), tuple(key.handle_right),
                         key.interpolation, key.handle_left_type, key.handle_right_type,
                         key.easing, key.amplitude, key.back, key.period)
                        for key in curve.keyframe_points]))
    payload = {'frameRange': list(action.frame_range), 'curves': sorted(curves)}
    return hashlib.sha256(json.dumps(payload, separators=(',', ':')).encode()).hexdigest()


def geometry_digest():
    result = {}
    for obj in bpy.data.objects:
        if obj.type != 'MESH':
            continue
        digest = hashlib.sha256()
        coordinates = np.empty(len(obj.data.vertices)*3, dtype=np.float32)
        obj.data.vertices.foreach_get('co', coordinates)
        digest.update(coordinates.tobytes())
        for key in obj.data.shape_keys.key_blocks if obj.data.shape_keys else []:
            digest.update(key.name.encode())
            key.data.foreach_get('co', coordinates)
            digest.update(coordinates.tobytes())
        for layer in obj.data.uv_layers:
            values = np.empty(len(layer.data)*2, dtype=np.float32)
            layer.data.foreach_get('uv', values)
            digest.update(layer.name.encode()); digest.update(values.tobytes())
        payload = {'faces': [(list(p.vertices), p.material_index) for p in obj.data.polygons],
                   'groups': [g.name for g in obj.vertex_groups],
                   'weights': [[(g.group, g.weight) for g in v.groups] for v in obj.data.vertices],
                   'materials': [m.name if m else None for m in obj.data.materials],
                   'world': [list(row) for row in obj.matrix_world]}
        digest.update(json.dumps(payload, separators=(',', ':')).encode())
        result[obj.name] = digest.hexdigest()
    return result


bpy.ops.wm.open_mainfile(filepath=str(args.motion_source), load_ui=False)
rig = current_rig()
motion_bind = bind_contract(rig)
fps = bpy.context.scene.render.fps
fps_base = bpy.context.scene.render.fps_base
metadata = {name: bpy.context.scene[name]
            for name in ['locomotion_contract', 'retargeted_motion_generation']}
expected = {}
for name in CLIPS:
    action = bpy.data.actions[name]
    digest = action_digest(rig, action)
    first, last = action.frame_range
    samples = []
    for phase in np.linspace(0, 1, 17):
        frame = first+(last-first)*float(phase)
        bpy.context.scene.frame_set(math.floor(frame), subframe=frame-math.floor(frame))
        bpy.context.view_layer.update()
        samples.append({'frame': frame,
                        'matrices': {bone.name: [list(row) for row in bone.matrix]
                                     for bone in rig.pose.bones}})
    expected[name] = {'curvesSha256': digest, 'samples': samples}

bpy.ops.wm.open_mainfile(filepath=str(args.art_source), load_ui=False)
rig = current_rig()
if bind_contract(rig) != motion_bind:
    raise RuntimeError('Art and motion must have exactly matching bind/hierarchy/rotation modes')
before = geometry_digest()
archived = {}
for name in CLIPS:
    old = bpy.data.actions.get(name)
    if old:
        old.name = 'PRESERVED pre-motion integration '+name
        old.use_fake_user = True
        archived[name] = old.name
select_action(bpy, rig, None)
with bpy.data.libraries.load(str(args.motion_source), link=False) as (available, loaded):
    if any(name not in available.actions for name in CLIPS):
        raise RuntimeError('Motion library missing canonical action')
    loaded.actions = list(CLIPS)
scene = bpy.context.scene
scene.render.fps = fps
scene.render.fps_base = fps_base
for name, value in metadata.items():
    scene[name] = value
results = {}
for name in CLIPS:
    action = bpy.data.actions[name]
    if action_digest(rig, action) != expected[name]['curvesSha256']:
        raise RuntimeError('Appended action curves changed '+name)
    maximum = 0.
    for sample in expected[name]['samples']:
        at = sample['frame']
        scene.frame_set(math.floor(at), subframe=at-math.floor(at))
        bpy.context.view_layer.update()
        maximum = max(maximum, max(abs(rig.pose.bones[n].matrix[i][j]-matrix[i][j])
                                  for n, matrix in sample['matrices'].items()
                                  for i in range(4) for j in range(4)))
    if maximum > 2e-6:
        raise RuntimeError('Combined rig pose differs from motion source '+name)
    results[name] = {'curvesSha256': expected[name]['curvesSha256'],
                     'sampleCount': 17, 'maximumRigMatrixElementDifference': maximum}
select_action(bpy, rig, bpy.data.actions['Idle'])
scene.frame_set(int(bpy.data.actions['Idle'].frame_range[0]))
bpy.context.view_layer.update()
if before != geometry_digest():
    raise RuntimeError('Motion integration changed art geometry/UVs/weights/material assignments')
if bind_contract(rig) != motion_bind:
    raise RuntimeError('Motion integration changed bind')
output = args.output/(args.art_source.stem+'_IntegratedMotion.blend')
bpy.ops.wm.save_as_mainfile(filepath=str(output), compress=True)
if any(sha(Path(path)) != value for path, value in inputs.items()):
    raise RuntimeError('An input source changed')
report = {'status': 'Actual combined source; posed art and engine review pending',
          'inputs': inputs, 'output': str(output), 'outputSha256': sha(output),
          'recipeSha256': sha(Path(__file__)), 'preservedMeshComponents': len(before),
          'geometryDigests': before, 'exactBindPreserved': True,
          'boneCount': len(rig.data.bones), 'archivedActions': archived,
          'clips': results, 'sharedAssetsChanged': False, 'engineExported': False,
          'artisticAcceptance': False}
(args.output/'integration.json').write_text(json.dumps(report, indent=2)+'\n', newline='\n')
print('KRAG_KINGS_MOTION_INTEGRATION_COMPLETE', flush=True)
