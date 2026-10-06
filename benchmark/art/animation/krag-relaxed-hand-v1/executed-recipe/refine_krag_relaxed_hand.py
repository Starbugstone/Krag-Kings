"""Apply isolated free-hand controls, preserving geometry and non-hand curves."""
import argparse, hashlib, json, sys
from pathlib import Path
import bpy
from bpy_extras.anim_utils import action_get_channelbag_for_slot

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent/'nib/restorative_wip')]
from contracts import rig_contract, surface_hash
from export_contract import CLIPS, select_action
import krag_relaxed_hand_pose

p=argparse.ArgumentParser()
p.add_argument('--source', type=Path, required=True)
p.add_argument('--source-sha256', required=True)
p.add_argument('--output', type=Path, required=True)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
if sha(a.source)!=a.source_sha256:raise RuntimeError('Pinned input changed')
if a.output.exists():raise RuntimeError('Preserve previous hand study')
a.output.mkdir(parents=True)
bpy.ops.wm.open_mainfile(filepath=str(a.source),load_ui=False)
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE' and 'Pelvis' in o.data.bones)
scene=bpy.context.scene
before=rig_contract(rig)
meshes={o.name:surface_hash(o) for o in bpy.data.objects if o.type=='MESH'}
for track in rig.animation_data.nla_tracks:track.mute=True
names=[n for n in rig.pose.bones.keys() if n.endswith('_L') and n.startswith(('Finger','Thumb'))]
paths={rig.pose.bones[n].path_from_id()+'.rotation_euler' for n in names}

def untouched(action):
    select_action(bpy,rig,action)
    bag=action_get_channelbag_for_slot(action,rig.animation_data.action_slot)
    rows=[(c.data_path,c.array_index,c.extrapolation,
           [(tuple(k.co),tuple(k.handle_left),tuple(k.handle_right),k.interpolation,
             k.handle_left_type,k.handle_right_type,k.easing,k.amplitude,k.back,k.period)
            for k in c.keyframe_points]) for c in bag.fcurves if c.data_path not in paths]
    return hashlib.sha256(json.dumps(sorted(rows),separators=(',',':')).encode()).hexdigest()

clips={}
for clip in ['Idle','Walk','Run']:
    old=bpy.data.actions[clip];stable=untouched(old)
    old.name='Preserved_'+clip+'_BeforeRelaxedHand';old.use_fake_user=True
    action=old.copy();action.name=clip;action.use_fake_user=True
    select_action(bpy,rig,action)
    bag=action_get_channelbag_for_slot(action,rig.animation_data.action_slot)
    for curve in list(bag.fcurves):
        if curve.data_path in paths:bag.fcurves.remove(curve)
    first,last=map(round,action.frame_range);samples=[]
    for frame in range(first,last+1):
        scene.frame_set(frame)
        changed,report=krag_relaxed_hand_pose.pose(rig,clip)
        for name in changed:rig.pose.bones[name].keyframe_insert('rotation_euler',frame=frame,group=name)
        samples.append({'frame':frame,**report})
    for curve in bag.fcurves:
        if curve.data_path in paths:
            for key in curve.keyframe_points:key.interpolation='LINEAR'
    if untouched(action)!=stable:raise RuntimeError('Non-hand curves changed '+clip)
    clips[clip]={'samples':samples,'nonHandCurvesSha256':stable}
for name in CLIPS:bpy.data.actions[name].use_fake_user=True
expected=rig_contract(rig)
if before['bones']!=expected['bones']:raise RuntimeError('Hand pose altered bind')
for name in ['Melee','Shoot','Hit','FacePerformance']:
    if before['actions'][name]!=expected['actions'][name]:raise RuntimeError('Unrelated take changed '+name)
select_action(bpy,rig,bpy.data.actions['Idle']);scene.frame_set(1)
output=a.output/'Krag_RelaxedHand_v1.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(output),compress=True)
bpy.ops.wm.open_mainfile(filepath=str(output),load_ui=False)
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE' and 'Pelvis' in o.data.bones)
if rig_contract(rig)!=expected:raise RuntimeError('Saved rig/action payload changed')
for name,digest in meshes.items():
    if surface_hash(bpy.data.objects[name])!=digest:raise RuntimeError('Saved mesh changed '+name)
if sha(a.source)!=a.source_sha256:raise RuntimeError('Input changed')
report={'source':str(a.source),'sourceSha256':a.source_sha256,'output':str(output),
        'outputSha256':sha(output),'savedSourceReopened':True,'bindAndGeometryPreserved':True,
        'unchangedMeshComponents':len(meshes),'canonicalTakes':list(CLIPS),'clips':clips,
        'recipeHashes':{p.name:sha(p) for p in [Path(__file__),Path(krag_relaxed_hand_pose.__file__)]},
        'artisticAcceptance':False,'engineExported':False,'sharedAssetsChanged':False}
(a.output/'relaxed-hand.json').write_text(json.dumps(report,indent=2)+'\n')
print('KRAG_RELAXED_HAND_SAVED_AND_REOPENED',flush=True)
