"""Exact corner provenance for triangulation, including authored split normals.

The map is external validation evidence, not an extra runtime mesh attribute.
Every new triangle must belong to one original polygon and preserve its oriented
boundary; internal diagonals cancel. Coincident vertices on different faces do
not make their shading corners interchangeable.
"""
import numpy as np


def decode_polygons(raw):
    raw = np.asarray(raw, dtype=np.int64)
    ends = np.flatnonzero(raw < 0)
    if not len(ends) or ends[-1] != len(raw) - 1:
        raise ValueError('Invalid polygon termination')
    sizes = np.diff(np.r_[-1, ends])
    if np.any(sizes < 3):
        raise ValueError('Expected polygon surfaces, not loose edges')
    return np.where(raw < 0, -raw - 1, raw), sizes


def _oriented_boundary(edges):
    # Corner IDs are globally unique and triangles are checked against their
    # source face first, so the undirected pair alone is an unambiguous key.
    pairs = np.sort(edges, axis=1)
    signs = np.where(edges[:, 0] < edges[:, 1], 1, -1)
    if np.any(edges[:, 0] == edges[:, 1]):
        raise ValueError('Triangle repeats the same original corner')
    keys, inverse = np.unique(pairs, axis=0, return_inverse=True)
    counts = np.bincount(inverse, weights=signs).astype(np.int64)
    keep = counts != 0
    return keys[keep], counts[keep]


def validate(source_raw, target_raw, target_to_source, source_uv=None,
             target_uv=None, source_material=None, target_material=None):
    source, sizes = decode_polygons(source_raw)
    target, target_sizes = decode_polygons(target_raw)
    mapping = np.asarray(target_to_source, dtype=np.int64)
    if not np.all(target_sizes == 3):
        raise ValueError('Target contains nontriangular polygons')
    if mapping.shape != target.shape or np.any(mapping < 0) or np.any(mapping >= len(source)):
        raise ValueError('Corner provenance index/count mismatch')
    if not np.array_equal(source[mapping], target):
        raise ValueError('Corner provenance changes vertex identity')
    source_face = np.repeat(np.arange(len(sizes)), sizes)
    triangle_faces = source_face[mapping].reshape((-1, 3))
    if not np.all(triangle_faces == triangle_faces[:, :1]):
        raise ValueError('Triangle combines corners from different source polygons')
    if not np.array_equal(np.bincount(triangle_faces[:, 0], minlength=len(sizes)), sizes - 2):
        raise ValueError('Per-polygon triangle count changed')
    if not np.array_equal(np.unique(mapping), np.arange(len(source))):
        raise ValueError('An authored source corner disappeared')
    tri = mapping.reshape((-1, 3))
    edges = np.stack((tri, np.roll(tri, -1, axis=1)), axis=2).reshape((-1, 2))
    actual_edges, actual_counts = _oriented_boundary(edges)
    following = np.arange(len(source)) + 1
    ends = np.cumsum(sizes) - 1
    following[ends] = np.r_[0, ends[:-1] + 1]
    expected_edges, expected_counts = _oriented_boundary(np.column_stack((np.arange(len(source)), following)))
    if not np.array_equal(actual_edges, expected_edges) or not np.array_equal(actual_counts, expected_counts):
        raise ValueError('Triangulation changed oriented polygon boundaries or winding')
    if source_uv is not None:
        if target_uv is None or not np.array_equal(np.asarray(source_uv)[mapping], target_uv):
            raise ValueError('Original per-corner UV payload changed')
    if source_material is not None:
        if target_material is None or not np.array_equal(np.asarray(source_material)[mapping], target_material):
            raise ValueError('Original per-corner material assignment changed')
    return {'sourcePolygons':len(sizes), 'sourceCorners':len(source),
            'triangles':len(target_sizes), 'targetCorners':len(target),
            'sameSourcePolygon':True, 'orientedBoundaryUnchanged':True,
            'allSourceCornersRetained':True, 'vertexIdentityUnchanged':True}


def load_and_validate(path, source_raw, target_raw, **kwargs):
    with np.load(path, allow_pickle=False) as arrays:
        if not np.array_equal(arrays['sourcePolygonVertexIndex'], source_raw):
            raise ValueError('Raw source FBX loop order differs from recorded Blender assembly')
        if not np.array_equal(arrays['targetPolygonVertexIndex'], target_raw):
            raise ValueError('Raw target FBX loop order differs from recorded Blender assembly')
        mapping = arrays['targetToSourceCorner'].copy()
    result = validate(source_raw, target_raw, mapping, **kwargs)
    return mapping, result
