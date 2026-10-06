"""Prepared diagnostic macroface, preserving frozen engine content.

This may run only in the allocated guarded slot. The explicit diagnostic flag
retains the known combined-smile warning; it never labels art/export accepted.
"""
import argparse,hashlib,json,sys
from pathlib import Path
import bpy,numpy as np
from mathutils import Matrix,Vector
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sys.path[:0]=[str(HERE),str(HERE.parent/'restorative_wip'),str(HERE.parent/'v5_wip')]
from macro_field_candidate import transform,jacobian
from contracts import rig_contract,surface_hash
from audit_face_coordinates import facial_snapshot
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--source-sha256',required=True);p.add_argument('--output-dir',type=Path,required=True);p.add_argument('--allow-combination-diagnostic',action='store_true');args=p.parse_args(sys.argv[sys.argv.index('--')+1:]);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if sha(args.source)!=args.source_sha256 or args.source_sha256!='ed53df0741441724ea84b09af8124132a1be6f33c1d02a31b9b377ddb53c8903':raise RuntimeError('Wrong pinned coherent regional source')
if args.output_dir.exists():raise RuntimeError('Preserve previous macroface candidate')
if not args.output_dir.resolve().is_relative_to((ROOT/'benchmark/art/nib/identity-study').resolve()):raise RuntimeError('Owned isolated source output required')
proposal_dir=ROOT/'benchmark/art/nib/identity-study/macroface-numerical-v6';numerical=json.loads((proposal_dir/'numerical.json').read_text());proposal=np.load(proposal_dir/'proposal.npz');params=numerical['params']
if sha(proposal_dir/'proposal.npz')!=numerical['proposalSha256']:raise RuntimeError('Numerical target payload changed')
if sha(HERE/'macro_field_candidate.py')!=numerical['codeSha256']['macro_field_candidate.py']:raise RuntimeError('Candidate field recipe changed')
allowed=['Morph-combination nonlinear error exceeds0.25mm Playful']
if numerical['blockingIssues']!=allowed or not args.allow_combination_diagnostic:raise RuntimeError('Explicit known-warning diagnostic required; no general gate bypass')
inherited=json.loads((args.source.parent/'source.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(args.source),load_ui=False);scene=bpy.context.scene;rig=bpy.data.objects['Nib_Rig'];head=bpy.data.objects['Nib v5 fitted animation face'];collection=bpy.data.collections['Nib_Authored_Components']
for n in ['Idle','Walk','Run','Melee','Shoot','Hit','FacePerformance']:
 if n not in bpy.data.actions:raise RuntimeError('Missing canonical action '+n)
 bpy.data.actions[n].use_fake_user=True
before=rig_contract(rig);rig.animation_data.action=None
for track in rig.animation_data.nla_tracks:track.mute=True
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
scene.frame_set(1);bpy.context.view_layer.update()
coordinates=lambda data:np.asarray([v.co[:]for v in data],np.float64)
for key in head.data.shape_keys.key_blocks:
 if not np.array_equal(coordinates(key.data),proposal['expected_'+key.name]):raise RuntimeError('Actual saved shape differs from preflight '+key.name)
oral=('Provisional recessed oral cavity','Upper provisional gum ridge','Lower provisional gum ridge','Upper provisional tooth','Lower provisional tooth','Canonical dark blue Nib tongue')
changed=[o for o in collection.objects if o.type=='MESH'and(o==head or o.name=='Nib v5 fine facial fuzz' or o.name.startswith(('Nib v5 fitted iris ','Nib v5 fitted sclera ')+oral) or(o.name.startswith(('Nib v6 cards ','Nib v6 opaque accents '))and o.get('bone')in['Head','Jaw']))]
if not any(o.name.startswith('Canonical dark blue')for o in changed):raise RuntimeError('Actual oral geometry selection incomplete')
retained={o.name:surface_hash(o)for o in bpy.data.objects if o.type=='MESH'and o not in changed}
images={i.name:{'path':str(Path(bpy.path.abspath(i.filepath)).resolve()),'sha256':sha(Path(bpy.path.abspath(i.filepath)).resolve()),'colorspace':i.colorspace_settings.name}for i in bpy.data.images if i.source=='FILE'and i.filepath}
structures={};records=[];driver_states=[]
for obj in changed:
 mesh=obj.data;old=coordinates(mesh.vertices);keys=mesh.shape_keys
 if keys and keys.animation_data:
  for d in keys.animation_data.drivers:driver_states.append((d,d.mute));d.mute=True
 if keys:
  for k in keys.key_blocks:k.value=0
 matrix=head.matrix_world.inverted()@obj.matrix_world;L=np.asarray(matrix.to_3x3(),float);t=np.asarray(matrix.translation,float);inverse=np.linalg.inv(L)
 head_points=old@L.T+t
 normals=np.asarray([n.vector[:]for n in mesh.corner_normals],float)if mesh.has_custom_normals else None
 structure={'polygons':[(tuple(f.vertices),f.material_index)for f in mesh.polygons],'weights':[[(g.group,g.weight)for g in v.groups]for v in mesh.vertices],'uv':{u.name:[tuple(d.uv)for d in u.data]for u in mesh.uv_layers},'materials':[m.name if m else None for m in mesh.materials]}
 structures[obj.name]=structure
 target=(transform(head_points,params)-t)@inverse.T
 if obj==head and not np.allclose(target,proposal['target_Basis'],atol=1e-10,rtol=0):raise RuntimeError('Native field differs from numerical Basis')
 if keys:
  for key in keys.key_blocks:
   q=coordinates(key.data)@L.T+t;values=(transform(q,params)-t)@inverse.T
   if obj==head and not np.allclose(values,proposal['target_'+key.name],atol=1e-10,rtol=0):raise RuntimeError('Native shape differs from numerical proposal')
   key.data.foreach_set('co',values.astype(np.float32).ravel())
 mesh.vertices.foreach_set('co',target.astype(np.float32).ravel());mesh.update()
 if normals is not None:
  indices=np.asarray([l.vertex_index for l in mesh.loops]);J=jacobian(head_points,params);inverses=np.linalg.inv(J)
  normal_head=normals@inverse
  adjusted=np.einsum('ni,nij->nj',normal_head,inverses[indices])@L
  adjusted/=np.maximum(np.linalg.norm(adjusted,axis=1)[:,None],1e-15);mesh.normals_split_custom_set(adjusted.tolist())
 mesh.calc_loop_triangles();tri=np.asarray([f.vertices[:]for f in mesh.loop_triangles],int)
 def area(q):
  v=q[tri];return np.linalg.norm(np.cross(v[:,1]-v[:,0],v[:,2]-v[:,0]),axis=1)
 a,b=area(old),area(target)
 if np.any((a>1e-14)&(b<=1e-14)):raise RuntimeError('Native transfer introduced degenerate geometry '+obj.name)
 actual={'polygons':[(tuple(f.vertices),f.material_index)for f in mesh.polygons],'weights':[[(g.group,g.weight)for g in v.groups]for v in mesh.vertices],'uv':{u.name:[tuple(d.uv)for d in u.data]for u in mesh.uv_layers},'materials':[m.name if m else None for m in mesh.materials]}
 if actual!=structure:raise RuntimeError('Macro transfer changed topology/weights/UV/material '+obj.name)
 records.append({'object':obj.name,'vertices':len(old),'maximumMoveMeters':float(np.linalg.norm(target-old,axis=1).max()),'customCornerNormalsTransported':normals is not None,'shapeKeys':len(keys.key_blocks)if keys else 0})
for driver,mute in driver_states:driver.mute=mute
# Explicit facial bind migration: full ocular similarities and corresponding
# Jaw/Tongue pivots. No body/hand/ear/FaceRoot bind or canonical curve is changed.
allowed_bones={'Eye_L','Eye_R','Jaw','TongueBase','TongueTip'};old_bones={n:{'head':rig.data.bones[n].head_local.copy(),'tail':rig.data.bones[n].tail_local.copy(),'z':rig.data.bones[n].z_axis.copy(),'parent':rig.data.bones[n].parent.name}for n in allowed_bones}
M=head.matrix_world.inverted()@rig.matrix_world;I=M.inverted();bone_targets={}
for name,b in old_bones.items():
 q=np.asarray([M@b['head'],M@b['tail']]);new=transform(q,params);J=jacobian(q[:1],params)[0];z=I.to_3x3()@(Matrix(J.tolist())@(M.to_3x3()@b['z']))
 bone_targets[name]={'head':I@Vector(new[0]),'tail':I@Vector(new[1]),'z':z}
bpy.context.view_layer.objects.active=rig;rig.hide_set(False);rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
for name,v in bone_targets.items():
 b=rig.data.edit_bones[name];b.head=v['head'];b.tail=v['tail'];b.align_roll(v['z'])
bpy.ops.object.mode_set(mode='OBJECT');bpy.context.view_layer.update();after=rig_contract(rig)
if before['actions']!=after['actions']or before['world']!=after['world']:raise RuntimeError('Macro source changed action curves/rig transform')
unchanged_error=0.
for name,old in before['bones'].items():
 new=after['bones'][name]
 if old['parent']!=new['parent']or old['connected']!=new['connected']:raise RuntimeError('Hierarchy changed '+name)
 if name not in allowed_bones:
  e=float(np.max(np.abs(np.array(old['matrix'])-new['matrix'])));unchanged_error=max(unchanged_error,e)
  if e>1e-6:raise RuntimeError('Unrelated bind changed '+name)
for name,h in retained.items():
 if surface_hash(bpy.data.objects[name])!=h:raise RuntimeError('Unrelated source mesh changed '+name)
head_basis=coordinates(head.data.shape_keys.key_blocks['Basis'].data);neck=proposal['expectedBasis'][:,2]<=1.077
if not np.array_equal(head_basis[neck],proposal['expectedBasis'][neck]):raise RuntimeError('Retained fitted neck geometry moved')
audit=facial_snapshot(scene,rig,head)
scene['source_version']='Macroface diagnostic v1: coherent ocular/rest migration, broad envelope; unaccepted'
scene['nib_macroface_contract']=json.dumps({'diagnosticOnly':True,'sourceSha256':args.source_sha256,'numericalWarnings':numerical['blockingIssues'],'bindMigration':sorted(allowed_bones),'requiresMatchingFullMeshAndClips':True})
args.output_dir.mkdir(parents=True);rig.animation_data.action=bpy.data.actions['Idle'];scene.frame_set(1)
expected={o.name:surface_hash(o)for o in changed};target=args.output_dir/'Nib_Coherent_Macroface_Diagnostic_v1.blend';bpy.ops.wm.save_as_mainfile(filepath=str(target),compress=True);bpy.ops.wm.open_mainfile(filepath=str(target),load_ui=False)
if rig_contract(bpy.data.objects['Nib_Rig'])!=after:raise RuntimeError('Saved macroface changed exact post-migration rig/actions')
for name,digest in {**retained,**expected}.items():
 if surface_hash(bpy.data.objects[name])!=digest:raise RuntimeError('Saved source mesh differs '+name)
for name,entry in images.items():
 i=bpy.data.images[name];path=Path(bpy.path.abspath(i.filepath)).resolve();size=list(i.size)
 if str(path)!=entry['path']or sha(path)!=entry['sha256']or i.colorspace_settings.name!=entry['colorspace']or not i.has_data or min(size)<=0:raise RuntimeError('Saved connected texture differs '+name)
if sha(args.source)!=args.source_sha256:raise RuntimeError('Pinned regional source changed')
report={'status':'Actual diagnostic source only; known composition warning retained and all visual checks pending','source':str(args.source),'sourceSha256':args.source_sha256,'candidate':str(target),'candidateSha256':sha(target),'savedSourceReopened':True,'numericalReportSha256':sha(proposal_dir/'numerical.json'),'numericalWarnings':numerical['blockingIssues'],'preRenderGate':{'passed':False,'blockingIssues':list(inherited['preRenderGate']['blockingIssues'])+numerical['blockingIssues'],'diagnosticOverride':'Known combined morph nonlinearity '+str(numerical['combined']['Playful']['maximumMorphSuperpositionErrorMeters'])+' metres; no topology/Jacobian override'},'neutralCoordinates':audit,'preservedActions':after['actions'],'beforeRig':before,'afterRig':after,'allowedFacialBindMigration':sorted(allowed_bones),'maximumUnrelatedBindMatrixError':unchanged_error,'retainedMeshHashes':retained,'changedMeshHashes':expected,'objects':records,'connectedImages':images,'artisticAcceptance':False,'sharedChanged':False,'requiresMatchingFullMeshAndClipExport':True,'pending':['Neutral/Profile/ThreeQuarter identity','Actual Tongue and Blink contact, not only numerical correspondence','Updated source/baked ocular and face PBR comparison','No current engine promotion'],'codeSha256':{p.name:sha(p)for p in [Path(__file__),HERE/'macro_field_candidate.py']}}
(args.output_dir/'source.json').write_text(json.dumps(report,indent=2)+'\n',newline='\n');print('NIB_MACROFACE_DIAGNOSTIC_SAVED_AND_REOPENED',flush=True)
