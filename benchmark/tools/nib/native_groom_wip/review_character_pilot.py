"""Read-only actual native groom image, with explicit pilot/control visibility."""
import argparse,json,sys
from pathlib import Path
import bpy
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
from strand_contract import sha
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--report',type=Path,required=True)
p.add_argument('--output-dir',type=Path,required=True);p.add_argument('--view',choices=['Neutral','Profile'],required=True)
p.add_argument('--control-cards',action='store_true');a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
report=json.loads(a.report.read_text());source_sha=sha(a.source)
if report['candidateSha256']!=source_sha or not report['savedSourceReopened']:raise RuntimeError('Require actual saved native source receipt')
image=a.output_dir/(a.view+('-ControlCards'if a.control_cards else'')+'.png');metadata=image.with_suffix('.json')
if image.exists()or metadata.exists():raise RuntimeError('Preserve previous native groom view')
a.output_dir.mkdir(parents=True,exist_ok=True);bpy.ops.wm.open_mainfile(filepath=str(a.source),load_ui=False)
scene=bpy.context.scene;rig=bpy.data.objects['Nib_Rig'];camera=scene.camera;hidden={x['name']for x in report['hiddenControlGroom']}
for track in rig.animation_data.nla_tracks:track.mute=True
for obj in bpy.data.collections['Nib_Authored_Components'].objects:
    show=obj.get('variant','all')in ['all','natural','organic']
    if obj.name in hidden:show=show and a.control_cards
    obj.hide_render=not show;obj.hide_set(not show)
for obj in bpy.data.collections['Nib_Native_Groom_Pilot'].objects:obj.hide_render=a.control_cards;obj.hide_set(a.control_cards)
for obj in bpy.data.collections['Nib_Native_Groom_Attachment'].objects:obj.hide_render=True;obj.hide_set(False)
rig.animation_data.action=bpy.data.actions['Idle'];scene.frame_set(1);bpy.context.view_layer.update()
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.render.threads_mode='FIXED';scene.render.threads=4
scene.cycles.samples=24;scene.cycles.use_denoising=True;scene.cycles.transparent_max_bounces=16
scene.render.resolution_x=1400;scene.render.resolution_y=1100;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.use_sequencer=False
target=Vector((0,-.005,1.17));camera.data.type='ORTHO';camera.data.ortho_scale=.69
camera.location=(.35,-3,1.33)if a.view=='Neutral'else target+Vector((3,0,.015))
camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(image)
bpy.ops.render.render(write_still=True)
if sha(a.source)!=source_sha:raise RuntimeError('Read-only groom review changed source')
metadata.write_text(json.dumps({'status':'Actual native character groom diagnostic; unaccepted','sourceSha256':source_sha,
    'sourceReportSha256':sha(a.report),'view':a.view,'controlCards':a.control_cards,'curveCount':0 if a.control_cards else report['curveCount'],
    'action':'Idle','frame':1,'renderer':'Cycles CPU','samples':24,'dimensions':[1400,1100],
    'imageSha256':sha(image),'recipeSha256':sha(Path(__file__)),'artisticAcceptance':False,'engineImported':False,'sharedChanged':False},indent=2)+'\n',newline='\n')
print('NIB_NATIVE_GROOM_ACTUAL_VIEW_COMPLETE',flush=True)
