"""Root-fixed rigid crown fit: preserve size instead of stretching hooks."""
from pathlib import Path
import sys, math
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent/'v9l_wip'))
from tusk_exterior_fit_v9lfa import axial_rings
sys.path.insert(0, str(HERE.parent/'v9j_wip'))
from dental_arch import components


def apply(head, face):
    def read(key):
        values = np.empty(len(key.data)*3, np.float32)
        key.data.foreach_get('co', values)
        return values.reshape(-1, 3).astype(float)
    if not np.allclose(np.asarray(face.matrix_world), np.eye(4), atol=1e-7):
        raise RuntimeError('Rigid crown fitter expects established world-space Face data')
    hp = read(head.data.shape_keys.key_blocks['Basis'])
    hm = np.asarray(head.matrix_world, float)
    hp = hp@hm[:3, :3].T+hm[:3, 3]
    tree = BVHTree.FromPolygons(hp, [p.vertices[:] for p in head.data.polygons])
    keys = face.data.shape_keys.key_blocks
    basis = read(keys['Basis'])
    group = face.vertex_groups['Jaw'].index
    jaw_ids = {v.index for v in face.data.vertices if any(g.group == group and g.weight > .999 for g in v.groups)}
    parts = [part for part in components(face.data) if int(part[0]) in jaw_ids]
    if len(parts) != 2 or any(len(part) != 408 for part in parts):
        raise RuntimeError('Expected actual two17x24 natural crowns')
    revised = basis.copy()
    report = []
    for part in parts:
        rings = axial_rings(face.data, part)
        centers = basis[rings].mean(1)
        root = centers[0]
        side = 1 if root[0] > 0 else -1
        proposals = []
        baseline_clearance = None
        for pitch in range(0, 56, 5):
            for outward in range(0, 21, 5):
                rotation = np.asarray(Matrix.Rotation(math.radians(side*outward), 3, 'Y') @
                                      Matrix.Rotation(math.radians(pitch), 3, 'X'), float)
                candidate = (basis[part]-root)@rotation.T+root
                lookup = {int(i): candidate[j] for j, i in enumerate(part)}
                rows = np.asarray([[lookup[int(i)] for i in row] for row in rings])
                new_centers = rows.mean(1)
                clear = []
                for point in new_centers:
                    hit = tree.ray_cast(Vector((point[0], -2, point[2])), Vector((0, 1, 0)), 4)[0]
                    clear.append(float(hit.y-point[1]) if hit is not None else 1.)
                exposed = 0
                for value in reversed(clear):
                    if value < .0005:
                        break
                    exposed += 1
                surface_clear = []
                for point in rows[-2:].reshape(-1, 3):
                    hit = tree.ray_cast(Vector((point[0], -2, point[2])), Vector((0, 1, 0)), 4)[0]
                    surface_clear.append(float(hit.y-point[1]) if hit is not None else 1.)
                if pitch == 0 and outward == 0:
                    baseline_clearance = {'visibleTerminalRings': exposed,
                                          'terminalSurfaceClearanceMeters': min(surface_clear),
                                          'centerlineForwardSkinClearanceMeters': clear}
                if exposed >= 4 and min(surface_clear) >= .0003:
                    proposals.append((pitch+outward*.6, pitch, outward, candidate, clear, exposed, min(surface_clear)))
        if not proposals:
            raise RuntimeError('No root-fixed natural tusk fit within55deg pitch/20deg outward bounds')
        _, pitch, outward, candidate, clearance, exposed, surface_minimum = min(proposals, key=lambda p: p[0])
        revised[part] = candidate
        original_distances = np.linalg.norm(basis[part]-root, axis=1)
        new_distances = np.linalg.norm(candidate-root, axis=1)
        rigid_error = float(abs(original_distances-new_distances).max())
        if rigid_error > 1e-7:
            raise RuntimeError('Crown fitting changed tooth size')
        report.append({'side': 'L' if side > 0 else 'R', 'fixedGingivalRoot': root.tolist(),
                       'actualBaselineOcclusion': baseline_clearance,
                       'pitchDegrees': pitch, 'outwardDegrees': outward,
                       'maximumRadialSizeErrorMeters': rigid_error,
                       'visibleTerminalRings': exposed, 'terminalSurfaceClearanceMeters': surface_minimum,
                       'centerlineForwardSkinClearanceMeters': clearance})
    untouched = np.ones(len(basis), bool)
    untouched[list(jaw_ids)] = False
    discarded_morph = 0.
    for key in keys:
        old = read(key)
        updated = old.copy()
        discarded_morph = max(discarded_morph, float(np.linalg.norm(old[~untouched]-basis[~untouched], axis=1).max()))
        updated[~untouched] = revised[~untouched]
        key.data.foreach_set('co', updated.astype(np.float32).ravel())
        if not np.array_equal(read(key)[untouched].astype(np.float32), old[untouched].astype(np.float32)):
            raise RuntimeError('Natural crown fit changed ocular geometry')
    face.data.vertices.foreach_set('co', revised.astype(np.float32).ravel())
    face.data.update()
    return {'method': 'Rigid orientation about preserved actual gingival roots; fixed size/shape, no surface-following stretch',
            'sides': report, 'maximumRemovedSoftTuskMorphMeters': discarded_morph,
            'ocularShapeCoordinatesExact': True, 'actualNeutralOpenContactReviewRequired': True}
