"""Coordinated neutral facial planes from the actual v9u whole-face review.

The named surface handles are provisional sculpt targets, not recovered metric
depths from a perspective illustration. They share one continuous interpolant;
the actual ocular returns and closed oral contact loops remain exact.
"""
from pathlib import Path
import sys
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent/'landmark_wip'))
from landmark_relief import pick
from profile_and_lip import smooth, member, distances


def front_pixels(points):
    camera = np.asarray((0., -4., 1.92))
    target = np.asarray((0., -.02, 1.9))
    forward = target-camera; forward /= np.linalg.norm(forward)
    right = np.cross(forward, (0., 0., 1.)); right /= np.linalg.norm(right)
    up = np.cross(right, forward)
    p = np.asarray(points)-target
    return np.column_stack((500+p@right/.53*1000, 500-p@up/.53*1000))


class WholeFace:
    def __init__(self, points, edges, masks, triangles, ocular_held):
        p = np.asarray(points, float)
        self.points = p
        pixels = front_pixels(p)
        oral = member(masks, 7)
        optical_distance = distances(p, edges, ocular_held)
        oral_distance = distances(p, edges, oral)
        self.support = smooth(optical_distance/.012)*smooth(oral_distance/.008)
        self.support *= smooth((.025-p[:, 1])/.085)
        self.support[ocular_held | oral] = 0
        # Coordinate the corrugators, supported supraorbital ridge, alar
        # volume, malar plane and lip roll in one solve. Adjacent retreat
        # handles distinguish planes without cutting a new sharp crease.
        specs = [
            ('glabella_furrow', (500, 400), -.171, False),
            ('glabella_base', (500, 450), -.184, False),
            ('corrugator_column', (527, 423), -.190, True),
            ('corrugator_forehead_support', (535, 377), -.158, True),
            ('medial_brow_crest', (550, 441), -.198, True),
            ('middle_brow_crest', (606, 445), -.182, True),
            ('lateral_brow_crest', (650, 450), -.151, True),
            ('brow_roof_support', (605, 403), -.169, True),
            ('nasal_root', (500, 500), -.184, False),
            ('nasal_tip_retained', (500, 535), None, False),
            ('alar_mass', (570, 540), -.185, True),
            ('alar_return', (612, 553), -.150, True),
            ('malar_crest', (695, 530), -.151, True),
            ('oblique_cheek_plane', (695, 578), -.132, True),
            ('masseter_support', (720, 625), -.128, True),
            ('nasolabial_turn', (625, 600), -.158, True),
            ('upper_muzzle_plane', (562, 591), -.184, True),
            ('philtrum', (500, 597), -.178, False),
            ('upper_lip_margin', (565, 628), -.190, True),
            ('upper_lip_center', (500, 628), -.190, False),
        ]
        for i, xy in enumerate(((500, 275), (630, 300), (700, 365),
                                (732, 475), (730, 575), (700, 688),
                                (630, 728), (500, 730))):
            specs.append(('retained_periphery_'+str(i), xy, None, xy[0] != 500))
        self.handles = []
        for name, pixel, depth, mirror in specs:
            for side in range(2 if mirror else 1):
                xy = (1000-pixel[0], pixel[1]) if side else pixel
                point, triangle, bary = pick(p, triangles, pixels, xy)
                target = point.copy()
                if depth is not None:
                    target[1] = depth
                attenuation = float(self.support[triangles[triangle]]@bary)
                if attenuation < .12 and np.linalg.norm(target-point) > .001:
                    raise RuntimeError('A facial mass target touches the real contact loops: '+name)
                self.handles.append(dict(name=name+('_R' if side else '_L' if mirror else ''),
                                         pixel=list(xy), point=point.tolist(),
                                         target=target.tolist(), support=attenuation))
        self.centers = np.asarray([h['point'] for h in self.handles])
        targets = np.asarray([h['target'] for h in self.handles])
        support = np.asarray([h['support'] for h in self.handles])
        self.coefficients = np.linalg.solve(self.kernel(self.centers)+np.eye(len(support))*1e-9,
                                            (targets-self.centers)/np.maximum(support[:, None], 1e-10))
        delta = np.zeros_like(p)
        for start in range(0, len(p), 2048):
            q = p[start:start+2048]
            delta[start:start+len(q)] = (self.kernel(q)@self.coefficients)*self.support[start:start+len(q), None]
        # The actual front shows an overly broad dome and inflated lateral
        # cheeks. Narrow only their outside envelope, leaving the approved
        # eye and oral intervals, ear roots and the continuous chin profile.
        side = smooth((abs(p[:, 0])-.068)/.066)
        vertical = smooth((p[:, 2]-1.79)/.055)
        cranial = smooth((p[:, 2]-1.951)/.055)
        envelope = -.045*p[:, 0]*side*vertical
        envelope += -.025*p[:, 0]*cranial
        delta[:, 0] += envelope*self.support
        self.delta = delta
        self.held = ocular_held | oral
        if np.any(delta[self.held] != 0):
            raise RuntimeError('Whole-face field moved a real oral/ocular contact point')
        maximum = float(np.linalg.norm(delta, axis=1).max())
        if maximum > .030:
            raise RuntimeError('Whole-face relief exceeds30mm: '+str(maximum))
        residual = np.linalg.norm(self.centers+(self.kernel(self.centers)@self.coefficients)*support[:, None]-targets, axis=1)
        self.report = dict(method='One compact continuous facial-plane solve with exact surface handles and a modest lateral envelope fit',
                           maximumDisplacementMeters=maximum, maximumDepthHandleResidualMeters=float(residual.max()),
                           actualOcularAndOralPointsHeld=int(self.held.sum()),
                           upperCranialNarrowingProposal=.025, lateralEnvelopeNarrowingProposal=.045,
                           handles=self.handles,
                           sourceReference='concept01, compared against actual v9u front/three-quarter/open views',
                           targetDepthsAreSculptProposals=True, artisticAcceptance=False)

    def kernel(self, points):
        d = (np.asarray(points)[:, None]-self.centers[None])*np.asarray((1., .4, 1.))
        r = np.linalg.norm(d, axis=2)/.066
        return np.maximum(1-r, 0)**4*(4*r+1)

    def head(self, points):
        p = np.asarray(points, float)
        if p.shape != self.delta.shape:
            raise RuntimeError('Actual unchanged Head indexing required')
        return p+self.delta
