"""Predict rim support from exact v9u points and a retained actual Jaw matrix.

Native source evaluation remains the authoritative deformation gate. This
preflight isolates the singular corner curve before another Blender launch.
"""
import os
os.environ.setdefault('OPENBLAS_NUM_THREADS', '2')
from pathlib import Path
import sys, json, hashlib
import numpy as np
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE))
from preflight_whole_face_v9v import reconstructed
from profile_and_lip import member, ordered_rim, smooth
from broad_oral_v9s import mandibular_rim_weights
from paired_lip_curve import lower_arc
p, edges, masks, triangles, held = reconstructed()
lower = ordered_rim(edges, member(masks,24)&member(masks,7), p)
upper = ordered_rim(edges, member(masks,33)&member(masks,7), p)
matrix_source = ROOT/'benchmark/art/krag/oral-volume-study/v9r-arch-envelope-attribution.json'
jaw = np.asarray(json.loads(matrix_source.read_text())['jawOnlyMatrixFromActualDentalPairs'])
rigid = p@jaw[:3,:3].T+jaw[:3,3]
weight = mandibular_rim_weights(lower,p)
posed = p.copy(); posed[lower] = p[lower]*(1-weight[:,None])+rigid[lower]*weight[:,None]
target = posed.copy(); half = max(abs(p[lower,0]))
target[upper,2] -= .006*smooth((abs(p[upper,0])/half-.60)/.40)
center = lower[np.argmin(abs(p[lower,0]))]; bottom = posed[center]
prior = target.copy(); reports = []
for sign in (-1,1):
    ids = lower[p[lower,0]*sign >= -1e-5]; corner = lower[0 if sign<0 else -1]
    u = np.clip(abs(p[ids,0])/abs(p[corner,0]),0,1)
    prior[ids,2] = bottom[2]+(prior[corner,2]-bottom[2])*(1-np.maximum(1-u*u,0)**.25)
    z, report = lower_arc(u,bottom[2],target[corner,2],u,posed[ids,2])
    target[ids,2] = z; reports.append(dict(side=sign,**report))
before = float(np.linalg.norm(prior[lower]-posed[lower],axis=1).max())
after = float(np.linalg.norm(target[lower]-posed[lower],axis=1).max())
if after > .020 or after >= before:
    raise RuntimeError('Finite corner fit still exceeds the intended bounded rim movement')
result = dict(status='Prepared finite oral-corner curve from reconstructed points and retained actual Jaw transform; native validation pending',
              artisticAcceptance=False, sharedPromotion=False,
              inputSourceSha256='7c6d88870a8ac46112708147bce98f44b3516387a462b7536ccb117bf0883f19',
              jawMatrixReceiptSha256=hashlib.sha256(matrix_source.read_bytes()).hexdigest(),
              previousInfiniteCornerMaximumPosedRimChangeMeters=before,
              finiteCornerMaximumPosedRimChangeMeters=after,
              nativeSourceResidualLimitMeters=.025, nativeLimitUnchanged=True,
              curves=reports, fullHingeAndCenterDropRetained=True,
              samples=[dict(vertex=int(i),rest=p[i].tolist(),predictedOld=posed[i].tolist(),target=target[i].tolist()) for i in lower[::8]],
              recipeSha256=hashlib.sha256((HERE/'paired_lip_curve.py').read_bytes()).hexdigest())
out=ROOT/'benchmark/art/krag/oral-volume-study/paired-lip-v9va-preflight.json'
out.write_text(json.dumps(result,indent=2)+'\n',newline='\n')
print(json.dumps({k:v for k,v in result.items() if k!='samples'},indent=2))
