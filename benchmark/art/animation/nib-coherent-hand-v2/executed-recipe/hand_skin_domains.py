"""Topology-based domains for the actual fitted Nib left hand.

Distal fingers are disconnected components of a cross-section of the saved
mesh, not overlapping Euclidean influence spheres. Harmonic transition through
the palm keeps their skin connected without exchanging distant digit weights.
This only prepares skinning fields; an actual native pose review is mandatory.
"""
import numpy as np

DIGITS = ['Index', 'Middle', 'Ring', 'Little', 'Thumb']


def components(indices, adjacent):
    unseen = set(map(int, indices)); result = []
    while unseen:
        queue = [unseen.pop()]; part = []
        while queue:
            vertex = queue.pop(); part.append(vertex)
            near = adjacent[vertex] & unseen
            unseen -= near; queue.extend(near)
        result.append(sorted(part))
    return result


def solve(points, faces, source_cage=False):
    points = np.asarray(points, dtype=np.float64)
    edges = set()
    for face in faces:
        face = list(face)
        for a, b in zip(face, face[1:]+face[:1]):
            if a != b:
                edges.add(tuple(sorted((int(a), int(b)))))
    adjacent = [set() for _ in points]
    for a, b in edges:
        adjacent[a].add(b); adjacent[b].add(a)
    fingers = components(np.flatnonzero(points[:, 2] < (-.125 if source_cage else .550)), adjacent)
    if len(fingers) != 4:
        raise RuntimeError('Expected four separate actual distal finger surfaces')
    fingers.sort(key=lambda part: float(points[part, 0].mean()), reverse=source_cage)
    thumb_mask = ((points[:, 0] > .072) & (points[:, 2] < -.070) if source_cage else
                  (points[:, 0] < .197) & (points[:, 2] < .580))
    thumb = components(np.flatnonzero(thumb_mask), adjacent)
    if len(thumb) != 1:
        raise RuntimeError('Expected one connected actual distal thumb surface')
    fields = np.zeros((len(points), 6))
    pinned = (((points[:, 2] > -.055) & (points[:, 0] < .035)) | (points[:, 2] > -.025)
              if source_cage else
              ((points[:, 2] > .583) & (points[:, 0] > .204)) | (points[:, 2] > .606))
    fields[pinned, 5] = 1
    palm_count = int(pinned.sum())
    for digit, part in enumerate(fingers+[thumb[0]]):
        if pinned[part].any():
            raise RuntimeError('Semantic finger and palm seeds overlap')
        pinned[part] = True; fields[part, digit] = 1
    edges = np.array(sorted(edges), dtype=np.int32)
    a = np.concatenate([edges[:, 0], edges[:, 1]])
    b = np.concatenate([edges[:, 1], edges[:, 0]])
    conductance = 1/np.maximum(np.linalg.norm(points[a]-points[b], axis=1), 1e-7)
    degree = np.bincount(a, weights=conductance, minlength=len(points))
    if (degree <= 0).any():
        raise RuntimeError('Isolated hand vertices')
    unknown = np.flatnonzero(~pinned)
    local = np.full(len(points), -1, dtype=np.int32); local[unknown] = np.arange(len(unknown))
    both = (~pinned[a]) & (~pinned[b])
    ia, ib, w = local[a[both]], local[b[both]], conductance[both]
    diagonal = degree[unknown]
    rhs = np.column_stack([np.bincount(a, weights=conductance*fields[b, channel],
                                      minlength=len(points))[unknown] for channel in range(6)])

    def apply(value):
        return diagonal[:, None]*value-np.column_stack([
            np.bincount(ia, weights=w*value[ib, channel], minlength=len(unknown))
            for channel in range(6)])

    # Jacobi-preconditioned conjugate gradients on the positive Dirichlet
    # Laplacian. Each channel is an independent RHS with shared connectivity.
    x = np.zeros_like(rhs); residual = rhs.copy()
    z = residual/diagonal[:, None]; direction = z.copy()
    rz = np.sum(residual*z, axis=0)
    scale = np.maximum(np.sqrt(np.sum(rhs*rhs, axis=0)), 1)
    active = np.ones(6, dtype=bool)
    for iteration in range(2000):
        product = apply(direction)
        denominator = np.sum(direction*product, axis=0)
        alpha = np.divide(rz, denominator, out=np.zeros(6), where=active & (denominator > 0))
        x += direction*alpha
        residual -= product*alpha
        relative = np.sqrt(np.sum(residual*residual, axis=0))/scale
        active = relative > 1e-9
        if not active.any():
            break
        z = residual/diagonal[:, None]
        next_rz = np.sum(residual*z, axis=0)
        beta = np.divide(next_rz, rz, out=np.zeros(6), where=active & (rz > 0))
        direction = z+direction*beta
        direction[:, ~active] = 0
        rz = next_rz
    if active.any():
        raise RuntimeError('Hand-domain harmonic solve failed to converge')
    fields[unknown] = x
    error = float(np.max(np.abs(fields.sum(axis=1)-1)))
    if error > 1e-6 or fields.min() < -1e-7 or not np.isfinite(fields).all():
        raise RuntimeError('Invalid harmonic hand partition')
    fields = np.maximum(fields, 0); fields /= fields.sum(axis=1)[:, None]
    return fields, {'coordinateSource': 'Original licensed cage' if source_cage else 'Saved fitted hand',
                    'digitSeedCounts': dict(zip(DIGITS, map(len, fingers+[thumb[0]]))),
                    'palmSeedCount': palm_count, 'unknownVertices': len(unknown),
                    'iterations': iteration+1, 'maximumRelativeResidual': float(relative.max()),
                    'maximumPartitionError': error}


def weights(points, domains, chains, side='L', joint_half_width=.0035):
    points = np.asarray(points, dtype=np.float64)
    domains = domains.copy()
    # An interdigital web belongs to its two neighboring digits and the palm.
    # Long-range harmonic tails from other digits should remain in the palm,
    # rather than dragging that surface toward several independently bent tips.
    ranked = np.argsort(-domains[:, :5], axis=1)
    keep = np.zeros((len(points), 5), dtype=bool)
    np.put_along_axis(keep, ranked[:, :2], True, axis=1)
    palmar_residual = np.where(keep, 0., domains[:, :5]).sum(axis=1)
    domains[:, :5] = np.where(keep, domains[:, :5], 0.)
    domains[:, 5] += palmar_residual
    names = ['Hand_'+side]
    fields = [domains[:, 5]]
    for digit, name in enumerate(DIGITS):
        joints = np.asarray(chains[name], dtype=np.float64)
        vectors = joints[1:]-joints[:-1]
        lengths = np.linalg.norm(vectors, axis=1)
        offsets = np.r_[0., np.cumsum(lengths)]
        t = np.clip(np.sum((points[:, None, :]-joints[:-1])*vectors, axis=2)/lengths**2, 0, 1)
        nearest = joints[:-1]+t[:, :, None]*vectors
        segment = np.argmin(np.linalg.norm(points[:, None, :]-nearest, axis=2), axis=1)
        s = offsets[segment]+t[np.arange(len(points)), segment]*lengths[segment]
        previous = np.ones(len(points))
        for joint in range(1, len(joints)):
            if joint == len(joints)-1:
                following = np.zeros(len(points))
            else:
                value = np.clip((s-offsets[joint]+joint_half_width)/(2*joint_half_width), 0, 1)
                following = value*value*(3-2*value)
            fields.append(domains[:, digit]*np.maximum(0., previous-following))
            names.append(name+str(joint)+'_'+side)
            previous = following
    values = np.array(fields).T
    order = np.argsort(-values, axis=1)
    keep = np.zeros_like(values, dtype=bool)
    np.put_along_axis(keep, order[:, :4], True, axis=1)
    removed = np.sum(np.where(keep, 0, values), axis=1)
    values = np.where(keep, values, 0)
    values /= values.sum(axis=1)[:, None]
    return names, values, {'maximumHarmonicTailReturnedToPalm': float(palmar_residual.max()),
                          'maximumDiscardedWeightForFourInfluences': float(removed.max()),
                          'jointTransitionHalfWidthMeters': joint_half_width}
