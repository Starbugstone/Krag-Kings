"""Light neutral-surface fit from the exact retained v9u coordinate recipe."""
import os
os.environ.setdefault('OMP_NUM_THREADS', '2')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '2')
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
from whole_face_v9v import WholeFace
from macro_envelope_v9nb import surface_report


def reconstructed():
    cache = ROOT/'benchmark/local/krag-normal-mouth-v9p-posed-cache.npz'
    assert hashlib.sha256(cache.read_bytes()).hexdigest() == '5407ee8e83729337f36fa7d1d95502858d817c080a0771f7abf572091bf800b7'
    d = np.load(cache); p = d['Head_basis']; edges = d['Head_edges']; masks = d['Head_membership']
    optical = Relief(); held = optical.head_support == 0
    p = OralProfile(p, edges, masks, optical.eyes, optical.radii+.001, held).head(p).astype(np.float32).astype(float)
    p = BroadOral(p, edges, masks, held).head(p).astype(np.float32).astype(float)
    p = MandibularTissue(p, edges, masks).head(p).astype(np.float32).astype(float)
    p = ContinuousProfile(p, edges, masks, d['Head_triangles'], d['Head_triangle_sets']).head(p).astype(np.float32).astype(float)
    return p, edges, masks, d['Head_triangles'], held


if __name__ == '__main__':
    p, edges, masks, triangles, held = reconstructed()
    fit = WholeFace(p, edges, masks, triangles, held)
    after = fit.head(p)
    try:
        surface = surface_report(p, after, triangles)
    except RuntimeError as error:
        a, b = p[triangles], after[triangles]
        an = np.cross(a[:,1]-a[:,0], a[:,2]-a[:,0]); bn = np.cross(b[:,1]-b[:,0], b[:,2]-b[:,0])
        cosine = np.einsum('ij,ij->i', an, bn)/np.maximum(np.linalg.norm(an, axis=1)*np.linalg.norm(bn, axis=1), 1e-30)
        ratio = np.linalg.norm(bn, axis=1)/np.maximum(np.linalg.norm(an, axis=1), 1e-30)
        worst = np.argsort(cosine)[:8]
        surface = dict(error=str(error), flippedTriangles=int((cosine<=0).sum()), minimumAreaRatio=float(ratio.min()),
                       worstCenters=a[worst].mean(1).tolist(), worstCosines=cosine[worst].tolist())
    result = dict(status='Prepared coordinated facial fit on reconstructed actual neutral points; native source and views pending',
                  artisticAcceptance=False, sharedPromotion=False,
                  inputSourceSha256='7c6d88870a8ac46112708147bce98f44b3516387a462b7536ccb117bf0883f19',
                  sourceCoordinateReconstructionSha256=hashlib.sha256(p.astype(np.float32).tobytes()).hexdigest(),
                  field=fit.report, surface=surface,
                  recipeSha256=hashlib.sha256((HERE/'whole_face_v9v.py').read_bytes()).hexdigest(),
                  pending=['Coherent provisional dental/gum/tongue fit and full-range residual',
                           'Actual source save/reopen and matched neutral/open views',
                           'Verified v4 motion merge before any eventual engine promotion'])
    (ROOT/'benchmark/art/krag/oral-volume-study/whole-face-v9v-preflight.json').write_text(json.dumps(result, indent=2)+'\n', newline='\n')
    print(json.dumps({k:v for k,v in result.items() if k != 'field'}, indent=2))
