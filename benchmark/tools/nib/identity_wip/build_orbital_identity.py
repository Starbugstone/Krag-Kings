"""Isolated wider anatomical lid aperture on the current coherent source.

No face, ear, clothing or action acceptance follows from numerical construction.
Keep the actual full-Blink warning visible and inspect native extreme poses.
"""
import argparse,hashlib,json,sys
from pathlib import Path
import bpy,numpy as np
from mathutils import Matrix

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sys.path[:0]=[str(HERE.parent/'restorative_wip'),str(HERE.parent/'v5_wip'),str(ROOT/'benchmark/tools/krag')]
from contracts import rig_contract,surface_hash
from nib_groom_v5 import fine_face_fuzz
from runtime_reduction import attach_portable_drivers
from audit_face_coordinates import facial_snapshot

parser=argparse.ArgumentParser()
parser.add_argument('--source',type=Path,required=True)
parser.add_argument('--source-sha256',required=True)
parser.add_argument('--output-dir',type=Path,required=True)
parser.add_argument('--diagnostic-normal-warning',action='store_true')
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
proposal_path=ROOT/'benchmark/art/nib/identity-study/orbital-identity-v2-numerical.json'
cache_path=ROOT/'benchmark/art/nib/identity-study/orbital-identity-v2.npz'
proposal=json.loads(proposal_path.read_text())
if sha(args.source)!=args.source_sha256:raise RuntimeError('Pinned coherent source changed')
if sha(cache_path)!=proposal['proposalCacheSha256']:raise RuntimeError('Prepared orbital cache differs')
if proposal['hardStructuralFailure']:raise RuntimeError('Prepared orbital neutral has a structural failure')
if proposal['fullBlinkNormalWarningsRetained'] and not args.diagnostic_normal_warning:
    raise RuntimeError('Full closure normal rotation warning needs explicit diagnostic review')
if args.output_dir.exists():raise RuntimeError('Preserve previous native identity candidate')
if not args.output_dir.resolve().is_relative_to((ROOT/'benchmark/art/nib').resolve()):raise RuntimeError('Owned isolated source output required')
args.output_dir.mkdir(parents=True)
prepared=np.load(cache_path)
bpy.ops.wm.open_mainfile(filepath=str(args.source),load_ui=False)
scene=bpy.context.scene;rig=bpy.data.objects['Nib_Rig'];head=bpy.data.objects['Nib v5 fitted animation face']
collection=bpy.data.collections['Nib_Authored_Components'];fuzz=bpy.data.objects['Nib v5 fine facial fuzz']
canonical=['Idle','Walk','Run','Melee','Shoot','Hit','FacePerformance']
for name in canonical:
    if name not in bpy.data.actions:raise RuntimeError('Input lost canonical action '+name)
    bpy.data.actions[name].use_fake_user=True
before=rig_contract(rig);retained={o.name:surface_hash(o) for o in bpy.data.objects if o.type=='MESH' and o not in [head,fuzz]}
rig.animation_data.action=None
for track in rig.animation_data.nla_tracks:track.mute=True
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
head.active_shape_key_index=0;keys=head.data.shape_keys
driver_state=[(d,d.mute) for d in keys.animation_data.drivers]
for d,_ in driver_state:d.mute=True
for key in keys.key_blocks:key.value=0
scene.frame_set(1);bpy.context.view_layer.update()
coordinates=lambda data:np.asarray([v.co[:] for v in data],np.float32)
basis=coordinates(keys.key_blocks['Basis'].data)
if not np.array_equal(basis,prepared['expectedBasis']):raise RuntimeError('Actual coherent face differs from the numerical orbital input')
def face_contract(obj):
    return {'weights':[[(g.group,g.weight) for g in v.groups] for v in obj.data.vertices],
        'groups':[g.name for g in obj.vertex_groups],'faces':[list(p.vertices) for p in obj.data.polygons],
        'uv':{u.name:[list(v.uv) for v in u.data] for u in obj.data.uv_layers},
        'materials':[m.name for m in obj.data.materials],'matrix':[list(r) for r in obj.matrix_world]}
face_before=face_contract(head)
relative={k.name:coordinates(k.data).astype(float)-basis for k in keys.key_blocks}
neutral=prepared['neutral'];changed={'Blink_L','Blink_R','Squint_L','Squint_R'}
for key in keys.key_blocks:
    delta=prepared[key.name] if key.name in changed else relative[key.name]
    key.data.foreach_set('co',(neutral+delta).astype(np.float32).ravel())
head.data.vertices.foreach_set('co',neutral.astype(np.float32).ravel());head.data.update()
other_error=max(float(np.linalg.norm(coordinates(k.data)-coordinates(keys.key_blocks['Basis'].data)-relative[k.name],axis=1).max()) for k in keys.key_blocks if k.name not in changed)
if other_error>1e-6:raise RuntimeError('Unrelated facial shape changed beyond float32 precision')
for d,mute in driver_state:d.mute=mute
material=fuzz.data.materials[0];old_mesh=fuzz.data;bpy.data.objects.remove(fuzz,do_unlink=True)
if old_mesh.users==0:bpy.data.meshes.remove(old_mesh)
fuzz=fine_face_fuzz(head,collection,rig,material,False)
attach_portable_drivers(fuzz,rig,json.loads(scene['deformation_contract']))
if face_contract(head)!=face_before:raise RuntimeError('Orbital fit altered repaired jaw weights, topology, UVs or materials')
if rig_contract(rig)!=before:raise RuntimeError('Orbital fit changed body/face/ear bind or clips')
for name,digest in retained.items():
    if surface_hash(bpy.data.objects[name])!=digest:raise RuntimeError('Orbital fit changed unrelated mesh '+name)
changed_hashes={o.name:surface_hash(o) for o in [head,fuzz]}
neutral_coordinates=facial_snapshot(scene,rig,head)
rig.animation_data.action=bpy.data.actions['Idle'];scene.frame_set(1)
idle_coordinates=facial_snapshot(scene,rig,head)
issues=[pose+': '+issue for pose,data in [('neutral',neutral_coordinates),('Idle',idle_coordinates)] for issue in data['neutralStructuralBlockersIfClosedMouthExpected']]
issues.append('Full Blink normal rotation warning retained; actual folds/collisions require the native posed views')
scene['source_version']='Orbital identity v1 on coherent source; wider true lid aperture with conservative full-Blink warning; unaccepted'
scene['nib_orbital_identity']=json.dumps({'inputSha256':args.source_sha256,'proposalSha256':sha(proposal_path),'faceOnly':True,'allRigAndActionsPreserved':True,'artisticAcceptance':False})
text=bpy.data.texts.new('Nib orbital identity source v1');text.write(Path(__file__).read_text())
target=args.output_dir/'Nib_Coherent_OrbitalIdentity_v1.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(target),compress=True)
bpy.ops.wm.open_mainfile(filepath=str(target),load_ui=False)
if rig_contract(bpy.data.objects['Nib_Rig'])!=before:raise RuntimeError('Saved identity source changed rig/actions')
for name,digest in {**retained,**changed_hashes}.items():
    if surface_hash(bpy.data.objects[name])!=digest:raise RuntimeError('Saved identity source changed mesh payload '+name)
if sha(args.source)!=args.source_sha256:raise RuntimeError('Input changed')
report={'status':'Actual diagnostic orbital source; neutral and extreme-expression review required','source':str(args.source),
    'sourceSha256':args.source_sha256,'candidate':str(target),'candidateSha256':sha(target),'savedSourceReopened':True,
    'proposalReportSha256':sha(proposal_path),'proposalCacheSha256':sha(cache_path),'preservedRig':before,
    'retainedMeshHashes':retained,'changedMeshHashes':changed_hashes,'otherExpressionMaxDifferenceMeters':other_error,
    'neutralCoordinates':neutral_coordinates,'idleCoordinates':idle_coordinates,
    'preRenderGate':{'passed':False,'blockingIssues':issues,'scope':'Diagnostic normal-rotation and inherited oral flags retained, never hidden by numeric aperture improvement'},
    'numericEvidence':{'eyes':proposal['eyes'],'neutral':proposal['neutral'],'poses':proposal['poses']},
    'codeSha256':{p.name:sha(p) for p in [Path(__file__),HERE.parent/'restorative_wip/contracts.py',HERE.parent/'v5_wip/nib_groom_v5.py']},
    'artisticAcceptance':False,'sharedChanged':False,
    'pending':['Actual neutral/Blink/Tongue/eye closeup','Adult nose/brow/cheek identity','Coordinated steep cupped ears and finer flowing groom','All inherited body and garment failures']}
(args.output_dir/'source.json').write_text(json.dumps(report,indent=2)+'\n',newline='\n')
print('NIB_ORBITAL_IDENTITY_SAVED_AND_REOPENED',flush=True)
