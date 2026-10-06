"""Actual posed forearm/body/cloth inspection; read-only Blender clay views."""
import argparse, hashlib, json, sys
from pathlib import Path
import bpy
from mathutils import Matrix, Vector
sys.path.insert(0,str(Path(__file__).parent))
from export_contract import select_action
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
expected=sha(a.source)
if a.output.exists():raise RuntimeError('Preserve prior posed wrap review')
a.output.mkdir(parents=True);bpy.ops.wm.open_mainfile(filepath=str(a.source),load_ui=False)
rig=bpy.data.objects['Nib_Rig'];scene=bpy.context.scene;camera=scene.camera
for track in rig.animation_data.nla_tracks:track.mute=True
active={o.name for o in bpy.data.collections['Nib_Authored_Components'].all_objects}
for o in bpy.data.objects:
 if o.type=='MESH':
  show=o.name in active and o.get('variant','all') in ['all','organic','natural']
  o.hide_render=not show;o.hide_viewport=not show
scene.render.engine='BLENDER_WORKBENCH';scene.render.resolution_x=800;scene.render.resolution_y=900;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False;scene.render.use_compositing=False;scene.render.use_sequencer=False
shade=scene.display.shading;shade.light='STUDIO';shade.color_type='SINGLE';shade.single_color=(.54,.54,.54)
shade.show_shadows=True;shade.show_cavity=True;shade.cavity_type='BOTH';shade.background_type='WORLD';scene.world.color=(.065,.065,.065);scene.display.render_aa='8'
camera.data.type='ORTHO';camera.data.ortho_scale=.27;camera.data.clip_start=.001;camera.data.clip_end=100
views=[]
for clip,phase in [('Idle',0.),('Shoot',.46),('Run',.5)]:
 action=bpy.data.actions[clip];select_action(bpy,rig,action);first,last=action.frame_range;at=first+phase*(last-first)
 scene.frame_set(int(at),subframe=at-int(at));bpy.context.view_layer.update()
 for side,sign in [('L',1),('R',-1)]:
  forearm=rig.pose.bones['LowerArm_'+side];hand=rig.pose.bones['Hand_'+side]
  delta=forearm.matrix.to_3x3()@forearm.bone.matrix_local.to_3x3().inverted()
  up=(forearm.head-hand.head).normalized();target=rig.matrix_world@forearm.head.lerp(hand.head,.72)
  for name,original in [('front',Vector((sign*.45,-1,0))),('outer',Vector((sign,0,0)))]:
   outward=(delta@original).normalized();outward-=up*outward.dot(up);outward.normalize()
   right=up.cross(outward).normalized();camera_up=outward.cross(right).normalized()
   camera.matrix_world=Matrix((right,camera_up,outward)).transposed().to_4x4();camera.location=target+outward*.8
   path=a.output/f'{clip}_{side}_{name}.png';scene.render.filepath=str(path);bpy.ops.render.render(write_still=True)
   views.append({'clip':clip,'phase':phase,'side':side,'view':name,'image':str(path),'sha256':sha(path)})
if sha(a.source)!=expected:raise RuntimeError('Review changed source')
(a.output/'review.json').write_text(json.dumps({'source':str(a.source),'sourceSha256':expected,'recipeSha256':sha(Path(__file__)),
 'renderer':'Blender Workbench actual skinned source','materialReview':False,'surfaceIntersectionProof':False,'sourceModified':False,
 'artisticAcceptance':False,'views':views},indent=2)+'\n')
print('NIB_ACTUAL_WRAPS_REVIEW_COMPLETE',flush=True)
