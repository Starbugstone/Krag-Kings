"""Numerical source-domain measurements; no Blender pose proof."""
from pathlib import Path
import json,hashlib,numpy as np
from krag_hand_domains import solve
root=Path(__file__).resolve().parents[3];p=root/'benchmark/art/krag/anatomy-study/GEO-body_male_realistic.npz'
s=np.load(p,allow_pickle=True);v=s['vertices'];faces=s['polygons'];fields,stats=solve(v,faces)
regions={'palm':(abs(v[:,0])>.34)&(v[:,2]>.839)&(v[:,2]<.88), 'distalDigits':(abs(v[:,0])>.32)&(v[:,2]<.765)&(v[:,2]>.69), 'forearm':(abs(v[:,0])>.31)&(v[:,2]>.92)&(v[:,2]<1.01)}
report={'sourceSha256':hashlib.sha256(p.read_bytes()).hexdigest(),'statistics':stats,'regions':{}}
for name,mask in regions.items():
 f=fields[mask];report['regions'][name]={'vertices':int(mask.sum()),'maximumTotalDigitWeight':float(f.sum(1).max()),'meanTotalDigitWeight':float(f.sum(1).mean()),'maximumSecondaryDigitWeight':float(np.sort(f,axis=1)[:,-2].max())}
out=root/'benchmark/art/krag/anatomy-study/hand-domain-v3-measurements.json';out.write_text(json.dumps(report,indent=2)+'\n',newline='\n');print(json.dumps(report,indent=2))
