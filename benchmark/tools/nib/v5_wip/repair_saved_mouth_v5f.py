"""Isolated v5e Jaw-weight repair; preserves frozen source and shared assets.

No face sculpt, new hair coverage, clip change or interior redesign. Only the
head's Jaw/Head weights, lower-face JawOpen support, and corresponding fine
facial-fuzz deformation change. Source and actual pose review remain required.
"""
import hashlib,json,sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Matrix

HERE=Path(__file__).parent;ROOT=HERE.parents[3]
sys.path.insert(0,str(HERE));sys.path.insert(0,str(ROOT/'benchmark/tools/krag'))
from mouth_jaw_weights import calculate
from nib_groom_v5 import fine_face_fuzz
from runtime_reduction import attach_portable_drivers
from audit_face_coordinates import facial_snapshot

ART=ROOT/'benchmark/art/nib'
SOURCE=ART/'Nib_Master_v5e_WIP.blend'
TARGET=ART/'Nib_Master_v5f_JawRepair_WIP.blend'
REPORT=ART/'v5-study/native-head-v5f-jaw-repair.json'
EXPECTED='3791f8405b44c1114728e357caf3c6d21172c5882feee4178e627982a5120b96'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if sha(SOURCE)!=EXPECTED:raise RuntimeError('Frozen v5e source differs from audited input')
if TARGET.exists():raise RuntimeError('Refusing to overwrite a saved repair candidate')
bpy.ops.wm.open_mainfile(filepath=str(SOURCE),load_ui=False)
scene=bpy.context.scene;rig=bpy.data.objects['Nib_Rig'];head=bpy.data.objects['Nib v5 fitted animation face']
collection=bpy.data.collections['Nib_Authored_Components']
rig.animation_data.action=None
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
scene.frame_set(1);bpy.context.view_layer.update()

def coordinates(items):return np.asarray([tuple(v.co) for v in items],dtype=np.float32)
def digest(array):return hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()
def snapshots():
    data={}
    for obj in collection.objects:
        if obj.type!='MESH':continue
        data[obj.name]={'basis':digest(coordinates(obj.data.vertices)),
            'polygons':digest(np.asarray([v for p in obj.data.polygons for v in p.vertices],dtype=np.int32)),
            'matrix':digest(np.asarray(obj.matrix_world,dtype=np.float32)),
            'uv':{uv.name:digest(np.asarray([tuple(item.uv) for item in uv.data],dtype=np.float32)) for uv in obj.data.uv_layers},
            'shapeKeys':{k.name:digest(coordinates(k.data)) for k in obj.data.shape_keys.key_blocks} if obj.data.shape_keys else {}}
    return data

before=snapshots()
bind_before=digest(np.asarray([list(bone.matrix_local) for bone in rig.data.bones],dtype=np.float64))
source=np.asarray([tuple(v.vector) for v in head.data.attributes['nib_source_position'].data],dtype=np.float64)
faces=[list(p.vertices) for p in head.data.polygons]
sets=np.asarray([item.value for item in head.data.attributes['.sculpt_face_set'].data],dtype=np.int32)
edges=np.asarray([tuple(e.vertices) for e in head.data.edges],dtype=np.int32)
neck=np.zeros(len(source))
for v in head.data.vertices:
    for group in v.groups:
        if head.vertex_groups[group.group].name=='Neck':neck[v.index]=group.weight
weights,field_report=calculate(source,faces,sets,edges,neck)
for name in ['Head','Jaw']:
    group=head.vertex_groups.get(name)
    if group:head.vertex_groups.remove(group)
groups={name:head.vertex_groups.new(name=name) for name in ['Head','Jaw']}
for i,jaw in enumerate(weights):
    skull=max(0,1-neck[i]-jaw)
    if jaw>0:groups['Jaw'].add([i],float(jaw),'REPLACE')
    if skull>0:groups['Head'].add([i],float(skull),'REPLACE')
keys=head.data.shape_keys;basis=coordinates(keys.key_blocks['Basis'].data)
old_open=coordinates(keys.key_blocks['JawOpen'].data)
# The inherited residual shape also uses the old world-space support. Restrict
# it to the same mandibular domain; do not let it pull fixed upper-lip skin.
new_open=basis+(old_open-basis)*weights[:,None]
keys.key_blocks['JawOpen'].data.foreach_set('co',new_open.astype(np.float32).ravel())

# Reproduce the existing deterministic fine-fuzz geometry with the repaired
# root weights and key. Larger scalp/ear fur and all coverage stay unchanged.
old_fuzz=bpy.data.objects['Nib v5 fine facial fuzz'];fuzz_name=old_fuzz.name
old_fuzz_points=coordinates(old_fuzz.data.vertices);fuzz_material=old_fuzz.data.materials[0]
old_fuzz_mesh=old_fuzz.data
bpy.data.objects.remove(old_fuzz,do_unlink=True)
if old_fuzz_mesh.users==0:bpy.data.meshes.remove(old_fuzz_mesh)
new_fuzz=fine_face_fuzz(head,collection,rig,fuzz_material,False)
if new_fuzz.name!=fuzz_name:raise RuntimeError('Unexpected repaired fuzz object identity')
fuzz_points=coordinates(new_fuzz.data.vertices)
if fuzz_points.shape!=old_fuzz_points.shape:raise RuntimeError('Fine-fuzz topology changed')
fuzz_error=float(np.linalg.norm(fuzz_points-old_fuzz_points,axis=1).max())
if fuzz_error>1e-6:raise RuntimeError('Fine-fuzz root reconstruction changed visible geometry')
deformation=json.loads(scene['deformation_contract'])
attach_portable_drivers(new_fuzz,rig,deformation)
after=snapshots()
permitted={head.name,fuzz_name}
for name,item in before.items():
    if name not in after:raise RuntimeError('Repair removed authored component '+name)
    if name not in permitted and item!=after[name]:raise RuntimeError('Repair changed unrelated component '+name)
for name in permitted:
    for field in ['basis','polygons','matrix','uv']:
        if before[name][field]!=after[name][field]:
            if name==fuzz_name and field=='basis' and fuzz_error<=1e-6:continue
            raise RuntimeError('Repair changed pinned '+field+' on '+name)
    for key,value in before[name]['shapeKeys'].items():
        if key!='JawOpen' and value!=after[name]['shapeKeys'][key]:
            raise RuntimeError('Repair changed unrelated expression '+name+'/'+key)
if bind_before!=digest(np.asarray([list(bone.matrix_local) for bone in rig.data.bones],dtype=np.float64)):
    raise RuntimeError('Repair changed the skeleton bind')

report={'status':'Isolated Jaw repair candidate; native neutral/Tongue/Blink review required; no artistic acceptance',
        'artisticAcceptance':False,'source':str(SOURCE),'sourceSha256':EXPECTED,
        'jawField':field_report,'fineFuzzMaximumBasisDifferenceMeters':fuzz_error,
        'preservation':{'unrelatedMeshComponents':len(before)-2,'basisTopologyUVAndBindChange':False,
                        'clipChange':False,'facialMorphChange':['JawOpen'],
                        'noseAndUpperMuzzleJawInfluence':0.0},
        'authoringCode':{},'sharedChanged':False}
for filename in ['repair_saved_mouth_v5f.py','mouth_jaw_weights.py','nib_groom_v5.py']:
    path=HERE/filename;report['authoringCode'][filename]=sha(path)
    text=bpy.data.texts.new('Nib source v5f Jaw repair '+filename);text.write(path.read_text())
rig.animation_data.action=None
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
scene.frame_set(1);report['neutralCoordinates']=facial_snapshot(scene,rig,head)
rig.animation_data.action=bpy.data.actions['Idle'];scene.frame_set(1)
report['idleCoordinates']=facial_snapshot(scene,rig,head)
issues=[pose+': '+issue for pose in ['neutralCoordinates','idleCoordinates']
        for issue in report[pose]['neutralStructuralBlockersIfClosedMouthExpected']]
report['preRenderGate']={'passed':not issues,'blockingIssues':issues,
                       'scope':'Strict sampled neutral/Idle oral visibility and irises; diagnostics retain any failure'}
scene['source_version']='v5f isolated loop-aware Jaw repair after failed v5e Tongue; unaccepted'
bpy.ops.wm.save_as_mainfile(filepath=str(TARGET),compress=True)
if sha(SOURCE)!=EXPECTED:raise RuntimeError('Frozen source changed')
report['candidateSha256']=sha(TARGET)
REPORT.write_text(json.dumps(report,indent=2)+'\n',newline='\n')
print('NIB_V5F_MOUTH_REPAIR_SAVED',flush=True)
