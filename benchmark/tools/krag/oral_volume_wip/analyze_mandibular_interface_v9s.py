"""Attribute inherited lateral jaw crease from the actual saved-pose cache.
No Blender source or current candidate is edited by this diagnostic.
"""
import os
os.environ.setdefault('OMP_NUM_THREADS','2');os.environ.setdefault('OPENBLAS_NUM_THREADS','2')
from pathlib import Path
import sys,json,hashlib
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
for path in (HERE,HERE.parent/'landmark_wip'):
 sys.path.insert(0,str(path))
from profile_and_lip import member,distances
from rest_profile_v9r import OralProfile
from broad_oral_v9s import BroadOral
from landmark_relief import Relief
cache=ROOT/'benchmark/local/krag-normal-mouth-v9p-posed-cache.npz';d=np.load(cache)
p,q,e,m,w=d['Head_basis'],d['Head_posed'],d['Head_edges'],d['Head_membership'],d['Head_weights'][:,1]
interface=member(m,24)&member(m,33);distance=distances(p,e,interface)
a,b=e.T
length=np.linalg.norm(p[b]-p[a],axis=1);posed_length=np.linalg.norm(q[b]-q[a],axis=1)
max_displacement=abs(w[b]-w[a]);gradient=max_displacement/np.maximum(length,1e-8)
# Posterior/lateral cheek, away from the independently repaired commissures.
region=(abs(p[:,0])>.075)&(p[:,1]>-.115)&(p[:,2]>1.745)&(p[:,2]<1.895)&(distance<.035)
selected=np.flatnonzero(region[e].all(1)&(length>1e-6))
worst=selected[np.argsort(gradient[selected])[-12:]][::-1]
optical=Relief();profile=OralProfile(p,e,m,optical.eyes,optical.radii+.001,optical.head_support==0)
v9r=profile.head(p).astype(np.float32).astype(float)
v9s=BroadOral(v9r,e,m,optical.head_support==0).head(v9r).astype(np.float32).astype(float)
examples=[]
for i in worst:
 ids=e[i]
 examples.append({'vertexIds':ids.tolist(),'basis':p[ids].tolist(),'actualV9pPosed':q[ids].tolist(),
  'jawWeights':w[ids].tolist(),'restEdgeMeters':float(length[i]),'posedEdgeMeters':float(posed_length[i]),
  'actualPoseEdgeStretch':float(posed_length[i]/length[i]),'weightGradientPerMeter':float(gradient[i]),
  'interfaceDistancesMeters':distance[ids].tolist(),
  'v9sNeutralDisplacementFromV9pMeters':np.linalg.norm(v9s[ids]-p[ids],axis=1).tolist()})
report={'status':'Read-only actual v9p pose attribution with exact later recipe correspondence; current v9s native pose cache not captured',
 'artisticAcceptance':False,'cacheSha256':hashlib.sha256(cache.read_bytes()).hexdigest(),
 'currentV9sSourceSha256':'bbe3deadd7d9507a027afc0474206ad8528de8820606539246bc3242ffd171fd',
 'actualComparedViews':['benchmark/art/krag/renders/Krag_NormalMouth_v9p_OpenRight.png','benchmark/art/krag/renders/Krag_BroadOral_v9s_OpenRight.png'],
 'interfaceVertices':int(interface.sum()),'posteriorLateralEdgesExamined':len(selected),
 'interfaceJawWeightMaximum':float(w[interface].max()),
 'maximumLateralJawWeightGradientPerMeter':float(gradient[selected].max()),
 'maximumActualLateralEdgeStretch':float((posed_length[selected]/length[selected]).max()),
 'worstWeightEdges':examples,'toolSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
 'caution':'Actual images confirm the crease was already present in v9p. Numeric gradients are attribution evidence, not permission to change upper-lip/nose support or proof of a repaired surface.'}
path=ROOT/'benchmark/art/krag/oral-volume-study/v9s-lateral-jaw-attribution.json';path.write_text(json.dumps(report,indent=2)+'\n',newline='\n')
print(json.dumps({k:v for k,v in report.items()if k!='worstWeightEdges'},indent=2));print(json.dumps(examples[:3],indent=2))
