"""Lightweight raw-cage check; no Blender process and no asset mutation."""
import hashlib,json
from pathlib import Path
import numpy as np
from fit_head_v5d import fit_head as prior_fit
from fit_head_v5e import fit_head,shape_receipt,nose_mask

ROOT=Path(__file__).resolve().parents[4]
path=ROOT/'benchmark/art/krag/anatomy-study/GEO-head_animation_realistic.npz'
points=np.load(path,allow_pickle=True)['vertices'].astype(np.float64)
old=prior_fit(points);new=fit_head(points)
if not np.isfinite(new).all():raise RuntimeError('Nonfinite proposed shape')
report=shape_receipt(points)
report['status']='Raw control-cage measurements only; not an evaluated saved mesh, render, or approved anatomy'
report['coordinateSpace']='Metres before common HEAD_DROP -0.032 m'
x,y,z=points.T
lip=(abs(x)<.037)&(z>.225)&(z<.248)&(y<-.117)
nose=nose_mask(points)>.5
report['profileRelationship']={}
for label,values in [('actualRecipeV5dRaw',old),('proposedV5eRaw',new)]:
    lip_y=float(values[lip,1].min());nose_y=float(values[nose,1].min())
    report['profileRelationship'][label]={'lipMinimumY':lip_y,'noseMinimumY':nose_y,
        'noseLeadMeters':lip_y-nose_y,'definition':'Positive means nose leads lip toward negative Y'}
if report['profileRelationship']['proposedV5eRaw']['noseLeadMeters']<=0:
    raise RuntimeError('Raw proposal still has a lip-leading profile')
report['referenceTopologySha256']=hashlib.sha256(path.read_bytes()).hexdigest()
report['codeSha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in
                     [Path(__file__),Path(__file__).with_name('fit_head_v5e.py'),
                      Path(__file__).with_name('fit_head_v5d.py'),Path(__file__).with_name('fit_head.py')]}
out=ROOT/'benchmark/art/nib/v5-study/shape-proposal-v5e.json'
out.write_text(json.dumps(report,indent=2)+'\n',newline='\n')
print(json.dumps({'profileRelationship':report['profileRelationship'],
                  'oralTranslationMeters':report['oralTranslationMeters'],
                  'protectedRegionMaximumDisplacements':{n:report['regions'][n]['maximumDisplacementMeters'] for n in ['orbital','lowerNeck']}},indent=2))
