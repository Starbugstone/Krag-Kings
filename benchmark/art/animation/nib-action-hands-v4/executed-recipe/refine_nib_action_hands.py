"""Isolated action-hand candidate on the actual fitted Nib hand.

Keeps the evaluated arm/weapon paths, body/facial/ear curves and all mesh/bind
data. Replaces only natural left-digit rotation curves in three action takes.
The contact poses are provisional until actual closeups have been inspected.
The stronger melee flexion still needs actual skin/contact review. Optional
thumb fitting is a separate prepared proposal; executed recipes are preserved
beside their source evidence.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy
from bpy_extras.anim_utils import action_get_channelbag_for_slot

sys.path.insert(0, str(Path(__file__).parent))
from export_contract import CLIPS, select_action
import nib_anatomical_hand_pose as hand_pose

parser = argparse.ArgumentParser()
parser.add_argument('--source', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--all-clips', action='store_true')
parser.add_argument('--generation', default='v1')
parser.add_argument('--fist-thumb-contact', action='store_true')
args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
if args.output.exists():
    raise RuntimeError('Preserve previous action-hand candidate')
args.output.mkdir(parents=True)
if args.fist_thumb_contact:
    import fist_thumb_contact
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
input_hash = sha(args.source)
bpy.ops.wm.open_mainfile(filepath=str(args.source), load_ui=False)
rig = bpy.data.objects['Nib_Rig']
source_bind = {b.name: [list(row) for row in b.matrix_local] for b in rig.data.bones}
scene = bpy.context.scene
for track in rig.animation_data.nla_tracks:
    track.mute = True
visibility = {o.name: o.hide_viewport for o in bpy.data.objects if o.type == 'MESH'}
for name in visibility:
    bpy.data.objects[name].hide_viewport = True
digits = [name for name in rig.pose.bones.keys() if name.endswith('_L') and
          name.startswith(('Index', 'Middle', 'Ring', 'Little', 'Thumb'))]
paths = {rig.pose.bones[name].path_from_id()+'.rotation_euler' for name in digits}


def untouched_curves(action, slot):
    rows = []
    for curve in action_get_channelbag_for_slot(action, slot).fcurves:
        if curve.data_path in paths:
            continue
        rows.append((curve.data_path, curve.array_index,
                     [(list(k.co), list(k.handle_left), list(k.handle_right),
                       k.interpolation, k.handle_left_type, k.handle_right_type)
                      for k in curve.keyframe_points]))
    return hashlib.sha256(json.dumps(sorted(rows), sort_keys=True).encode()).hexdigest()


report = {'source': str(args.source), 'sourceSha256': input_hash,
          'recipeSha256': sha(Path(__file__)),
          'handPoseRecipeSha256': sha(Path(hand_pose.__file__)),
          'status': 'Actual action-hand candidate; contact/visual review pending',
          'sharedAssetsChanged': False, 'engineExported': False,
          'artisticAcceptance': False, 'clips': {}}
specs = {
    'Shoot': {'angles': {'Index': (25, 75, 35), 'Middle': (28, 78, 38),
                         'Ring': (30, 80, 40), 'Little': (33, 82, 40)},
              'thumb': (12, 18), 'opposition': 25},
    'Melee': {'angles': {name: (82, 98, 55) for name in hand_pose.RELAXED},
              'thumb': (18, 25), 'opposition': 32},
    'Hit': {'angles': {name: (30, 40, 18) for name in hand_pose.RELAXED},
            'thumb': (10, 14), 'opposition': 18},
}
if args.all_clips:
    for clip in ['Idle', 'Walk', 'FacePerformance']:
        specs[clip] = {'angles': hand_pose.RELAXED, 'thumb': (5, 8), 'opposition': 12}
    specs['Run'] = {'angles': {'Index': (45, 65, 25), 'Middle': (50, 65, 25),
                              'Ring': (52, 65, 28), 'Little': (55, 68, 28)},
                    'thumb': (8, 10), 'opposition': 20}
for clip, spec in specs.items():
    original = bpy.data.actions[clip]
    select_action(bpy, rig, original)
    old_slot = rig.animation_data.action_slot
    untouched_before = untouched_curves(original, old_slot)
    original.name = 'PRESERVED pre-anatomical-hand '+clip
    original.use_fake_user = True
    action = original.copy()
    action.name = clip
    action.use_fake_user = True
    select_action(bpy, rig, action)
    bag = action_get_channelbag_for_slot(action, rig.animation_data.action_slot)
    first, last = action.frame_range
    for curve in list(bag.fcurves):
        if curve.data_path in paths:
            bag.fcurves.remove(curve)
    samples = []
    for frame in range(round(first), round(last)+1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        t = (frame-first)/(last-first)
        if clip == 'Shoot':
            amount = min(1., t/.20, (1-t)/.22)
            amount = amount*amount*(3-2*amount)
        elif clip == 'Melee':
            # Close during anticipation, retain the fist through impact, then release.
            amount = min(1., t/.20, (1-t)/.22)
            amount = amount*amount*(3-2*amount)
        elif clip == 'Hit':
            amount = math.sin(t/.20*math.pi/2) if t < .20 else (1-t)/.8
        else:
            amount = 1.
        angles = {name: tuple(a+(b-a)*amount for a, b in zip(rest, spec['angles'][name]))
                  for name, rest in hand_pose.RELAXED.items()}
        thumb = tuple(a+(b-a)*amount for a, b in zip((5, 8), spec['thumb']))
        changed = hand_pose.pose(rig, angles, thumb, 12+(spec['opposition']-12)*amount)
        thumb_contact = (fist_thumb_contact.pose(rig, amount)
                         if args.fist_thumb_contact and clip == 'Melee' else None)
        for name in changed:
            rig.pose.bones[name].keyframe_insert('rotation_euler', frame=frame, group=name)
        samples.append({'frame': frame, 'amount': amount,
                        'thumbContact': thumb_contact,
                        'fingertips': {name: list(rig.pose.bones[name+'3_L'].tail)
                                      for name in hand_pose.RELAXED}})
    for curve in bag.fcurves:
        if curve.data_path in paths:
            for key in curve.keyframe_points:
                key.interpolation = 'LINEAR'
    untouched_after = untouched_curves(action, rig.animation_data.action_slot)
    if untouched_before != untouched_after:
        raise RuntimeError('Non-hand action curves changed '+clip)
    report['clips'][clip] = {'target': spec, 'samples': samples,
                              'bodyFaceEarWeaponCurvesPreserved': True,
                              'untouchedCurvesSha256': untouched_after}
for name, hidden in visibility.items():
    bpy.data.objects[name].hide_viewport = hidden
select_action(bpy, rig, bpy.data.actions['Idle'])
scene.frame_set(1)
output = args.output/f'Nib_ActionHands_Study_{args.generation}.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(output))
report['output'] = str(output)
report['outputSha256'] = sha(output)
bpy.ops.wm.open_mainfile(filepath=str(output), load_ui=False)
rig = bpy.data.objects['Nib_Rig']
if source_bind != {b.name: [list(row) for row in b.matrix_local] for b in rig.data.bones}:
    raise RuntimeError('Saved action source changed skeletal bind')
persisted = {}
for name in CLIPS:
    action = bpy.data.actions.get(name)
    if action is None or not action.use_fake_user:
        raise RuntimeError('Saved action source lost canonical take '+name)
    select_action(bpy, rig, action)
    if name in report['clips']:
        digest = untouched_curves(action, rig.animation_data.action_slot)
        if digest != report['clips'][name]['untouchedCurvesSha256']:
            raise RuntimeError('Saved action source altered non-hand curves '+name)
    persisted[name] = list(action.frame_range)
report['reopenedSavedFile'] = True
report['persistedCanonicalActions'] = persisted
if args.fist_thumb_contact:
    report['fistThumbContactRecipeSha256'] = sha(Path(fist_thumb_contact.__file__))
if sha(args.source) != input_hash:
    raise RuntimeError('Action authoring changed input source')
(args.output/'action-hands.json').write_text(json.dumps(report, indent=2)+'\n')
print('NIB_ACTION_HANDS_COMPLETE', flush=True)
