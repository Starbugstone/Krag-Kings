"""Light preparation from the exact retained v9p-to-v9ta coordinate recipe."""
import os
os.environ.setdefault('OMP_NUM_THREADS', '2'); os.environ.setdefault('OPENBLAS_NUM_THREADS', '2')
from pathlib import Path
import sys, json, hashlib
import numpy as np
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[3]
for path in (HERE, HERE.parent/'landmark_wip', HERE.parent/'v9n_wip'):
    sys.path.insert(0, str(path))
from landmark_relief import Relief
from rest_profile_v9r import OralProfile
from broad_oral_v9s import BroadOral
from mandibular_tissue_v9ta import MandibularTissue
from continuous_profile_v9u import ContinuousProfile
from macro_envelope_v9nb import surface_report
cache = ROOT/'benchmark/local/krag-normal-mouth-v9p-posed-cache.npz'
d = np.load(cache); p = d['Head_basis']; edges = d['Head_edges']; masks = d['Head_membership']
optical = Relief(); held = optical.head_support == 0
p = OralProfile(p, edges, masks, optical.eyes, optical.radii+.001, held).head(p).astype(np.float32).astype(float)
p = BroadOral(p, edges, masks, held).head(p).astype(np.float32).astype(float)
p = MandibularTissue(p, edges, masks).head(p).astype(np.float32).astype(float)
field = ContinuousProfile(p, edges, masks, d['Head_triangles'], d['Head_triangle_sets'])
after = field.head(p)
result = {'status': 'Prepared continuous profile; no native source or views',
          'artisticAcceptance': False, 'sharedPromotion': False,
          'inputSourceSha256': '5a06f5890097ce0f3fa3afe3f62a686df73428d775a30d6602bc9d3a800d56e9',
          'cacheSha256': hashlib.sha256(cache.read_bytes()).hexdigest(),
          'surface': surface_report(p, after, d['Head_triangles']),
          'profile': field.report,
          'opticalPointsExact': bool(np.array_equal(after[held], p[held])),
          'recipeSha256': hashlib.sha256((HERE/'continuous_profile_v9u.py').read_bytes()).hexdigest(),
          'caution': 'Reconstructed unchanged neutral correspondence only. Native save/reopen and actual full-range mouth views are required.'}
if not result['opticalPointsExact']:
    raise RuntimeError('Actual optical points changed')
out = ROOT/'benchmark/art/krag/oral-volume-study/continuous-profile-v9u-preflight.json'
out.write_text(json.dumps(result, indent=2)+'\n', newline='\n')
print(json.dumps({k: v for k, v in result.items() if k != 'profile'}, indent=2))
