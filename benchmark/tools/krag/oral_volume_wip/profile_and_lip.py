"""Coherent profile proposal and posed lip residuals on true oral topology.

These are unaccepted fitting values derived from the actual v9qa failure.
They do not change the authored jaw range or replace the facial topology.
"""
from pathlib import Path
import sys
import heapq
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent/'landmark_wip'))
from landmark_relief import smooth


def distances(points, edges, seeds):
    graph = [[] for _ in points]
    for a, b in edges:
        length = float(np.linalg.norm(points[a]-points[b]))
        graph[a].append((int(b), length))
        graph[b].append((int(a), length))
    result = np.full(len(points), np.inf)
    queue = []
    for i in np.flatnonzero(seeds):
        result[i] = 0
        heapq.heappush(queue, (0., int(i)))
    while queue:
        distance, a = heapq.heappop(queue)
        if distance != result[a]:
            continue
        for b, length in graph[a]:
            proposal = distance+length
            if proposal < result[b]:
                result[b] = proposal
                heapq.heappush(queue, (proposal, b))
    return result


def membership(mesh):
    tags = np.asarray([v.value for v in mesh.attributes['.sculpt_face_set'].data], int)
    masks = np.zeros(len(mesh.vertices), np.uint64)
    for polygon, tag in zip(mesh.polygons, tags):
        masks[list(polygon.vertices)] |= np.uint64(1) << np.uint64(tag)
    return masks


def member(masks, tag):
    return (masks & (np.uint64(1) << np.uint64(tag))) != 0


class Profile:
    oral_translation = np.asarray((0., .008, .010))

    def __init__(self, points, edges, masks, eyes, eye_radii):
        self.points = np.asarray(points, float)
        self.eyes = np.asarray(eyes)
        self.eye_radii = np.asarray(eye_radii)
        self.upper = member(masks, 33) & member(masks, 7)
        self.lower = member(masks, 24) & member(masks, 7)
        self.corner = self.upper & self.lower
        if self.corner.sum() != 2:
            raise RuntimeError('Expected two true oral commissures')
        self.oral_distance = distances(points, edges, self.upper | self.lower)
        # Full coherent mouth translation over the lip rolls; a broad smooth
        # transition brings the surrounding muzzle and chin along with it.
        self.oral_support = 1-smooth((self.oral_distance-.012)/.048)
        self.oral_support[self.oral_distance >= .060] = 0

    def nasal(self, points):
        p = np.asarray(points, float)
        # v9qa compressed each alar mass by about14mm. Restore broad nasal
        # width and anterior support instead of sharpening another small tip.
        center = np.asarray((0., -.150, 1.897))
        radius = np.linalg.norm((p-center)/np.asarray((.073, .105, .039)), axis=1)
        field = 1-smooth((radius-.38)/.62)
        for eye, eye_radius in zip(self.eyes, self.eye_radii):
            field *= smooth((np.linalg.norm(p-eye, axis=1)-eye_radius)/.014)
        delta = np.zeros_like(p)
        delta[:, 0] = p[:, 0]*.35*field
        delta[:, 1] = -.008*field
        return delta

    def head(self, points):
        p = np.asarray(points, float)
        if len(p) != len(self.oral_support):
            raise RuntimeError('Profile needs unchanged actual Head indexing')
        return p+self.nasal(p)+self.oral_support[:, None]*self.oral_translation


def ordered_rim(edges, selected, points):
    selected_ids = set(map(int, np.flatnonzero(selected)))
    graph = {i: [] for i in selected_ids}
    for a, b in edges:
        if int(a) in selected_ids and int(b) in selected_ids:
            graph[int(a)].append(int(b)); graph[int(b)].append(int(a))
    ends = [i for i, neighbors in graph.items() if len(neighbors) == 1]
    if len(ends) != 2 or any(len(n) not in (1, 2) for n in graph.values()):
        raise RuntimeError('Actual oral rim is not one open simple path')
    start = min(ends, key=lambda i: points[i, 0])
    order = [start]; prior = None
    while True:
        following = [i for i in graph[order[-1]] if i != prior]
        if not following:
            break
        prior, current = order[-1], following[0]
        order.append(current)
    if len(order) != len(selected_ids):
        raise RuntimeError('Oral rim has disconnected topology')
    return np.asarray(order, int)


def round_lower_rim(order, rest, posed, rigid_jaw):
    """A continuous lower arc, with fixed actual corners and full center drop.

    Target positions are posed residual constraints, not another jaw rotation.
    Cubic tangents give rounded transitions instead of the current straight
    near-vertical sheets. Dental clearance remains an actual-render gate.
    """
    center_index = int(np.argmin(abs(rest[order, 0])))
    center_id = int(order[center_index])
    middle = rigid_jaw[center_id].copy()
    target = posed[order].copy()
    for part in (order[:center_index+1], order[center_index:][::-1]):
        start = posed[part[0]].copy()
        arc = np.linalg.norm(np.diff(rest[part], axis=0), axis=1)
        t = np.r_[0., np.cumsum(arc)]
        t /= t[-1]
        # Rounded support across the complete corner-to-center lip, not a
        # point adjustment at the two endpoint vertices.
        a = start*.82+middle*.18
        a[2] = start[2]*.55+middle[2]*.45
        b = start*.50+middle*.50
        b[2] = middle[2]
        curve = ((1-t)**3)[:, None]*start+3*((1-t)**2*t)[:, None]*a
        curve += 3*((1-t)*t*t)[:, None]*b+(t**3)[:, None]*middle
        lookup = {int(vertex): i for i, vertex in enumerate(order)}
        for vertex, point in zip(part, curve):
            target[lookup[int(vertex)]] = point
    return target


def extend_residual(points, edges, lower_order, targets, posed, upper_mask):
    """Graph-harmonic posed correction in a bounded actual oral neighborhood."""
    lower = np.zeros(len(points), bool); lower[lower_order] = True
    distance = distances(points, edges, lower)
    active = distance < .035
    fixed = ~active | upper_mask | lower
    delta = np.zeros_like(points)
    delta[lower_order] = targets-posed[lower_order]
    delta[upper_mask] = 0
    a, b = edges.T
    weight = 1/np.maximum(np.linalg.norm(points[a]-points[b], axis=1), .00005)
    diagonal = np.bincount(a, weight, len(points))+np.bincount(b, weight, len(points))
    unknown = np.flatnonzero(~fixed)
    if len(unknown) == 0:
        raise RuntimeError('No continuous oral support around real lip rim')
    # Damped Jacobi is adequate for the small, bounded support; exact rim
    # controls remain Dirichlet values at every iteration.
    converged = False
    for iteration in range(1800):
        neighbor = np.zeros_like(delta)
        for axis in range(3):
            neighbor[:, axis] = np.bincount(a, weight*delta[b, axis], len(points))
            neighbor[:, axis] += np.bincount(b, weight*delta[a, axis], len(points))
        proposed = neighbor[unknown]/diagonal[unknown, None]
        residual = float(abs(proposed-delta[unknown]).max())
        delta[unknown] += .85*(proposed-delta[unknown])
        if residual < .0000003:
            converged = True
            break
    if not converged:
        raise RuntimeError('Lip support solve did not converge within bounded iterations')
    return delta, {'iterations': iteration+1, 'freeVertices': len(unknown),
                   'maximumPosedCorrectionMeters': float(np.linalg.norm(delta, axis=1).max()),
                   'maximumIterationResidualMeters': residual}
