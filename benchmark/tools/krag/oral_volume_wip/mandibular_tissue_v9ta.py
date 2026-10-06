"""Bounded mandibular tissue proposal after the actual v9s profile failure.

The true oral rims, ocular loops and jaw range stay fixed.  This is a source
authoring proposal, not evidence of a saved mesh or an accepted mouth.
"""
import numpy as np
from profile_and_lip import member, distances, smooth


class MandibularTissue:
    def __init__(self, points, edges, masks):
        self.points = np.asarray(points, float)
        self.masks = masks
        self.lower = member(masks, 24)
        self.rim = (member(masks, 24) | member(masks, 33)) & member(masks, 7)
        self.rim_distance = distances(self.points, edges, self.rim)
        self.interface = member(masks, 24) & member(masks, 33)
        self.interface_distance = distances(self.points, edges, self.interface)
        self.edges = np.asarray(edges, int)
        self.boundary = self.lower & ~member(masks, 7) & ((masks & ~(np.uint64(1) << np.uint64(24))) != 0)
        self.boundary_distance = distances(self.points, edges, self.boundary)
        # An exterior-only, smoothly feathered domain.  A hard face-set cut
        # alone would recreate the earlier separate lip/chin shelves.
        self.exterior = self.lower & ~member(masks, 7)
        self.support = smooth(self.rim_distance/.010) * self.exterior

    @staticmethod
    def depth_profile(z):
        # Positive Y retreats the pointed chin; negative Y fills its deep
        # labiomental valley.  Quintic segments have zero first/second
        # derivative at the knots; there is no thin extrusion at a band edge.
        knots = np.asarray([1.743, 1.762, 1.776, 1.797, 1.813, 1.829])
        values = np.asarray([0., .001, .008, -.010, -.003, 0.])
        index = np.clip(np.searchsorted(knots, z, side='right')-1, 0, len(knots)-2)
        t = smooth((z-knots[index])/(knots[index+1]-knots[index]))
        result = values[index]*(1-t)+values[index+1]*t
        result[(z <= knots[0]) | (z >= knots[-1])] = 0
        return result

    def head(self, points):
        p = np.asarray(points, float)
        if len(p) != len(self.points):
            raise RuntimeError('Mandibular fit requires the actual Head correspondence')
        q = p.copy()
        front = 1-smooth((p[:, 1]+.145)/.070)
        lateral = 1-smooth((abs(p[:, 0])-.048)/.077)
        q[:, 1] += self.depth_profile(p[:, 2])*front*lateral*self.support
        if not np.array_equal(q[self.rim], p[self.rim]):
            raise RuntimeError('Mandibular profile changed the true oral rim')
        return q

    def weights(self, current, available=None):
        p = self.points
        current = np.asarray(current, float)
        # The measured source reaches full Jaw influence only11mm below a
        # fixed cheek interface.  Solve a broad35mm transition against every
        # actual cranial/neck boundary, not only the24/33 cheek interface.
        if available is None:
            available = np.ones(len(current))
        available = np.asarray(available, float)
        fixed = ~self.lower | member(self.masks, 7) | self.boundary
        anchors = self.lower & ~fixed & (self.boundary_distance >= .035)
        known = fixed | anchors
        unknown = ~known
        value = np.divide(current, available, out=np.zeros_like(current), where=available > 1e-9)
        value[anchors] = 1
        a, b = self.edges.T
        conductance = 1/np.maximum(np.linalg.norm(p[b]-p[a], axis=1), .00005)
        diagonal_all = np.bincount(a, conductance, len(p))+np.bincount(b, conductance, len(p))
        def neighbors(v):
            return np.bincount(a, conductance*v[b], len(p))+np.bincount(b, conductance*v[a], len(p))
        diagonal = diagonal_all[unknown]
        value[unknown] = 0
        rhs = neighbors(value)[unknown]
        def multiply(v):
            whole = np.zeros(len(p)); whole[unknown] = v
            return diagonal*v-neighbors(whole)[unknown]
        solution = np.zeros(int(unknown.sum())); residual = rhs.copy()
        preconditioned = residual/diagonal; direction = preconditioned.copy()
        rz = float(np.dot(residual, preconditioned)); initial = max(float(np.linalg.norm(rhs)), 1e-30)
        relative = float(np.linalg.norm(residual))/initial
        for iteration in range(3000):
            if relative < 1e-9:
                break
            product = multiply(direction); denominator = float(np.dot(direction, product))
            if denominator <= 0:
                raise RuntimeError('Mandibular tissue graph lost positive definiteness')
            step = rz/denominator; solution += step*direction; residual -= step*product
            relative = float(np.linalg.norm(residual))/initial
            next_preconditioned = residual/diagonal
            next_rz = float(np.dot(residual, next_preconditioned))
            direction = next_preconditioned+(next_rz/rz)*direction; rz = next_rz
        if relative >= 1e-9:
            raise RuntimeError('Mandibular tissue solve did not converge')
        value[unknown] = solution
        revised = np.clip(value, 0, 1)*available
        revised[fixed] = current[fixed]
        raw_range = [float(revised.min()), float(revised.max())]
        if not np.isfinite(revised).all() or revised.min() < -1e-7 or revised.max() > 1+1e-7:
            raise RuntimeError('Invalid mandibular weight proposal: '+str(raw_range))
        revised = np.clip(revised, 0, 1)
        return revised, {
            'transitionMeters': .035, 'iterations': iteration+1,
            'rawWeightRangeBeforeRoundingClamp': raw_range, 'normalizationRoundingTolerance': 1e-7,
            'relativeResidual': relative, 'anchorVertices': int(anchors.sum()),
            'changedVertices': int((abs(revised-current) > 1e-8).sum()),
            'maximumWeightChange': float(abs(revised-current).max()),
            'trueOralRimsUpperFaceNoseUnchanged': bool(np.array_equal(revised[fixed], current[fixed])),
            'method': 'Graph-harmonic lower-face tissue between actual cranial/neck boundaries,35mm mandibular anchors and preserved oral rims; full jaw rotation retained',
            'actualPoseAcceptance': False,
        }
