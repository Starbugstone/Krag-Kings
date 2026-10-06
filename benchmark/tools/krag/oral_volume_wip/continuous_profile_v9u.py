"""One continuous anterior mandibular envelope from actual mesh sections.

Unlike the rejected additive depth bands, each sagittal section has one
convex cubic contour. Actual endpoints and its anterior volume set the fit.
The true oral boundary, rear surface and lateral jaw tissue remain intact.
"""
import numpy as np
from profile_and_lip import member, distances, smooth


def cubic(a, b, c, d, t):
    return b+.5*t*(c-a+t*(2*a-5*b+4*c-d+t*(3*(b-c)+d-a)))


def sample_grid(grid, x, z, xs, zs):
    u = np.clip((x-xs[0])/(xs[1]-xs[0]), 0, len(xs)-1)
    v = np.clip((z-zs[0])/(zs[1]-zs[0]), 0, len(zs)-1)
    i = np.minimum(np.floor(u).astype(int), len(xs)-2)
    j = np.minimum(np.floor(v).astype(int), len(zs)-2)
    tx, tz = u-i, v-j
    rows = []
    for offset in (-1, 0, 1, 2):
        row = np.clip(i+offset, 0, len(xs)-1)
        values = [grid[row, np.clip(j+k, 0, len(zs)-1)] for k in (-1, 0, 1, 2)]
        rows.append(cubic(*values, tz))
    return cubic(*rows, tx)


class ContinuousProfile:
    def __init__(self, points, edges, masks, triangles, triangle_sets):
        p = np.asarray(points, float)
        self.xs = np.linspace(-.075, .075, 31)
        self.zs = np.linspace(1.768, 1.825, 49)
        source = np.full((len(self.xs), len(self.zs)), np.nan)
        tri = p[np.asarray(triangles)[np.asarray(triangle_sets) == 24]]
        a = tri[:, 0][:, [0, 2]]
        b = tri[:, 1][:, [0, 2]]-a
        c = tri[:, 2][:, [0, 2]]-a
        determinant = b[:, 0]*c[:, 1]-b[:, 1]*c[:, 0]
        valid = abs(determinant) > 1e-14
        for i, x in enumerate(self.xs):
            for j, z in enumerate(self.zs):
                q = np.asarray([x, z])-a
                u = np.divide(q[:, 0]*c[:, 1]-q[:, 1]*c[:, 0], determinant,
                              out=np.zeros(len(tri)), where=valid)
                v = np.divide(b[:, 0]*q[:, 1]-b[:, 1]*q[:, 0], determinant,
                              out=np.zeros(len(tri)), where=valid)
                selected = valid & (u >= -1e-8) & (v >= -1e-8) & (u+v <= 1+1e-8)
                if not selected.any():
                    raise RuntimeError('Missing actual exterior mandibular section at '+str((float(x), float(z))))
                y = tri[:, 0, 1]+u*(tri[:, 1, 1]-tri[:, 0, 1])+v*(tri[:, 2, 1]-tri[:, 0, 1])
                source[i, j] = y[selected].min()
        # One convex curve, with fixed sampled endpoints and preserved
        # midpoint anterior extent. Equal inner control depths guarantee a
        # single broad anterior mass rather than repeated ledges.
        t = (self.zs-self.zs[0])/(self.zs[-1]-self.zs[0])
        bottom, top = source[:, 0], source[:, -1]
        apex = source.min(1)
        control = (apex-.125*(bottom+top))/.75
        target = ((1-t)**3)[None]*bottom[:, None]+(t**3)[None]*top[:, None]
        target += (3*t*(1-t))[None]*control[:, None]
        self.source_sections, self.target_sections = source, target
        self.section_delta = target-source
        rim = (member(masks, 24) | member(masks, 33)) & member(masks, 7)
        distance = distances(p, edges, rim)
        u = (p[:, 2]-self.zs[0])/(self.zs[-1]-self.zs[0])
        z_support = smooth(u/.13)*smooth((1-u)/.13)
        x_support = 1-smooth((abs(p[:, 0])-.050)/.025)
        hull = sample_grid(source, p[:, 0], p[:, 2], self.xs, self.zs)
        anterior_support = 1-smooth((p[:, 1]-hull-.004)/.024)
        support = z_support*x_support*anterior_support*smooth(distance/.010)
        support *= member(masks, 24) & ~member(masks, 7)
        self.delta = np.zeros_like(p)
        self.delta[:, 1] = sample_grid(self.section_delta, p[:, 0], p[:, 2], self.xs, self.zs)*support
        if abs(self.delta).max() > .016:
            raise RuntimeError('Continuous profile exceeds16mm bounded correction')
        self.rim = rim
        if np.any(self.delta[rim] != 0):
            raise RuntimeError('Continuous profile changed the real oral boundary')
        self.report = {
            'method': 'Actual31x49 anterior mesh sections fitted with one convex cubic per sagittal section; bicubic continuous surface correction',
            'xRangeMeters': [float(self.xs[0]), float(self.xs[-1])],
            'zRangeMeters': [float(self.zs[0]), float(self.zs[-1])],
            'actualSectionSamples': int(source.size),
            'maximumCorrectionMeters': float(np.linalg.norm(self.delta, axis=1).max()),
            'centerSectionActualY': source[len(self.xs)//2].tolist(),
            'centerSectionTargetY': target[len(self.xs)//2].tolist(),
            'centerSectionZ': self.zs.tolist(),
            'trueOralBoundaryExact': True, 'requiresActualNeutralOpenReview': True,
        }

    def head(self, points):
        points = np.asarray(points, float)
        if points.shape != self.delta.shape:
            raise RuntimeError('Actual unchanged Head correspondence is required')
        # Translate every saved key identically at each vertex, retaining the
        # existing relative expression deltas and v9ta tissue/driver behavior.
        return points+self.delta
