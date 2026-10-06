"""Prepared dense-surface Krag planes/folds after the bounded v9h profile.

Only external cranial/labial skin receives these displacements. The preserved
oral bag and optical regions are excluded. This is ungenerated sculpt work,
not an accepted face or a substitute for the next actual profile/head review.
"""
import heapq
import numpy as np


def surface_tags(mesh):
    attribute = mesh.attributes.get('.sculpt_face_set')
    if attribute is None:
        raise RuntimeError('Dense facial relief requires audited anatomical face sets')
    tags = np.zeros(len(mesh.vertices), dtype=np.uint64)
    for polygon, item in zip(mesh.polygons, attribute.data):
        tags[list(polygon.vertices)] |= np.uint64(1) << np.uint64(item.value)
    return tags


def boundary_fade(raw, edges, allowed, width=.005):
    """Fade within external skin to protected lip/lid boundaries along edges."""
    neighbors = [[] for _ in raw]
    border = np.zeros(len(raw), dtype=bool)
    for a, b in edges:
        if allowed[a] != allowed[b]:
            border[a if allowed[a] else b] = True
        elif allowed[a]:
            length = float(np.linalg.norm(raw[a] - raw[b]))
            neighbors[a].append((b, length)); neighbors[b].append((a, length))
    distance = np.full(len(raw), np.inf)
    queue = [(0., int(i)) for i in np.flatnonzero(border)]
    for _, i in queue:
        distance[i] = 0
    heapq.heapify(queue)
    while queue:
        value, i = heapq.heappop(queue)
        if value != distance[i] or value >= width:
            continue
        for j, length in neighbors[i]:
            trial = value + length
            if trial < distance[j]:
                distance[j] = trial; heapq.heappush(queue, (trial, int(j)))
    t = np.clip(distance / width, 0, 1)
    return t * t * (3 - 2 * t) * allowed


def apply(raw, points, tags, edges):
    raw = np.asarray(raw, dtype=float)
    result = np.asarray(points, dtype=float).copy()
    x, y, z = raw.T
    member = lambda value: (tags & (np.uint64(1) << np.uint64(value))) != 0
    external = (member(33) | member(24) | member(11)) & ~member(7)
    # Preserve true orbital/lid margins, mouth rim and inner oral surfaces.
    external &= ~(member(5) | member(6) | member(9) | member(10))
    front = np.clip((-y - .035) / .070, 0, 1) * boundary_fade(raw, edges, external)
    g = lambda a, c, w: np.exp(-((a - c) / w) ** 2)
    d = np.zeros_like(result)

    # A low thick supraorbital pad, not the removed narrow projecting beak.
    # Added projection is bounded to millimetres on the dense skin surface.
    arch = .326 + .24 * abs(x)
    hood = g(abs(x), .036, .023) * g(z, arch, .011) * front
    d[:, 1] -= .0045 * hood
    d[:, 2] -= .0020 * hood
    # Paired vertical glabellar cuts and restrained adjacent compression ridges.
    for sign in [-1, 1]:
        center = sign * (.010 + .038 * (z - .340))
        support = g(z, .349, .024) * front
        d[:, 1] += .0038 * g(x, center, .0018) * support
        d[:, 1] -= .0018 * g(x, center + sign * .0034, .0028) * support

    # Nasolabial furrow follows the actual alar-to-commissure interval, ending
    # near |source X|=.0242 rather than the obsolete .043 m mouth width.
    t = np.clip((.268 - z) / .037, 0, 1)
    nasolabial = .0190 + .0052 * t
    support = g(z, .250, .026) * front
    d[:, 1] += .0050 * g(abs(x), nasolabial, .0022) * support
    d[:, 1] -= .0025 * g(abs(x), nasolabial + .0036, .0038) * support

    # Flatten only the middle/lower lateral cheek toward a bounded plane.
    # Crown, outer silhouette, muzzle and the v9h rounded chin are preserved.
    cheek = g(abs(x), .058, .018) * g(z, .247, .031) * front
    plane = -.122 - .24 * (z - .240) + .36 * (abs(x) - .055)
    d[:, 1] += .65 * np.clip(plane - result[:, 1], -.011, .011) * cheek

    # Short broken vertical furrows on the upper/lower lip, with a quiet gap
    # at the true closed rim. Irregular spacing avoids an embossed comb effect.
    for side in [-1, 1]:
        for xx, strength in [(.0042, .00070), (.0090, .00095), (.0146, .00060), (.0190, .00075)]:
            stripe = g(x, side * (xx + .020 * (z - .245)), .00072)
            upper = g(z, .2435 + .001 * np.sin(xx * 380), .0060)
            lower = g(z, .2200 - .001 * np.sin(xx * 240), .0048)
            d[:, 1] += strength * stripe * (upper + .7 * lower) * front
    # Prevent a local overlap of fields from recreating profile spikes.
    d[:, 1] = np.clip(d[:, 1], -.007, .009)
    if not np.isfinite(d).all():
        raise RuntimeError('Invalid prepared face relief')
    return result + d
