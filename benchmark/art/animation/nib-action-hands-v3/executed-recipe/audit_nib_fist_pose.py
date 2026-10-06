"""Read-only native saved-pose and skinning audit; no source writes."""
import argparse,hashlib,json,math,sys
from pathlib import Path
import bpy
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).parent))
from export_contract import select_action
import nib_anatomical_hand_pose as controller
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
if a.output.exists():raise RuntimeError('Preserve prior audit')
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest(); digest=sha(a.source)
bpy.ops.wm.open_mainfile(filepath=str(a.source),load_ui=False)
rig=bpy.data.objects['Nib_Rig']; scene=bpy.context.scene
for track in rig.animation_data.nla_tracks:track.mute=True
hand=rig.pose.bones['Hand_L'];axis=(rig.data.bones['Index1_L'].head_local-rig.data.bones['Little1_L'].head_local).normalized()
select_action(bpy,rig,bpy.data.actions['Melee']);scene.frame_set(16);bpy.context.view_layer.update()

def capture():
 delta=hand.matrix@hand.bone.matrix_local.inverted(); inverse=delta.inverted(); result={}
 for finger in ['Index','Middle','Ring','Little','Thumb']:
  rows=[]
  ref=rig.data.bones[finger+'1_L'].tail_local-rig.data.bones[finger+'1_L'].head_local;ref-=axis*ref.dot(axis);ref.normalize()
  for segment in range(1,3 if finger=='Thumb' else 4):
   bone=rig.pose.bones[finger+str(segment)+'_L'];h=inverse@bone.head;t=inverse@bone.tail;direction=t-h;direction-=axis*direction.dot(axis);direction.normalize()
   angle=math.degrees(math.atan2(axis.dot(ref.cross(direction)),ref.dot(direction)))
   rows.append({'name':bone.name,'actualParent':bone.parent.name if bone.parent else None,'headInRestHandFrame':list(h),'tailInRestHandFrame':list(t),'cumulativeFlexionDegrees':angle,'location':list(bone.location),'scale':list(bone.scale),'rotationEuler':list(bone.rotation_euler)})
  result[finger]=rows
 return result
saved=capture(); changed=controller.pose(rig,{n:(82,98,55) for n in controller.RELAXED},(18,25),32);direct=capture()
mesh=bpy.data.objects['Nib v5 coherent hand L']; evaluated=mesh.evaluated_get(bpy.context.evaluated_depsgraph_get()); posed=evaluated.to_mesh(); delta=hand.matrix@hand.bone.matrix_local.inverted();inverse=delta.inverted()
points=[list(inverse@mesh.matrix_world@v.co) for v in posed.vertices];evaluated.to_mesh_clear()
a.output.parent.mkdir(parents=True,exist_ok=True)
a.output.write_text(json.dumps({'source':str(a.source),'sourceSha256':digest,'recipeSha256':sha(Path(__file__)),'savedMeleeFrame':16,'savedPose':saved,'directControllerPose':direct,'actualSkinInRestHandFrame':points,'restSkin':[list(v.co) for v in mesh.data.vertices],'weights':[[(mesh.vertex_groups[g.group].name,g.weight) for g in v.groups] for v in mesh.data.vertices],'polygons':[list(p.vertices) for p in mesh.data.polygons],'axis':list(axis),'sourceChanged':False},indent=2)+'\n')
assert sha(a.source)==digest
print('NIB_FIST_NATIVE_AUDIT_COMPLETE',flush=True)
