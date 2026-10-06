"""Lightweight LBS proposal check using the saved read-only Blender audit cache.

No Blender process, new source, or rendered validation is implied.
"""
import sys,json,hashlib,numpy as np
from pathlib import Path
root=Path(__file__).resolve().parents[4];sys.path.insert(0,str(Path(__file__).parent))
from mouth_jaw_weights import calculate
p=np.load(root/'benchmark/local/nib-v5e-mouth-audit.npz',allow_pickle=True);r=json.loads((root/'benchmark/art/nib/v5-study/native-v5e-mouth-audit.json').read_text())
w,receipt=calculate(p['source'],p['faces'],p['face_sets'],p['edges'],p['neck_weights'])
bind=np.asarray(r['jawBoneRestMatrix']);theta=np.deg2rad(15);rot=np.eye(4);rot[1:3,1:3]=[[np.cos(theta),-np.sin(theta)],[np.sin(theta),np.cos(theta)]];transform=bind@rot@np.linalg.inv(bind)
points=p['neutral'];q=(np.column_stack((points,np.ones(len(points))))@transform.T)[:,:3];old=points+(q-points)*p['jaw_weights'][:,None];new=points+(q-points)*w[:,None]
receipt['oldPredictionVersusSavedJawOnlyMaxMeters']=float(np.linalg.norm(old-p['jawOnly'],axis=1).max())
e=p['edges'];s=p['source'];mask=(abs(s[:,0])<.06)&(s[:,1]<-.08)&(s[:,2]>.20)&(s[:,2]<.282);sel=mask[e].all(1);length=np.linalg.norm(points[e[:,0]]-points[e[:,1]],axis=1);ratio=np.linalg.norm(new[e[:,0]]-new[e[:,1]],axis=1)/np.maximum(length,1e-12)
receipt['predictedJawOnlyMouthEdgeStretch']={'maximum':float(ratio[sel].max()),'p99':float(np.quantile(ratio[sel],.99))}
receipt['status']='Numerical proposal on actual saved audit cache; no new Blender source or render'
receipt['cacheSha256']=hashlib.sha256((root/'benchmark/local/nib-v5e-mouth-audit.npz').read_bytes()).hexdigest()
receipt['authoringCode']={name:hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest() for name in ['measure_v5f_jaw_proposal.py','mouth_jaw_weights.py']}
if receipt['oldPredictionVersusSavedJawOnlyMaxMeters']>1e-6:raise RuntimeError('Analytic Jaw frame does not reproduce saved evaluated pose')
np.savez_compressed(root/'benchmark/local/nib-v5f-jaw-proposal.npz',weights=w,predicted_jaw_only=new)
(root/'benchmark/art/nib/v5-study/native-v5f-jaw-proposal.json').write_text(json.dumps(receipt,indent=2)+'\n',newline='\n')
print(json.dumps(receipt,indent=2))
