"""Provisional hand-volume sculpt from the actual saved skin/bone centers.

The Basis-only review attributes the broad palmar ridge to the source surface.
Reduce its excessive depth while retaining hand length, finger-row width, all
joint locations, topology, UVs, weights, clips and relative corrective deltas.
This is an isolated shape proposal, never an automatic engine promotion.
"""
import argparse,hashlib,json,sys
from pathlib import Path
import bpy,numpy as np
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE),str(HERE.parent/'nib/restorative_wip')]
from contracts import rig_contract,surface_hash
from export_contract import CLIPS,select_action
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--source-sha256',required=True);p.add_argument('--output',type=Path,required=True)
p.add_argument('--palm-depth-scale',type=float,default=.55);p.add_argument('--digit-depth-scale',type=float,default=.78)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  while chunk:=f.read(1024*1024):h.update(chunk)
 return h.hexdigest()
if sha(a.source)!=a.source_sha256:raise RuntimeError('Pinned source changed')
if a.output.exists():raise RuntimeError('Preserve previous shape study')
if not .4<=a.palm_depth_scale<=1 or not .65<=a.digit_depth_scale<=1:raise RuntimeError('Unbounded depth proposal')
a.output.mkdir(parents=True)
bpy.ops.wm.open_mainfile(filepath=str(a.source),load_ui=False)
rig=bpy.data.objects['Krag_Rig'];before=rig_contract(rig);stable={o.name:surface_hash(o) for o in bpy.data.objects if o.type=='MESH' and o.name!='BioForearm_L'}
obj=bpy.data.objects['BioForearm_L'];mesh=obj.data
# Actual surface vertices and rig share model-local coordinates in this source.
if np.max(np.abs(np.asarray(obj.matrix_world)-np.asarray(rig.matrix_world)))>1e-7:raise RuntimeError('Mesh and rig spaces differ')
raw=np.asarray([v.co[:] for v in mesh.vertices],dtype=np.float64)
row=np.asarray(rig.data.bones['Finger1_0_L'].head_local)-np.asarray(rig.data.bones['Finger1_3_L'].head_local);row/=np.linalg.norm(row)
long=np.asarray(rig.data.bones['Hand_L'].tail_local)-np.asarray(rig.data.bones['Hand_L'].head_local);long-=row*np.dot(row,long);long/=np.linalg.norm(long);palm=np.cross(row,long);palm/=np.linalg.norm(palm)
if palm[0]>-.8:raise RuntimeError('Unexpected actual hand orientation')
names=[g.name for g in obj.vertex_groups];weights=np.zeros((len(raw),len(names)))
for vertex in mesh.vertices:
 for g in vertex.groups:weights[vertex.index,g.group]=g.weight
centers=np.zeros_like(raw);influence=np.zeros(len(raw));reduction=np.zeros(len(raw))
for i,name in enumerate(names):
 if not (name=='Hand_L' or name.endswith('_L') and name.startswith(('Finger','Thumb'))):continue
 b=rig.data.bones[name];head=np.asarray(b.head_local);axis=np.asarray(b.tail_local)-head
 t=np.clip(((raw-head)@axis)/np.dot(axis,axis),0,1);center=head+t[:,None]*axis
 w=weights[:,i];centers+=w[:,None]*center;influence+=w
 reduction+=w*(1-(a.palm_depth_scale if name=='Hand_L' else a.digit_depth_scale))
centers/=np.maximum(influence[:,None],1e-12)
depth=np.sum((raw-centers)*palm,axis=1)
delta=-palm[None,:]*(depth*reduction)[:,None];delta[influence<1e-8]=0
if np.max(np.linalg.norm(delta,axis=1))>.08:raise RuntimeError('Hand-depth change exceeds bounded80mm study limit')
new=raw+delta
mesh.calc_loop_triangles();tri=np.asarray([tuple(t.vertices) for t in mesh.loop_triangles])
def normals(v):return np.cross(v[tri[:,1]]-v[tri[:,0]],v[tri[:,2]]-v[tri[:,0]])
n0=normals(raw);n1=normals(new);ar0=np.linalg.norm(n0,axis=1);ar1=np.linalg.norm(n1,axis=1);valid=ar0>1e-12
flipped=(np.sum(n0*n1,axis=1)<0)&valid;degenerate=(ar1<1e-12)&valid
if degenerate.any() or flipped.any():raise RuntimeError('Native hand sculpt creates a degenerate/rotated triangle '+str({'newDegenerate':int(degenerate.sum()),'normalRotationsOver90':int(flipped.sum())}))
keys=mesh.shape_keys.key_blocks if mesh.shape_keys else [];morph_error=0.
for key in keys:
 values=np.asarray([v.co[:] for v in key.data],dtype=np.float64)
 corrected=np.asarray(values+delta,dtype=np.float32)
 error=(corrected.astype(np.float64)-np.asarray(new,dtype=np.float32))-(values-raw)
 morph_error=max(morph_error,float(np.max(np.linalg.norm(error,axis=1))))
 key.data.foreach_set('co',corrected.ravel())
if morph_error>3e-7:raise RuntimeError('Relative corrective delta changed beyond float32 tolerance')
mesh.vertices.foreach_set('co',np.asarray(new,dtype=np.float32).ravel());mesh.update()
if rig_contract(rig)!=before:raise RuntimeError('Shape correction changed rig/actions')
for name,h in stable.items():
 if surface_hash(bpy.data.objects[name])!=h:raise RuntimeError('Unrelated mesh changed '+name)
for name in CLIPS:bpy.data.actions[name].use_fake_user=True
select_action(bpy,rig,bpy.data.actions['Idle']);bpy.context.scene.frame_set(1)
output=a.output/'Krag_HandDepth_v1.blend';expected=surface_hash(obj)
bpy.ops.wm.save_as_mainfile(filepath=str(output),compress=True)
bpy.ops.wm.open_mainfile(filepath=str(output),load_ui=False)
if rig_contract(bpy.data.objects['Krag_Rig'])!=before:raise RuntimeError('Saved rig/actions changed')
if surface_hash(bpy.data.objects['BioForearm_L'])!=expected:raise RuntimeError('Saved corrected mesh changed')
for name,h in stable.items():
 if surface_hash(bpy.data.objects[name])!=h:raise RuntimeError('Saved unrelated mesh changed '+name)
if sha(a.source)!=a.source_sha256:raise RuntimeError('Input changed')
report={'status':'Actual isolated hand-depth proposal; native pose/shape review required','source':str(a.source),'sourceSha256':a.source_sha256,'output':str(output),'outputSha256':sha(output),'savedSourceReopened':True,'proposal':{'palmDepthScale':a.palm_depth_scale,'digitDepthScale':a.digit_depth_scale},'maximumPointMoveMeters':float(np.max(np.linalg.norm(delta,axis=1))),'changedPoints':int(np.sum(np.linalg.norm(delta,axis=1)>1e-8)),'unchangedMeshComponents':len(stable),'allBindAndActionHashesPreserved':True,'handLengthAndWidthCoordinatesPreserved':{'maxAlongErrorMeters':float(np.max(np.abs(delta@long))),'maxAcrossErrorMeters':float(np.max(np.abs(delta@row)))},'triangleCount':len(tri),'newDegenerateTriangles':int(degenerate.sum()),'normalRotationsOver90':int(flipped.sum()),'minimumAreaRatio':float(np.min(ar1[valid]/ar0[valid])),'recipeSha256':sha(Path(__file__)),'artisticAcceptance':False,'surfaceIntersectionProven':False,'sharedChanged':False,'engineExported':False}
(a.output/'hand-depth.json').write_text(json.dumps(report,indent=2)+'\n');print('KRAG_HAND_DEPTH_SAVED_AND_REOPENED',flush=True)
