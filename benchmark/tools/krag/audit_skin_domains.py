"""Read-only source-cage weight-domain measurement, not a Blender pose proof."""
from pathlib import Path
import hashlib,json,numpy as np
from krag_skin_domains import solve
from anatomy_warp_study import warp

root=Path(__file__).resolve().parents[3];path=root/'benchmark/art/krag/anatomy-study/GEO-body_male_realistic.npz'
source=np.load(path,allow_pickle=True);raw=source['vertices'];polys=source['polygons']
keep=(raw[:,2]<1.445)&((raw[:,2]>.945)|((np.abs(raw[:,0])>.240)&(raw[:,2]>.70)))
faces=[list(f) for f in polys if all(keep[i] for i in f)]
used=sorted({i for face in faces for i in face});index={old:new for new,old in enumerate(used)}
faces=[[index[i] for i in face] for face in faces];raw=raw[used]
field,statistics=solve(raw,faces);fitted=warp(raw)
old=np.clip((np.abs(fitted[:,0])-.235)/(.359-.235),0,1);old=old*old*(3-2*old)
regions={'lower_lateral_ribs':(np.abs(raw[:,0])>.115)&(np.abs(raw[:,0])<.207)&(raw[:,2]>1.04)&(raw[:,2]<1.235),
         'source_arms':(np.abs(raw[:,0])>.255)&(raw[:,2]>1.04)&(raw[:,2]<1.30),
         'shoulder_transition':(np.abs(raw[:,0])>.145)&(np.abs(raw[:,0])<.255)&(raw[:,2]>1.245)}
report={'status':'Code-only domain study; no saved Blender mesh, posed deformation or art acceptance',
        'sourceSha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'helperSha256':hashlib.sha256(Path(__file__).with_name('krag_skin_domains.py').read_bytes()).hexdigest(),
        'solver':statistics,'regions':{}}
for name,mask in regions.items():
    report['regions'][name]={'vertices':int(mask.sum()),'oldArmDomainMaximum':float(old[mask].max()),
        'newArmDomainMaximum':float(field[mask].max()),'oldArmDomainMean':float(old[mask].mean()),
        'newArmDomainMean':float(field[mask].mean())}
out=root/'benchmark/art/krag/anatomy-study/skin-domain-v2-measurements.json'
out.write_text(json.dumps(report,indent=2)+'\n',newline='\n');print(json.dumps(report,indent=2))
