"""Constrained correspondence fit of existing face topology to visible masses.

The generated bust supplies inspected broad landmark relief, not polygons,
micro-noise, eyes, teeth or a guessed posterior skull. Existing actual globe
and contact-loop coordinates remain exact. All targets remain review proposals.
"""
from pathlib import Path
import sys
import json
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE))
from reference_landmarks import measure
sys.path.insert(0, str(HERE.parent/'landmark_wip'))
from landmark_relief import Relief, pick, smooth


class MassFit:
    def __init__(self):
        previous = Relief()
        self.points = previous.transform_head(previous.points)
        self.triangles = previous.triangles
        self.eyes = previous.eyes
        self.radii = previous.radii
        self.head_support = previous.head_support.copy()
        # The closed topology ring protects the return sheet; the actual globe
        # additionally protects lid vertices already close to its real surface.
        # This does not freeze the broad brow mass, which lies farther forward.
        rings = json.loads((ROOT/'benchmark/art/krag/landmarks-v9nc/contact-ring-topology.json').read_text())
        self.optical_radii = []
        for side, eye in zip(('L', 'R'), self.eyes):
            ids = rings[side]['candidateRingVertexIds']
            self.optical_radii.append(float(np.linalg.norm(self.points[ids]-eye, axis=1).max())+.0005)
        reference = measure()
        frame = {name: np.asarray(item['faceFramePoint']) for name, item in reference['landmarks'].items()}
        self.scale = float(np.linalg.norm(self.eyes[0]-self.eyes[1]) /
                           np.linalg.norm(frame['ocular_left_frame']-frame['ocular_right_frame']))
        center = self.eyes.mean(0)
        center[1] -= float(np.mean(self.radii))
        # Only the source-visible near-side masses are used bilaterally. The
        # source's poorly reconstructed far side is not an anatomical template.
        specs = [
            ('glabella_mass', (500, 437), 'glabella_mass', False),
            ('glabella_furrow', (500, 374), 'glabella_furrow', False),
            ('brow_crest', (635, 423), 'brow_right_crest', True),
            ('brow_supported_mass', (635, 366), 'brow_right_support', True),
            ('bridge', (500, 509), 'bridge', False),
            ('nose_tip', (500, 562), 'nose_tip', False),
            ('nasal_ala', (613, 568), 'nasal_right_ala', True),
            ('malar_crest', (727, 550), 'right_malar_crest', True),
            ('malar_plane', (746, 592), 'right_malar_plane', True),
            ('nasolabial', (655, 636), 'right_nasolabial', True),
            ('upper_muzzle', (568, 626), 'upper_muzzle_right', True),
            ('upper_lip_roll', (500, 684), 'upper_lip_center', False),
            ('lower_lip_roll', (500, 724), 'lower_lip_center', False),
            ('chin_center', (500, 811), 'chin_right_plane', False),
            ('chin_plane', (589, 803), 'chin_right_plane', True),
            ('mandibular_plane', (721, 744), 'right_jaw_angle', True),
        ]
        handles = []
        for name, pixel, ref_name, paired in specs:
            for side in range(2 if paired else 1):
                xy = (1000-pixel[0], pixel[1]) if side else pixel
                point, triangle, bary = pick(self.points, self.triangles, previous.pixels, xy)
                target = center+frame[ref_name]*self.scale
                target[0] = abs(frame[ref_name][0])*self.scale*(1 if not side else -1) if paired else 0
                if name == 'chin_center':
                    # The visible near chin supplies anterior mass, not a
                    # false off-center midline created by one-view inference.
                    target[2] = point[2]
                handles.append({'name': name+('_R' if side else '_L' if paired else ''),
                                'sourcePixel': list(xy), 'referenceLandmark': ref_name,
                                'triangle': triangle, 'barycentric': bary.tolist(),
                                'source': point.tolist(), 'target': target.tolist()})
        for index, xy in enumerate([(500, 210), (630, 241), (750, 300), (810, 403),
                                    (814, 563), (806, 682), (740, 808), (632, 854), (500, 875)]):
            for side in range(2 if xy[0] != 500 else 1):
                pixel = (1000-xy[0], xy[1]) if side else xy
                point, triangle, bary = pick(self.points, self.triangles, previous.pixels, pixel)
                handles.append({'name': f'preserved_periphery_{index}_{side}', 'sourcePixel': list(pixel),
                                'referenceLandmark': None, 'triangle': triangle, 'barycentric': bary.tolist(),
                                'source': point.tolist(), 'target': point.tolist()})
        self.handles = handles
        self.centers = np.asarray([h['source'] for h in handles])
        targets = np.asarray([h['target'] for h in handles])
        self.radius = .105
        self.metric = np.asarray((1., .28, 1.))
        attenuation = smooth((.025-self.centers[:, 1])/.090)
        for eye, radius in zip(self.eyes, self.optical_radii):
            attenuation *= smooth((np.linalg.norm(self.centers-eye, axis=1)-radius)/.018)
        if np.any((attenuation < .10) & (np.linalg.norm(targets-self.centers, axis=1) > .001)):
            blocked = [h['name'] for h, a, d in zip(handles, attenuation, np.linalg.norm(targets-self.centers, axis=1)) if a < .10 and d > .001]
            raise RuntimeError('Reference handle overlaps a real protected ocular contact: '+str(blocked))
        wanted = (targets-self.centers)/np.maximum(attenuation[:, None], 1e-10)
        self.coefficients = np.linalg.solve(self.kernel(self.centers)+np.eye(len(handles))*1e-7, wanted)
        self.reference = reference

    def kernel(self, points):
        d = (np.asarray(points)[:, None, :]-self.centers[None, :, :])*self.metric
        r = np.linalg.norm(d, axis=2)/self.radius
        return np.maximum(1-r, 0)**4*(4*r+1)

    def velocity(self, points, support=None):
        points = np.asarray(points, float).reshape(-1, 3)
        out = np.empty_like(points)
        for start in range(0, len(points), 2048):
            q = points[start:start+2048]
            field = smooth((.025-q[:, 1])/.090)
            if support is not None:
                field *= support[start:start+len(q)]
            for center, radius in zip(self.eyes, self.optical_radii):
                field *= smooth((np.linalg.norm(q-center, axis=1)-radius)/.018)
            out[start:start+len(q)] = (self.kernel(q)@self.coefficients)*field[:, None]
        return out

    def flow(self, points, support=None):
        # Integrate a smooth velocity field. A one-step displacement can cross
        # a protected globe boundary despite zero velocity on the boundary.
        # Re-evaluating there prevents that overshoot without replacing lids.
        result = np.asarray(points, float).copy()
        steps = 24
        for _ in range(steps):
            result += self.velocity(result, support)*.85/steps
        return result

    def head(self, points):
        if len(points) != len(self.points):
            raise RuntimeError('Head topology changed')
        return self.flow(points)

    def transform(self, points):
        return self.flow(points)


if __name__ == '__main__':
    fit = MassFit()
    revised = fit.head(fit.points)
    a, b = fit.points[fit.triangles], revised[fit.triangles]
    an = np.cross(a[:, 1]-a[:, 0], a[:, 2]-a[:, 0])
    bn = np.cross(b[:, 1]-b[:, 0], b[:, 2]-b[:, 0])
    cosine = np.einsum('ij,ij->i', an, bn)/np.maximum(np.linalg.norm(an, axis=1)*np.linalg.norm(bn, axis=1), 1e-30)
    semantic = np.load(ROOT/'benchmark/art/krag/landmarks-v9nc/actual-neutral-surface.npz')['Head_triangle_sets']
    values, counts = np.unique(semantic[cosine <= 0], return_counts=True)
    report = {'status': 'Cached actual topology correspondence preflight only; native source/render pending',
              'referenceSha256': fit.reference['referenceSha256'], 'scaleNormalizedToMeters': fit.scale,
              'actualContactProtectingRadiiMeters': fit.optical_radii,
              'flowDuration': .85,
              'maximumDisplacementMeters': float(np.linalg.norm(revised-fit.points, axis=1).max()),
              'flippedTriangles': int((cosine <= 0).sum()), 'worstNormalCosine': float(cosine.min()),
              'flippedByFaceSet': {str(int(a)): int(b) for a, b in zip(values, counts)},
              'worstCenters': a[np.argsort(cosine)[:12]].mean(1).tolist(),
              'handles': fit.handles, 'artisticAcceptance': False}
    path = ROOT/'benchmark/art/krag/reference-fit-study/visible-mass-fit-preflight.json'
    path.write_text(json.dumps(report, indent=2)+'\n', newline='\n')
    print(json.dumps({k: report[k] for k in ['scaleNormalizedToMeters', 'maximumDisplacementMeters', 'flippedTriangles', 'worstNormalCosine']}, indent=2))
