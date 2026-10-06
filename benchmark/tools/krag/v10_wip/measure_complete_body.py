"""Read-only numerical fit report; does not create a Blender model."""
from pathlib import Path
import sys,json,hashlib
import numpy as np
folder=Path(__file__).resolve().parent;root=folder.parents[3];sys.path.insert(0,str(folder.parent))
from complete_body_fit import fit,lower_weights,SOURCE_ANCHORS,TARGET_ANCHORS
source=root/'benchmark/art/krag/anatomy-study/GEO-body_male_realistic.npz'
v=np.load(source)['vertices'];q=fit(v)
regions={}
for name,mask in [('left_foot',(v[:,0]>0)&(v[:,2]<.135)),('right_foot',(v[:,0]<0)&(v[:,2]<.135)),('legs',(v[:,2]<.780)&((abs(v[:,0])<.24)|(v[:,2]<.65))),('pelvis',(v[:,2]>=.780)&(v[:,2]<1.020)&(abs(v[:,0])<.24))]:
 a=q[mask];regions[name]={'vertices':len(a),'minimumMeters':a.min(0).tolist(),'maximumMeters':a.max(0).tolist(),'sizeMeters':np.ptp(a,axis=0).tolist()}
weights=[lower_weights(p) for p in q[v[:,2]<.95]]
report={'status':'Code-only complete-body fit; no generated master, anatomy or pose acceptance','sourceSha256':hashlib.sha256(source.read_bytes()).hexdigest(),'fitSha256':hashlib.sha256((folder/'complete_body_fit.py').read_bytes()).hexdigest(),'sourceAnchors':SOURCE_ANCHORS,'targetAnchors':TARGET_ANCHORS,'regions':regions,'maximumWeightSumError':max(abs(sum(w for n,w in ws)-1) for ws in weights),'maximumInfluences':max(map(len,weights)),'notes':['Preserves current Foot control markers at z=.24m; a posed barefoot review must evaluate true anatomical ankle pivot/foot roll before final rig approval.','Concept foot/toe anatomy is covered; this is a provisional CC0-derived organic master study, excluded from runtime by default.']}
out=root/'benchmark/art/krag/anatomy-study/complete-body-fit-v10.json';out.write_text(json.dumps(report,indent=2)+'\n',newline='\n');print(json.dumps(report,indent=2))
