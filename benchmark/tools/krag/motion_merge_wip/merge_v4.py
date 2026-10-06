"""Merge verified whole-body takes into an unchanged oral-art source.

The 72-bone hand study is deliberately excluded. The complete v4 actions
already contain facial timing matched to their new cadence and six-second
Idle, so no old short face cycle is spliced onto the longer body take.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import bpy
import numpy as np
from bpy_extras.anim_utils import action_get_channelbag_for_slot

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path[:0] = [str(HERE.parents[1]/'animation'),
               str(HERE.parents[1]/'animation/krag_hand_rebuild'),
               str(HERE.parents[1]/'nib/restorative_wip')]
from export_contract import CLIPS, select_action
from contracts import surface_hash
from morph_drivers import contract as driver_contract

DONOR = ROOT/'benchmark/art/animation/krag-human-motion-v4/Krag_HumanMotion_Study_v4.blend'
DONOR_SHA = '84822444a021194fc47e0360bfffc875c18687720bb8b8923588e486b9900607'
parser = argparse.ArgumentParser()
source_group = parser.add_mutually_exclusive_group(required=True)
source_group.add_argument('--source-receipt', type=Path)
source_group.add_argument('--source', type=Path)
parser.add_argument('--source-sha256')
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
if args.source_receipt:
    source_record = json.loads(args.source_receipt.read_text())['source']
    source = ROOT/source_record['path']
    source_sha = source_record['sha256']
else:
    source, source_sha = args.source, args.source_sha256
if not source_sha or sha(source) != source_sha or sha(DONOR) != DONOR_SHA:
    raise RuntimeError('Pinned art or movement source changed')
if args.output.exists():
    raise RuntimeError('Preserve prior actual merged source')


def rig_object():
    rigs = [o for o in bpy.data.objects if o.type == 'ARMATURE' and 'Pelvis' in o.data.bones]
    if len(rigs) != 1:
        raise RuntimeError('Expected exactly one character armature')
    return rigs[0]


def bind_contract(rig):
    return {'world': [list(row) for row in rig.matrix_world],
            'bones': {b.name: {'matrix': [list(row) for row in b.matrix_local],
                               'parent': b.parent.name if b.parent else None,
                               'connected': b.use_connect,
                               'rotationMode': rig.pose.bones[b.name].rotation_mode}
                      for b in rig.data.bones}}


def action_contract(rig, action):
    select_action(bpy, rig, action)
    bag = action_get_channelbag_for_slot(action, rig.animation_data.action_slot)
    if bag is None:
        raise RuntimeError('Missing canonical rig channel bag '+action.name)
    rows = [(c.data_path, c.array_index, c.extrapolation,
             [(tuple(k.co), tuple(k.handle_left), tuple(k.handle_right),
               k.interpolation, k.handle_left_type, k.handle_right_type,
               k.easing, k.amplitude, k.back, k.period)
              for k in c.keyframe_points]) for c in bag.fcurves]
    return hashlib.sha256(json.dumps({'frames': list(action.frame_range),
                                     'curves': sorted(rows)}, separators=(',', ':')).encode()).hexdigest()


def sample_actions(rig):
    result = {}
    for clip in CLIPS:
        action = bpy.data.actions[clip]
        select_action(bpy, rig, action)
        first, last = action.frame_range
        samples = []
        for phase in [0, .25, .5, .75, 1]:
            at = first+(last-first)*phase
            bpy.context.scene.frame_set(int(at), subframe=at-int(at))
            bpy.context.view_layer.update()
            samples.append({name: np.asarray(rig.pose.bones[name].matrix, float).tolist()
                            for name in sorted(rig.data.bones.keys())})
        result[clip] = samples
    return result


def surfaces():
    return {o.name: surface_hash(o) for o in bpy.data.objects if o.type == 'MESH'}


def drivers():
    return {o.name: driver_contract(o.data.shape_keys)
            for o in bpy.data.objects if o.type == 'MESH' and o.data.shape_keys}


bpy.ops.wm.open_mainfile(filepath=str(DONOR), load_ui=False)
rig = rig_object()
for track in rig.animation_data.nla_tracks:
    track.mute = True
donor_bind = bind_contract(rig)
if len(donor_bind['bones']) != 68:
    raise RuntimeError('This merge is pinned to the original 68-bone whole-body study')
donor_actions = {name: action_contract(rig, bpy.data.actions[name]) for name in CLIPS}
donor_samples = sample_actions(rig)
scene = bpy.context.scene
fps, fps_base = scene.render.fps, scene.render.fps_base
metadata = {key: scene[key] for key in ['locomotion_contract', 'retargeted_motion_generation']}
durations = {name: (bpy.data.actions[name].frame_range[1]-bpy.data.actions[name].frame_range[0])/(fps/fps_base)
             for name in CLIPS}
if abs(durations['Idle']-6.) > 1e-7:
    raise RuntimeError('Pinned movement donor lacks its six-second Idle')

bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False)
rig = rig_object()
original_bind = bind_contract(rig)
if original_bind != donor_bind:
    raise RuntimeError('Full body/facial bind or rotation modes differ; scoped retarget required')
original_surfaces, original_drivers = surfaces(), drivers()
original_action_hashes = {name: action_contract(rig, bpy.data.actions[name]) for name in CLIPS}
for track in rig.animation_data.nla_tracks:
    track.mute = True
select_action(bpy, rig, None)
for name in CLIPS:
    old = bpy.data.actions[name]
    old.name = 'Preserved_'+name+'_BeforeVerifiedV4Merge'
    old.use_fake_user = True
with bpy.data.libraries.load(str(DONOR), link=False) as (available, requested):
    if any(name not in available.actions for name in CLIPS):
        raise RuntimeError('Movement donor is missing a canonical take')
    requested.actions = list(CLIPS)
for name, action in zip(CLIPS, requested.actions):
    if action is None or action.name != name:
        raise RuntimeError('Imported movement action name conflict '+name)
    action.use_fake_user = True
    if action_contract(rig, action) != donor_actions[name]:
        raise RuntimeError('Imported action curves differ from verified donor '+name)
scene = bpy.context.scene
scene.render.fps, scene.render.fps_base = fps, fps_base
for key, value in metadata.items():
    scene[key] = value
scene['krag_art_motion_merge'] = 'Whole-body v4 merged onto '+source.name+'; no hand-study migration'
if surfaces() != original_surfaces or drivers() != original_drivers or bind_contract(rig) != original_bind:
    raise RuntimeError('Movement merge changed current art, morph drivers or bind')
select_action(bpy, rig, bpy.data.actions['Idle'])
scene.frame_set(1)
text = bpy.data.texts.new('VerifiedWholeBodyMergeV4/merge_v4.py')
text.write(Path(__file__).read_text())
args.output.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(args.output), compress=True)
bpy.ops.wm.open_mainfile(filepath=str(args.output), load_ui=False)
rig = rig_object()
for track in rig.animation_data.nla_tracks:
    track.mute = True
if bind_contract(rig) != original_bind or surfaces() != original_surfaces or drivers() != original_drivers:
    raise RuntimeError('Saved/reopened merged art or corrective drivers changed')
for name in CLIPS:
    if action_contract(rig, bpy.data.actions[name]) != donor_actions[name]:
        raise RuntimeError('Saved/reopened canonical motion differs '+name)
actual_samples = sample_actions(rig)
sample_errors = {}
for name in CLIPS:
    error = max(float(np.abs(np.asarray(actual_samples[name][i][bone])-
                             np.asarray(donor_samples[name][i][bone])).max())
                for i in range(5) for bone in donor_bind['bones'])
    if error > 2e-6:
        raise RuntimeError('Merged skeletal pose differs from v4 '+name+': '+str(error))
    sample_errors[name] = error
if sha(source) != source_sha or sha(DONOR) != DONOR_SHA:
    raise RuntimeError('Input source changed during merge')
result = {'status': 'Actual verified whole-body motion merged; art and engine review remain required',
          'artisticAcceptance': False, 'sharedPromotion': False,
          'source': {'path': source.relative_to(ROOT).as_posix(), 'sha256': source_sha},
          'motionDonor': {'path': DONOR.relative_to(ROOT).as_posix(), 'sha256': DONOR_SHA},
          'output': {'path': args.output.relative_to(ROOT).as_posix(), 'sha256': sha(args.output)},
          'fullBindExactlyMatched': True, 'bindBoneCount': len(original_bind['bones']),
          'unchangedMeshesMorphsWeightsUVs': original_surfaces,
          'unchangedCorrectiveDriverContracts': original_drivers,
          'preMergeCanonicalActionHashes': original_action_hashes,
          'verifiedCanonicalActionHashes': donor_actions,
          'actionDurationsSeconds': durations,
          'fiveSamplesPerActionMaximumMatrixError': sample_errors,
          'locomotion': json.loads(metadata['locomotion_contract']),
          'savedReopened': True, 'hand72StudyIncluded': False,
          'pending': ['Actual merged body/face review', 'Runtime material/export/import checks',
                      'Normal-mouth, silhouette, clothing and hand artistry remain unaccepted'],
          'recipeHashes': {p.name: sha(p) for p in [Path(__file__),
                           HERE.parents[1]/'animation/export_contract.py',
                           HERE.parents[1]/'animation/krag_hand_rebuild/morph_drivers.py',
                           HERE.parents[1]/'nib/restorative_wip/contracts.py']}}
args.output.with_suffix('.json').write_text(json.dumps(result, indent=2)+'\n', newline='\n')
print('KRAG_VERIFIED_V4_MERGE_COMPLETE', flush=True)
