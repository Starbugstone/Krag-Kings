"""Prepared continuous facial planes on the actual v9nb envelope.

This is a sculpt proposal, not accepted anatomy. Surface measurements anchor
bounded broad brow, cheek and mandibular planes. One smooth field also moves
oral/ocular shapes and facial pivots; no detached skin pieces are added.
"""
import numpy as np
from macro_envelope_v9nb import smooth, surface_report


class Envelope:
    def __init__(self, eye_centers, eye_radii, lip_center, nose_center,
                 head_points=None, measured_planes=None):
        self.eyes = np.asarray(eye_centers, float)
        self.radii = np.asarray(eye_radii, float)
        self.eye = self.eyes.mean(0)
        self.lip = np.asarray(lip_center, float)
        self.nose = np.asarray(nose_center, float)
        if not .005 < self.radii.min() <= self.radii.max() < .040:
            raise RuntimeError('Unexpected actual ocular bounds')
        if measured_planes is None:
            p = np.asarray(head_points, float)
            x, y, z = p.T
            ax = abs(x)
            anterior = y < self.eye[1] - .010
            regions = {
                'brow': anterior & (ax > .026) & (ax < .091)
                        & (z > self.eye[2] + .011) & (z < self.eye[2] + .042),
                'cheek': anterior & (ax > .070) & (ax < .111)
                         & (z > self.eye[2] - .069) & (z < self.eye[2] - .025),
                'chin': anterior & (ax < .062)
                        & (z > self.lip[2] - .061) & (z < self.lip[2] - .024),
            }
            if any(mask.sum() < 30 for mask in regions.values()):
                raise RuntimeError('Actual facial plane landmark support is missing')
            self.planes = {name: float(np.quantile(y[mask], .25)) for name, mask in regions.items()}
            self.measurement_counts = {name: int(mask.sum()) for name, mask in regions.items()}
        else:
            self.planes = dict(measured_planes)
            self.measurement_counts = None
        self.eye_moves = self.base_delta(self.eyes)

    def base_delta(self, points):
        p = np.asarray(points, float).reshape(-1, 3)
        x, y, z = p.T
        ax = np.sqrt(x*x + .006**2)
        eyz, lipz, nz = self.eye[2], self.lip[2], self.nose[2]
        g = lambda v, c, w: np.exp(-((v-c)/w)**2)
        front = smooth((self.eye[1] + .085-y)/.085)
        neck = smooth((z-(lipz-.100))/.055)
        crown = smooth(((eyz+.144)-z)/.055)
        support = front * neck * crown
        out = np.zeros_like(p)
        bx = float(np.mean(abs(self.eyes[:, 0])))

        # Broad sloped supraorbital surfaces blend into forehead, with a
        # separately readable pair. Their target is measured from this mesh,
        # not a larger arbitrary projection beyond the existing profile.
        brow_z = eyz + .020 + .15*(ax-bx)
        brow = np.minimum(g(x, bx, .045) + g(x, -bx, .045), 1.) * g(z, brow_z+.012, .040)
        brow_plane = self.planes['brow'] + .38*(z-(eyz+.020)) + .24*(ax-bx)
        out[:, 1] += .010*np.tanh((brow_plane-y)/.018) * brow

        # Upper cheek planes turn toward the side of the face instead of
        # forming a uniformly inflated convex pad.
        cheek = g(ax, .084, .039) * g(z, eyz-.048, .049)
        cheek_plane = self.planes['cheek'] + .52*(ax-.083) - .16*(z-(eyz-.048))
        out[:, 1] += .009*np.tanh((cheek_plane-y)/.018) * cheek

        # Nasolabial separation is a softly ended valley with an adjoining
        # broad cheek roll. No hard face-set cutoff or independent lobe.
        t = np.clip((nz-.006-z)/max(.018, nz-lipz+.002), 0, 1)
        fold_x = .035 + .025*t - .004*np.sin(np.pi*t)
        ends = smooth((nz+.008-z)/.018) * smooth((z-(lipz-.014))/.024)
        out[:, 1] += .0055*g(ax, fold_x, .011)*ends
        out[:, 1] -= .0020*g(ax, fold_x+.015, .022)*ends

        # Glabellar grooves and philtrum are subordinate to the large planes.
        # Their broad support preserves continuous first derivatives.
        glabella = (g(x, .010, .0055)+g(x, -.010, .0055))*g(z, eyz+.040, .033)
        out[:, 1] += .0020*glabella
        philtrum = g(z, (nz+lipz)*.5-.006, .022)
        out[:, 1] += .0015*g(x, 0, .0055)*philtrum
        out[:, 1] -= .0012*(g(x, .009, .005)+g(x, -.009, .005))*philtrum

        # A broad short lower lip, with modest corner downturn. Both oral
        # margins receive the same field, rather than separating closed lips.
        lip_width = np.exp(-(x/.071)**6)
        out[:, 1] += .0018*g(z, lipz-.010, .012)*lip_width
        out[:, 1] -= .0017*g(z, lipz+.004, .008)*lip_width
        out[:, 2] -= .0028*g(ax, .056, .018)*g(z, lipz+.001, .025)

        # Shape mandibular front/side as a broad connected plane. The max
        # contribution is bounded; it cannot become another thin chin wedge.
        jaw = g(ax, .052, .056)*g(z, lipz-.042, .038)
        jaw_plane = self.planes['chin'] + .45*(ax-.040) + .10*(z-(lipz-.043))
        out[:, 1] += .008*np.tanh((jaw_plane-y)/.018)*jaw
        return out*support[:, None]

    def delta(self, points):
        p = np.asarray(points, float).reshape(-1, 3)
        d = self.base_delta(p)
        weights = []
        for center, radius in zip(self.eyes, self.radii):
            # The earlier50mm optical transition flattened most intended brow
            # shaping. This smaller field retains the actual globe/contact
            # envelope, with a bounded transition measured by the Jacobian.
            inner = radius + .0005
            distance = np.linalg.norm(p-center, axis=1)
            weights.append(1-smooth((distance-inner)/.026))
        w = np.stack(weights, axis=1)
        total = w.sum(1)
        return d*(1-np.minimum(total, 1))[:, None] + w@self.eye_moves/np.maximum(total, 1)[:, None]

    def transform(self, points):
        p = np.asarray(points, float).reshape(-1, 3)
        return p+self.delta(p)

    def jacobian_report(self, points):
        p = np.asarray(points, float)
        columns = []
        for axis in range(3):
            offset = np.zeros(3)
            offset[axis] = .00001
            columns.append((self.transform(p+offset)-self.transform(p-offset))/.00002)
        j = np.stack(columns, axis=2)
        det = np.linalg.det(j)
        sv = np.linalg.svd(j, compute_uv=False)
        if det.min() <= .20 or sv.min() <= .20 or sv.max() > 2.2:
            raise RuntimeError('Anatomical field exceeds unchanged deformation bounds: '+str((float(det.min()), float(sv.min()), float(sv.max()))))
        return {'minimumJacobianDeterminant': float(det.min()), 'minimumLocalScale': float(sv.min()),
                'maximumLocalScale': float(sv.max()), 'sampleCount': len(p)}
