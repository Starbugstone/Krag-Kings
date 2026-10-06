"""Bounded numerical hand-space study using the actual saved Nib hand.

This evaluates ordinary LBS from saved Basis, weights and rest joints. It does
not claim native animation evaluation, surface collision clearance or acting
approval. Root owns actual clip authoring and subsequent rendered validation.
"""
import argparse,hashlib,json,math,os
from pathlib import Path
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
import numpy as np
parser=argparse.ArgumentParser();parser.add_argument('--cache',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);a=parser.parse_args()
d=json.loads(a.cache.read_text());p=np.asarray(d['vertices'],float);bones=d['bones'];names=list(bones);weights=np.zeros((len(p),len(names)))
for i,row in enumerate(d['weights']):
 for n,v in row:weights[i,names.index(n)]=v
if np.max(abs(weights.sum(axis=1)-1))>1e-6:raise RuntimeError('Actual saved hand weights do not sum to one')
heads={n:np.asarray(b['head']) for n,b in bones.items()};tails={n:np.asarray(b['tail']) for n,b in bones.items()}
# Actual knuckle row defines flexion; palmar -Y is the existing authored frame.
flex_axis=heads['Index1_L']-heads['Little1_L'];flex_axis/=np.linalg.norm(flex_axis)
opp_axis=np.asarray([0.,-1,0])
def rotation(axis,angle):
 axis=axis/np.linalg.norm(axis);x,y,z=axis;t=math.radians(angle);c=math.cos(t);s=math.sin(t);k=np.array([[0,-z,y],[z,0,-x],[-y,x,0.]])
 return c*np.eye(3)+(1-c)*np.outer(axis,axis)+s*k
run={'Index':[40,55,20],'Middle':[40,50,20],'Ring':[40,52,20],'Little':[42,55,20]}
walk={'Index':[27,42,16],'Middle':[28,42,16],'Ring':[29,44,17],'Little':[30,45,18]}
def pose(digits,opposition,thumb_flex):
 R={n:np.eye(3) for n in names};H={n:v.copy() for n,v in heads.items()}
 for digit,angles in digits.items():
  accum=0
  for j,angle in enumerate(angles,1):
   n=f'{digit}{j}_L';accum+=angle;R[n]=rotation(flex_axis,accum)
   if j>1:
    prev=f'{digit}{j-1}_L';H[n]=H[prev]+R[prev]@(heads[n]-heads[prev])
 for j in [1,2]:
  n=f'Thumb{j}_L';R[n]=rotation(flex_axis,sum(thumb_flex[:j]))@rotation(opp_axis,opposition)
  if j==2:H[n]=H['Thumb1_L']+R['Thumb1_L']@(heads[n]-heads['Thumb1_L'])
 q=np.zeros_like(p)
 for j,n in enumerate(names):q+=weights[:,j,None]*((p-heads[n])@R[n].T+H[n])
 return q,R,H
thumb=weights[:,names.index('Thumb2_L')];axis=tails['Thumb2_L']-heads['Thumb2_L'];progress=((p-heads['Thumb2_L'])@axis)/(axis@axis)
tip_ids=np.flatnonzero((thumb>.65)&(progress>.65));palm_ids=np.flatnonzero(weights[:,names.index('Hand_L')]>.85)
index_ids=np.flatnonzero(weights[:,names.index('Index1_L')]>.65)
if min(len(tip_ids),len(palm_ids),len(index_ids))<8:raise RuntimeError('Actual tip/palm/proximal-index sample regions insufficient')
# Vertex-cloud separation is descriptive and upper-bounds true surface gap.
def gaps(q):
 out={}
 for label,ids in [('palm',palm_ids),('indexProximal',index_ids)]:
  delta=q[tip_ids,None,:]-q[ids][None,:,:];distance=np.linalg.norm(delta,axis=2);where=np.unravel_index(np.argmin(distance),distance.shape)
  out[label]={'minimumVertexCloudGapMeters':float(distance[where]),'thumbVertex':int(tip_ids[where[0]]),'otherVertex':int(ids[where[1]])}
 return out
rows=[]
for label,digits,opposition,tf in [('Rest',{},0,[0,0]),('Walk fingers only',walk,0,[0,0]),('Run fingers only',run,0,[0,0]),('Walk thumb restrained',walk,12,[5,8]),('Run thumb restrained',run,20,[8,10]),('Run thumb stronger comparison',run,28,[10,12])]:
 q,R,H=pose(digits,opposition,tf);thumbtip=H['Thumb2_L']+R['Thumb2_L']@(tails['Thumb2_L']-heads['Thumb2_L'])
 rows.append({'name':label,'fingerAnglesDegrees':digits,'thumbOppositionDegrees':opposition,'thumbFlexDegrees':tf,'gaps':gaps(q),'thumbBoneTipMeters':thumbtip.tolist(),'maximumMeshDisplacementMeters':float(np.linalg.norm(q-p,axis=1).max())})
report={'status':'Actual saved hand coordinates and weights; numerical hand-space LBS proposals only, not native posed proof','source':d['source'],'sourceSha256':d['sourceSha256'],'cacheSha256':hashlib.sha256(a.cache.read_bytes()).hexdigest(),'savedMeshVertices':len(p),'savedMeshFaces':d['faceCount'],'maximumWeightSumError':float(np.max(abs(weights.sum(axis=1)-1))),'flexAxisHandBindSpace':flex_axis.tolist(),'oppositionAxisHandBindSpace':opp_axis.tolist(),'regions':{'distalThumbVertices':len(tip_ids),'palmVertices':len(palm_ids),'proximalIndexVertices':len(index_ids)},'rows':rows,'interpretation':'Distances between semantic vertex clouds are upper bounds on surface separation; do not claim no intersections. Thumb opposition is an unaccepted bounded control proposal on the actual two-joint anatomy. Keep the thumb beside curled index rather than forced into the palm.','nativeReviewRequired':['Inspect relaxed thumb/web at Idle and Run extrema','Check true triangle-surface contact and side/front silhouette','Confirm no thumb-pad penetration or palm/web stretching'],'codeSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'sharedChanged':False}
a.output.parent.mkdir(exist_ok=True,parents=True);a.output.write_text(json.dumps(report,indent=2)+'\n',newline='\n')
print(json.dumps({'output':str(a.output),'rows':[{k:v for k,v in r.items() if k in ['name','gaps','thumbBoneTipMeters']} for r in rows]}))
