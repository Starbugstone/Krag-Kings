"""Fit short provisional crowns to the real exterior labial skin.

Roots remain in the saved lower gingiva; the visible crown is not lengthened
to compensate for fitting against the wrong (interior) oral rim.
"""
from pathlib import Path
import sys
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
HERE = Path(__file__).resolve().parent
for path in (HERE, HERE.parent/'ironjaw_wip', HERE.parent/'v9j_wip', HERE.parent/'v9l_wip'):
    sys.path.insert(0, str(path))
from profile_and_lip import membership, member, ordered_rim, smooth
from replacement_surface import coordinates
from dental_arch import components
from tusk_exterior_fit_v9lfa import axial_rings


def apply(head, face, oral):
    hp = coordinates(head.data, 'Basis').astype(float)
    fp = coordinates(face.data, 'Basis').astype(float)
    op = coordinates(oral.data, 'Basis').astype(float)
    masks = membership(head.data)
    lower = member(masks, 24) & member(masks, 7)
    edges = np.asarray([edge.vertices[:] for edge in head.data.edges], int)
    rim = hp[ordered_rim(edges, lower, hp)]
    tags = np.asarray([entry.value for entry in head.data.attributes['.sculpt_face_set'].data])
    exterior_faces = [list(polygon.vertices) for polygon, tag in zip(head.data.polygons, tags) if tag == 24]
    exterior = BVHTree.FromPolygons(hp.tolist(), exterior_faces, all_triangles=False)
    jaw = oral.vertex_groups['Jaw'].index
    gingiva = {i for polygon in oral.data.polygons
               if oral.data.materials[polygon.material_index].name == 'Krag_Gingiva' for i in polygon.vertices}
    gum_parts = [part for part in components(oral.data) if int(part[0]) in gingiva
                 and any(g.group == jaw and g.weight > .999 for g in oral.data.vertices[int(part[0])].groups)]
    if len(gum_parts) != 1 or (len(gum_parts[0])-2) % 24:
        raise RuntimeError('Expected one unchanged24-sided lower gingival arch')
    gum_curve = op[gum_parts[0][:-2]].reshape(-1, 24, 3).mean(1)
    face_jaw = face.vertex_groups['Jaw'].index
    parts = [part for part in components(face.data)
             if any(g.group == face_jaw and g.weight > .999 for g in face.data.vertices[int(part[0])].groups)]
    if len(parts) != 2 or any(len(part) != 408 for part in parts):
        raise RuntimeError('Expected two actual17-ring canine components')
    revised = fp.copy(); reports = []
    uv = face.data.uv_layers.active
    for part in parts:
        rings = axial_rings(face.data, part)
        old_root = fp[rings[0]].mean(0)
        root = gum_curve[np.argmin(np.linalg.norm(gum_curve-old_root, axis=1))].copy()
        x = float(root[0]); base_z = float(np.interp(x, rim[:, 0], rim[:, 2])-.001)
        hit, normal, polygon_index, ray_distance = exterior.ray_cast(Vector((x, -.4, base_z)), Vector((0, 1, 0)), .5)
        if hit is None or normal.y >= -.1:
            raise RuntimeError('No anterior exterior lower-lip surface at canine emergence')
        emergence = np.asarray(hit[:], float)
        emergence[1] -= .001
        tip = emergence+np.asarray((np.sign(x)*.0003, -.0005, .014))
        height = float(tip[2]-root[2])
        if not .025 < height < .070 or np.linalg.norm(emergence-root) > .060:
            raise RuntimeError('Saved gingiva cannot support this compact provisional crown')
        q_erupt = float(np.clip((emergence[2]-root[2])/height, .25, .85))
        angles = {}
        wanted = set(map(int, part))
        for polygon in face.data.polygons:
            if len(polygon.vertices) != 4:
                continue
            for loop in polygon.loop_indices:
                vertex = face.data.loops[loop].vertex_index
                if vertex in wanted:
                    angles.setdefault(vertex, []).append(float(uv.data[loop].uv.x) % 1.)
        for row, ids in enumerate(rings):
            q = row/16
            center = root.copy()
            center[:2] += (emergence[:2]-root[:2])*smooth(q/q_erupt)
            center[2] += height*q
            above = np.clip((q-q_erupt)/(1-q_erupt), 0, 1)
            center[:2] += (tip[:2]-emergence[:2])*above
            radius = (.68+.32*smooth(q/.18))*(1-.975*above)
            theta = np.asarray([2*np.pi*np.median(angles[int(i)]) for i in ids])
            revised[ids] = center+np.column_stack((.006*radius*np.cos(theta), .0042*radius*np.sin(theta), np.zeros(24)))
        reports.append({'side': 'L' if x > 0 else 'R', 'actualGingivalRoot': root.tolist(),
                        'actualExteriorSkinHit': list(hit), 'exteriorNormal': list(normal),
                        'emergenceCenter': emergence.tolist(), 'tip': tip.tolist(),
                        'visibleHeightProposalMeters': .014, 'baseWidthMeters': .012,
                        'rootToExteriorMeters': float(np.linalg.norm(emergence-root)),
                        'actualNeutralOpenContactPending': True})
    changed = np.concatenate(parts)
    untouched = np.ones(len(fp), bool); untouched[changed] = False
    for key in face.data.shape_keys.key_blocks:
        old = coordinates(face.data, key.name)
        new = old.copy(); new[changed] = revised[changed]
        key.data.foreach_set('co', new.astype(np.float32).ravel())
        if not np.array_equal(coordinates(face.data, key.name)[untouched], old[untouched]):
            raise RuntimeError('Canine fit changed other Face/ocular points')
    face.data.vertices.foreach_set('co', revised.astype(np.float32).ravel())
    face.data.update()
    return {'method': 'Actual exterior24 labial surface and unchanged lower gingiva; short broad provisional visible crowns',
            'sides': reports, 'ocularPointsExact': True, 'requiresActualClosedOpenReview': True}
