"""Explicit surface-handle sculpt on the actual neutral v9nc head.

Depth targets are authored anatomical proposals from concept01, not measured
millimetres recovered from an uncalibrated illustration. Pixel picks identify
exact visible source points; a compact smooth interpolant meets those handles.
"""
from pathlib import Path
import json
import numpy as np

ROOT = Path(__file__).resolve().parents[4]
CACHE = ROOT / 'benchmark/art/krag/landmarks-v9nc'


def smooth(value):
    t = np.clip(value, 0., 1.)
    return t*t*t*(10+t*(-15+6*t))


def pick(points, triangles, pixels, xy):
    projected = pixels[triangles]
    a = projected[:, 0]
    b, c, q = projected[:, 1]-a, projected[:, 2]-a, np.asarray(xy)-a
    det = b[:, 0]*c[:, 1]-b[:, 1]*c[:, 0]
    valid = abs(det) > 1e-10
    u = np.divide(q[:, 0]*c[:, 1]-q[:, 1]*c[:, 0], det, out=np.zeros_like(det), where=valid)
    v = np.divide(b[:, 0]*q[:, 1]-b[:, 1]*q[:, 0], det, out=np.zeros_like(det), where=valid)
    hit = np.flatnonzero(valid & (u >= -1e-9) & (v >= -1e-9) & (u+v <= 1+1e-9))
    if not len(hit):
        raise RuntimeError('Named handle misses actual head surface: '+str(xy))
    bary = np.column_stack((1-u[hit]-v[hit], u[hit], v[hit]))
    world = np.einsum('ij,ijk->ik', bary, points[triangles[hit]])
    first = int(np.argmin(world[:, 1]))
    return world[first], int(hit[first]), bary[first]


class Relief:
    def __init__(self):
        cache = np.load(CACHE / 'actual-neutral-surface.npz')
        report = json.loads((CACHE / 'projection-review.json').read_text())
        self.points = cache['Head_world']
        self.triangles = cache['Head_triangles']
        self.pixels = np.load(CACHE / 'TrueFront-head-pixels.npy')
        self.eyes = np.asarray([report['bones'][name]['headWorld'] for name in ('Eye_L', 'Eye_R')])
        self.radii = np.asarray([.02051062218002459, .02054031389599626])
        # Named crest/valley and connecting forehead handles. Negative Y is
        # anterior. This creates a broad supported hood and zygomatic plane,
        # rather than incrementing another weak Gaussian or separate lobe.
        specs = [
            ('glabella_lower', (500, 437), -.175, False),
            ('glabella_furrow', (500, 374), -.157, False),
            ('corrugator_column', (550, 374), -.168, True),
            ('brow_medial_mass', (559, 440), -.178, True),
            ('brow_crest', (635, 423), -.180, True),
            ('brow_lateral_mass', (730, 422), -.137, True),
            ('forehead_brow_support', (635, 366), -.167, True),
            ('nasal_bridge', (500, 509), -.178, False),
            ('nasal_tip', (500, 562), -.187, False),
            ('upper_cheek_crest', (727, 550), -.153, True),
            ('oblique_malar_plane', (746, 592), -.135, True),
            ('malar_hollow', (711, 631), -.133, True),
            ('nasolabial_upper_valley', (623, 593), -.154, True),
            ('nasolabial_lower_valley', (655, 656), -.151, True),
            ('upper_muzzle_column', (568, 626), -.186, True),
            ('philtrum_valley', (500, 637), -.181, False),
            ('upper_lip_roll', (545, 684), -.194, True),
            ('upper_lip_center', (500, 684), -.194, False),
            ('lower_lip_roll', (551, 724), -.199, True),
            ('lower_lip_center', (500, 724), -.199, False),
            ('labiomental_recess', (500, 757), -.185, False),
            ('labiomental_lateral', (570, 757), -.179, True),
            ('chin_supported_front', (500, 811), -.199, False),
            ('mandibular_plane', (721, 744), -.145, True),
        ]
        # Zero anchors at skull/neck/periphery keep the identity silhouette
        # stable while the missing facial relief is authored explicitly.
        for i, xy in enumerate([(500, 210), (630, 241), (750, 300), (810, 403),
                                (814, 563), (806, 682), (740, 808), (632, 854),
                                (500, 875)]):
            specs.append(('unchanged_periphery_'+str(i), xy, None, xy[0] != 500))
        handles = []
        for name, pixel, target_y, mirror in specs:
            for side in range(2 if mirror else 1):
                xy = (1000-pixel[0], pixel[1]) if side else pixel
                point, triangle, bary = pick(self.points, self.triangles, self.pixels, xy)
                target = point.copy()
                if target_y is not None:
                    target[1] = target_y
                handles.append({'name': name+('_R' if side else '_L' if mirror else ''),
                                'pixel': list(xy), 'triangle': triangle,
                                'barycentric': bary.tolist(), 'source': point.tolist(),
                                'target': target.tolist()})
        self.handles = handles
        self.centers = np.asarray([h['source'] for h in handles])
        self.targets = np.asarray([h['target'] for h in handles])
        # Anisotropic support carries the external relief through internal
        # facial geometry without a sharp front/back spatial discontinuity.
        self.radius = .075
        self.metric = np.asarray((1., .30, 1.))
        matrix = self.kernel(self.centers)
        attenuation = self.attenuation(self.centers)
        wanted = self.targets-self.centers
        if np.any((attenuation < .10) & (np.linalg.norm(wanted, axis=1) > .001)):
            raise RuntimeError('An authored mass handle overlaps actual ocular contact protection')
        self.coefficients = np.linalg.solve(matrix+np.eye(len(matrix))*1e-9,
                                            wanted/np.maximum(attenuation[:, None], 1e-10))
        residual = np.linalg.norm(self.transform(self.centers)-self.targets, axis=1)
        if residual.max() > .000001:
            raise RuntimeError('Exact facial handle interpolation failed')
        self.maximum_handle_error = float(residual.max())

    def kernel(self, points):
        d = (np.asarray(points)[:, None, :]-self.centers[None, :, :])*self.metric
        r = np.linalg.norm(d, axis=2)/self.radius
        return np.maximum(1-r, 0)**4*(4*r+1)

    def attenuation(self, points):
        p = np.asarray(points)
        support = smooth((.020-p[:, 1])/.085)
        # Preserve the actual globe plus only a10mm transition; unlike the
        # old26–50mm field this does not pin the surrounding supraorbital mass.
        for center, radius in zip(self.eyes, self.radii):
            distance = np.linalg.norm(p-center, axis=1)
            support *= smooth((distance-(radius+.0005))/.010)
        return support

    def delta(self, points):
        p = np.asarray(points, float).reshape(-1, 3)
        out = np.empty_like(p)
        for start in range(0, len(p), 4096):
            q = p[start:start+4096]
            out[start:start+len(q)] = (self.kernel(q)@self.coefficients)*self.attenuation(q)[:, None]
        return out

    def transform(self, points):
        p = np.asarray(points, float).reshape(-1, 3)
        return p+self.delta(p)


if __name__ == '__main__':
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'v9n_wip'))
    from macro_envelope_v9nb import surface_report
    fit = Relief()
    deformed = fit.transform(fit.points)
    try:
        metrics = surface_report(fit.points, deformed, fit.triangles)
    except RuntimeError as failure:
        a = fit.points[fit.triangles]
        b = deformed[fit.triangles]
        an = np.cross(a[:, 1]-a[:, 0], a[:, 2]-a[:, 0])
        bn = np.cross(b[:, 1]-b[:, 0], b[:, 2]-b[:, 0])
        cosine = np.einsum('ij,ij->i', an, bn)/np.maximum(np.linalg.norm(an, axis=1)*np.linalg.norm(bn, axis=1), 1e-30)
        metrics = {'failed': str(failure), 'flippedTriangles': int((cosine <= 0).sum()),
                   'maximumDisplacementMeters': float(np.linalg.norm(deformed-fit.points, axis=1).max()),
                   'worstCenters': a[np.argsort(cosine)[:8]].mean(1).tolist(),
                   'worstCosines': np.sort(cosine)[:8].tolist()}
    result = {'status': 'Actual cached mesh preflight only; Blender source and clay/material views pending',
              'artisticAcceptance': False, 'handles': fit.handles,
              'maximumHandleResidualMeters': fit.maximum_handle_error,
              'surface': metrics}
    np.save(CACHE / 'proposed-relief-delta.npy', deformed-fit.points)
    (CACHE / 'landmark-relief-preflight.json').write_text(json.dumps(result, indent=2)+'\n', newline='\n')
    print(json.dumps(result['surface'], indent=2))
