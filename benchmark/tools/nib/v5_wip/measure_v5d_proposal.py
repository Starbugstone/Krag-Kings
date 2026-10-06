"""Lightweight raw-cage proposal audit; does not open Blender or edit an asset."""
import hashlib,json
from pathlib import Path
import numpy as np
from fit_head_v5d import fit_head,legacy_face_fit,shape_receipt,nose_mask

ROOT=Path(__file__).resolve().parents[4]
source=ROOT/'benchmark/art/krag/anatomy-study/GEO-head_animation_realistic.npz'
points=np.load(source,allow_pickle=True)['vertices'].astype(np.float64)
old=legacy_face_fit(points);new=fit_head(points)
if not np.isfinite(new).all():raise RuntimeError('Nonfinite proposed coordinates')
report=shape_receipt(points)
report['status']='Computed raw control-cage proposal only; not an evaluated saved mesh, visual pass or canonical dimension'
report['coordinateSpace']='Fitted source metres before common HEAD_DROP -0.032 m'
report['referenceTopologySha256']=hashlib.sha256(source.read_bytes()).hexdigest()
report['codeSha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),Path(__file__).with_name('fit_head_v5d.py'),Path(__file__).with_name('fit_head.py')]}
report['noseMask']={'verticesAboveHalf':int(np.sum(nose_mask(points)>.5)),'maximum':float(nose_mask(points).max())}
report['eyeLocalVerticalSpanStudy']=[]
for side in [-1,1]:
    p=np.asarray([[side*.035876,-.128,z] for z in [.304,.310037,.316]])
    a=legacy_face_fit(p);b=fit_head(p)
    report['eyeLocalVerticalSpanStudy'].append({'side':side,'sourceProbePoints':p.tolist(),
        'oldSpanMeters':float(np.ptp(a[:,2])),'proposedSpanMeters':float(np.ptp(b[:,2])),
        'scope':'Regional warp sensitivity at fixed eye X/Y; not a measured final eyelid aperture'})
out=ROOT/'benchmark/art/nib/v5-study/shape-proposal-v5d.json'
out.write_text(json.dumps(report,indent=2)+'\n',newline='\n')
print(json.dumps({'oralTranslationMeters':report['oralTranslationMeters'],'noseMask':report['noseMask'],
                  'eyeSpans':report['eyeLocalVerticalSpanStudy']},indent=2))
