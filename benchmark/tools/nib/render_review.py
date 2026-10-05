"""Fast actual-mesh review, including close-up and posed silhouettes."""
import bpy, math, sys, json, hashlib
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[3]
ART=ROOT/'benchmark/art/nib'
bpy.ops.wm.open_mainfile(filepath=str(ART/'Nib_Master.blend'))
report_path=ART/'source-report.json'
if report_path.exists():
    report=json.loads(report_path.read_text())
    if not report.get('nativeCompressed',False):
        report['priorUncompressedSha256']=report['sourceSha256']
        bpy.ops.wm.save_as_mainfile(filepath=str(ART/'Nib_Master.blend'),compress=True)
        report['sourceSha256']=hashlib.sha256((ART/'Nib_Master.blend').read_bytes()).hexdigest();report['nativeCompressed']=True
        report_path.write_text(json.dumps(report,indent=2))
scene=bpy.context.scene;camera=scene.camera
scene.render.threads_mode='FIXED';scene.render.threads=4;scene.cycles.device='CPU'
scene.render.engine='CYCLES';scene.cycles.samples=20;scene.cycles.use_denoising=True
scene.render.resolution_x=1100;scene.render.resolution_y=1400;scene.render.resolution_percentage=100
camera.data.type='ORTHO';camera.data.ortho_scale=1.63
def aim(p):camera.rotation_euler=(Vector(p)-camera.location).to_track_quat('-Z','Y').to_euler()
requested=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else ['Perspective','Face']
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
    if view in ['Walk','Run','Shoot','Melee','Hit']:
        rig.animation_data.action=bpy.data.actions[view];scene.frame_set({'Walk':7,'Run':7,'Shoot':15,'Melee':19,'Hit':8}[view])
    camera.location=(1.9,-4.4,1.6);aim((0,0,.745))
    output='Nib_Review'+view+'.png'
    if view in ['Face','Wary','Tongue','Blink']:
        camera.location=(.35,-3,1.33);aim((0,-.005,1.17));camera.data.ortho_scale=.69
        scene.render.resolution_x=1400;scene.render.resolution_y=1100;output='Nib_FaceReview.png' if view=='Face' else 'Nib_Expression'+view+'.png'
        if view!='Face':
            rig.animation_data.action=bpy.data.actions['FacePerformance'];scene.frame_set({'Wary':31,'Tongue':103,'Blink':16}[view])
    elif view in ['Front','Back','Side']:
        camera.location={'Front':(0,-4,.85),'Back':(0,4,.85),'Side':(4,0,.85)}[view];aim((0,0,.745))
    scene.render.filepath=str(ART/'renders'/output);bpy.ops.render.render(write_still=True)
    metadata={'source':'Nib_Master.blend','sourceSha256':hashlib.sha256((ART/'Nib_Master.blend').read_bytes()).hexdigest(),'view':view,'action':rig.animation_data.action.name,'frame':scene.frame_current,'variant':variant,'renderer':'Blender Cycles CPU','samples':scene.cycles.samples,'status':'Visual review evidence; no artistic approval implied'}
    (ART/'renders'/(output+'.json')).write_text(json.dumps(metadata,indent=2))
print('NIB_REVIEW_RENDER_COMPLETE')
