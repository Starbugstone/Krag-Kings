"""Isolated action-only repair; preserves the input master and every mesh."""
import argparse, hashlib, json, sys
from pathlib import Path
import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(Path(__file__).resolve().parent))
import krag_weapon_pose

arguments=sys.argv[sys.argv.index('--')+1:]
parser=argparse.ArgumentParser()
parser.add_argument('--source',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
parser.add_argument('--report',type=Path,required=True)
options=parser.parse_args(arguments)
if options.source.resolve()==options.output.resolve():raise ValueError('Must preserve the source master')
source_hash=hashlib.sha256(options.source.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(options.source))
scene=bpy.context.scene;rig=bpy.data.objects['Krag_Rig'];action=bpy.data.actions['Shoot']
rig.animation_data.action=action
modifier_states=[]
for obj in bpy.data.objects:
    for modifier in obj.modifiers:
        if modifier.type=='ARMATURE':
            modifier_states.append((modifier,modifier.show_viewport));modifier.show_viewport=False
samples=[]
for frame in range(1,32):
    scene.frame_set(frame);t=(frame-1)/30
    aim=min(t/.22,1)*(1-max(0,(t-.78)/.22))
    kick=max(0,1-abs(t-.40)/.065)+.70*max(0,1-abs(t-.58)/.055)
    for name in ['UpperArm_R','LowerArm_R','Hand_R']:
        rig.pose.bones[name].rotation_euler=(0,0,0)
    result=krag_weapon_pose.pose(rig,aim,kick)
    for name in ['UpperArm_R','LowerArm_R','Hand_R']:
        rig.pose.bones[name].keyframe_insert('rotation_euler',frame=frame,group=name)
    samples.append({'frame':frame,**result})
    if aim>.999 and result['dotIntendedDirection']<.9999:
        raise AssertionError('Solved muzzle does not match firing direction')
    if result['wristErrorMeters']>1e-5:raise AssertionError('Solved wrist failed target')
for modifier,state in modifier_states:modifier.show_viewport=state
rig.animation_data.action=bpy.data.actions['Idle'];scene.frame_set(1)
for name in ['fix_krag_aim.py','krag_weapon_pose.py']:
    text=bpy.data.texts.get(name) or bpy.data.texts.new(name)
    text.clear();text.write(Path(__file__).with_name(name).read_text())
options.output.parent.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(options.output),compress=True)
receipt={'source':str(options.source),'sourceSha256':source_hash,
    'output':str(options.output),'outputSha256':hashlib.sha256(options.output.read_bytes()).hexdigest(),
    'status':'Actual rig-space aim correction; source mesh and grip review still required; artistic acceptance false',
    'changed':'Shoot action UpperArm_R, LowerArm_R and Hand_R local rotation tracks only',
    'samples':samples}
options.report.write_text(json.dumps(receipt,indent=2)+'\n',newline='\n')
print('KRAG_AIM_CORRECTION_COMPLETE',flush=True)
