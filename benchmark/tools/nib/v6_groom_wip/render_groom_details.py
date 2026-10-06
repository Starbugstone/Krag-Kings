"""Actual saved-mesh ear/back-head views, separate from frozen face review."""
import argparse,hashlib,json,sys
from pathlib import Path
import bpy
from mathutils import Vector

parser=argparse.ArgumentParser()
parser.add_argument('--source',type=Path,required=True)
parser.add_argument('--report',type=Path,required=True)
parser.add_argument('--output-dir',type=Path,required=True)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
source_hash=hashlib.sha256(args.source.read_bytes()).hexdigest()
report=json.loads(args.report.read_text())
if report.get('candidateSha256')!=source_hash:raise RuntimeError('Groom source/report mismatch')
if not report.get('preRenderGate',{}).get('passed'):raise RuntimeError('Unresolved source face gate')
bpy.ops.wm.open_mainfile(filepath=str(args.source),load_ui=False)
scene=bpy.context.scene;rig=bpy.data.objects['Nib_Rig'];camera=scene.camera
rig.animation_data.action=bpy.data.actions['Idle'];scene.frame_set(1)
collection=bpy.data.collections['Nib_Authored_Components']
for obj in collection.objects:
    visible=obj.get('variant','all') in ['all','natural','organic']
    obj.hide_set(not visible);obj.hide_render=not visible
ear=next(o for o in collection.objects if o.name.startswith('Fennec cupped ear ') and o.get('bone')=='Ear_L')
points=[ear.matrix_world@v.co for v in ear.data.vertices]
center=sum(points,Vector())/len(points)
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=32
scene.cycles.use_denoising=True;scene.cycles.transparent_max_bounces=16
scene.render.threads_mode='FIXED';scene.render.threads=4
scene.render.resolution_x=1200;scene.render.resolution_y=1200;scene.render.resolution_percentage=100
camera.data.type='ORTHO';args.output_dir.mkdir(parents=True,exist_ok=True)
views=[('EarInner',center+Vector((.10,-1.6,.08)),center,.40),
       ('EarOuter',center+Vector((.15,1.6,.10)),center,.40),
       ('BackHead',Vector((0,2.4,1.23)),Vector((0,0,1.17)),.72)]
for name,position,target,scale in views:
    camera.location=position;camera.rotation_euler=(target-position).to_track_quat('-Z','Y').to_euler()
    camera.data.ortho_scale=scale
    path=args.output_dir/('Nib_Groom_'+name+'.png');scene.render.filepath=str(path)
    bpy.ops.render.render(write_still=True)
    metadata={'source':str(args.source),'sourceSha256':source_hash,'view':name,'action':'Idle','frame':1,
              'cameraPosition':list(position),'cameraTarget':list(target),'orthoScale':scale,
              'renderer':'Blender Cycles CPU','samples':32,'status':'Actual geometry review; no artistic acceptance'}
    path.with_name(path.name+'.json').write_text(json.dumps(metadata,indent=2)+'\n',newline='\n')
if hashlib.sha256(args.source.read_bytes()).hexdigest()!=source_hash:raise RuntimeError('Read-only render changed source')
print('NIB_GROOM_DETAIL_REVIEW_COMPLETE',flush=True)
