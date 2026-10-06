"""Small NumPy source-space audit; no Blender, edits or rendering."""
from pathlib import Path
import json
import numpy as np
from fit_head import fit_head

ROOT=Path(__file__).resolve().parents[4]
DATA=ROOT/'benchmark/art/krag/anatomy-study'
q=np.load(DATA/'GEO-head_animation_realistic.npz',allow_pickle=True)
v=q['vertices'];polys=q['polygons']
attributes=json.loads((ROOT/'benchmark/art/nib/v5-study/head-topology-attributes.json').read_text())
sets=next(a['values'] for a in attributes['attributes'] if a['name']=='.sculpt_face_set')
regions={}
for number in sorted(set(sets)):
    ids=sorted({int(i) for poly,s in zip(polys,sets) if s==number for i in poly})
    p=v[ids];f=fit_head(p);f[:,2]-=.032
    regions[str(number)]={'sourceMin':p.min(0).tolist(),'sourceMax':p.max(0).tolist(),
                         'fitWorldMin':f.min(0).tolist(),'fitWorldMax':f.max(0).tolist(),'count':len(ids)}
front_ids=np.where((abs(v[:,0])<.025)&(v[:,2]>.245)&(v[:,2]<.29))[0]
front_ids=front_ids[np.argsort(v[front_ids,1])[:40]]
report={'status':'Raw source control cage numeric diagnostic, not saved evaluated mesh evidence.',
        'faceSets':regions,'frontNoseVertices':[{'index':int(i),'source':v[i].tolist(),'fittedWorld':(fit_head(v[i:i+1])[0]-[0,0,.032]).tolist()} for i in front_ids]}
out=ROOT/'benchmark/art/nib/v5-study/source-face-fit-coordinate-audit.json'
out.write_text(json.dumps(report,indent=2)+'\n',newline='\n')
print(json.dumps(report,indent=2))
