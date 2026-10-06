"""Create an isolated digit-only refinement; preserve all other payloads."""
import argparse
import hashlib
import json
import sys
from pathlib import Path
import bpy
from bpy_extras.anim_utils import action_get_channelbag_for_slot

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path[:0] = [str(HERE), str(HERE.parent), str(ROOT / 'tools/nib/restorative_wip')]
from contracts import rig_contract, surface_hash
from export_contract import CLIPS, select_action
import morph_drivers
import pose_refinement

p = argparse.ArgumentParser()
p.add_argument('--source', type=Path, required=True)
p.add_argument('--source-sha256', required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args(sys.argv[sys.argv.index('--') + 1:])

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

assert sha(a.source) == a.source_sha256, 'Pinned source changed'
assert not a.output.exists(), 'Preserve previous candidate'
a.output.mkdir(parents=True)
bpy.ops.wm.open_mainfile(filepath=str(a.source), load_ui=False)
rig = bpy.data.objects['Krag_Rig']
scene = bpy.context.scene
before = rig_contract(rig)
surfaces = {o.name: surface_hash(o) for o in bpy.data.objects if o.type == 'MESH'}
drivers = morph_drivers.contract(bpy.data.objects['BioForearm_L'].data.shape_keys)
digits = [f'Finger{s}_{d}_L' for d in range(4) for s in range(1, 4)] + ['Thumb1_L', 'Thumb2_L']
paths = {rig.pose.bones[n].path_from_id() + '.' + c for n in digits for c in
         ('location', 'rotation_euler', 'rotation_quaternion', 'rotation_axis_angle', 'scale')}

def other_curves(action):
    select_action(bpy, rig, action)
    bag = action_get_channelbag_for_slot(action, rig.animation_data.action_slot)
    values = [(c.data_path, c.array_index, c.extrapolation,
               [(tuple(k.co), tuple(k.handle_left), tuple(k.handle_right), k.interpolation,
                 k.handle_left_type, k.handle_right_type, k.easing, k.amplitude, k.back, k.period)
                for k in c.keyframe_points]) for c in bag.fcurves if c.data_path not in paths]
    return hashlib.sha256(json.dumps(sorted(values), separators=(',', ':')).encode()).hexdigest()

for track in rig.animation_data.nla_tracks:
    track.mute = True
clips = {}
for name in CLIPS:
    original = bpy.data.actions[name]
    stable = other_curves(original)
    original.name = 'Preserved_' + name + '_BeforeHandConvergence'
    original.use_fake_user = True
    action = original.copy()
    action.name = name
    action.use_fake_user = True
    select_action(bpy, rig, action)
    bag = action_get_channelbag_for_slot(action, rig.animation_data.action_slot)
    for curve in list(bag.fcurves):
        if curve.data_path in paths:
            bag.fcurves.remove(curve)
    start, end = map(round, action.frame_range)
    for frame in range(start, end + 1):
        scene.frame_set(frame)
        changed = pose_refinement.apply(rig, name, (frame - start) / max(1, end - start))
        for bone in changed:
            rig.pose.bones[bone].keyframe_insert('rotation_euler', frame=frame, group=bone)
    for curve in bag.fcurves:
        if curve.data_path in paths:
            for key in curve.keyframe_points:
                key.interpolation = 'LINEAR'
    assert other_curves(action) == stable, 'Unrelated animation changed: ' + name
    clips[name] = {'frameRange': [start, end], 'nonDigitCurvesSha256': stable}
after = rig_contract(rig)
assert after['bones'] == before['bones'], 'Bind changed'
for name, digest in surfaces.items():
    assert surface_hash(bpy.data.objects[name]) == digest, 'Mesh changed: ' + name
assert morph_drivers.contract(bpy.data.objects['BioForearm_L'].data.shape_keys) == drivers
select_action(bpy, rig, bpy.data.actions['Idle'])
scene.frame_set(1)
output = a.output / 'Krag_ConvergentHand_v2.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(output), compress=True)
bpy.ops.wm.open_mainfile(filepath=str(output), load_ui=False)
assert rig_contract(bpy.data.objects['Krag_Rig']) == after, 'Saved rig/action mismatch'
for name, digest in surfaces.items():
    assert surface_hash(bpy.data.objects[name]) == digest, 'Saved surface mismatch: ' + name
assert morph_drivers.contract(bpy.data.objects['BioForearm_L'].data.shape_keys) == drivers
assert sha(a.source) == a.source_sha256
report = {'sourceSha256': a.source_sha256, 'outputSha256': sha(output), 'output': str(output),
          'savedSourceReopened': True, 'allMeshPayloadsPreserved': len(surfaces),
          'allBindBonesPreserved': len(after['bones']), 'correctiveDriversPreserved': len(drivers),
          'clips': clips, 'preparedPoseProposals': 'Digit adduction and full-fist MCP/PIP/DIP 76/90/49 degrees; two-bone thumb opposition toward index/middle PIP region with12mm pad offset.',
          'visualReviewCompleted': False, 'artisticAcceptance': False, 'sharedChanged': False,
          'recipeHashes': {q.name: sha(q) for q in (Path(__file__), Path(pose_refinement.__file__), HERE / 'morph_drivers.py')}}
(a.output / 'action-refinement.json').write_text(json.dumps(report, indent=2) + '\n', newline='\n')
print('KRAG_CONVERGENT_HAND_SAVED_AND_REOPENED', flush=True)
