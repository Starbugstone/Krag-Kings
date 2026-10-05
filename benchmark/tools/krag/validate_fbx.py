"""Fresh-process FBX roundtrip evidence; this is structural validation, not likeness approval."""
import bpy,sys,json,math,argparse,hashlib
from pathlib import Path
from mathutils import Vector
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
ap=argparse.ArgumentParser();ap.add_argument('--variant',default='Krag_Natural');opt=ap.parse_args(args)
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'benchmark/shared/characters/krag';ART=ROOT/'benchmark/art/krag'
manifest=json.loads((OUT/'manifest.json').read_text());contract=json.loads((OUT/'krag_asset_contract.json').read_text());variant=next(v for v in manifest['variants'] if v['name']==opt.variant);fbx=OUT/variant['fbx']
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False);bpy.ops.import_scene.fbx(filepath=str(fbx),use_anim=True)
rigs=[o for o in bpy.data.objects if o.type=='ARMATURE'];meshes=[o for o in bpy.data.objects if o.type=='MESH'];errors=[]
if len(rigs)!=1:errors.append(f'Expected one skeleton, got {len(rigs)}')
rig=rigs[0];rig.animation_data_clear()
for bone in rig.pose.bones:bone.rotation_mode='QUATERNION';bone.rotation_quaternion=(1,0,0,0);bone.location=(0,0,0);bone.scale=(1,1,1)
for mesh in meshes:
 if mesh.data.shape_keys:
  mesh.data.shape_keys.animation_data_clear()
  for shape in mesh.data.shape_keys.key_blocks:shape.value=0
bpy.context.view_layer.update()
keys=sorted(set(k.name for o in meshes if o.data.shape_keys for k in o.data.shape_keys.key_blocks if k.name!='Basis'))
def match(name):return any(k==name or k.endswith('.'+name) for k in keys)
deformation=variant.get('deformation',manifest['deformation'])
for driver in deformation['drivers']:
 if driver['bone'] not in rig.data.bones:errors.append('Missing driver bone '+driver['bone'])
 if not match(driver['morph']):errors.append('Missing morph '+driver['morph'])
if 'FaceRoot' not in rig.data.bones or rig.data.bones['FaceRoot'].parent.name!='Head':errors.append('Invalid FaceRoot subtree')
for bone in contract['bones']+contract.get('runtime_extra_bones',[]):
 if bone not in rig.data.bones:errors.append('Missing bone '+bone)
actions=[a.name for a in bpy.data.actions]
for clip in contract['clips']:
 if not any(a.endswith('|'+clip) or a==clip or a.endswith(clip) for a in actions):errors.append('Missing clip '+clip)
points=[o.matrix_world@Vector(corner) for o in meshes for corner in o.bound_box];bounds={'min':[min(v[i] for v in points) for i in range(3)],'max':[max(v[i] for v in points) for i in range(3)]}
for o in meshes:
 if not o.data.uv_layers:errors.append('Missing UVs '+o.name)
 if any(not math.isfinite(c) for v in o.data.vertices for c in v.co):errors.append('Nonfinite coordinates '+o.name)
 if any(not v.groups for v in o.data.vertices):errors.append('Unweighted vertices '+o.name)
for material in manifest['materials']:
 for channel in ['baseColor','normal','roughness','metallic']:
  if not (OUT/material[channel]).is_file():errors.append('Missing map '+material[channel])
# Evaluate imported body takes, rather than merely trusting source control-curve code.
for mesh in meshes:
 mesh.hide_set(True)
 for modifier in mesh.modifiers:
  if modifier.type=='ARMATURE':modifier.show_viewport=False
facial_per_clip={}
facial_bones=[p for p in rig.pose.bones if p.name=='FaceRoot' or any(parent.name=='FaceRoot' for parent in p.parent_recursive)]
rig.animation_data_create()
for clip in contract['clips']:
    candidates=[a for a in bpy.data.actions if a.name==clip or a.name.endswith('|'+clip) or a.name.endswith(clip)]
    if not candidates:continue
    action=next((a for a in candidates if a.name.startswith(rig.name+'|')),next(a for a in candidates if not a.name.startswith('Key|')));rig.animation_data.action=action
    if action.slots:rig.animation_data.action_slot=action.slots[0];lo,hi=action.frame_range;values={p.name:[] for p in facial_bones}
    for step in range(17):
        bpy.context.scene.frame_set(round(lo+(hi-lo)*step/16));bpy.context.view_layer.update()
        for p in facial_bones:
            q=p.matrix_basis.to_quaternion();angle=math.degrees(q.angle);parent_matrix=p.parent.matrix.to_3x3() if p.parent else rig.matrix_world.to_3x3();translation=(parent_matrix@p.matrix_basis.translation).length
            values[p.name].append((angle,translation))
    animated=[name for name,samples in values.items() if max(x[0] for x in samples)-min(x[0] for x in samples)>.001 or max(x[1] for x in samples)-min(x[1] for x in samples)>1e-6]
    facial_per_clip[clip]={'animatedFaceBones':animated,'maxLocalRotationDegrees':max(x[0] for samples in values.values() for x in samples),'maxLocalTranslationMeters':max(x[1] for samples in values.values() for x in samples)}
    if not animated:errors.append('No varying imported facial performance in '+clip)
data=dict(variant=opt.variant,fbx=str(fbx),fbx_sha256=hashlib.sha256(fbx.read_bytes()).hexdigest(),boneCount=len(rig.data.bones),meshCount=len(meshes),vertices=sum(len(o.data.vertices) for o in meshes),triangles=sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in meshes),materialSlots=sum(len(o.data.materials) for o in meshes),morphs=keys,actions=actions,facialPerformanceByClip=facial_per_clip,boundsMeters=bounds,errors=errors,structuralValidationPassed=not errors,artisticAcceptance=False)
(ART/(opt.variant+'-fbx-roundtrip.json')).write_text(json.dumps(data,indent=2));print(json.dumps(data,indent=2),flush=True)
if errors:raise RuntimeError('; '.join(errors))
