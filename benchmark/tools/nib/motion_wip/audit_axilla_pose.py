"""Read-only actual Body Shoot/LBS audit plus original source face-set inventory.

No saved mesh changes, no retarget, no acceptance gate relaxation. Root allocates
this short native inspection separately from character generation/rendering.
"""
import json,hashlib,sys
from pathlib import Path
import bpy,numpy as np
from mathutils import Matrix
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sys.path.insert(0,str(HERE));from forearm_twist import smooth
SOURCE=ROOT/'benchmark/art/nib/groom-study/coherent79-v2-runtime-wide-nap/Nib_Groom_v6_runtime_WIP.blend'
EXPECTED='edc3aef50c7ef70b3eb609a5da3c1b739b80b7127f6afa03636204ee1b4b2def'
LIBRARY=ROOT/'benchmark/art/reference-anatomy/blender-studio-human-base-meshes/source/human-base-meshes-bundle-v1.4.1/human_base_meshes_bundle.blend'
LIBRARY_SHA='3c121505651140ceb4d69fd1d8923f7788ffadd81672f5be14845a5f2c75c137'
OUT=ROOT/'benchmark/art/nib/motion-study/axilla-actual-shoot-audit-v2.json'
CACHE=ROOT/'benchmark/local/nib-axilla-actual-shoot-v2.npz';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if sha(SOURCE)!=EXPECTED or sha(LIBRARY)!=LIBRARY_SHA:raise RuntimeError('Pinned source changed')
if OUT.exists() or CACHE.exists():raise RuntimeError('Preserve prior audit output')
bpy.ops.wm.open_mainfile(filepath=str(SOURCE),load_ui=False);rig=bpy.data.objects['Nib_Rig'];scene=bpy.context.scene
obj=bpy.data.objects['Continuous Nib anatomy organic']
for o in bpy.data.collections['Nib_Authored_Components'].objects:
 if o.type=='MESH':o.hide_set(o!=obj)
for track in rig.animation_data.nla_tracks:track.mute=True
rig.animation_data.action=bpy.data.actions['Shoot'];a,b=map(float,rig.animation_data.action.frame_range);frame=a+.46*(b-a)
scene.frame_set(int(frame),subframe=frame%1);bpy.context.view_layer.update()
if not np.allclose(np.asarray(obj.matrix_world),np.eye(4),atol=1e-8) or not np.allclose(np.asarray(rig.matrix_world),np.eye(4),atol=1e-8):raise RuntimeError('Expected preserved identity bind object frames')
mesh=obj.data;p=np.asarray([v.co[:] for v in mesh.vertices],float);raw=np.asarray([v.vector[:] for v in mesh.attributes['Nib_BodyReferencePosition'].data],float);domain=np.asarray([v.value for v in mesh.attributes['Nib_ArmDomain'].data],float)
keys=mesh.shape_keys;basis=np.asarray([v.co[:] for v in keys.key_blocks['Basis'].data],float);mixed=basis.copy();keyvalues={}
for key in keys.key_blocks:
 if key.name=='Basis':continue
 keyvalues[key.name]=float(key.value);mixed+=float(key.value)*(np.asarray([v.co[:] for v in key.data],float)-basis)
weights=np.zeros((len(p),len(obj.vertex_groups)));names=[g.name for g in obj.vertex_groups]
for v in mesh.vertices:
 for g in v.groups:weights[v.index,g.group]=g.weight
matrices={name:np.asarray(rig.pose.bones[name].matrix@rig.data.bones[name].matrix_local.inverted(),float) for name in names}
def lbs(points):
 result=np.zeros_like(points);h=np.column_stack((points,np.ones(len(points))))
 for j,name in enumerate(names):result+=(h@matrices[name].T)[:,:3]*weights[:,j,None]
 return result
skin_only=lbs(basis);full=lbs(mixed)
evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());evaluated_mesh=evaluated.to_mesh();actual=np.asarray([v.co[:] for v in evaluated_mesh.vertices],float);evaluated.to_mesh_clear()
if actual.shape!=full.shape:raise RuntimeError('Evaluated Body topology differs')
error=np.linalg.norm(actual-full,axis=1)
if error.max()>2e-6:raise RuntimeError('Explicit LBS does not reproduce actual native surface: '+str(error.max()))
threshold=.120+.035*np.clip((raw[:,2]-1.20)/.16,0,1);fit=smooth(threshold,threshold+.09,abs(raw[:,0]));ids=np.flatnonzero((fit>.75)&(domain<.25)&(raw[:,2]>1.10)&(raw[:,2]<1.37))
# Inventory actual licensed source face sets; labels still require anatomical
# interpretation against source surface, not arbitrary field thresholding.
with bpy.data.libraries.load(str(LIBRARY),link=False) as (available,loaded):loaded.objects=['GEO-body_male_realistic']
reference=loaded.objects[0];ref=reference.data;rp=np.asarray([v.co[:] for v in ref.vertices],float);rf=[list(p.vertices) for p in ref.polygons];attr=ref.attributes.get('.sculpt_face_set');sets=np.asarray([v.value for v in attr.data],int) if attr else np.full(len(rf),-1,int)
source_sets=[]
for number in np.unique(sets):
 faces=np.flatnonzero(sets==number);vertices=np.unique(np.concatenate([np.asarray(rf[i],int) for i in faces]));points=rp[vertices]
 source_sets.append({'id':int(number),'faces':len(faces),'vertices':len(vertices),'bounds':[points.min(0).tolist(),points.max(0).tolist()]})
np.savez_compressed(CACHE,rest=basis,source_points=raw,arm_domain=domain,fit_domain=fit,posed=actual,skin_only=skin_only,weights=weights,group_names=np.asarray(names),candidate_ids=ids,reference_points=rp,reference_faces=np.asarray(rf,dtype=object),reference_face_sets=sets)
rows=[{'vertex':int(i),'sourcePosition':raw[i].tolist(),'restPosition':basis[i].tolist(),'actualShootPosition':actual[i].tolist(),'skinOnlyPosition':skin_only[i].tolist(),'fitArmBlend':float(fit[i]),'skinArmDomain':float(domain[i]),'weights':{n:float(weights[i,j]) for j,n in enumerate(names) if weights[i,j]>1e-6}} for i in sorted(ids,key=lambda i:float(domain[i]-fit[i]))[:20]]
report={'status':'Actual source Shoot evaluation and portable LBS attribution; no repair or acceptance','source':str(SOURCE),'sourceSha256':EXPECTED,'action':'Shoot','normalizedTime':.46,'frame':frame,'sourceBodyTag':{'variant':obj.get('variant'),'bone':obj.get('bone')},'restVertices':len(p),'candidateCount':len(ids),'candidateRestBounds':[basis[ids].min(0).tolist(),basis[ids].max(0).tolist()],'candidateShootBounds':[actual[ids].min(0).tolist(),actual[ids].max(0).tolist()],'explicitLbsVsNativeMaxErrorMeters':float(error.max()),'bodyMorphWeights':keyvalues,'bodyMorphPosedMaxDeltaMeters':float(np.linalg.norm(full-skin_only,axis=1).max()),'worstDomainRows':rows,'poseSkinMatrices':{k:v.tolist() for k,v in matrices.items()},'referenceFaceSets':source_sets,'referenceSha256':LIBRARY_SHA,'cache':str(CACHE),'cacheSha256':sha(CACHE),'authoringCodeSha256':sha(Path(__file__)),'sourceUnchanged':sha(SOURCE)==EXPECTED,'sharedChanged':False}
if not report['sourceUnchanged']:raise RuntimeError('Read-only audit modified source')
OUT.write_text(json.dumps(report,indent=2)+'\n',newline='\n');print('NIB_AXILLA_ACTUAL_SHOOT_AUDIT_COMPLETE',flush=True)
