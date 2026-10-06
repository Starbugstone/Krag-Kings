"""Prepared next face study; pin the reviewed rooted-card input explicitly.

Not executed. Preserve all canonical actions, bone binds, lid/Jaw semantics
and the mouth aperture. This cannot produce a shared/runtime handoff directly.
"""
import argparse,hashlib,json,sys
from pathlib import Path
import bpy,numpy as np
from mathutils import Matrix
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sys.path[:0]=[str(HERE),str(HERE.parent/'restorative_wip'),str(HERE.parent/'v5_wip'),str(ROOT/'benchmark/tools/krag')]
from contracts import rig_contract,surface_hash
from nib_groom_v5 import fine_face_fuzz
from runtime_reduction import attach_portable_drivers
from audit_face_coordinates import facial_snapshot
from ocular_identity import iris_coordinates,materials
from transfer_face_groom import transfer

parser=argparse.ArgumentParser()
parser.add_argument('--source',type=Path,required=True)
parser.add_argument('--source-sha256',required=True)
parser.add_argument('--source-report',type=Path,required=True)
parser.add_argument('--output-dir',type=Path,required=True)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if sha(args.source)!=args.source_sha256:raise RuntimeError('Pinned rooted-card input changed')
inherited=json.loads(args.source_report.read_text())
if inherited.get('candidateSha256')!=args.source_sha256 or not inherited.get('savedSourceReopened'):
    raise RuntimeError('Actual rooted-card source receipt required')
if args.output_dir.exists():raise RuntimeError('Preserve earlier adult identity study')
if not args.output_dir.resolve().is_relative_to((ROOT/'benchmark/art/nib/identity-study').resolve()):raise RuntimeError('Owned isolated identity output required')
proposal_dir=ROOT/'benchmark/art/nib/identity-study/adult-face-numerical-v2'
proposal=json.loads((proposal_dir/'numerical.json').read_text())
if sha(proposal_dir/'proposal.npz')!=proposal['proposalCacheSha256'] or proposal['hardStructuralFailure']:
    raise RuntimeError('Prepared numerical proposal changed or failed')
prepared=np.load(proposal_dir/'proposal.npz')
bpy.ops.wm.open_mainfile(filepath=str(args.source),load_ui=False)
scene=bpy.context.scene;rig=bpy.data.objects['Nib_Rig'];head=bpy.data.objects['Nib v5 fitted animation face']
fuzz=bpy.data.objects['Nib v5 fine facial fuzz'];collection=bpy.data.collections['Nib_Authored_Components']
if not scene.get('nib_groom_root_attachment'):raise RuntimeError('Next geometry study requires the actual rooted groom source')
canonical=['Idle','Walk','Run','Melee','Shoot','Hit','FacePerformance']
for name in canonical:
    if name not in bpy.data.actions:raise RuntimeError('Input lost canonical action '+name)
    bpy.data.actions[name].use_fake_user=True
before=rig_contract(rig)
groom=[o for o in collection.objects if o.type=='MESH' and o.get('bone') in ['Head','Jaw'] and o.name.startswith(('Nib v6 cards ','Nib v6 opaque accents '))]
eyes=[bpy.data.objects['Nib v5 fitted '+part+' '+side] for part in ['iris','sclera'] for side in ['L','R']]
changed_names={o.name for o in [head,fuzz,*groom,*eyes]}
retained={o.name:surface_hash(o) for o in bpy.data.objects if o.type=='MESH' and o.name not in changed_names}
rig.animation_data.action=None
for track in rig.animation_data.nla_tracks:track.mute=True
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
keys=head.data.shape_keys;driver_state=[(d,d.mute) for d in keys.animation_data.drivers]
for driver,_ in driver_state:driver.mute=True
for key in keys.key_blocks:key.value=0
scene.frame_set(1);bpy.context.view_layer.update()
coordinates=lambda data:np.asarray([v.co[:] for v in data],np.float32)
basis=coordinates(keys.key_blocks['Basis'].data)
if not np.array_equal(basis,prepared['expectedBasis']):raise RuntimeError('Actual face differs from the numerical orbital source')

def structural(obj):
    return {'faces':[(list(p.vertices),p.material_index) for p in obj.data.polygons],
        'weights':[[(g.group,g.weight) for g in v.groups] for v in obj.data.vertices],
        'groups':[g.name for g in obj.vertex_groups],
        'uv':{u.name:[list(v.uv) for v in u.data] for u in obj.data.uv_layers},
        'matrix':[list(r) for r in obj.matrix_world]}

structures={o.name:structural(o) for o in [head,*groom,*eyes]}
ocular_geometry={o.name:coordinates(o.data.vertices) for o in eyes}
relative={k.name:coordinates(k.data).astype(np.float64)-basis for k in keys.key_blocks}
delta=prepared['delta'];neutral=prepared['target']
groom_report=transfer(head,basis,delta,groom)
for key in keys.key_blocks:key.data.foreach_set('co',(neutral+relative[key.name]).astype(np.float32).ravel())
head.data.vertices.foreach_set('co',neutral.astype(np.float32).ravel());head.data.update()
relative_error=max(float(np.linalg.norm(coordinates(k.data)-coordinates(keys.key_blocks['Basis'].data)-relative[k.name],axis=1).max()) for k in keys.key_blocks)
if relative_error>1e-6:raise RuntimeError('Existing expression delta changed beyond float32 precision')
for driver,mute in driver_state:driver.mute=mute

# The actual warm nose pigment attribute remains. Only its dry surface response
# is corrected; color cannot substitute for the proposed continuous projection.
face_material=head.data.materials[0].copy();face_material.name='Nib_IdentityFacialSkin';head.data.materials[0]=face_material
rough=face_material.node_tree.nodes.get('Nib nose leather roughness')
if rough is None or rough.type!='MIX_RGB':raise RuntimeError('Expected actual masked nose roughness network')
rough.inputs[2].default_value=(.55,.55,.55,1)
ocular_materials=materials();ocular_report=[]
iris_attributes={}
for obj in eyes:
    part='iris' if ' iris ' in obj.name else 'globe'
    if part=='iris':
        ocular_report.append(iris_coordinates(obj))
        data=np.asarray([v.vector[:] for v in obj.data.attributes['Nib_IrisCoord'].data],np.float32)
        iris_attributes[obj.name]=hashlib.sha256(data.tobytes()).hexdigest()
    obj.data.materials.clear();obj.data.materials.append(ocular_materials[part])
    if not np.array_equal(coordinates(obj.data.vertices),ocular_geometry[obj.name]):raise RuntimeError('Ocular pigment study moved its shell')

fuzz_material=fuzz.data.materials[0];old_mesh=fuzz.data;bpy.data.objects.remove(fuzz,do_unlink=True)
if old_mesh.users==0:bpy.data.meshes.remove(old_mesh)
fuzz=fine_face_fuzz(head,collection,rig,fuzz_material,False)
attach_portable_drivers(fuzz,rig,json.loads(scene['deformation_contract']))
for name,contract in structures.items():
    if structural(bpy.data.objects[name])!=contract:raise RuntimeError('Identity pass changed topology, weights, UVs or transforms: '+name)
for name,digest in retained.items():
    if surface_hash(bpy.data.objects[name])!=digest:raise RuntimeError('Unrelated mesh changed: '+name)
if rig_contract(rig)!=before:raise RuntimeError('Identity pass changed bind or actions')
neutral_audit=facial_snapshot(scene,rig,head)
rig.animation_data.action=bpy.data.actions['Idle'];scene.frame_set(1)
idle_audit=facial_snapshot(scene,rig,head)
issues=list(inherited['preRenderGate'].get('blockingIssues',[]))
for pose,audit in [('new neutral',neutral_audit),('new Idle',idle_audit)]:
    issues.extend(pose+': '+issue for issue in audit['neutralStructuralBlockersIfClosedMouthExpected'])
gate={'passed':False,'blockingIssues':list(dict.fromkeys(issues)),
    'scope':'Inherited flags plus actual new neutral/Idle coordinate checks; face geometry and optical views still require review'}
changed={name:surface_hash(bpy.data.objects[name]) for name in changed_names}
scene['source_version']='Adult identity v1; broad continuous face relief and actual iris pigment; unaccepted'
scene['nib_identity_iris_contract']=json.dumps({'material':'Nib_IdentityOcularIris','attribute':'Nib_IrisCoord','requiredBake':'Actual assigned iris surfaces with nonoverlapping UV atlas; no generic tile','representation':'Existing opaque curved shell, no separate transparent cornea','artisticAcceptance':False})
scripts=[Path(__file__),HERE/'ocular_identity.py',HERE/'transfer_face_groom.py',HERE/'adult_face_field.py']
for p in scripts:
    text=bpy.data.texts.new('Nib adult identity v1 '+p.name);text.write(p.read_text())
args.output_dir.mkdir(parents=True)
target=args.output_dir/'Nib_Coherent_AdultIdentity_v1.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(target),compress=True)
bpy.ops.wm.open_mainfile(filepath=str(target),load_ui=False)
if rig_contract(bpy.data.objects['Nib_Rig'])!=before:raise RuntimeError('Saved identity source changed bind/actions')
for name,digest in {**retained,**changed}.items():
    if surface_hash(bpy.data.objects[name])!=digest:raise RuntimeError('Saved identity mesh differs: '+name)
for name,digest in iris_attributes.items():
    data=np.asarray([v.vector[:] for v in bpy.data.objects[name].data.attributes['Nib_IrisCoord'].data],np.float32)
    if hashlib.sha256(data.tobytes()).hexdigest()!=digest:raise RuntimeError('Saved iris pigment coordinates differ: '+name)
if sha(args.source)!=args.source_sha256:raise RuntimeError('Input changed')
report={'status':'Actual adult identity source; all visual gates pending','source':str(args.source),'sourceSha256':args.source_sha256,
    'sourceReportSha256':sha(args.source_report),'candidate':str(target),'candidateSha256':sha(target),'savedSourceReopened':True,
    'preservedRig':before,'retainedMeshHashes':retained,'changedMeshHashes':changed,'relativeExpressionDeltaMaxErrorMeters':relative_error,
    'numericalProposal':proposal,'groomSurfaceTransfer':groom_report,'ocularCoordinates':ocular_report,'irisAttributeHashes':iris_attributes,
    'neutralCoordinates':neutral_audit,'idleCoordinates':idle_audit,'preRenderGate':gate,
    'numericEvidence':inherited['numericEvidence'],'codeSha256':{p.name:sha(p) for p in scripts},
    'artisticAcceptance':False,'sharedChanged':False,
    'pending':['Actual Neutral/Profile/ThreeQuarter/Blink/Tongue and optical closeup','True skin/groom root attachment after face warp',
               'Actual eye field atlas and source/baked/engine material parity','Full adult ear/groom/clothing identity and inherited deformation defects']}
(args.output_dir/'source.json').write_text(json.dumps(report,indent=2)+'\n',newline='\n')
print('NIB_ADULT_IDENTITY_SAVED_AND_REOPENED',flush=True)
