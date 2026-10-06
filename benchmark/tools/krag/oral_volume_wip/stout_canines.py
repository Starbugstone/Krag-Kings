"""Fit compact provisional crowns from the true lower gum to the oral rim."""
from pathlib import Path
import sys
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent/'ironjaw_wip'))
sys.path.insert(0, str(HERE.parent/'v9j_wip'))
sys.path.insert(0, str(HERE.parent/'v9l_wip'))
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
    edges = np.asarray([e.vertices[:] for e in head.data.edges], int)
    rim = hp[ordered_rim(edges, lower, hp)]
    if np.any(np.diff(rim[:, 0]) < -.0002):
        raise RuntimeError('Lower rim X folds; cannot fit a canine from its actual arch')
    jaw = oral.vertex_groups['Jaw'].index
    gingiva = {i for p in oral.data.polygons if oral.data.materials[p.material_index].name == 'Krag_Gingiva' for i in p.vertices}
    gum_parts = [part for part in components(oral.data) if int(part[0]) in gingiva
                 and any(g.group == jaw and g.weight > .999 for g in oral.data.vertices[int(part[0])].groups)]
    if len(gum_parts) != 1 or (len(gum_parts[0])-2) % 24:
        raise RuntimeError('Expected one authored24-sided lower gingival arch')
    gum_curve = op[gum_parts[0][:-2]].reshape(-1, 24, 3).mean(1)
    face_jaw = face.vertex_groups['Jaw'].index
    parts = [part for part in components(face.data)
             if any(g.group == face_jaw and g.weight > .999 for g in face.data.vertices[int(part[0])].groups)]
    if len(parts) != 2 or any(len(part) != 408 for part in parts):
        raise RuntimeError('Expected two actual17-ring crowns')
    revised = fp.copy(); reports = []
    for part in parts:
        rings = axial_rings(face.data, part)
        old_root = fp[rings[0]].mean(0)
        root = gum_curve[np.argmin(np.linalg.norm(gum_curve-old_root, axis=1))].copy()
        x = float(root[0])
        emergence = np.asarray((x, np.interp(x, rim[:, 0], rim[:, 1])-.003,
                                np.interp(x, rim[:, 0], rim[:, 2])))
        tip = emergence+np.asarray((np.sign(x)*.001, -.0005, .016))
        height = float(tip[2]-root[2])
        if not .025 < height < .070:
            raise RuntimeError('Gum-to-lip crown height is anatomically inconsistent: '+str(height))
        q_erupt = float(np.clip((emergence[2]-root[2])/height, .30, .85))
        for row, ids in enumerate(rings):
            q = row/16
            center = root.copy()
            center[:2] += (emergence[:2]-root[:2])*smooth(q/q_erupt)
            center[2] += height*q
            above = np.clip((q-q_erupt)/(1-q_erupt), 0, 1)
            center[:2] += (tip[:2]-emergence[:2])*above
            radius = (.68+.32*smooth(q/.18))*(1-.975*above)
            # Existing circumferential UVs identify actual vertex angles;
            # never assume BMesh's indices are an ordered perimeter.
            uv = face.data.uv_layers.active
            angles = {}
            wanted = set(map(int, ids))
            for polygon in face.data.polygons:
                if len(polygon.vertices) != 4:
                    continue
                for loop in polygon.loop_indices:
                    vertex = face.data.loops[loop].vertex_index
                    if vertex in wanted:
                        angles.setdefault(vertex, []).append(float(uv.data[loop].uv.x) % 1.)
            theta = np.asarray([2*np.pi*np.median(angles[int(i)]) for i in ids])
            revised[ids] = center+np.column_stack((.006*radius*np.cos(theta), .0042*radius*np.sin(theta), np.zeros(24)))
        reports.append({'side': 'L' if x > 0 else 'R', 'gingivalRoot': root.tolist(),
                        'trueLowerRimEmergence': emergence.tolist(), 'tip': tip.tolist(),
                        'heightMeters': height, 'exposedHeightProposalMeters': .016,
                        'emergenceWidthMeters': .012, 'sourceIndicesAndTopologyPreserved': True})
    changed = np.concatenate(parts)
    untouched = np.ones(len(fp), bool); untouched[changed] = False
    for key in face.data.shape_keys.key_blocks:
        old = coordinates(face.data, key.name)
        new = old.copy(); new[changed] = revised[changed]
        key.data.foreach_set('co', new.astype(np.float32).ravel())
        if not np.array_equal(coordinates(face.data, key.name)[untouched], old[untouched]):
            raise RuntimeError('Canine reconstruction moved ocular coordinates')
    face.data.vertices.foreach_set('co', revised.astype(np.float32).ravel())
    face.data.update()
    return {'method': 'Actual lower gingiva and true oral rim; compact crown with no exterior skin-ray hook',
            'sides': reports, 'neutralOpenLipContactPending': True}
