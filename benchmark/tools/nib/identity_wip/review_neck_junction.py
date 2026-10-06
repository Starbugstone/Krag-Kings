"""Read-only matched neck correction views; inherited face/cloth defects retained."""
import argparse,hashlib,json,sys
from pathlib import Path
import bpy
from mathutils import Vector

parser=argparse.ArgumentParser()
parser.add_argument('--source',type=Path,required=True)
parser.add_argument('--report',type=Path,required=True)
parser.add_argument('--output-dir',type=Path,required=True)
parser.add_argument('--view',choices=['Neutral','Profile','ThreeQuarter','Blink','Tongue','EyeCloseup'],required=True)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source_sha=sha(args.source);report=json.loads(args.report.read_text())
if report.get('candidateSha256')!=source_sha or not report.get('savedSourceReopened'):
    raise RuntimeError('Require actual saved/reopened candidate with matching report')
args.output_dir.mkdir(parents=True,exist_ok=True)
image=args.output_dir/(args.view+'.png');metadata=args.output_dir/(args.view+'.json')
if image.exists() or metadata.exists():raise RuntimeError('Preserve the preceding actual diagnostic view')
bpy.ops.wm.open_mainfile(filepath=str(args.source),load_ui=False)
scene=bpy.context.scene;rig=bpy.data.objects['Nib_Rig'];camera=scene.camera
for track in rig.animation_data.nla_tracks:track.mute=True
for obj in bpy.data.collections['Nib_Authored_Components'].objects:
    show=obj.get('variant','all') in ['all','natural','organic'];obj.hide_set(not show);obj.hide_render=not show
action,frame=('FacePerformance',16 if args.view=='Blink' else 103) if args.view in ['Blink','Tongue'] else ('Idle',1)
rig.animation_data.action=bpy.data.actions[action];scene.frame_set(frame);bpy.context.view_layer.update()
scene.render.engine='CYCLES';scene.render.threads_mode='FIXED';scene.render.threads=4
scene.cycles.device='CPU';scene.cycles.samples=24;scene.cycles.use_denoising=True
scene.render.resolution_x=1400;scene.render.resolution_y=1100;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.use_sequencer=False
camera.data.type='ORTHO';camera.data.ortho_scale=.69;camera.location=(.35,-3,1.33);target=Vector((0,-.005,1.17))
if args.view=='Profile':camera.location=target+Vector((3,0,.015))
if args.view=='ThreeQuarter':camera.location=target+Vector((1.8,-3,.12))
if args.view=='EyeCloseup':
    target=(rig.matrix_world@rig.pose.bones['Eye_L'].head+rig.matrix_world@rig.pose.bones['Eye_R'].head)*.5
    camera.location=target+Vector((.12,-3,.08));camera.data.ortho_scale=.18
    scene.render.resolution_x=1500;scene.render.resolution_y=900
camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
scene.render.filepath=str(image);bpy.ops.render.render(write_still=True)
head=bpy.data.objects['Nib v5 fitted animation face']
shapes={k.name:float(k.value) for k in head.data.shape_keys.key_blocks if k.name!='Basis'}
result={'status':'Actual diagnostic mesh image; normal/oral warnings retained and artistic acceptance pending',
    'source':str(args.source),'sourceSha256':source_sha,'sourceReportSha256':sha(args.report),
    'view':args.view,'action':action,'frame':frame,'headMorphValues':shapes,
    'headHasCustomNormals':bool(head.data.has_custom_normals),
    'headMaterialNames':[m.name for m in head.data.materials],
    'preRenderGate':report['preRenderGate'],'neckActualPosedSeam':report['actualPosedSeam'],
    'render':{'engine':'Cycles CPU','samples':24,'width':scene.render.resolution_x,'height':scene.render.resolution_y},
    'imageSha256':sha(image),'scriptSha256':sha(Path(__file__)),'artisticAcceptance':False,'sharedChanged':False}
if sha(args.source)!=source_sha:raise RuntimeError('Read-only diagnostic render altered input')
metadata.write_text(json.dumps(result,indent=2)+'\n',newline='\n')
print('NIB_NECK_JUNCTION_ACTUAL_VIEW_COMPLETE',flush=True)
