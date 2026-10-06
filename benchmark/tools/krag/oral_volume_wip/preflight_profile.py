"""Check the proposed coherent rest-envelope against cached actual topology."""
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
sys.path.insert(0, str(HERE.parent/'reference_fit_wip'))
sys.path.insert(0, str(HERE.parent/'v9n_wip'))
from profile_and_lip import Profile
from fit_visible_masses_v9qa import MassFit
from macro_envelope_v9nb import surface_report

cache = np.load(ROOT/'benchmark/local/krag-normal-mouth-v9p-posed-cache.npz')
prior = MassFit()
points = prior.head(cache['Head_basis'])
profile = Profile(points, cache['Head_edges'], cache['Head_membership'], prior.eyes, prior.optical_radii)
after = profile.head(points)
result = {'status': 'Prepared rest-profile only; no saved source or posed correction exists',
          'source': 'benchmark/art/krag/Krag_VisibleMassFit_v9qa_WIP.blend',
          'sourceSha256': '9e3a0ca39088053cbbca9e8b20b8144c8e12d51927ed9d613a42b4c1f704b01c',
          'oralTranslationMeters': profile.oral_translation.tolist(),
          'nasalWidthScaleProposal': 1.35, 'nasalAnteriorSupportMeters': .008,
          'artisticAcceptance': False}
try:
    result['head'] = surface_report(points, after, cache['Head_triangles'])
    result['passed'] = True
except RuntimeError as failure:
    result['passed'] = False
    result['failure'] = str(failure)
    tri = cache['Head_triangles']
    a, b = points[tri], after[tri]
    an = np.cross(a[:, 1]-a[:, 0], a[:, 2]-a[:, 0])
    bn = np.cross(b[:, 1]-b[:, 0], b[:, 2]-b[:, 0])
    aa, bb = np.linalg.norm(an, axis=1), np.linalg.norm(bn, axis=1)
    cosine = np.einsum('ij,ij->i', an, bn)/np.maximum(aa*bb, 1e-30)
    ratio = bb/np.maximum(aa, 1e-30)
    failed = (cosine <= 0)|(ratio < .20)
    tags = cache['Head_triangle_sets']
    result['minimumAreaRatio'] = float(ratio.min())
    result['flips'] = int((cosine <= 0).sum())
    result['failedByFaceSet'] = {str(int(k)): int(v) for k, v in zip(*np.unique(tags[failed], return_counts=True))}
    result['worstCenters'] = a[np.argsort(cosine)[:8]].mean(1).tolist()
directory = ROOT/'benchmark/art/krag/oral-volume-study'
directory.mkdir(exist_ok=True)
(directory/'profile-preflight.json').write_text(json.dumps(result, indent=2)+'\n', newline='\n')
print(json.dumps(result, indent=2))
