"""Prepared actual cuff/neutral, curled-hand and Shoot compatibility views."""
import argparse,hashlib,json,sys
from pathlib import Path
import bpy
from mathutils import Vector

parser=argparse.ArgumentParser()
parser.add_argument('--source',type=Path,required=True)
parser.add_argument('--report',type=Path,required=True)
parser.add_argument('--output-dir',type=Path,required=True)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
expected=sha(args.source)
report=json.loads(args.report.read_text())
if report.get('candidateSha256')!=expected or not report.get('savedSourceReopened'):
    raise RuntimeError('Require the actual matching saved/reopened candidate')
if args.output_dir.exists():raise RuntimeError('Preserve previous review')
args.output_dir.mkdir(parents=True)
bpy.ops.wm.open_mainfile(filepath=str(args.source),load_ui=False)
scene=bpy.context.scene;rig=bpy.data.objects['Nib_Rig'];camera=scene.camera
for track in rig.animation_data.nla_tracks:track.mute=True
def visible(obj):
    tag=obj.get('variant','all');region=obj.get('bone','')
    if tag in ['all','grip']:return True
    if tag=='organic':return False
    if tag=='natural':
        return not (region in ['Arm_L','LowerArm_L','Hand_L'] or
                    (region.endswith('_L') and region.startswith(('Finger_','Index','Middle','Ring','Little','Thumb'))))
    return False
shown=[]
for obj in bpy.data.collections['Nib_Authored_Components'].objects:
    show=visible(obj);obj.hide_set(not show);obj.hide_render=not show
    obj.color=(.58,.57,.53,1)
    if obj.get('variant')=='grip':obj.color=(.34,.47,.48,1)
    if obj.get('bone')=='BodyAnatomy':obj.color=(.55,.39,.24,1)
    if show:shown.append(obj.name)
if 'Continuous Nib anatomy organic' in shown or 'Continuous Nib anatomy grip coherent' not in shown:
    raise RuntimeError('Variant body visibility overlaps or is incomplete')
scene.render.engine='BLENDER_WORKBENCH';scene.render.resolution_x=1100;scene.render.resolution_y=1100
scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
scene.render.use_compositing=False;scene.render.use_sequencer=False;scene.render.film_transparent=False
shade=scene.display.shading;shade.light='STUDIO';shade.color_type='OBJECT';shade.show_shadows=True
shade.show_cavity=True;shade.cavity_type='BOTH';shade.background_type='WORLD';scene.world.color=(.065,.065,.065)
scene.display.render_aa='16';camera.data.type='ORTHO';records=[]
for name,action,phase in [('ArmNeutral','Idle',0.),('HandCurl','Run',.25),('Shoot','Shoot',.46)]:
    rig.animation_data.action=bpy.data.actions[action]
    start,end=map(float,rig.animation_data.action.frame_range);frame=start+(end-start)*phase
    scene.frame_set(int(frame),subframe=frame%1);bpy.context.view_layer.update()
    hand=rig.matrix_world@rig.pose.bones['Hand_L'].head
    elbow=rig.matrix_world@rig.pose.bones['LowerArm_L'].head
    if name=='ArmNeutral':target=(elbow+hand)*.5;offset=Vector((1,-2,.1));scale=.39
    elif name=='HandCurl':
        tip=rig.matrix_world@rig.pose.bones['Middle3_L'].tail
        target=(hand+tip)*.5;offset=Vector((1,-2,.45));scale=.17
    else:target=Vector((0,-.02,.85));offset=Vector((1.8,-3,.20));scale=.92
    camera.data.ortho_scale=scale;camera.location=target+offset
    camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
    path=args.output_dir/(name+'.png');scene.render.filepath=str(path);bpy.ops.render.render(write_still=True)
    records.append({'view':name,'action':action,'normalizedTime':phase,'frame':frame,
                    'image':str(path),'imageSha256':sha(path),
                    'actualBonePoints':{n:{'head':list(rig.matrix_world@rig.pose.bones[n].head),
                                           'tail':list(rig.matrix_world@rig.pose.bones[n].tail)}
                                        for n in ['LowerArm_L','ForearmTwist_L','Hand_L','Index1_L','Index3_L','Thumb1_L','Thumb2_L']}})
if sha(args.source)!=expected:raise RuntimeError('Read-only review changed candidate')
result={'status':'Actual restorative posed mesh views; inspect cuff, ordinary reach and contact before any acceptance',
        'source':str(args.source),'sourceSha256':expected,'sourceReportSha256':sha(args.report),
        'recipeSha256':sha(Path(__file__)),'variantVisibleObjects':shown,'poses':records,
        'artisticAcceptance':False,'sharedChanged':False}
(args.output_dir/'review.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n')
print('NIB_RESTORATIVE_COMPATIBILITY_ACTUAL_REVIEW_COMPLETE',flush=True)
