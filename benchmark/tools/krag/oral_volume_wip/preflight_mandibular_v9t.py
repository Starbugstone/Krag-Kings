"""Light numerical preparation using actual cached source correspondence.

No Blender source is edited; this is not a substitute for saved posed views.
"""
import os
os.environ.setdefault('OMP_NUM_THREADS', '2')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '2')
from pathlib import Path
import sys, json, hashlib
import numpy as np
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
for path in (HERE, HERE.parent/'landmark_wip', HERE.parent/'v9n_wip'):
    sys.path.insert(0, str(path))
from profile_and_lip import member, distances
from rest_profile_v9r import OralProfile
from broad_oral_v9s import BroadOral, weight_support
from mandibular_tissue_v9t import MandibularTissue
from landmark_relief import Relief
from macro_envelope_v9nb import surface_report

cache = ROOT/'benchmark/local/krag-normal-mouth-v9p-posed-cache.npz'
d = np.load(cache)
p, e, m = d['Head_basis'], d['Head_edges'], d['Head_membership']
optical = Relief(); held = optical.head_support == 0
r = OralProfile(p, e, m, optical.eyes, optical.radii+.001, held)
v9r = r.head(p).astype(np.float32).astype(float)
v9s = BroadOral(v9r, e, m, held).head(v9r).astype(np.float32).astype(float)
# Reconstruct the actual commissure-support recipe with its cubic smoothstep.
# The older v9s preflight used the unrelated quintic helper at this step;
# retain that historical report rather than silently rewriting it.
corner = member(m, 24) & member(m, 7) & member(m, 33)
t = np.clip(distances(v9r, e, corner)/.014, 0, 1)
old = d['Head_weights'][:, 1]*(t*t*(3-2*t))
current, old_report = weight_support(v9s, e, m, old)
tissue = MandibularTissue(v9s, e, m)
after = tissue.head(v9s)
new, report = tissue.weights(current, 1-d['Head_weights'][:, 2])
surface = surface_report(v9s, after, d['Head_triangles'])
a, b = e.T
length = np.linalg.norm(v9s[b]-v9s[a], axis=1)
region = ((abs(v9s[:, 0]) > .075) & (v9s[:, 1] > -.115)
          & (v9s[:, 2] > 1.745) & (v9s[:, 2] < 1.895)
          & (tissue.interface_distance < .035))
selected = region[e].all(1) & (length > 1e-6)
gradient = lambda weight: abs(weight[b]-weight[a])/np.maximum(length, 1e-8)
# The actual v9p posed cache supplies the existing combined morph position.
# Invert its actual LBS, then change only the lateral weight field.  This is
# a source-weight-only prediction, not an exact new v9s skin evaluation.
arch = json.loads((ROOT/'benchmark/art/krag/oral-volume-study/v9r-arch-envelope-attribution.json').read_text())
jaw = np.asarray(arch['jawOnlyMatrixFromActualDentalPairs'])
old_weights = d['Head_weights'][:, 1]
baseline_tissue = MandibularTissue(p, e, m)
predicted_weights, _ = baseline_tissue.weights(old_weights, 1-d['Head_weights'][:, 2])
identity = np.eye(3)
rot = identity[None]+old_weights[:, None, None]*(jaw[:3, :3]-identity)[None]
translations = old_weights[:, None]*jaw[:3, 3]
effective = np.linalg.solve(rot, (d['Head_posed']-translations)[:, :, None])[:, :, 0]
new_rot = identity[None]+predicted_weights[:, None, None]*(jaw[:3, :3]-identity)[None]
predicted = np.einsum('ijk,ik->ij', new_rot, effective)+predicted_weights[:, None]*jaw[:3, 3]
old_length = np.linalg.norm(p[b]-p[a], axis=1)
stretch = np.linalg.norm(predicted[b]-predicted[a], axis=1)/np.maximum(old_length, 1e-8)
before_stretch = np.linalg.norm(d['Head_posed'][b]-d['Head_posed'][a], axis=1)/np.maximum(old_length, 1e-8)
result = {
    'status': 'Numerically prepared; no saved v9t source or actual views',
    'artisticAcceptance': False, 'sharedPromotion': False,
    'inputSourceSha256': 'bbe3deadd7d9507a027afc0474206ad8528de8820606539246bc3242ffd171fd',
    'actualCacheSha256': hashlib.sha256(cache.read_bytes()).hexdigest(),
    'neutralSurface': surface, 'mandibularSupport': report,
    'exactOpticalPoints': bool(np.array_equal(v9s[held], after[held])),
    'exactTrueOralRims': bool(np.array_equal(v9s[tissue.rim], after[tissue.rim])),
    'v9sSupportReconstruction': old_report,
    'lateralMaximumWeightGradientBeforePerMeter': float(gradient(current)[selected].max()),
    'lateralMaximumWeightGradientAfterPerMeter': float(gradient(new)[selected].max()),
    'actualV9pLateralMaximumEdgeStretch': float(before_stretch[selected].max()),
    'predictedWeightOnlyV9pLateralMaximumEdgeStretch': float(stretch[selected].max()),
    'predictionLimit': 'Actual cached v9p combined shape, changed lateral skin weights only; current v9s native posed proof still required',
    'tools': {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in (Path(__file__), HERE/'mandibular_tissue_v9t.py')},
}
if not result['exactOpticalPoints'] or not result['exactTrueOralRims']:
    raise RuntimeError('Protected actual loops changed')
out = ROOT/'benchmark/art/krag/oral-volume-study/mandibular-v9t-preflight.json'
out.write_text(json.dumps(result, indent=2)+'\n', newline='\n')
print(json.dumps(result, indent=2))
