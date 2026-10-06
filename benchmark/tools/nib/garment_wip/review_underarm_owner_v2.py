"""Read-only object-color attribution of the actual v2 Shoot underarm sheet."""
import hashlib,json
from pathlib import Path
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[4]
SOURCE=ROOT/'benchmark/art/nib/garment-study/v2/Nib_ShirtStrapsStudy_v2.blend'
EXPECTED='4df4d2fb46d83a457277ad1395adb63f6acde3af9d817ae430d7a282f82792f8'
OUT=ROOT/'benchmark/art/nib/garment-study/v2/underarm-ownership'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if sha(SOURCE)!=EXPECTED:raise RuntimeError('Pinned garment source changed')
if OUT.exists():raise RuntimeError('Preserve previous object-ownership evidence')
OUT.mkdir(parents=True);bpy.ops.wm.open_mainfile(filepath=str(SOURCE),load_ui=False)
scene=bpy.context.scene;rig=bpy.data.objects['Nib_Rig'];camera=scene.camera
colors={'Continuous Nib anatomy organic':(.08,.65,.28,1),'Sleeveless dust undershirt':(.9,.65,.04,1),'Overalls draped bib':(.09,.24,.75,1)}
for obj in bpy.data.collections['Nib_Authored_Components'].objects:
    visible=obj.get('variant','all') in ['all','natural','organic'];obj.hide_render=not visible;obj.hide_viewport=not visible
    obj.color=colors.get(obj.name,(.36,.36,.36,1))
for track in rig.animation_data.nla_tracks:track.mute=True
rig.animation_data.action=bpy.data.actions['Shoot'];first,last=map(float,rig.animation_data.action.frame_range);frame=first+.46*(last-first)
scene.frame_set(int(frame),subframe=frame%1);bpy.context.view_layer.update()
scene.render.engine='BLENDER_WORKBENCH';scene.render.resolution_x=1000;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.use_compositing=False;scene.render.use_sequencer=False;scene.render.film_transparent=False
shade=scene.display.shading;shade.light='STUDIO';shade.color_type='OBJECT';shade.show_shadows=True;shade.show_cavity=True;shade.cavity_type='BOTH';shade.background_type='WORLD'
scene.world.color=(.065,.065,.065);scene.display.render_aa='16';camera.data.type='ORTHO';camera.data.ortho_scale=.88
target=Vector((0,-.015,.905));camera.location=target+Vector((1.8,-3,.20));camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
image=OUT/'Shoot-objects.png';scene.render.filepath=str(image);bpy.ops.render.render(write_still=True)
report={'status':'Actual object-color attribution only; no visual acceptance','source':str(SOURCE),'sourceSha256':EXPECTED,'action':'Shoot','normalizedTime':.46,'frame':frame,'colors':colors,'otherObjects':'neutral grey','image':str(image),'imageSha256':sha(image),'codeSha256':sha(Path(__file__)),'sourceUnchanged':sha(SOURCE)==EXPECTED,'sharedChanged':False}
if not report['sourceUnchanged']:raise RuntimeError('Read-only ownership view modified source')
(OUT/'review.json').write_text(json.dumps(report,indent=2)+'\n',newline='\n');print('NIB_UNDERARM_OWNERSHIP_V2_REVIEW_COMPLETE',flush=True)
