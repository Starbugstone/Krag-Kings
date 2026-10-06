"""Export seven isolated runtime takes and a tiny true-rest bind reference.

No shared files or source masters are overwritten. The skeletal samples support
roundtrip verification; they do not establish mesh deformation or artistic fit.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import bpy
from mathutils import Matrix
sys.path.insert(0,str(Path(__file__).parent))
import export_contract

parser=argparse.ArgumentParser()
parser.add_argument('--source',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
if args.output.exists():raise RuntimeError('Preserve previous animation candidate')
args.output.mkdir(parents=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source_sha=sha(args.source)
bpy.ops.wm.open_mainfile(filepath=str(args.source))
scene=bpy.context.scene
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE' and 'Pelvis' in o.data.bones)
locomotion,contract=export_contract.prepare(bpy,{})
for track in rig.animation_data.nla_tracks:track.mute=True
for obj in bpy.data.objects:
    if obj.type=='MESH':obj.hide_viewport=True;obj.hide_set(True)
mesh=bpy.data.meshes.new('Motion rest bind carrier')
mesh.from_pydata([(0,0,0),(.001,0,0),(0,.001,0)],[],[(0,1,2)]);mesh.update()
carrier=bpy.data.objects.new('Motion_RestBindCarrier',mesh);scene.collection.objects.link(carrier)
carrier.parent=rig;carrier.vertex_groups.new(name='Root').add([0,1,2],1.,'REPLACE')
carrier.modifiers.new('Explicit true rest binding','ARMATURE').object=rig
bpy.ops.object.select_all(action='DESELECT');rig.hide_set(False);rig.select_set(True)
carrier.select_set(True);bpy.context.view_layer.objects.active=rig
rest={b.name:(rig.matrix_world@b.matrix_local).copy() for b in rig.data.bones}
report={'source':str(args.source),'sourceSha256':source_sha,'recipeSha256':sha(Path(__file__)),
        'actionContract':contract,'locomotion':locomotion,'bones':list(rest),
        'sourceParents':{b.name:b.parent.name if b.parent else None for b in rig.data.bones},
        'sourceRest':{n:[list(r) for r in m] for n,m in rest.items()},
        'clips':{},'sharedAssetsChanged':False,'artisticAcceptance':False}

def export(path,animated):
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH','ARMATURE'},
        use_mesh_modifiers=False,use_triangles=True,axis_forward='-Z',axis_up='Y',
        apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',add_leaf_bones=False,
        use_armature_deform_only=False,bake_anim=animated,bake_anim_use_all_actions=False,
        bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_simplify_factor=0)

export_contract.select_action(bpy,rig,None)
scene.frame_set(1);bpy.context.view_layer.update()
reference=args.output/'RestBinding.fbx';export(reference,False)
report['bindReference']={'file':reference.name,'sha256':sha(reference)}
for name in export_contract.CLIPS:
    action=bpy.data.actions[name];export_contract.select_action(bpy,rig,action)
    scene.name=name;first,last=(int(v) for v in action.frame_range)
    scene.frame_start=first;scene.frame_end=last
    samples=[]
    for index in range(17):
        frame=round(first+(last-first)*index/16)
        scene.frame_set(frame);bpy.context.view_layer.update()
        joints={}
        for bone in rig.pose.bones:
            world=rig.matrix_world@bone.matrix
            joints[bone.name]={'head':list(world.translation),
                              'worldScale':list(world.to_scale()),
                              'deformationQuaternion':list((world@rest[bone.name].inverted()).to_quaternion())}
        samples.append({'frame':frame,'bones':joints})
    scene.frame_set(first);path=args.output/(name+'.fbx');export(path,True)
    report['clips'][name]={'file':path.name,'sha256':sha(path),'frameRange':[first,last],
                           'fps':scene.render.fps/scene.render.fps_base,'sourceSamples':samples}
if sha(args.source)!=source_sha:raise AssertionError('Export changed source')
(args.output/'export.json').write_text(json.dumps(report,indent=2)+'\n',newline='\n')
print('KRAG_KINGS_MOTION_EXPORT_COMPLETE',flush=True)
