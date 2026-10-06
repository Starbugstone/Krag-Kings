"""Lightweight measured oral envelope/rigid arch attribution; no Blender writes.

Uses actual v9p saved-pose cache and exact v9r recipe/receipt. Reconstructed
v9r rim constraints are predictions, not a replacement for its actual mesh view.
"""
import os
os.environ.setdefault('OMP_NUM_THREADS','2')
os.environ.setdefault('OPENBLAS_NUM_THREADS','2')
from pathlib import Path
import json,hashlib,sys
import numpy as np
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
for folder in (HERE,HERE.parent/'landmark_wip',HERE.parent/'reference_fit_wip'):
 sys.path.insert(0,str(folder))
from profile_and_lip import member,ordered_rim,round_lower_rim
from rest_profile_v9r import OralProfile
from landmark_relief import Relief
CACHE=ROOT/'benchmark/local/krag-normal-mouth-v9p-posed-cache.npz'
z=np.load(CACHE)
basis,posed=z['Mouth_basis'],z['Mouth_posed']
parent=np.arange(len(basis))
def find(i):
 while parent[i]!=i:
  parent[i]=parent[parent[i]];i=parent[i]
 return i
for tri in z['Mouth_triangles']:
 root=find(int(tri[0]))
 for i in tri[1:]: parent[find(int(i))]=root
parts={}
for i in range(len(basis)):parts.setdefault(find(i),[]).append(i)
parts=[np.asarray(v) for v in parts.values()]
centers=np.asarray([basis[p].mean(0) for p in parts])
old=json.loads((ROOT/'benchmark/art/krag/anatomy-study/oral-occlusion-v9p.json').read_text())
owners={'Head':[],'Jaw':[]}
for tooth in old['teeth']:
 q=np.linalg.norm(centers-np.asarray(tooth['centerBasis']),axis=1)
 if q.min()>1e-6:raise RuntimeError('Saved tooth center no longer matches cache')
 owners[tooth['bone']].extend(parts[q.argmin()].tolist())
def rigid(ids):
 a,b=basis[ids],posed[ids];ac,bc=a.mean(0),b.mean(0)
 u,_,vt=np.linalg.svd((a-ac).T@(b-bc));r=vt.T@u.T
 if np.linalg.det(r)<0:raise RuntimeError('Rigid dental fit reflected')
 t=bc-r@ac;err=np.linalg.norm(a@r.T+t-b,axis=1)
 if err.max()>2e-6:raise RuntimeError('Dental region is not rigid in actual cache')
 m=np.eye(4);m[:3,:3]=r;m[:3,3]=t
 return m,float(err.max())
head,herr=rigid(owners['Head']);jaw,jerr=rigid(owners['Jaw'])
local_jaw=np.linalg.inv(head)@jaw
p=z['Head_basis'];optical=Relief()
profile=OralProfile(p,z['Head_edges'],z['Head_membership'],optical.eyes,optical.radii+.001,optical.head_support==0)
rest=profile.head(p)
lower=member(z['Head_membership'],24)&member(z['Head_membership'],7)
order=ordered_rim(z['Head_edges'],lower,rest)
# Endpoints remain fixed upper commissures. The target recipe only reads
# these posed endpoints and the full Jaw-owned central rim position.
rigid_jaw=rest@local_jaw[:3,:3].T+local_jaw[:3,3]
target=round_lower_rim(order,rest,rest,rigid_jaw)
receipt=json.loads((ROOT/'benchmark/art/krag/profile-oral-v9r.json').read_text())
crowns=[]
for c in receipt['canines']['sides']:
 tip=np.asarray(c['tip'])@local_jaw[:3,:3].T+local_jaw[:3,3]
 y,zlip=[float(np.interp(tip[0],target[:,0],target[:,axis]))for axis in (1,2)]
 crowns.append({'side':c['side'],'tipJawOnly':tip.tolist(),'rimAtTipX':[float(tip[0]),y,zlip],
                'tipAboveRimMeters':float(tip[2]-zlip),'tipBehindRimMeters':float(tip[1]-y),
                'neutralCanineHalfMouthRatio':abs(c['gingivalRoot'][0])/float(np.max(abs(rest[order,0])))})
report={'status':'Actual cached dental fits plus exact recipe rim prediction; new saved-mesh attribution still required',
 'artisticAcceptance':False,'cacheSha256':hashlib.sha256(CACHE.read_bytes()).hexdigest(),
 'v9rSource':receipt['source'],'actualRigidDentalFitMaximumMeters':{'Head':herr,'Jaw':jerr},
 'jawOnlyMatrixFromActualDentalPairs':local_jaw.tolist(),
 'neutralOralWidthMeters':float(np.ptp(rest[order,0])),
 'actualEyeSpacingMeters':float(abs(optical.eyes[0,0]-optical.eyes[1,0])),
 'oralWidthToEyeSpacing':float(np.ptp(rest[order,0])/abs(optical.eyes[0,0]-optical.eyes[1,0])),
 'conceptFrontManualReading':{'reference':'krag-kings-design/concept-art/01-krag-character-sheet.png',
  'commissuresPixels':[[258,88],[313,88]],'eyesPixels':[[265,58],[305,58]],
  'landmarkUncertaintyPixels':3,'approximateLipToEyeSpacing':55/40,
  'caution':'Illustration is uncalibrated; use as a width interval, not canonical dimensions. Dental arch is provisional and must fit the external envelope.'},
 'lowerRimPredictionSamples':target[::8].tolist(),'canineVisibilityCrossSections':crowns,
 'conclusions':['Current true lip span is narrower than interocular distance, unlike the reference front reading.',
 'Rigid canines occupy the highly supported commissure region; compare tip height and anterior offset against actual posed rim.',
 'Next source must fit the whole oral envelope and provisional arch together, preserving optical surfaces and actual jaw range.']}
OUT=ROOT/'benchmark/art/krag/oral-volume-study/v9r-arch-envelope-attribution.json'
OUT.write_text(json.dumps(report,indent=2)+'\n',newline='\n')
print(json.dumps(report,indent=2))
