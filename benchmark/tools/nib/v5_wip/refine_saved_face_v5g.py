"""Separate v5g facial-plane/contact proposal from the proven v5f Jaw repair.

No shared export or new full groom. Generate only in the serialized guard;
actual neutral/depth/Tongue/Blink views decide whether the proposal improves.
"""
import hashlib,json,sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Matrix

HERE=Path(__file__).parent;ROOT=HERE.parents[3]
sys.path.insert(0,str(HERE));sys.path.insert(0,str(ROOT/'benchmark/tools/krag'))
from face_planes_v5g import plane_delta,semantics
from mouth_jaw_weights import smooth
from nib_groom_v5 import fine_face_fuzz
from runtime_reduction import attach_portable_drivers
from audit_face_coordinates import facial_snapshot

ART=ROOT/'benchmark/art/nib';SOURCE=ART/'Nib_Master_v5f_JawRepair_WIP.blend'
TARGET=ART/'Nib_Master_v5g_FacePlanes_WIP.blend';REPORT=ART/'v5-study/native-head-v5g-face-planes.json'
EXPECTED='9b3380fd9b44eb2cff299310ae89f95d3faa4600c5653cc6ca06fba6fcf5c90e'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if sha(SOURCE)!=EXPECTED:raise RuntimeError('Repaired input differs from the reviewed v5f source')
if TARGET.exists():raise RuntimeError('Refusing to overwrite a generated facial proposal')
bpy.ops.wm.open_mainfile(filepath=str(SOURCE),load_ui=False)
scene=bpy.context.scene;rig=bpy.data.objects['Nib_Rig'];head=bpy.data.objects['Nib v5 fitted animation face']
collection=bpy.data.collections['Nib_Authored_Components'];deformation=json.loads(scene['deformation_contract'])
rig.animation_data.action=None
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
keys=head.data.shape_keys;drivers=list(keys.animation_data.drivers)
head.active_shape_key_index=0
for driver in drivers:driver.mute=True
for key in keys.key_blocks:key.value=0
scene.frame_set(1);bpy.context.view_layer.update()
def coordinates(items):return np.asarray([tuple(v.co) for v in items],dtype=np.float64)
def digest(array):return hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()
def weights_digest(obj):
    values=[[(obj.vertex_groups[g.group].name,float(g.weight)) for g in v.groups] for v in obj.data.vertices]
    return hashlib.sha256(json.dumps(values,separators=(',',':')).encode()).hexdigest()
def component_state():
    result={}
    for obj in collection.objects:
        if obj.type!='MESH' or obj is head or obj.name=='Nib v5 fine facial fuzz':continue
        result[obj.name]={'basis':digest(coordinates(obj.data.vertices)),
                         'matrix':digest(np.asarray(obj.matrix_world,dtype=np.float64))}
    return result

unrelated=component_state();head_weights=weights_digest(head)
head_uv={layer.name:digest(np.asarray([tuple(v.uv) for v in layer.data],dtype=np.float64)) for layer in head.data.uv_layers}
bind=digest(np.asarray([list(b.matrix_local) for b in rig.data.bones],dtype=np.float64))
source=np.asarray([tuple(v.vector) for v in head.data.attributes['nib_source_position'].data],dtype=np.float64)
faces=[list(p.vertices) for p in head.data.polygons];edges=np.asarray([tuple(e.vertices) for e in head.data.edges],dtype=np.int32)
sets=np.asarray([v.value for v in head.data.attributes['.sculpt_face_set'].data],dtype=np.int32)
tags=semantics(len(source),faces,sets)
old_keys={key.name:coordinates(key.data) for key in keys.key_blocks};basis=old_keys['Basis']
delta,field_report=plane_delta(source,basis);field_report['status']='Applied to isolated candidate; actual native review pending'
new_basis=basis+delta
contact_report={'applied':False,'status':'Deferred: curve-matching closure rotates 43 lip/oral triangles over 90 degrees in the actual-cache diagnostic; existing v5f aperture retained'}
new_keys={};contact_keys={};blink_support=np.ones(len(source))
# Retain the existing eyelid closure while fading its inherited wide support
# out of the brow/bridge. The old closure drags skin well above the aperture,
# producing the observed nasal-side pinches. This remains a review proposal.
blink_support*=1-smooth(.322,.336,source[:,2])
blink_support[tags[11]]=0
for name,old in old_keys.items():
    if name=='Basis':value=new_basis
    elif name=='JawOpen':value=new_basis+(old-basis)
    else:
        relative=old-basis
        if name.startswith('Blink_'):relative*=blink_support[:,None]
        value=new_basis+relative
    if not np.isfinite(value).all():raise RuntimeError('Nonfinite face key '+name)
    new_keys[name]=value
for name,value in new_keys.items():keys.key_blocks[name].data.foreach_set('co',value.astype(np.float32).ravel())
head.data.vertices.foreach_set('co',new_basis.astype(np.float32).ravel());head.data.update()
for driver in drivers:driver.mute=False

# Regional leathery nose response. Preserve the actual geometry-dependent
# NibNoseMask; generic tile baking must not erase this field in later exports.
material=head.data.materials[0].copy();material.name='Nib_v5g_FacialSkin';head.data.materials[0]=material
nodes=material.node_tree.nodes;links=material.node_tree.links
shader=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
attribute=next((n for n in nodes if n.type=='ATTRIBUTE' and n.attribute_name=='NibNoseMask'),None)
if attribute is None:raise RuntimeError('Missing authored nose attribute')
base_node=shader.inputs['Base Color'].links[0].from_node
if base_node.type!='MIX_RGB':raise RuntimeError('Unexpected existing nose color network')
base_node.inputs[2].default_value=(.120,.045,.024,1)
rough=shader.inputs['Roughness'];old_link=rough.links[0].from_socket if rough.links else None
mix=nodes.new('ShaderNodeMixRGB');mix.name='Nib nose leather roughness';mix.blend_type='MIX'
if old_link:links.new(old_link,mix.inputs[1])
else:mix.inputs[1].default_value=(rough.default_value,)*3+(1,)
mix.inputs[2].default_value=(.38,.38,.38,1);links.new(attribute.outputs['Fac'],mix.inputs[0]);links.new(mix.outputs[0],rough)
sss=shader.inputs['Subsurface Weight'];old_sss=sss.links[0].from_socket if sss.links else None
invert=nodes.new('ShaderNodeMath');invert.operation='MULTIPLY_ADD';invert.inputs[1].default_value=-.90;invert.inputs[2].default_value=1
links.new(attribute.outputs['Fac'],invert.inputs[0])
scale=nodes.new('ShaderNodeMath');scale.operation='MULTIPLY';links.new(invert.outputs[0],scale.inputs[0])
if old_sss:links.new(old_sss,scale.inputs[1])
else:scale.inputs[1].default_value=sss.default_value
links.new(scale.outputs[0],sss)

# The existing fine facial fuzz follows its changed surface. Full scalp/ear
# groom and body fuzz are preserved; this is not the separate card-groom pass.
old_fuzz=bpy.data.objects['Nib v5 fine facial fuzz'];fuzz_material=old_fuzz.data.materials[0];mesh=old_fuzz.data
bpy.data.objects.remove(old_fuzz,do_unlink=True)
if mesh.users==0:bpy.data.meshes.remove(mesh)
fuzz=fine_face_fuzz(head,collection,rig,fuzz_material,False);attach_portable_drivers(fuzz,rig,deformation)
if unrelated!=component_state():raise RuntimeError('Facial proposal changed an unrelated component')
if head_weights!=weights_digest(head):raise RuntimeError('Facial proposal changed repaired Jaw weights')
if head_uv!={layer.name:digest(np.asarray([tuple(v.uv) for v in layer.data],dtype=np.float64)) for layer in head.data.uv_layers}:
    raise RuntimeError('Facial proposal changed UV coordinates')
if bind!=digest(np.asarray([list(b.matrix_local) for b in rig.data.bones],dtype=np.float64)):
    raise RuntimeError('Facial proposal changed skeleton bind')
report={'status':'Generated isolated facial-plane/contact proposal; actual views required; no artistic acceptance',
        'artisticAcceptance':False,'source':str(SOURCE),'sourceSha256':EXPECTED,
        'geometry':field_report,'neutralContact':contact_report,'closedExpressionContact':contact_keys,
        'preserved':{'repairedJawWeightsSha256':head_weights,'skeletonBindSha256':bind,'uvLayers':head_uv,'unrelatedComponents':len(unrelated),
                     'eyeMeshesAndPivots':True,'darkBlueTongueAndInteriors':True,'scalpEarGroom':True},
        'noseMaterial':{'name':material.name,'maskAttribute':'NibNoseMask','linearBrownProposal':[.120,.045,.024],
                        'roughness':.38,'relativeSubsurfaceAtFullMask':.10,'actualMeshAtlasRequiredBeforeExport':True},
        'blinkChange':'Fade old wide support above sourceZ .322–.336 and remove nasal-set11 motion; actual closure/crease review mandatory',
        'authoringCode':{},'sharedChanged':False}
for name in ['refine_saved_face_v5g.py','face_planes_v5g.py','mouth_jaw_weights.py']:
    path=HERE/name;report['authoringCode'][name]=sha(path)
    text=bpy.data.texts.new('Nib source v5g '+name);text.write(path.read_text())
rig.animation_data.action=None
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
scene.frame_set(1);report['neutralCoordinates']=facial_snapshot(scene,rig,head)
rig.animation_data.action=bpy.data.actions['Idle'];scene.frame_set(1);report['idleCoordinates']=facial_snapshot(scene,rig,head)
issues=[pose+': '+issue for pose in ['neutralCoordinates','idleCoordinates']
        for issue in report[pose]['neutralStructuralBlockersIfClosedMouthExpected']]
report['preRenderGate']={'passed':not issues,'blockingIssues':issues,'scope':'Strict neutral/Idle oral visibility and visible irises; actual pose/art review still required'}
scene['source_version']='v5g continuous face planes, preserving v5f Jaw repair; contact proposal deferred; unaccepted'
bpy.ops.wm.save_as_mainfile(filepath=str(TARGET),compress=True)
if sha(SOURCE)!=EXPECTED:raise RuntimeError('Repaired v5f input changed')
report['candidateSha256']=sha(TARGET)
REPORT.write_text(json.dumps(report,indent=2)+'\n',newline='\n')
print('NIB_V5G_FACE_PLANES_SAVED',flush=True)
