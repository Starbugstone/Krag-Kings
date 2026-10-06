"""Fast actual-mesh review, including close-up and posed silhouettes."""
import bpy, math, sys, json, hashlib, argparse
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[3]
ART=ROOT/'benchmark/art/nib'
parser=argparse.ArgumentParser()
parser.add_argument('--source',type=Path,default=ART/'Nib_Master.blend')
parser.add_argument('--output-dir',type=Path,default=ART/'renders')
parser.add_argument('--coordinate-report',type=Path,help='Require a matching saved-source structural pre-render gate')
parser.add_argument('views',nargs='*',default=['Perspective','Face'])
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
SOURCE=args.source;RENDER_OUT=args.output_dir;RENDER_OUT.mkdir(parents=True,exist_ok=True)
if args.coordinate_report:
    gate_report=json.loads(args.coordinate_report.read_text())
    if gate_report.get('candidateSha256')!=hashlib.sha256(SOURCE.read_bytes()).hexdigest():raise RuntimeError('Coordinate report does not match this saved source')
    if not gate_report.get('preRenderGate',{}).get('passed',False):raise RuntimeError('Saved source has unresolved pre-render structural blockers: '+str(gate_report.get('preRenderGate')))
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
report_path=ART/'source-report.json'
if report_path.exists() and SOURCE.resolve()==(ART/'Nib_Master.blend').resolve():
    report=json.loads(report_path.read_text())
    if not report.get('nativeCompressed',False):
        report['priorUncompressedSha256']=report['sourceSha256']
        bpy.ops.wm.save_as_mainfile(filepath=str(ART/'Nib_Master.blend'),compress=True)
        report['sourceSha256']=hashlib.sha256((ART/'Nib_Master.blend').read_bytes()).hexdigest();report['nativeCompressed']=True
        report_path.write_text(json.dumps(report,indent=2),newline='\n')
scene=bpy.context.scene;camera=scene.camera
scene.render.threads_mode='FIXED';scene.render.threads=4;scene.cycles.device='CPU'
scene.render.engine='CYCLES';scene.cycles.samples=20;scene.cycles.use_denoising=True
scene.render.resolution_x=1100;scene.render.resolution_y=1400;scene.render.resolution_percentage=100
camera.data.type='ORTHO';camera.data.ortho_scale=1.63
def aim(p):camera.rotation_euler=(Vector(p)-camera.location).to_track_quat('-Z','Y').to_euler()
requested=args.views or ['Perspective','Face']
rig=bpy.data.objects['Nib_Rig']
for view in requested:
    camera.data.ortho_scale=1.63;scene.render.resolution_x=1100;scene.render.resolution_y=1400
    rig.animation_data.action=bpy.data.actions['Idle'];scene.frame_set(1)
    variant='grip' if view=='Grip' else 'leg' if view=='Leg' else 'natural'
    for obj in bpy.data.collections['Nib_Authored_Components'].objects:
        tag=obj.get('variant','all');region=obj.get('bone','')
        visible=tag=='all' or tag==variant or (tag=='organic' and variant!='grip')
        if tag=='natural':
            visible=not ((variant=='grip' and (region in ['Arm_L','LowerArm_L','Hand_L'] or (region.endswith('_L') and any(region.startswith(n) for n in ['Finger_','Index','Middle','Ring','Little','Thumb'])))) or (variant=='leg' and region in ['Shin_R','Foot_R']))
        obj.hide_render=not visible;obj.hide_set(not visible)
    if view in ['Walk','Run','Shoot','Melee','Hit','ShootHands']:
        action_name='Shoot' if view=='ShootHands' else view
        rig.animation_data.action=bpy.data.actions[action_name];scene.frame_set({'Walk':7,'Run':7,'Shoot':15,'Melee':19,'Hit':8}[action_name])
    camera.location=(1.9,-4.4,1.6);aim((0,0,.745))
    output='Nib_Review'+view+'.png'
    if view in ['Face','FaceProfile','FaceThreeQuarter','Wary','Tongue','Blink']:
        camera.location=(.35,-3,1.33);aim((0,-.005,1.17));camera.data.ortho_scale=.69
        scene.render.resolution_x=1400;scene.render.resolution_y=1100;output='Nib_FaceReview.png' if view=='Face' else 'Nib_Expression'+view+'.png'
        if view in ['FaceProfile','FaceThreeQuarter']:
            camera.location=(3,0,1.20) if view=='FaceProfile' else (.9,-1.3,1.27)
            aim((0,0,1.165));camera.data.ortho_scale=.56 if view=='FaceProfile' else .69
            output='Nib_'+view+'.png'
        elif view!='Face':
            rig.animation_data.action=bpy.data.actions['FacePerformance'];scene.frame_set({'Wary':31,'Tongue':103,'Blink':16}[view])
    elif view in ['Front','Back','Side']:
        camera.location={'Front':(0,-4,.85),'Back':(0,4,.85),'Side':(4,0,.85)}[view];aim((0,0,.745))
    elif view in ['Hands','ShootHands']:
        target=(-.225,-.055,.586) if view=='Hands' else (0,-.26,.900)
        camera.location=(-1.4,-2,.85) if view=='Hands' else (.60,-1.8,1.13)
        aim(target);camera.data.ortho_scale=.23 if view=='Hands' else .40
        scene.render.resolution_x=1200;scene.render.resolution_y=1000
    scene.render.filepath=str(RENDER_OUT/output);bpy.ops.render.render(write_still=True)
    metadata={'source':SOURCE.name,'sourceSha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'view':view,'action':rig.animation_data.action.name,'frame':scene.frame_current,'variant':variant,'renderer':'Blender Cycles CPU','samples':scene.cycles.samples,'status':'Visual review evidence; no artistic approval implied'}
    (RENDER_OUT/(output+'.json')).write_text(json.dumps(metadata,indent=2),newline='\n')
print('NIB_REVIEW_RENDER_COMPLETE')
