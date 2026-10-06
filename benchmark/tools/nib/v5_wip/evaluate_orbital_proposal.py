"""Evaluate the loop/globe eyelid proposal against actual cached geometry.

This is a numerical study, not a native source or posed-render acceptance.
"""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
import argparse,sys,json,hashlib
from pathlib import Path
import numpy as np
HERE=Path(__file__).parent
sys.path.insert(0,str(HERE))
from orbital_closure_v5i import propose
parser=argparse.ArgumentParser()
parser.add_argument('--geometry-cache',type=Path,required=True)
parser.add_argument('--audit',type=Path,required=True)
parser.add_argument('--topology',type=Path,required=True)
parser.add_argument('--output-cache',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
parser.add_argument('--rotation-preservation',action='store_true')
args=parser.parse_args()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
cachepath=args.geometry_cache;cache=np.load(cachepath)
audit=json.loads(args.audit.read_text())
if sha(cachepath)!=audit['cacheSha256']:raise RuntimeError('Actual geometry cache hash mismatch')
top=json.loads(args.topology.read_text())
neutral,shapes,report=propose(cache,top,rotation_preservation=args.rotation_preservation)
basis=cache['basis'];f=cache['faces'];tri=np.vstack((f[:,[0,1,2]],f[:,[0,2,3]]));edges=cache['edges']
def normals(p):
 t=p[tri];return np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0])
oldn=normals(basis);oldlength=np.linalg.norm(oldn,axis=1);edge_length=np.linalg.norm(basis[edges[:,1]]-basis[edges[:,0]],axis=1)
def metrics(p):
 n=normals(p);area=np.linalg.norm(n,axis=1);dot=np.sum(n*oldn,axis=1)/(np.maximum(area*oldlength,1e-20))
 ratio=np.linalg.norm(p[edges[:,1]]-p[edges[:,0]],axis=1)/np.maximum(edge_length,1e-12)
 return {'maxDisplacementMeters':float(np.linalg.norm(p-basis,axis=1).max()),'introducedDegenerates':int(((area<1e-14)&(oldlength>=1e-14)).sum()),'trianglesRotatedOver90':int((dot<0).sum()),'minimumAreaRatio':float((area/np.maximum(oldlength,1e-20)).min()),'maximumEdgeStretch':float(ratio.max())}
report['cacheSha256']=sha(cachepath);report['sourceSha256']=audit['sourceSha256'];report['neutral']=metrics(neutral)
report['poses']={}
for name in ['Blink','Squint']:
 for fraction in [.25,.5,.75,1.]:
  p=neutral+fraction*(shapes[name+'_L']+shapes[name+'_R']);report['poses'][name+'_'+str(fraction)]=metrics(p)
report['methodRotationPreservation']=args.rotation_preservation
report['codeSha256']={name:sha(HERE/name) for name in ['evaluate_orbital_proposal.py','orbital_closure_v5i.py']}
report['numericGate']={'passed':all(p['introducedDegenerates']==0 and p['trianglesRotatedOver90']==0 for p in [report['neutral'],*report['poses'].values()]),
    'scope':'Conservative normal-rotation diagnostic; visible fold quality still requires actual mesh review',
    'fullClosureWarningsRetained':True}
nasal=np.unique(f[cache['faceSets']==11])
report['nasalMaximumChangeMeters']=float(np.linalg.norm(neutral[nasal]-basis[nasal],axis=1).max())
report['nasalMaximumExpressionDeltaMeters']=max(float(np.linalg.norm(v[nasal],axis=1).max()) for v in shapes.values())
if report['nasalMaximumChangeMeters']>1e-12 or report['nasalMaximumExpressionDeltaMeters']>1e-12:raise RuntimeError('Orbital proposal moves nasal anchors')
if any(p['introducedDegenerates'] for p in [report['neutral'],*report['poses'].values()]):raise RuntimeError('Orbital proposal introduces degenerate triangles')
args.output_cache.parent.mkdir(parents=True,exist_ok=True)
np.savez_compressed(args.output_cache,neutral=neutral,**shapes)
report['proposalCacheSha256']=sha(args.output_cache)
args.output.parent.mkdir(parents=True,exist_ok=True)
args.output.write_text(json.dumps(report,indent=2)+'\n',newline='\n')
print(json.dumps({'neutral':report['neutral'],'fullBlink':report['poses']['Blink_1.0'],'numericGate':report['numericGate']}))
print('NIB_ORBITAL_PROPOSAL_EVALUATED')
