"""Export only the corrected Shoot take from an isolated saved runtime source."""
import argparse, hashlib, json, sys
from pathlib import Path
import bpy

parser=argparse.ArgumentParser()
parser.add_argument('--source',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
parser.add_argument('--report',type=Path,required=True)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
bpy.ops.wm.open_mainfile(filepath=str(args.source))
rig=bpy.data.objects['Krag_Rig'];scene=bpy.context.scene
# Match the established explicit bind carrier. It is not a character mesh.
data=bpy.data.meshes.new('AnimationBindMesh')
data.from_pydata([(0,0,0),(.001,0,0),(0,.001,0)],[],[(0,1,2)]);data.update()
carrier=bpy.data.objects.new('AnimationBindMesh',data);bpy.context.collection.objects.link(carrier)
carrier.parent=rig;carrier.vertex_groups.new(name='Root').add([0,1,2],1,'REPLACE')
modifier=carrier.modifiers.new('Explicit rest binding','ARMATURE');modifier.object=rig
bpy.ops.object.select_all(action='DESELECT');rig.hide_set(False);rig.select_set(True)
carrier.select_set(True);bpy.context.view_layer.objects.active=rig
rig.animation_data.action=bpy.data.actions['Shoot']
scene.frame_start=1;scene.frame_end=31;scene.frame_set(1);scene.name='Shoot'
args.output.parent.mkdir(parents=True,exist_ok=True)
bpy.ops.export_scene.fbx(filepath=str(args.output),use_selection=True,
    object_types={'MESH','ARMATURE'},use_mesh_modifiers=False,use_triangles=True,
    axis_forward='-Z',axis_up='Y',apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',
    add_leaf_bones=False,use_armature_deform_only=False,bake_anim=True,
    bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,
    bake_anim_force_startend_keying=True,bake_anim_simplify_factor=0)
report={'source':str(args.source),'sourceSha256':hashlib.sha256(args.source.read_bytes()).hexdigest(),
        'output':str(args.output),'sha256':hashlib.sha256(args.output.read_bytes()).hexdigest(),
        'clip':'Shoot','bones':len(rig.data.bones),'frames':[1,31],
        'bindCarrier':'Root-weighted 1 mm triangle; same established export settings',
        'status':'Exported donor curves; roundtrip and visible grip validation pending'}
args.report.write_text(json.dumps(report,indent=2)+'\n',newline='\n')
print('KRAG_AIM_CLIP_EXPORTED',flush=True)
