from pathlib import Path
import sys,json,numpy as np
r=Path(r'D:\Dev\Krag-Kings\benchmark');sys.path.insert(0,str(r/'tools/krag'))
from anatomy_warp_study import warp
v=np.load(r/'art/krag/anatomy-study/GEO-body_male_realistic.npz',allow_pickle=True)['vertices'];mask=(v[:,0]>.32)&(v[:,2]<.955)&(v[:,2]>.70);p=v[mask];d=1e-5
j=np.stack([(warp(p+np.eye(3)[k]*d)-warp(p-np.eye(3)[k]*d))/(2*d) for k in range(3)],axis=2);det=np.linalg.det(j);sv=np.linalg.svd(j,compute_uv=False)
report={'sourcePoints':len(p),'jacobianStepMeters':d,'negativeJacobianCount':int((det<0).sum()),'determinantQuantiles':np.quantile(det,[0,.05,.5,.95,1]).tolist(),'singularValueExtrema':[float(sv.min()),float(sv.max())],'lowestDeterminants':[{'source':p[i].tolist(),'target':warp(p[i:i+1])[0].tolist(),'det':float(det[i]),'singular':sv[i].tolist()} for i in np.argsort(det)[:12]]}
(r/'local/krag-hand-warp-jacobian.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
