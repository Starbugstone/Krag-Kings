"""Prepared coherent neck interface correction on the reviewed fine-atlas source.

Keeps the entire Head shape, rig, actions, hands, garments and material payloads.
The only geometric edits are the diagnosed Body neck interface and its fine
fuzz, identically transported to the restorative Body partition. No export.
"""
import argparse,hashlib,json,sys
from pathlib import Path
import bpy,numpy as np
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sys.path[:0]=[str(HERE),str(HERE.parent/'restorative_wip'),str(ROOT/'benchmark/tools/krag')]
from contracts import rig_contract,surface_hash
from runtime_reduction import attach_portable_drivers
from neck_topology import triangulate_boundary
parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,required=True);parser.add_argument('--source-sha256',required=True);parser.add_argument('--output-dir',type=Path,required=True)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:]);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if sha(args.source)!=args.source_sha256:raise RuntimeError('Pinned fine-atlas source changed')
if args.output_dir.exists():raise RuntimeError('Preserve prior native neck output')
if not args.output_dir.resolve().is_relative_to((ROOT/'benchmark/art/nib/identity-study').resolve()):raise RuntimeError('Owned neck output required')
proposal_dir=ROOT/'benchmark/art/nib/identity-study/neck-junction-numerical-v5'
report=json.loads((proposal_dir/'proposal.json').read_text());cache=proposal_dir/'proposal.npz'
if report['hardStructuralFailure'] or sha(cache)!=report['proposalSha256']:raise RuntimeError('Numeric neck proposal failed/changed')
data=np.load(cache);bpy.ops.wm.open_mainfile(filepath=str(args.source),load_ui=False)
scene=bpy.context.scene;rig=bpy.data.objects['Nib_Rig'];head=bpy.data.objects['Nib v5 fitted animation face']
body=bpy.data.objects['Continuous Nib anatomy organic'];grip=bpy.data.objects['Continuous Nib anatomy grip coherent']
fuzz=bpy.data.objects['Fine skin fuzz organic'];grip_fuzz=bpy.data.objects['Fine skin fuzz grip coherent']
changed_names={o.name for o in [head,body,grip,fuzz,grip_fuzz]};canonical=['Idle','Walk','Run','Melee','Shoot','Hit','FacePerformance']
for name in canonical:
    if name not in bpy.data.actions:raise RuntimeError('Input missing '+name)
    bpy.data.actions[name].use_fake_user=True
before=rig_contract(rig);retained={o.name:surface_hash(o)for o in bpy.data.objects if o.type=='MESH' and o.name not in changed_names}
image_paths={i.name:str(Path(bpy.path.abspath(i.filepath)).resolve())for i in bpy.data.images if i.source=='FILE' and i.filepath}
rig.animation_data.action=None
for track in rig.animation_data.nla_tracks:track.mute=True
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
scene.frame_set(1);bpy.context.view_layer.update()
def coords(obj):return np.asarray([v.co[:]for v in (obj.data.shape_keys.key_blocks['Basis'].data if obj.data.shape_keys else obj.data.vertices)],np.float32)
original=coords(body);head_original=coords(head)
if not np.array_equal(original,data['expectedBody']) or not np.array_equal(head_original,data['expectedHeadLocal']):raise RuntimeError('Cached source surface differs')
if not np.array_equal(np.asarray(body.matrix_world),np.eye(4)):raise RuntimeError('Expected identity Body transform')
delta=data['bodyDelta'];head_keys={k.name:np.asarray([v.co[:]for v in k.data],np.float32)for k in head.data.shape_keys.key_blocks}
# Exact existing partition mapping; do not regenerate the source cage or hand.
lookup={p.tobytes():i for i,p in enumerate(original)}
if len(lookup)!=len(original):raise RuntimeError('Ambiguous actual Body point correspondence')
gp=coords(grip)
try:grip_map=np.asarray([lookup[p.tobytes()]for p in gp],int)
except KeyError:raise RuntimeError('Restorative Body no longer matches Natural')
if not np.array_equal(gp,original[grip_map]):raise RuntimeError('Restorative source mismatch')
local_map={int(old):i for i,old in enumerate(grip_map)}
plans={int(k):v for k,v in report['boundaryQuadTriangulation'].items()}
grip_faces={tuple(int(grip_map[v])for v in p.vertices):p.index for p in grip.data.polygons}
grip_plan={}
for index,triangles in plans.items():
    original_face=tuple(body.data.polygons[index].vertices)
    if original_face not in grip_faces:raise RuntimeError('Restorative torso lost neck face')
    grip_plan[grip_faces[original_face]]=[[local_map[v]for v in t]for t in triangles]
# Fuzz is a disconnected six-point component layout, matched to the actual
# pre-edit Body. Move whole fiber rigidly; existing morph offsets stay exact.
body.data.calc_loop_triangles();tri=np.asarray([t.vertices[:]for t in body.data.loop_triangles],int)
tree=BVHTree.FromPolygons(original.tolist(),tri.tolist(),all_triangles=True)
fp=coords(fuzz).astype(np.float64)
if len(fp)%6 or any(len({v//6 for v in p.vertices})!=1 for p in fuzz.data.polygons):raise RuntimeError('Unsupported body fuzz layout')
fd=np.zeros_like(fp);fuzz_records=[]
for first in range(0,len(fp),6):
    root=fp[first:first+3].mean(0)
    if root[2]<.992:continue
    hit,normal,index,distance=tree.find_nearest(Vector(root))
    if index is None or distance>.0002:raise RuntimeError('Neck fuzz lost its original surface')
    q=original[tri[index]].astype(float);u=q[1]-q[0];v=q[2]-q[0];w=np.asarray(hit)-q[0]
    uu=u@u;uv=u@v;vv=v@v;uw=u@w;vw=v@w;den=uu*vv-uv*uv
    if den<1e-28:raise RuntimeError('Degenerate neck fuzz support')
    b=(vv*uw-uv*vw)/den;c=(uu*vw-uv*uw)/den;weights=np.asarray([1-b-c,b,c]);weights=np.maximum(weights,0);weights/=weights.sum()
    displacement=weights@delta[tri[index]]
    if np.linalg.norm(displacement)<1e-9:continue
    target=q+delta[tri[index]];n0=np.cross(q[1]-q[0],q[2]-q[0]);n1=np.cross(target[1]-target[0],target[2]-target[0]);rotation=Vector(n0).normalized().rotation_difference(Vector(n1).normalized())
    for i in range(first,first+6):fd[i]=root+displacement+np.asarray(rotation@Vector(fp[i]-root))-fp[i]
    fuzz_records.append({'strand':first//6,'originalSurfaceDistanceMeters':float(distance),'displacementMeters':float(np.linalg.norm(displacement))})
flookup={p.astype(np.float32).tobytes():i for i,p in enumerate(fp)}
if len(flookup)!=len(fp):raise RuntimeError('Ambiguous original fine-fuzz point correspondence')
gfp=coords(grip_fuzz)
try:gfmap=np.asarray([flookup[p.tobytes()]for p in gfp],int)
except KeyError:raise RuntimeError('Restorative fuzz lacks actual Natural correspondence')
if not np.array_equal(gfp,fp.astype(np.float32)[gfmap]):raise RuntimeError('Restorative fuzz differs')
body,body_topology=triangulate_boundary(body,plans);grip,grip_topology=triangulate_boundary(grip,grip_plan)
contract=json.loads(scene['deformation_contract'])
for obj in [body,grip]:attach_portable_drivers(obj,rig,contract)

def move(obj,amount):
    basis=coords(obj).astype(np.float64);maximum_error=0.
    for key in obj.data.shape_keys.key_blocks if obj.data.shape_keys else []:
        original_key=np.asarray([v.co[:]for v in key.data],np.float64);new=(original_key+amount).astype(np.float32);key.data.foreach_set('co',new.ravel())
        maximum_error=max(maximum_error,float(np.linalg.norm((new.astype(float)-(basis+amount).astype(np.float32).astype(float))-(original_key-basis),axis=1).max()))
    obj.data.vertices.foreach_set('co',(basis+amount).astype(np.float32).ravel());obj.data.update()
    if maximum_error>1e-6:raise RuntimeError('Named morph delta changed beyond float32 precision '+obj.name)
    return maximum_error
morph_errors={obj.name:move(obj,amount)for obj,amount in [(body,delta),(grip,delta[grip_map]),(fuzz,fd),(grip_fuzz,fd[gfmap])]}
if not np.array_equal(coords(grip),coords(body)[grip_map]):raise RuntimeError('Final restorative Body geometry differs')
body.data.calc_loop_triangles();actual_tri=np.asarray([t.vertices[:]for t in body.data.loop_triangles],int)
def triangle_vectors(points):
    q=points[actual_tri].astype(float);n=np.cross(q[:,1]-q[:,0],q[:,2]-q[:,0]);return n,np.linalg.norm(n,axis=1)
n0,a0=triangle_vectors(original);n1,a1=triangle_vectors(coords(body));normal_dot=np.sum(n0*n1,axis=1)/np.maximum(a0*a1,1e-25)
actual_surface={'triangles':len(actual_tri),'introducedDegenerates':int(np.sum((a0>1e-16)&(a1<=1e-16))),'trianglesRotatedOver90':int(np.sum(normal_dot<0)),'minimumAreaRatio':float((a1/np.maximum(a0,1e-25)).min())}
if actual_surface['introducedDegenerates'] or actual_surface['trianglesRotatedOver90']:raise RuntimeError('Actual native triangle surface failed: '+json.dumps(actual_surface))
# Head interface shares Neck with Body. Zero-Jaw geodesic field never changes
# lip/muzzle/mandibular support, and no Head point or shape coordinate changes.
influence=data['headNeckWeightInfluence'];head_weight_changes=0
for i,amount in enumerate(influence):
    if amount<=0:continue
    old={head.vertex_groups[g.group].name:g.weight for g in head.data.vertices[i].groups}
    if old.get('Jaw',0)>1e-7:raise RuntimeError('Neck correction touched Jaw skin')
    if set(old)-{'Head','Neck'}:raise RuntimeError('Unexpected facial support in neck interface')
    for name,value in old.items():head.vertex_groups[name].add([i],float(value*(1-amount)),'REPLACE')
    head.vertex_groups['Neck'].add([i],float(old.get('Neck',0)*(1-amount)+amount),'REPLACE');head_weight_changes+=1
for name,points in head_keys.items():
    if not np.array_equal(points,np.asarray([v.co[:]for v in head.data.shape_keys.key_blocks[name].data],np.float32)):raise RuntimeError('Head shape moved '+name)
# The intended seam is a narrow hidden overlap, not a claimed welded topology.
# Validate actual evaluated LBS/morph surfaces for canonical action poses.
ring=data['bodyRing'];seam=[]
for action,frame in [('Idle',1),('Walk',7),('Run',7),('Shoot',24),('FacePerformance',16),('FacePerformance',103)]:
    rig.animation_data.action=bpy.data.actions[action];scene.frame_set(frame);bpy.context.view_layer.update();deps=bpy.context.evaluated_depsgraph_get()
    eo=head.evaluated_get(deps);hm=eo.to_mesh();hp=[eo.matrix_world@v.co for v in hm.vertices];hf=[list(p.vertices)for p in hm.polygons]
    htree=BVHTree.FromPolygons(hp,hf);bo=body.evaluated_get(deps);bm=bo.to_mesh();distances=[]
    for i in ring:
        p=bo.matrix_world@bm.vertices[int(i)].co;hit,normal,index,distance=htree.find_nearest(p)
        if hit is None:raise RuntimeError('Posed neck has no Head support')
        distances.append(distance)
    eo.to_mesh_clear();bo.to_mesh_clear();maximum=max(distances)
    seam.append({'action':action,'frame':frame,'maximumBodyRingToHeadMeters':maximum})
    if maximum>.001:raise RuntimeError('Posed neck seam exceeds1mm: '+json.dumps(seam[-1]))
for name,digest in retained.items():
    if surface_hash(bpy.data.objects[name])!=digest:raise RuntimeError('Unrelated mesh changed '+name)
if rig_contract(rig)!=before:raise RuntimeError('Neck correction changed bind/actions')
changed={name:surface_hash(bpy.data.objects[name])for name in changed_names}
rig.animation_data.action=bpy.data.actions['Idle'];scene.frame_set(1)
scene['nib_neck_junction']=json.dumps({'sourceSha256':args.source_sha256,'planeMeters':1.035,'method':'Body neck fit to actual closed Head section; explicit local cap diagonals; posed overlap','welded':False,'artisticAcceptance':False})
scene['source_version']='Coherent Nib fitted neck interface; face, fine atlas, garments, rig/actions retained; unaccepted'
for script in [Path(__file__),HERE/'neck_topology.py',HERE/'prepare_neck_junction.py']:
    text=bpy.data.texts.new('Nib neck junction '+script.name);text.write(script.read_text())
args.output_dir.mkdir(parents=True);target=args.output_dir/'Nib_Coherent_NeckJunction_v1.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(target),compress=True);bpy.ops.wm.open_mainfile(filepath=str(target),load_ui=False)
if rig_contract(bpy.data.objects['Nib_Rig'])!=before:raise RuntimeError('Saved neck source changed rig/actions')
for name,digest in {**retained,**changed}.items():
    if surface_hash(bpy.data.objects[name])!=digest:raise RuntimeError('Saved mesh differs '+name)
for name,path in image_paths.items():
    actual=str(Path(bpy.path.abspath(bpy.data.images[name].filepath)).resolve())
    if actual!=path:raise RuntimeError('Saved image path changed '+name)
if sha(args.source)!=args.source_sha256:raise RuntimeError('Original fine-atlas input changed')
result={'status':'Actual saved neck candidate; diagnostic Profile/Neutral required','source':str(args.source),'sourceSha256':args.source_sha256,'candidate':str(target),'candidateSha256':sha(target),'savedSourceReopened':True,
 'preservedRig':before,'retainedMeshHashes':retained,'changedMeshHashes':changed,'numericProposal':report,'naturalTopology':body_topology,'restorativeTopology':grip_topology,
 'headGeometryAndAllExpressionsExact':True,'headNeckWeightVertices':head_weight_changes,'morphDeltaErrorsMeters':morph_errors,'fineFuzzRootTransfers':fuzz_records,'actualPosedSeam':seam,'actualNativeSurface':actual_surface,
 'interfaceConstruction':'Measured0.2mm inward overlap on a closed Head cross-section; not a weld','imageAbsolutePathsPreserved':True,
 'preRenderGate':{'passed':False,'blockingIssues':['Inherited adult likeness, sparse/stiff groom, rigid scarf and raised-arm defects; actual neck review pending']},
 'codeSha256':{p.name:sha(p)for p in [Path(__file__),HERE/'neck_topology.py',HERE/'prepare_neck_junction.py']},'sharedChanged':False,'artisticAcceptance':False}
(args.output_dir/'source.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n')
print('NIB_NECK_JUNCTION_SAVED_AND_REOPENED',flush=True)
