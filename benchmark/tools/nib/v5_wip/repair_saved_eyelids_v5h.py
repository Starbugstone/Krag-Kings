"""Isolated continuous Blink-support repair; requires actual v5g audit first.

Preserve neutral anatomy, mouth/Jaw repair, other expressions, materials, rig,
clips and shared assets. Only Blink_L/R and their fine-fuzz deformation change.
"""
import hashlib,json,sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Matrix

HERE=Path(__file__).parent;ROOT=HERE.parents[3]
sys.path.insert(0,str(HERE));sys.path.insert(0,str(ROOT/'benchmark/tools/krag'))
from eyelid_support_v5h import calculate
from nib_groom_v5 import fine_face_fuzz
from runtime_reduction import attach_portable_drivers
from audit_face_coordinates import facial_snapshot

ART=ROOT/'benchmark/art/nib';SOURCE=ART/'Nib_Master_v5g_FacePlanes_WIP.blend'
TARGET=ART/'Nib_Master_v5h_EyelidRepair_WIP.blend';REPORT=ART/'v5-study/native-head-v5h-eyelid-repair.json'
AUDIT=ART/'v5-study/native-v5g-eyelid-audit.json';CACHE=ROOT/'benchmark/local/nib-v5g-eyelid-audit.npz'
EXPECTED='1586cb3a4c66897be5d1b2c5ba43fdb34a462a6fc96d6d51d90fa417dd185db9'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if sha(SOURCE)!=EXPECTED:raise RuntimeError('Frozen v5g source differs from audited input')
if TARGET.exists():raise RuntimeError('Refusing to overwrite an existing eyelid candidate')
audit=json.loads(AUDIT.read_text());archive=np.load(CACHE,allow_pickle=True)
if audit['sources'][SOURCE.name]!=EXPECTED or audit['cacheSha256']!=sha(CACHE):
    raise RuntimeError('Actual audit/cache provenance mismatch')
for name in ['Blink_L','Blink_R']:
    metric=audit['keyBoundaryGradients'][name]
    if metric['v5g']['maximumBoundaryGradient']<=2*metric['v5f']['maximumBoundaryGradient']:
        raise RuntimeError('Actual audit does not establish the expected new cutoff defect: '+name)

bpy.ops.wm.open_mainfile(filepath=str(SOURCE),load_ui=False)
scene=bpy.context.scene;rig=bpy.data.objects['Nib_Rig'];head=bpy.data.objects['Nib v5 fitted animation face']
collection=bpy.data.collections['Nib_Authored_Components'];head.active_shape_key_index=0
rig.animation_data.action=None
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
keys=head.data.shape_keys;driver_state=[(d,bool(d.mute)) for d in keys.animation_data.drivers]
for driver,_ in driver_state:driver.mute=True
for key in keys.key_blocks:key.value=0
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
            'weights':hashlib.sha256(json.dumps([[(obj.vertex_groups[g.group].name,float(g.weight)) for g in v.groups] for v in obj.data.vertices],separators=(',',':')).encode()).hexdigest(),
            'uv':{uv.name:digest(np.asarray([tuple(v.uv) for v in uv.data],dtype=np.float32)) for uv in obj.data.uv_layers},
            'shapeKeys':{k.name:digest(coordinates(k.data)) for k in obj.data.shape_keys.key_blocks} if obj.data.shape_keys else {}}
    return data
before=snapshots();bind=digest(np.asarray([list(b.matrix_local) for b in rig.data.bones],dtype=np.float64))
source=np.asarray([tuple(v.vector) for v in head.data.attributes['nib_source_position'].data])
faces=[list(p.vertices) for p in head.data.polygons];sets=np.asarray([v.value for v in head.data.attributes['.sculpt_face_set'].data])
edges=np.asarray([tuple(e.vertices) for e in head.data.edges],dtype=np.int32)
basis=coordinates(keys.key_blocks['Basis'].data)
if not np.array_equal(source,archive['source']) or not np.array_equal(basis,archive['basis']):
    raise RuntimeError('Actual cached surface correspondence is not identical')
support,field=calculate(source,faces,sets,edges,width=.004)
metrics={};length=np.linalg.norm(basis[edges[:,1]]-basis[edges[:,0]],axis=1)
for name in ['Blink_L','Blink_R']:
    old=archive['old_'+name];new=old*support[:,None]
    previous=archive['new_'+name]
    keys.key_blocks[name].data.foreach_set('co',(basis+new).astype(np.float32).ravel())
    metrics[name]={'maximumChangeFromV5gMeters':float(np.linalg.norm(new-previous,axis=1).max()),
        'maximumDeltaMeters':float(np.linalg.norm(new,axis=1).max()),
        'maximumEdgeDeltaGradient':float((np.linalg.norm(new[edges[:,1]]-new[edges[:,0]],axis=1)/np.maximum(length,1e-10)).max())}
head.data.update()
for driver,mute in driver_state:driver.mute=mute

fuzz=bpy.data.objects['Nib v5 fine facial fuzz'];fuzz_name=fuzz.name;old_points=coordinates(fuzz.data.vertices)
material=fuzz.data.materials[0];mesh=fuzz.data;bpy.data.objects.remove(fuzz,do_unlink=True)
if mesh.users==0:bpy.data.meshes.remove(mesh)
fuzz=fine_face_fuzz(head,collection,rig,material,False)
if fuzz.name!=fuzz_name:raise RuntimeError('Unexpected fine-fuzz identity')
fuzz_error=float(np.linalg.norm(coordinates(fuzz.data.vertices)-old_points,axis=1).max())
if fuzz_error>1e-6:raise RuntimeError('Fine-fuzz visible Basis changed')
attach_portable_drivers(fuzz,rig,json.loads(scene['deformation_contract']))
after=snapshots();permitted={head.name,fuzz.name}
for name,item in before.items():
    if name not in after:raise RuntimeError('Repair removed authored component '+name)
    if name not in permitted and item!=after[name]:raise RuntimeError('Repair changed unrelated component '+name)
for name in permitted:
    for field_name in ['basis','polygons','matrix','weights','uv']:
        if before[name][field_name]!=after[name][field_name]:raise RuntimeError('Repair changed pinned '+field_name+' on '+name)
    for key,value in before[name]['shapeKeys'].items():
        if key not in ['Blink_L','Blink_R'] and value!=after[name]['shapeKeys'][key]:
            raise RuntimeError('Repair changed unrelated expression '+name+'/'+key)
if bind!=digest(np.asarray([list(b.matrix_local) for b in rig.data.bones],dtype=np.float64)):
    raise RuntimeError('Repair changed rig bind')
report={'status':'Isolated continuous Blink repair candidate; actual pose review mandatory; no acceptance',
    'source':str(SOURCE),'sourceSha256':EXPECTED,'auditSha256':sha(AUDIT),'field':field,'keys':metrics,
    'fineFuzzMaximumBasisDifferenceMeters':fuzz_error,'artisticAcceptance':False,'sharedChanged':False,
    'preserved':{'unrelatedComponents':len(before)-2,'basisTopologyWeightsUVBindAndMaterials':True,
        'jawRepairAndOtherExpressions':True,'clips':True},'authoringCode':{}}
for filename in ['repair_saved_eyelids_v5h.py','eyelid_support_v5h.py']:
    path=HERE/filename;report['authoringCode'][filename]=sha(path)
    text=bpy.data.texts.new('Nib source v5h '+filename);text.write(path.read_text())
rig.animation_data.action=None
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
scene.frame_set(1);report['neutralCoordinates']=facial_snapshot(scene,rig,head)
rig.animation_data.action=bpy.data.actions['Idle'];scene.frame_set(1);report['idleCoordinates']=facial_snapshot(scene,rig,head)
issues=[pose+': '+issue for pose in ['neutralCoordinates','idleCoordinates'] for issue in report[pose]['neutralStructuralBlockersIfClosedMouthExpected']]
report['preRenderGate']={'passed':not issues,'blockingIssues':issues,'scope':'Strict neutral/Idle oral visibility and irises; diagnostic failure retained'}
scene['source_version']='v5h isolated continuous Blink support after failed v5g; unaccepted'
bpy.ops.wm.save_as_mainfile(filepath=str(TARGET),compress=True)
if sha(SOURCE)!=EXPECTED:raise RuntimeError('Frozen source changed')
report['candidateSha256']=sha(TARGET)
REPORT.write_text(json.dumps(report,indent=2)+'\n',newline='\n')
print('NIB_V5H_EYELID_REPAIR_SAVED',flush=True)
