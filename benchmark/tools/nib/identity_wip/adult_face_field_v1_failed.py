"""Prepared, bounded adult-face relief on the actual continuous head.

This is an artist's provisional construction, not approved species dimensions.
All existing ocular-domain and oral-bag points remain fixed; the repaired lid
and Jaw deformation semantics are not replaced by a new spatial mask.
"""
import numpy as np


def smooth(a, b, value):
    t = np.clip((value-a)/(b-a), 0, 1)
    return t*t*(3-2*t)


def membership(count, faces, face_sets):
    result = np.zeros(count, dtype=np.uint64)
    for face, tag in zip(faces, face_sets):
        if not 0 <= int(tag) < 64:
            raise RuntimeError('Unexpected unaudited face set')
        result[np.asarray(face, int)] |= np.uint64(1) << np.uint64(tag)
    return lambda tag: (result & (np.uint64(1) << np.uint64(tag))) != 0


def propose(source, basis, faces, face_sets, edges):
    """Screened graph smoothing of broad form controls with exact boundaries.

    No topology, point ordering, optical shell, pivot, weight or action changes.
    Caller must transfer the same displacement to every existing shape and
    compare actual neutral/depth/Blink/Tongue views before any acceptance.
    """
    source = np.asarray(source, np.float64)
    basis = np.asarray(basis, np.float64)
    edges = np.asarray(edges, np.int32)
    member = membership(len(source), faces, face_sets)
    x, y, z = source.T
    absolute_x = np.abs(x)
    front = smooth(.070, .125, -y)
    envelope = front*smooth(.180, .205, z)*(1-smooth(.348, .368, z))
    gauss = lambda v, c, w: np.exp(-((v-c)/w)**2)
    target = np.zeros_like(source)

    # A broad arched supraorbital volume. No narrow ridge/tube is added and
    # actual eye-set vertices remain fixed rather than inheriting brow motion.
    t = np.clip((absolute_x-.011)/.056, 0, 1)
    arch = .331+.009*np.sin(np.pi*t)+.003*t
    span = smooth(.008, .023, absolute_x)*(1-smooth(.057, .080, absolute_x))
    brow = gauss(z, arch, .014)*span*front
    target[:, 1] -= .0038*brow
    target[:, 2] += .0009*brow*t

    # The adult zygomatic plane leads into a quieter infraorbital hollow.
    cheek = gauss(absolute_x, .059, .027)*gauss(z, .273, .029)*front
    hollow = gauss(absolute_x, .049, .026)*gauss(z, .244, .021)*front
    target[:, 1] -= .0024*cheek
    target[:, 1] += .0015*hollow
    target[:, 0] -= np.sign(x)*.0013*hollow

    # Raise the continuous nasal pad as a compact rounded animal landmark;
    # reduce the spread of the human alar base without deleting its nostrils.
    # This is a shape proposal, never a brown mask used to imply projection.
    nasal_front = smooth(.129, .152, -y)
    pad = np.exp(-(x/.023)**4-((z-.270)/.019)**4)*nasal_front
    alar = gauss(absolute_x, .022, .018)*gauss(z, .258, .017)*nasal_front
    target[:, 1] -= .0038*pad
    target[:, 0] -= np.sign(x)*.0018*alar
    target[:, 2] += .0008*gauss(absolute_x, .009, .011)*gauss(z, .277, .012)*pad
    target[:, 2] -= .0006*gauss(x, 0, .008)*gauss(z, .259, .010)*pad

    # Paired compact muzzle pads connect the nose to the unchanged lip rim.
    muzzle = gauss(absolute_x, .021, .018)*gauss(z, .245, .022)*front
    target[:, 1] -= .0015*muzzle
    target[:, 1] += .0006*gauss(x, 0, .007)*gauss(z, .247, .018)*front
    target *= envelope[:, None]

    # Closed ocular domains preserve the actual shell clearance throughout
    # existing Blink/Squint. Oral surfaces and their independent rims stay put.
    fixed = member(7) | member(9) | member(10) | (z <= .190) | (z >= .365) | (y >= -.065)
    target[fixed] = 0
    a, b = edges.T
    lengths = np.linalg.norm(basis[a]-basis[b], axis=1)
    if np.any(lengths < 1e-10):
        raise RuntimeError('Zero-length edge in adult face graph')
    conductance = 1/lengths
    degree = np.bincount(a, conductance, minlength=len(source))+np.bincount(b, conductance, minlength=len(source))
    unknown = ~fixed
    if np.any(degree[unknown] <= 0):
        raise RuntimeError('Disconnected free face vertex')
    strength = 2.0
    diagonal = (1+strength)*degree[unknown, None]
    rhs = degree[unknown, None]*target[unknown]

    def neighbors(values):
        return np.column_stack([
            np.bincount(a, conductance*values[b, k], minlength=len(source))+
            np.bincount(b, conductance*values[a, k], minlength=len(source))
            for k in range(3)])

    def multiply(values):
        whole = np.zeros_like(basis)
        whole[unknown] = values
        return diagonal*values-strength*neighbors(whole)[unknown]

    solution = np.zeros_like(rhs)
    residual = rhs.copy()
    preconditioned = residual/diagonal
    direction = preconditioned.copy()
    rz = float(np.sum(residual*preconditioned))
    initial = max(float(np.linalg.norm(rhs)), 1e-30)
    relative = float(np.linalg.norm(residual))/initial
    for iteration in range(1000):
        if relative < 1e-10:
            break
        product = multiply(direction)
        denominator = float(np.sum(direction*product))
        if denominator <= 0:
            raise RuntimeError('Adult face graph is not positive definite')
        alpha = rz/denominator
        solution += alpha*direction
        residual -= alpha*product
        relative = float(np.linalg.norm(residual))/initial
        next_preconditioned = residual/diagonal
        next_rz = float(np.sum(residual*next_preconditioned))
        direction = next_preconditioned+(next_rz/rz)*direction
        rz = next_rz
    if relative >= 1e-10:
        raise RuntimeError('Adult face field failed convergence')
    delta = np.zeros_like(basis)
    delta[unknown] = solution
    if np.linalg.norm(delta, axis=1).max() > .005:
        raise RuntimeError('Bounded face relief exceeds five millimetres')
    if np.any(delta[fixed]):
        raise RuntimeError('Fixed lid/oral/neck boundaries moved')
    gradient = np.linalg.norm(delta[a]-delta[b], axis=1)/lengths
    return delta, {
        'status': 'Numerical construction only; actual identity and expressions unreviewed',
        'method': 'Broad anatomical form controls with screened graph interpolation and exact semantic boundary constraints',
        'fixedVertices': int(fixed.sum()),
        'ocularAndOralMaximumDisplacementMeters': float(np.linalg.norm(delta[member(7)|member(9)|member(10)], axis=1).max()),
        'maximumDisplacementMeters': float(np.linalg.norm(delta, axis=1).max()),
        'edgeDisplacementGradientMaximum': float(gradient.max()),
        'edgeDisplacementGradientP99': float(np.quantile(gradient, .99)),
        'iterations': iteration+1,
        'relativeResidual': relative,
        'provisionalDimensions': True,
        'unchanged': ['topology', 'ocular shells', 'all bone bind transforms', 'repaired Jaw semantics', 'mouth opening', 'actual lid contact'],
        'pending': ['Neutral/profile/three-quarter adult likeness', 'Blink and Tongue actual mesh review', 'Nasal material and actual-geometry ocular atlas']}
