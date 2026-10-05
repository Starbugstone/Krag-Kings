"""Verify standalone animation FBXs against imported natural-variant skeleton binding."""
import bpy,json,math,hashlib,argparse,sys
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--directory',type=Path);ap.add_argument('--report-tag',default='');opt=ap.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
ROOT=Path(__file__).resolve().parents[3];OUT=opt.directory or ROOT/'benchmark/shared/characters/krag';ART=ROOT/'benchmark/art/krag'
manifest=json.loads((OUT/'manifest.json').read_text());errors=[];results={}
def angular_error(a,b):
    x=a.to_quaternion();y=b.to_quaternion();dot=sum(float(x[i])*float(y[i]) for i in range(4));norm=math.sqrt(sum(float(v)*float(v) for v in x)*sum(float(v)*float(v) for v in y));return math.degrees(2*math.acos(min(1,abs(dot)/norm)))
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(OUT/'Krag_Natural.fbx'),use_anim=False)
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
reference={b.name:(rig.matrix_world@b.matrix_local).copy() for b in rig.data.bones}
for clip,relative in manifest['animations'].items():
    bpy.ops.wm.read_factory_settings(use_empty=True);path=OUT/relative;bpy.ops.import_scene.fbx(filepath=str(path),use_anim=True);rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
    missing=sorted(set(reference)-set(rig.data.bones.keys()));position_error=0;rotation_error=0
    for bone in rig.data.bones:
        if bone.name not in reference:continue
        a=reference[bone.name];b=rig.matrix_world@bone.matrix_local;position_error=max(position_error,(a.translation-b.translation).length);rotation_error=max(rotation_error,angular_error(a,b))
    if missing:errors.append(clip+' missing bones '+str(missing))
    if position_error>1e-4 or rotation_error>.05:errors.append(clip+' incompatible bind transform')
    print('BIND CHECK',clip,'position',position_error,'rotation',rotation_error,'actions',[a.name for a in bpy.data.actions],flush=True)
    action=next((a for a in bpy.data.actions if a.name==clip or a.name.endswith('|'+clip) or a.name.endswith(clip)),next(iter(bpy.data.actions),None))
    if not action:errors.append(clip+' missing action');continue
    rig.animation_data_create();rig.animation_data.action=action
    if action.slots:rig.animation_data.action_slot=action.slots[0]
    lo,hi=action.frame_range
    controls=[p for p in rig.pose.bones if p.name=='FaceRoot' or any(q.name=='FaceRoot' for q in p.parent_recursive)];samples={p.name:[] for p in controls}
    for k in range(17):
        bpy.context.scene.frame_set(round(lo+(hi-lo)*k/16));bpy.context.view_layer.update()
        for p in controls:samples[p.name].append((p.matrix_basis.to_quaternion().angle,p.matrix_basis.translation.length))
    varying=[n for n,values in samples.items() if max(v[0] for v in values)-min(v[0] for v in values)>1e-5 or max(v[1] for v in values)-min(v[1] for v in values)>1e-6]
    if not varying:errors.append(clip+' missing facial motion')
    result=dict(file=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),bones=len(rig.data.bones),maxBindPositionErrorMeters=position_error,maxBindRotationErrorDegrees=rotation_error,missingBones=missing,frameRange=[lo,hi],fps=bpy.context.scene.render.fps,varyingFacialControls=varying)
    results[clip]=result;print('ANIMATION VALIDATED',clip,json.dumps(result),flush=True)
report=dict(structuralValidationPassed=not errors,errors=errors,clips=results,artisticAcceptance=False)
(ART/('standalone-animation-roundtrip'+('-'+opt.report_tag if opt.report_tag else '')+'.json')).write_text(json.dumps(report,indent=2),newline='\n')
if errors:raise RuntimeError('; '.join(errors))
