"""Actual Blender FBX roundtrip of corrected Shoot markers and bind transforms."""
import argparse,hashlib,json,math,sys
from pathlib import Path
import bpy
from mathutils import Vector

parser=argparse.ArgumentParser();parser.add_argument('--directory',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(args.directory/'Krag_Natural.fbx'),use_anim=False)
reference_rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
reference={b.name:(reference_rig.matrix_world@b.matrix_local).copy() for b in reference_rig.data.bones}
bpy.ops.wm.read_factory_settings(use_empty=True)
path=args.directory/'animations/Shoot.fbx';bpy.ops.import_scene.fbx(filepath=str(path),use_anim=True)
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
if set(rig.data.bones.keys())!=set(reference):raise AssertionError('Standalone bone set differs')
position_error=0.;rotation_error=0.
for bone in rig.data.bones:
    a=reference[bone.name];b=rig.matrix_world@bone.matrix_local
    position_error=max(position_error,(a.translation-b.translation).length)
    dot=abs(a.to_quaternion().normalized().dot(b.to_quaternion().normalized()))
    rotation_error=max(rotation_error,math.degrees(2*math.acos(min(1,dot))))
if position_error>1e-5 or rotation_error>.05:raise AssertionError('Standalone bind changed')
action=next(a for a in bpy.data.actions if a.name=='Shoot' or a.name.endswith('|Shoot'))
rig.animation_data_create();rig.animation_data.action=action
if action.slots:rig.animation_data.action_slot=action.slots[0]
lo,hi=action.frame_range;samples=[]
for i in range(31):
    frame=lo+(hi-lo)*i/30;bpy.context.scene.frame_set(int(frame),subframe=frame-int(frame));bpy.context.view_layer.update()
    t=i/30;aim=min(t/.22,1)*(1-max(0,(t-.78)/.22))
    kick=max(0,1-abs(t-.40)/.065)+.70*max(0,1-abs(t-.58)/.055)
    muzzle=rig.matrix_world@rig.pose.bones['WeaponMuzzle'].head
    endpoint=rig.matrix_world@rig.pose.bones['WeaponAim'].head
    direction=(endpoint-muzzle).normalized();intended=Vector((0,-1,.07*kick)).normalized()
    dot=direction.dot(intended)
    samples.append({'normalizedTime':t,'importedFrame':frame,'muzzleWorldMeters':list(muzzle),
                    'direction':list(direction),'aimWeight':aim,'dotIntendedDirection':dot})
    if aim>.999 and dot<.9999:raise AssertionError('Roundtripped weapon direction failed '+str(samples[-1]))
report={'file':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'actualBlenderRoundtripPassed':True,'bindPositionMaxErrorMeters':position_error,
        'bindRotationMaxErrorDegrees':rotation_error,'bones':len(rig.data.bones),
        'samples':samples,'status':'Bind and actual imported aim verified; render/grip acceptance recorded separately',
        'artisticAcceptance':False}
args.output.write_text(json.dumps(report,indent=2)+'\n',newline='\n')
print('KRAG_AIM_ROUNDTRIP_PASSED',flush=True)
