"""Remove the saved lower-rim square-root endpoint singularity locally."""
from pathlib import Path
import sys
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent/'ironjaw_wip'))
from anatomical_exclusion import _distance


def refine(mesh, obj, points):
    tags = np.asarray([v.value for v in mesh.attributes['.sculpt_face_set'].data], int)
    membership = np.zeros(len(points), np.uint64)
    for polygon, tag in zip(mesh.polygons, tags):
        membership[list(polygon.vertices)] |= np.uint64(1) << np.uint64(tag)
    member = lambda tag: (membership & (np.uint64(1) << np.uint64(tag))) != 0
    corner = member(7) & member(24) & member(33)
    if corner.sum() != 2:
        raise RuntimeError('Expected actual two oral commissures')
    edges = np.asarray([e.vertices[:] for e in mesh.edges], int)
    distance = _distance(points, edges, corner, np.ones(len(points), bool))
    t = np.clip(distance/.014, 0, 1)
    taper = t*t*(3-2*t)
    head, jaw, neck = [obj.vertex_groups[n] for n in ('Head', 'Jaw', 'Neck')]
    values = np.zeros((len(points), 3))
    groups = {head.index: 0, jaw.index: 1, neck.index: 2}
    for vertex in mesh.vertices:
        for item in vertex.groups:
            if item.group not in groups:
                raise RuntimeError('Unexpected Head skin influence')
            values[vertex.index, groups[item.group]] = item.weight
    revised = values.copy()
    revised[:, 1] *= taper
    revised[:, 0] += values[:, 1]-revised[:, 1]
    if np.max(abs(revised.sum(1)-values.sum(1))) > 1e-7:
        raise RuntimeError('Commissure refinement changed weight normalization')
    if np.any(revised[member(33)|member(11), 1] > 1e-8):
        raise RuntimeError('Mandible pulls fixed upper lip or nose')
    for i in np.flatnonzero(abs(revised[:, 1]-values[:, 1]) > 1e-9):
        jaw.add([int(i)], float(revised[i, 1]), 'REPLACE')
        head.add([int(i)], float(revised[i, 0]), 'REPLACE')
    length = np.linalg.norm(points[edges[:, 1]]-points[edges[:, 0]], axis=1)
    region = (distance[edges].max(1) < .016) & (length > 1e-8)
    before = abs(values[edges[:, 1], 1]-values[edges[:, 0], 1])/np.maximum(length, 1e-8)
    after = abs(revised[edges[:, 1], 1]-revised[edges[:, 0], 1])/np.maximum(length, 1e-8)
    return {'method': 'Smooth finite-slope factor on the old square-root rim support within14mm of each real commissure',
            'affectedVertices': int(np.count_nonzero(abs(revised[:, 1]-values[:, 1]) > 1e-9)),
            'worldGeodesicSupportMeters': .014, 'beforeMaximumLocalJawGradientPerMeter': float(before[region].max()),
            'afterMaximumLocalJawGradientPerMeter': float(after[region].max()),
            'centralFullMandibularSupportAndRangePreserved': True,
            'actualPoseAcceptance': False}
