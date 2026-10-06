"""Bound the reference-flow duration at the unchanged orbital area gate.

v9q's 0.85 interval compressed 145 actual orbital triangles below20% area.
This correction preserves the same reference handles, ocular constraints and
continuous spatial field, reducing only its integration interval to0.68.
"""
from pathlib import Path
import os
os.environ.setdefault('OMP_NUM_THREADS', '2')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '2')
import sys
import json
import numpy as np
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE))
from fit_visible_masses import MassFit as OriginalMassFit
sys.path.insert(0, str(HERE.parent/'v9n_wip'))
from macro_envelope_v9nb import surface_report


class MassFit(OriginalMassFit):
    duration = .68

    def flow(self, points, support=None):
        result = np.asarray(points, float).copy()
        steps = 24
        for _ in range(steps):
            result += self.velocity(result, support)*self.duration/steps
        return result


if __name__ == '__main__':
    fit = MassFit()
    after = fit.head(fit.points)
    old = fit.points[fit.triangles]
    new = after[fit.triangles]
    an = np.cross(old[:, 1]-old[:, 0], old[:, 2]-old[:, 0])
    bn = np.cross(new[:, 1]-new[:, 0], new[:, 2]-new[:, 0])
    aa, bb = np.linalg.norm(an, axis=1), np.linalg.norm(bn, axis=1)
    valid = aa > 1e-12
    ratio = bb[valid]/aa[valid]
    cosine = np.einsum('ij,ij->i', an[valid], bn[valid])/np.maximum(aa[valid]*bb[valid], 1e-30)
    result = {'status': 'Cached actual source full area/normal preflight; no native source/render yet',
              'flowDuration': fit.duration,
              'minimumTriangleAreaRatio': float(ratio.min()),
              'minimumNormalCosine': float(cosine.min()),
              'maxDisplacementMeters': float(np.linalg.norm(after-fit.points, axis=1).max()),
              'flippedTriangles': int(np.count_nonzero(cosine <= 0)),
              'areaGateFailures': int(np.count_nonzero(ratio < .20)),
              'artisticAcceptance': False}
    try:
        result['nativeSurfaceGate'] = surface_report(fit.points, after, fit.triangles)
        result['passed'] = True
    except RuntimeError as failure:
        result['passed'] = False
        result['failure'] = str(failure)
    # The later read-only oral attribution cached exact v9p Head/Mouth Basis.
    # Reuse those actual values as well, avoiding another source-only failure
    # that could already have been found without launching Blender.
    exact = np.load(ROOT/'benchmark/local/krag-normal-mouth-v9p-posed-cache.npz')
    result['actualV9pNeutralModules'] = {}
    for name in ('Head', 'Mouth'):
        points = exact[name+'_basis'].astype(float)
        transformed = fit.head(points) if name == 'Head' else fit.transform(points)
        try:
            result['actualV9pNeutralModules'][name] = surface_report(points, transformed, exact[name+'_triangles'])
        except RuntimeError as failure:
            result['passed'] = False
            result['actualV9pNeutralModules'][name] = {'failed': str(failure)}
    path = ROOT/'benchmark/art/krag/reference-fit-study/visible-mass-fit-v9qa-preflight.json'
    path.write_text(json.dumps(result, indent=2)+'\n', newline='\n')
    print(json.dumps(result, indent=2))
