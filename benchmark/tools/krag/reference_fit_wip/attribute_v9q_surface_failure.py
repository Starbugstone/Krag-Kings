"""Read the frozen cached Head and explain the native v9q surface rejection."""
import os
os.environ.setdefault('OMP_NUM_THREADS', '2')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '2')
from pathlib import Path
import sys
import json
import numpy as np
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE))
from fit_visible_masses import MassFit

fit = MassFit()
before = fit.points
after = fit.head(before)
tri = fit.triangles
a = np.cross(before[tri[:, 1]]-before[tri[:, 0]], before[tri[:, 2]]-before[tri[:, 0]])
b = np.cross(after[tri[:, 1]]-after[tri[:, 0]], after[tri[:, 2]]-after[tri[:, 0]])
aa, bb = np.linalg.norm(a, axis=1), np.linalg.norm(b, axis=1)
valid = aa > 1e-12
ratio = np.divide(bb, aa, out=np.ones_like(aa), where=valid)
cosine = np.einsum('ij,ij->i', a, b)/np.maximum(aa*bb, 1e-30)
tags = np.load(ROOT/'benchmark/art/krag/landmarks-v9nc/actual-neutral-surface.npz')['Head_triangle_sets']
failed = valid & ((ratio < .20)|(cosine <= 0))
selected = np.flatnonzero(failed)[np.argsort(ratio[failed])[:20]]
result = {
    'status': 'Cached actual Head attribution of native gate rejection; no source mutation',
    'minimumAreaRatio': float(ratio[valid].min()),
    'minimumNormalCosine': float(cosine[valid].min()),
    'flippedTriangleCount': int(np.count_nonzero(valid & (cosine <= 0))),
    'collapsedTriangleCount': int(np.count_nonzero(valid & (ratio < .20))),
    'failedByFaceSet': {str(int(k)): int(v) for k, v in zip(*np.unique(tags[failed], return_counts=True))},
    'worst': [{'triangle': int(i), 'set': int(tags[i]), 'areaRatio': float(ratio[i]),
               'normalCosine': float(cosine[i]), 'vertexIds': tri[i].tolist(),
               'before': before[tri[i]].tolist(), 'after': after[tri[i]].tolist()}
              for i in selected],
    'artisticAcceptance': False
}
path = ROOT/'benchmark/art/krag/reference-fit-study/visible-mass-fit-v9q-area-failure.json'
path.write_text(json.dumps(result, indent=2)+'\n', newline='\n')
print(json.dumps({k: v for k, v in result.items() if k != 'worst'}, indent=2))
