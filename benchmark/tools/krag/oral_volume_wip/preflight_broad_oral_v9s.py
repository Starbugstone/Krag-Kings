"""Numerical preparation against actual cached v9p topology and v9r recipe.

This does not claim a new saved source, pose validation or artistic success.
"""
import os
os.environ.setdefault('OMP_NUM_THREADS','2');os.environ.setdefault('OPENBLAS_NUM_THREADS','2')
from pathlib import Path
import sys,json,hashlib
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
for path in (HERE,HERE.parent/'landmark_wip',HERE.parent/'v9n_wip'):
 sys.path.insert(0,str(path))
from landmark_relief import Relief
from rest_profile_v9r import OralProfile
from broad_oral_v9s import BroadOral,lower_rim_target,weight_support
from profile_and_lip import member,distances,smooth
from macro_envelope_v9nb import surface_report
z=np.load(ROOT/'benchmark/local/krag-normal-mouth-v9p-posed-cache.npz')
optical=Relief();held=optical.head_support==0
profile=OralProfile(z['Head_basis'],z['Head_edges'],z['Head_membership'],optical.eyes,optical.radii+.001,held)
# Match native v9r's saved float32 Basis, not an ideal double approximation.
source=profile.head(z['Head_basis']).astype(np.float32).astype(float)
field=BroadOral(source,z['Head_edges'],z['Head_membership'],held)
after=field.head(source)
r={'status':'Prepared v9s broad external mouth; no saved source or actual new render',
   'artisticAcceptance':False,'source':'benchmark/art/krag/Krag_ProfileOral_v9r_WIP.blend',
   'sourceSha256':'c27cecdc6e8709a42f472906db4595aaa6554c3e2897a994fdf19de767e1ceab',
   'actualBasisWidthMeters':float(np.ptp(source[field.rim,0])),
   'proposedBasisWidthMeters':float(np.ptp(after[field.rim,0])),
   'proposalWidthToInterocular':float(field.target_width/abs(optical.eyes[0,0]-optical.eyes[1,0])),
   'heldOpticalVertices':int(held.sum()),'exactHeldOpticalCoordinates':bool(np.array_equal(source[held],after[held]))}
try:r['surface']=surface_report(source,after,z['Head_triangles']);r['passed']=True
except RuntimeError as e:
 r['passed']=False;r['failure']=str(e)
 tri=z['Head_triangles'];a,b=source[tri],after[tri]
 an=np.cross(a[:,1]-a[:,0],a[:,2]-a[:,0]);bn=np.cross(b[:,1]-b[:,0],b[:,2]-b[:,0])
 aa,bb=np.linalg.norm(an,axis=1),np.linalg.norm(bn,axis=1)
 cosine=np.einsum('ij,ij->i',an,bn)/np.maximum(aa*bb,1e-30);ratio=bb/np.maximum(aa,1e-30)
 bad=(cosine<=0)|(ratio<.20);tags=z['Head_triangle_sets']
 r['surfaceFailure']={'flips':int((cosine<=0).sum()),'minimumAreaRatio':float(ratio.min()),
  'failedByFaceSet':{str(int(k)):int(v)for k,v in zip(*np.unique(tags[bad],return_counts=True))},
  'worstCenters':a[np.argsort(cosine)[:8]].mean(1).tolist()}

arch=json.loads((ROOT/'benchmark/art/krag/oral-volume-study/v9r-arch-envelope-attribution.json').read_text())
m=np.asarray(arch['jawOnlyMatrixFromActualDentalPairs']);rigid=after@m[:3,:3].T+m[:3,3]
target=lower_rim_target(field.rim,after,after,rigid)
r['canineCrossSections']=[]
for c in arch['canineVisibilityCrossSections']:
 tip=np.asarray(c['tipJawOnly']);rim=np.asarray([tip[0],*[np.interp(tip[0],target[:,0],target[:,a])for a in (1,2)]])
 r['canineCrossSections'].append({'side':c['side'],'tipJawOnly':tip.tolist(),'proposedRimAtTipX':rim.tolist(),
  'tipAboveRimMeters':float(tip[2]-rim[2]),'tipBehindRimMeters':float(tip[1]-rim[1])})
r['posedTargetRimSamples']=target[::8].tolist()
corners=member(z['Head_membership'],24)&member(z['Head_membership'],7)&member(z['Head_membership'],33)
old_jaw=z['Head_weights'][:,1]*(smooth(distances(source,z['Head_edges'],corners)/.014))
new_jaw,weight_report=weight_support(after,z['Head_edges'],z['Head_membership'],old_jaw)
r['mandibularSupportPreflight']=weight_report
r['weightNormalization']={'minimumHeadWeight':float((1-z['Head_weights'][:,2]-new_jaw).min()),
 'fixedUpperNoseMaximumJawWeight':float(new_jaw[member(z['Head_membership'],33)|member(z['Head_membership'],11)].max())}
r['scope']='Dental/tusk geometry unchanged in this prediction; actual arch hull and intermediate poses still require source review'
r['toolHashes']={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in (Path(__file__),HERE/'broad_oral_v9s.py')}
out=ROOT/'benchmark/art/krag/oral-volume-study/broad-oral-v9s-preflight.json'
out.write_text(json.dumps(r,indent=2)+'\n',newline='\n');print(json.dumps(r,indent=2))
