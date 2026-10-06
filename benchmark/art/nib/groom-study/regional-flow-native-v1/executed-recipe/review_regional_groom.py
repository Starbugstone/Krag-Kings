"""Prepared actual regional groom views; no beauty or acceptance substitution."""
import argparse,hashlib,json,sys
from pathlib import Path
import bpy
from mathutils import Vector
parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,required=True);parser.add_argument('--report',type=Path,required=True);parser.add_argument('--output-dir',type=Path,required=True);parser.add_argument('--view',choices=['Neutral','EarDetail','Back'],required=True)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:]);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();source_sha=sha(args.source);report=json.loads(args.report.read_text())
if report['candidateSha256']!=source_sha or not report['savedSourceReopened']:raise RuntimeError('Actual saved matching source required')
args.output_dir.mkdir(parents=True,exist_ok=True);image=args.output_dir/(args.view+'.png');metadata=args.output_dir/(args.view+'.json')
if image.exists()or metadata.exists():raise RuntimeError('Preserve previous actual view')
bpy.ops.wm.open_mainfile(filepath=str(args.source),load_ui=False);scene=bpy.context.scene;rig=bpy.data.objects['Nib_Rig'];camera=scene.camera
for track in rig.animation_data.nla_tracks:track.mute=True
for obj in bpy.data.collections['Nib_Authored_Components'].objects:
    visible=obj.get('variant','all')in['all','natural','organic'];obj.hide_set(not visible);obj.hide_render=not visible
rig.animation_data.action=bpy.data.actions['Idle'];scene.frame_set(1);bpy.context.view_layer.update()
scene.render.engine='CYCLES';scene.render.threads_mode='FIXED';scene.render.threads=4;scene.cycles.device='CPU';scene.cycles.samples=24;scene.cycles.use_denoising=True
scene.render.resolution_x=1400;scene.render.resolution_y=1100;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.render.use_sequencer=False
camera.data.type='ORTHO';camera.data.ortho_scale=.69;target=Vector((0,-.005,1.17));camera.location=(.35,-3,1.33)
if args.view=='EarDetail':
    ear=next(o for o in bpy.data.collections['Nib_Authored_Components'].objects if o.name.startswith('Fennec cupped ear ')and o.get('bone')=='Ear_L')
    evaluated=ear.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=evaluated.to_mesh();points=[evaluated.matrix_world@v.co for v in mesh.vertices]
    target=Vector(tuple((min(p[i]for p in points)+max(p[i]for p in points))*.5 for i in range(3)));evaluated.to_mesh_clear()
    camera.location=target+Vector((.72,-3,.14));camera.data.ortho_scale=.36;scene.render.resolution_x=1400;scene.render.resolution_y=1200
elif args.view=='Back':camera.location=target+Vector((.20,3,.10))
camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(image);bpy.ops.render.render(write_still=True)
result={'status':'Actual source groom image; regional coverage, roots and adult concept comparison required','source':str(args.source),'sourceSha256':source_sha,'sourceReportSha256':sha(args.report),'view':args.view,'action':'Idle','frame':1,'imageSha256':sha(image),'scriptSha256':sha(Path(__file__)),
 'earPose':{n:[list(r)for r in rig.pose.bones[n].matrix]for n in ['Ear_L','Ear_R','EarTip_L','EarTip_R']},'render':{'engine':'Cycles CPU','samples':24,'width':scene.render.resolution_x,'height':scene.render.resolution_y},'preRenderGate':report['preRenderGate'],'artisticAcceptance':False,'sharedChanged':False}
if sha(args.source)!=source_sha:raise RuntimeError('Review altered source')
metadata.write_text(json.dumps(result,indent=2)+'\n',newline='\n');print('NIB_REGIONAL_GROOM_ACTUAL_VIEW_COMPLETE',flush=True)
