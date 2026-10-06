"""Small source-recipe overlap audit after actual v9h oral review failure.

This uses original control-cage topology and exact authored formulas. It is
not a posed Blender intersection test or a claim that a repair exists.
"""
from pathlib import Path
import ast, sys, json, hashlib
import numpy as np

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / 'benchmark/tools/krag'
sys.path.insert(0, str(BASE / 'v9h_wip'))
import profile_fit

tree = ast.parse((BASE / 'krag_head_v9.py').read_text())
fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'fit')
namespace = {'np': np}
exec(compile(ast.Module(body=[fn], type_ignores=[]), 'frozen-v9h-base-fit', 'exec'), namespace)
def fit(raw):
    return profile_fit.refine(raw, namespace['fit'](raw))

geometry = ROOT / 'benchmark/art/krag/anatomy-study/GEO-head_animation_realistic.npz'
attributes = ROOT / 'benchmark/art/nib/v5-study/head-topology-attributes.json'
data = np.load(geometry, allow_pickle=True)
raw, faces = data['vertices'], data['polygons']
info = json.loads(attributes.read_text())
sets = np.asarray(next(a['values'] for a in info['attributes'] if a['name'] == '.sculpt_face_set'))
assert len(sets) == len(faces)
tags = np.zeros(len(raw), dtype=np.uint64)
for face, tag in zip(faces, sets):
    tags[np.asarray(face, dtype=int)] |= np.uint64(1) << np.uint64(tag)
member = lambda tag: (tags & (np.uint64(1) << np.uint64(tag))) != 0
corners = member(7) & member(24) & member(33)

lining_center = fit([(0, -.028, .230)])[0]
lining_radii = np.asarray((.105, .114, .084))
fitted = fit(raw)
oral_triangles = []
for face, tag in zip(faces, sets):
    if tag != 7:
        continue
    for j in range(1, len(face) - 1):
        oral_triangles.append(fitted[[face[0], face[j], face[j + 1]]])
oral_triangles = np.asarray(oral_triangles)
def oral_ray_hits(point):
    # Orthographic source-space +Y ray at a tooth's X/Z: a local diagnostic,
    # not a claim about the actual posed camera or subdivided surface.
    a, b, c = (oral_triangles[:, i, [0, 2]] for i in range(3))
    v0, v1, q = b - a, c - a, point[[0, 2]] - a
    determinant = v0[:, 0] * v1[:, 1] - v0[:, 1] * v1[:, 0]
    valid = abs(determinant) > 1e-14
    u = np.zeros(len(a)); v = np.zeros(len(a))
    u[valid] = (q[valid, 0] * v1[valid, 1] - q[valid, 1] * v1[valid, 0]) / determinant[valid]
    v[valid] = (v0[valid, 0] * q[valid, 1] - v0[valid, 1] * q[valid, 0]) / determinant[valid]
    valid &= (u >= 0) & (v >= 0) & (u + v <= 1)
    y = oral_triangles[:, 0, 1] + u * (oral_triangles[:, 1, 1] - oral_triangles[:, 0, 1]) + v * (oral_triangles[:, 2, 1] - oral_triangles[:, 0, 1])
    return sorted(y[valid].tolist())
teeth = []
for upper in [True, False]:
    z = .241 if upper else .217
    for i in range(8):
        x = (i - 3.5) * .0088
        center = fit([(x, -.109 + .013 * (abs(x) / .035) ** 2, z)])[0]
        center[2] += -.010 if upper else .009
        # Exact authored tooth box front-face center before shared H/scale.
        front = center + np.asarray((0, -.010, 0))
        q = (front - lining_center) / lining_radii
        yz_radius_squared = 1 - q[0] ** 2 - q[2] ** 2
        shell_front_y = (lining_center[1] - lining_radii[1] * np.sqrt(yz_radius_squared)
                         if yz_radius_squared >= 0 else None)
        teeth.append({'upper': upper, 'index': i, 'centerBeforeSharedHeadTransform': center.tolist(),
                      'frontFaceCenterInsideExtraEllipsoid': bool(np.dot(q, q) < 1),
                      'extraShellInFrontOfToothCenterMeters': None if shell_front_y is None else float(front[1] - shell_front_y),
                      'sourceOralBagYIntersectionsAtToothCenterXZ': oral_ray_hits(front),
                      'toothFrontY': float(front[1])})

actual_corners = raw[corners]
landmark_errors = []
for sign in [-1, 1]:
    actual = actual_corners[np.argmin(abs(actual_corners[:, 0] - sign * .0243))]
    authored = np.asarray((sign * .043, -.112, .234))
    landmark_errors.append({'side': sign, 'actualCornerSource': actual.tolist(),
                            'authoredControlSource': authored.tolist(),
                            'sourceDistanceMeters': float(np.linalg.norm(actual - authored)),
                            'fittedDistanceBeforeHeadTransformMeters': float(np.linalg.norm(fit([actual])[0] - fit([authored])[0]))})

report = {'status': 'Source-formula diagnostics only; actual saved posed occlusion still requires inspection',
          'observedFailure': 'v9h OpenMouth frame146: rectangular aperture and mostly hidden dental/gum anatomy',
          'sourceRecipe': 'benchmark/art/krag/v9h-prepared-recipe.json',
          'sourceGeometrySha256': hashlib.sha256(geometry.read_bytes()).hexdigest(),
          'mouthCorners': landmark_errors,
          'extraOpaqueLining': {'centerBeforeSharedHeadTransform': lining_center.tolist(),
                               'radiiBeforeSharedHeadTransform': lining_radii.tolist(),
                               'teeth': teeth},
          'nextBoundedCorrection': ['Inspect actual posed oral-bag envelope against dental/gum surfaces; the extra ellipsoid does not cover neutral tooth front centers in this formula check',
                                    'Fit controls and dental/gum layout to true oral rims instead of obsolete mouth-corner coordinates',
                                    'Inspect actual neutral/open views and commissure deformation before accepting any change']}
out = ROOT / 'benchmark/art/krag/anatomy-study/mouth-construction-audit-v9h.json'
out.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8', newline='\n')
print(json.dumps({'corners': landmark_errors, 'toothFrontsInsideExtraEllipsoid': sum(t['frontFaceCenterInsideExtraEllipsoid'] for t in teeth),
                  'maximumShellFrontOcclusionMeters': max(t['extraShellInFrontOfToothCenterMeters'] for t in teeth if t['extraShellInFrontOfToothCenterMeters'] is not None)}, indent=2))
