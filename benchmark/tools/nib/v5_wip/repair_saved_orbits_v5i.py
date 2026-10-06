"""Isolated diagnostic native source from the audited loop/globe proposal.

The conservative full-Blink normal-rotation warning is retained. Generation
requires an explicit diagnostic flag and never establishes artistic approval.
Preserve the repaired Jaw, all ear/body tracks, rig, eyes, and unrelated parts.
"""
import argparse,hashlib,json,sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Matrix

HERE=Path(__file__).parent;ROOT=HERE.parents[3]
sys.path.insert(0,str(HERE));sys.path.insert(0,str(ROOT/'benchmark/tools/krag'))
from nib_groom_v5 import fine_face_fuzz
from runtime_reduction import attach_portable_drivers
from audit_face_coordinates import facial_snapshot

parser=argparse.ArgumentParser()
parser.add_argument('--diagnostic-allow-normal-rotation-warning',action='store_true')
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
ART=ROOT/'benchmark/art/nib';SOURCE=ART/'Nib_EarMotionStudy_v1.blend'
TARGET=ART/'Nib_Master_v5i_OrbitalClosure_WIP.blend';OUT=ART/'v5-study/native-head-v5i-orbital-closure.json'
AUDIT=ART/'v5-study/native-v5i-orbital-geometry-audit.json'
GEOMETRY=ROOT/'benchmark/local/nib-v5i-orbital-geometry.npz'
PROPOSAL=ART/'v5-study/native-v5i-orbital-proposal-rotation.json'
CACHE=ROOT/'benchmark/local/nib-v5i-orbital-proposal-rotation.npz'
EXPECTED='4f5465424ae61376af51e5f57a38cc197f6e4c5bb127b4748193e435d87bbd47'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if sha(SOURCE)!=EXPECTED:raise RuntimeError('Pinned source differs from audited ear study')
if TARGET.exists():raise RuntimeError('Preserve existing orbital-closure candidate')
audit=json.loads(AUDIT.read_text());proposal=json.loads(PROPOSAL.read_text())
if audit['sourceSha256']!=EXPECTED or proposal['sourceSha256']!=EXPECTED:raise RuntimeError('Orbital source provenance mismatch')
if sha(GEOMETRY)!=audit['cacheSha256'] or sha(CACHE)!=proposal['proposalCacheSha256']:raise RuntimeError('Orbital numerical cache provenance mismatch')
for name,digest in proposal['codeSha256'].items():
    if sha(HERE/name)!=digest:raise RuntimeError('Numerical recipe changed after evaluation: '+name)
if not proposal['numericGate']['passed'] and not args.diagnostic_allow_normal_rotation_warning:
    raise RuntimeError('Conservative normal-rotation gate still fails; diagnostic source must be explicit')
archive=np.load(GEOMETRY);prepared=np.load(CACHE)
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
    result={}
    for obj in collection.objects:
        if obj.type!='MESH':continue
        result[obj.name]={'basis':digest(coordinates(obj.data.vertices)),
            'polygons':digest(np.asarray([v for p in obj.data.polygons for v in p.vertices],dtype=np.int32)),
            'matrix':digest(np.asarray(obj.matrix_world,dtype=np.float32)),
            'weights':hashlib.sha256(json.dumps([[(obj.vertex_groups[g.group].name,float(g.weight)) for g in v.groups] for v in obj.data.vertices],separators=(',',':')).encode()).hexdigest(),
            'uv':{uv.name:digest(np.asarray([tuple(v.uv) for v in uv.data],dtype=np.float32)) for uv in obj.data.uv_layers},
            'materials':[m.name for m in obj.data.materials],
            'shapeKeys':{k.name:digest(coordinates(k.data)) for k in obj.data.shape_keys.key_blocks} if obj.data.shape_keys else {}}
    return result
before=snapshots();bind=digest(np.asarray([list(b.matrix_local) for b in rig.data.bones],dtype=np.float64))
basis=coordinates(keys.key_blocks['Basis'].data)
if not np.array_equal(basis,archive['basis']):raise RuntimeError('Actual Basis does not match the eye audit')
old_relative={key.name:coordinates(key.data).astype(np.float64)-basis for key in keys.key_blocks}
new_basis=prepared['neutral'];changed={'Blink_L','Blink_R','Squint_L','Squint_R'}
for key in keys.key_blocks:
    relative=prepared[key.name] if key.name in changed else old_relative[key.name]
    key.data.foreach_set('co',(new_basis+relative).astype(np.float32).ravel())
head.data.vertices.foreach_set('co',new_basis.astype(np.float32).ravel());head.data.update()
other_error=0.
for key in keys.key_blocks:
    if key.name not in changed:
        other_error=max(other_error,float(np.linalg.norm(coordinates(key.data)-coordinates(keys.key_blocks['Basis'].data)-old_relative[key.name],axis=1).max()))
if other_error>1e-6:raise RuntimeError('Unrelated facial expression changed relative to the new Basis')
for driver,mute in driver_state:driver.mute=mute
fuzz=bpy.data.objects['Nib v5 fine facial fuzz'];fuzz_name=fuzz.name
material=fuzz.data.materials[0];mesh=fuzz.data;bpy.data.objects.remove(fuzz,do_unlink=True)
if mesh.users==0:bpy.data.meshes.remove(mesh)
fuzz=fine_face_fuzz(head,collection,rig,material,False)
if fuzz.name!=fuzz_name:raise RuntimeError('Unexpected fine-fuzz identity')
attach_portable_drivers(fuzz,rig,json.loads(scene['deformation_contract']))
after=snapshots();permitted={head.name,fuzz.name}
for name,item in before.items():
    if name not in after:raise RuntimeError('Orbital source lost an authored component')
    if name not in permitted and item!=after[name]:raise RuntimeError('Orbital source changed unrelated component '+name)
for field in ['polygons','matrix','weights','uv','materials']:
    if before[head.name][field]!=after[head.name][field]:raise RuntimeError('Orbital repair changed pinned '+field)
if bind!=digest(np.asarray([list(b.matrix_local) for b in rig.data.bones],dtype=np.float64)):raise RuntimeError('Orbital source changed bind')
report={'status':'Diagnostic loop/globe closure candidate; full-Blink fold warning and artistic review remain unresolved',
    'source':str(SOURCE),'sourceSha256':EXPECTED,'auditSha256':sha(AUDIT),'proposalSha256':sha(PROPOSAL),
    'numericGate':proposal['numericGate'],'numericGeometry':{'neutral':proposal['neutral'],'poses':proposal['poses']},
    'preserved':{'unrelatedComponents':len(before)-2,'jawWeightsRigUVTopologyMaterialsAndClips':True,
        'maximumOtherExpressionRelativeDifferenceMeters':other_error,'independentEarMotion':True},
    'artisticAcceptance':False,'sharedChanged':False,'authoringCode':{}}
for filename in ['repair_saved_orbits_v5i.py','orbital_closure_v5i.py','evaluate_orbital_proposal.py']:
    report['authoringCode'][filename]=sha(HERE/filename)
    text=bpy.data.texts.new('Nib v5i orbital study '+filename);text.write((HERE/filename).read_text())
rig.animation_data.action=None
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
scene.frame_set(1);report['neutralCoordinates']=facial_snapshot(scene,rig,head)
rig.animation_data.action=bpy.data.actions['Idle'];scene.frame_set(1);report['idleCoordinates']=facial_snapshot(scene,rig,head)
issues=[pose+': '+issue for pose in ['neutralCoordinates','idleCoordinates'] for issue in report[pose]['neutralStructuralBlockersIfClosedMouthExpected']]
if not proposal['numericGate']['passed']:issues.append('Full-Blink fold/canthus triangles rotate over 90 degrees relative to neutral; actual diagnostic inspection required')
report['preRenderGate']={'passed':not issues,'blockingIssues':issues,'scope':'Inherited oral/iris gates and explicit conservative full-Blink warning; diagnostic override is not acceptance'}
scene['source_version']='v5i diagnostic anatomical orbital closure on ear-study source; no runtime or art promotion'
bpy.ops.wm.save_as_mainfile(filepath=str(TARGET),compress=True)
if sha(SOURCE)!=EXPECTED:raise RuntimeError('Pinned source changed')
report['candidateSha256']=sha(TARGET)
OUT.write_text(json.dumps(report,indent=2)+'\n',newline='\n')
print('NIB_V5I_ORBITAL_DIAGNOSTIC_SOURCE_SAVED',flush=True)
