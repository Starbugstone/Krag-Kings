import bpy,json,sys,argparse,hashlib
from pathlib import Path
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
ap=argparse.ArgumentParser();ap.add_argument('--tag',default='');ap.add_argument('--view',default='Natural_Front');ap.add_argument('--variant',default='Krag_Natural');ap.add_argument('--runtime',action='store_true');ap.add_argument('--keep-pose',action='store_true');ap.add_argument('--show-weapon',action='store_true');ap.add_argument('--clip',default='Idle');ap.add_argument('--frame',type=int,default=1);ap.add_argument('--source',type=Path);ap.add_argument('--contract',type=Path);opt=ap.parse_args(args)
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[3];ART=ROOT/'benchmark/art/krag';OUT=ROOT/'benchmark/shared/characters/krag'
source_path=opt.source or ART/('Krag_Runtime.blend' if opt.runtime else 'Krag_Master.blend');source_sha=hashlib.sha256(source_path.read_bytes()).hexdigest();bpy.ops.wm.open_mainfile(filepath=str(source_path))
scene=bpy.context.scene;cam=scene.camera;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=16;scene.render.resolution_x=1000;scene.render.resolution_y=1000
contract=json.loads((opt.contract or OUT/'krag_asset_contract.json').read_text());rig=bpy.data.objects['Krag_Rig'];rig.animation_data.action=bpy.data.actions[opt.clip];scene.frame_set(opt.frame)
if not opt.runtime and not opt.keep_pose and opt.clip=='Idle':
    rig.animation_data.action=None
    for pb in rig.pose.bones:
        if pb.name.startswith('Finger') or pb.name.startswith('Thumb'):pb.rotation_euler=(0,0,0)
    bpy.context.view_layer.update()
for o in bpy.data.objects:
    if o.type=='MESH' and 'module'in o:o.hide_render=o['module'] in contract['variants'][opt.variant]['off'] and not((opt.runtime or opt.show_weapon) and o['module']=='Weapon_R')
for name,pos,target,scale in [('Natural_Front',(0,-6,1.3),(0,0,1.06),2.38),('Natural_Head',(1.1,-4,2.05),(0,-.02,1.9),.53),('Natural_Side',(6,0,1.4),(0,0,1.08),2.4),('Natural_Back',(0,6,1.5),(0,0,1.08),2.4),('Natural_LeftHand',(2.2,-3,1.15),(.625,-.055,.90),.46),('Natural_RightGrip',(-2.2,-3,1.15),(-.605,-.065,.85),.60)]:
    if name!=opt.view:continue
    if opt.clip=='Shoot':
        for o in bpy.data.objects:
            if o.get('module')=='Weapon_R':o.hide_render=False
    cam.location=pos;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale;scene.render.filepath=str(ART/'renders'/('Krag_'+name+('_Runtime' if opt.runtime else '')+('_'+opt.clip if opt.clip!='Idle' else '')+('_'+opt.tag if opt.tag else '')+'.png'));bpy.ops.render.render(write_still=True)
    Path(scene.render.filepath).with_suffix('.meta.json').write_text(json.dumps({'source_file':str(source_path),'source_sha256':source_sha,'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'generation':opt.tag,'view':name,'variant':opt.variant,'clip':opt.clip,'frame':opt.frame,'keepAuthoredPose':opt.keep_pose,'showWeapon':opt.show_weapon,'engine':scene.render.engine,'samples':scene.cycles.samples,'status':'Actual mesh WIP; not accepted'},indent=2),newline='\n')
    print('REVIEW SAVED',name,flush=True)
