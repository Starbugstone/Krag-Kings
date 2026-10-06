"""Prepared matching restorative torso/upper arm, without Natural-body edits.

The licensed left-forearm face set is carried through the same subdivision.
The actual dense face/point correspondence is asserted before it removes faces.
Restorative cuff fit and posed coverage remain separate actual-view gates.
"""
import json
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from surface_subset import subset


def derive(rig, root, collection, attach_drivers):
    body = bpy.data.objects['Continuous Nib anatomy organic']
    fuzz = bpy.data.objects['Fine skin fuzz organic']
    cage = bpy.data.objects['EDITABLE Nib semantic shoulder domain cage v2']
    library = root/'benchmark/art/krag/anatomy-study/GEO-body_male_realistic.npz'
    source = np.load(library, allow_pickle=True)
    # The companion audit pins the exact local reference NPZ before semantics.
    import hashlib
    semantics = json.loads((root/'benchmark/art/nib/motion-study/body-reference-face-sets.json').read_text())
    if hashlib.sha256(library.read_bytes()).hexdigest() != semantics['referenceCacheSha256']:
        raise RuntimeError('Original topology cache no longer matches semantic audit')
    # Names are asserted at execution, never inferred from another mesh.
    reference_points = np.asarray(source['vertices'], float)
    reference_faces = source['polygons']
    source_sets = np.asarray(semantics['faceSetIds'], np.int32)
    from anatomical_body_fit import crop
    used, faces = crop(reference_points, reference_faces)
    actual_ref = np.asarray([v.vector[:] for v in cage.data.attributes['Nib_BodyReferencePosition'].data], np.float32)
    if not np.array_equal(actual_ref, reference_points[used].astype(np.float32)):
        raise RuntimeError('Control cage source point correspondence differs')
    if [list(p.vertices) for p in cage.data.polygons] != faces:
        raise RuntimeError('Control cage source face correspondence differs')
    lookup = {tuple(f): i for i, f in enumerate(reference_faces)}
    ids = np.asarray([lookup[tuple(int(used[i]) for i in f)] for f in faces], np.int32)
    face_sets = source_sets[ids]
    selected = [f for f, region in zip(faces, face_sets) if region == 12]
    if not selected or min(actual_ref[i, 0] for f in selected for i in f) <= 0:
        raise RuntimeError('Audited left-forearm set does not have left-side membership')
    temp = cage.copy()
    temp.data = cage.data.copy()
    temp.name = 'TEMP exact restorative semantic subdivision'
    bpy.context.scene.collection.objects.link(temp)
    temp.hide_set(False)
    attr = temp.data.attributes.new('Nib_RestorativeRegion', 'INT', 'FACE')
    attr.data.foreach_set('value', face_sets)
    bpy.ops.object.select_all(action='DESELECT')
    temp.select_set(True)
    bpy.context.view_layer.objects.active = temp
    mod = temp.modifiers.new('Matching subdivision only', 'SUBSURF')
    mod.levels = 2
    mod.render_levels = 2
    bpy.ops.object.modifier_apply(modifier=mod.name)
    dense_faces = [tuple(p.vertices) for p in temp.data.polygons]
    if dense_faces != [tuple(p.vertices) for p in body.data.polygons]:
        raise RuntimeError('Dense semantic faces no longer match actual Body')
    dense = np.asarray([v.co[:] for v in temp.data.vertices], np.float32)
    original = np.asarray([v.co[:] for v in body.data.shape_keys.key_blocks['Basis'].data], np.float32)
    if not np.array_equal(dense, original):
        raise RuntimeError('Dense semantic points no longer match actual Body')
    regions = np.asarray([v.value for v in temp.data.attributes['Nib_RestorativeRegion'].data], np.int32)
    if set(regions) != set(face_sets):
        raise RuntimeError('Subdivision did not preserve categorical face regions')
    keep = regions != 12
    new_body, body_report = subset(body, keep, 'Continuous Nib anatomy grip coherent', collection)
    new_body['variant'] = 'grip'
    new_body['bone'] = 'BodyAnatomy'
    new_body['restorative_partition'] = 'Exact original left-forearm face set 12 omitted; no retained anatomy overlap'
    # Determine the new cut loop from original face edge incidence. Existing
    # neck, waist and opposite wrist boundaries are not mistaken for this seam.
    edge_sides = {}
    for p, retained in zip(body.data.polygons, keep):
        f = list(p.vertices)
        for a, b in zip(f, f[1:]+f[:1]):
            edge_sides.setdefault(tuple(sorted((a, b))), set()).add(bool(retained))
    seam_edges = [edge for edge, sides in edge_sides.items() if len(sides) == 2]
    seam_ids = sorted({v for edge in seam_edges for v in edge})
    counts = {v: sum(v in edge for edge in seam_edges) for v in seam_ids}
    if not seam_edges or any(n != 2 for n in counts.values()):
        raise RuntimeError('Replacement forearm boundary is not a closed degree-two loop')
    seam = original[seam_ids]
    if seam[:, 0].min() < .12 or seam[:, 2].min() < .72 or seam[:, 2].max() > .81:
        raise RuntimeError('New cut is outside actual elbow/cuff region')
    body_report['newCutOriginalVertexIds'] = seam_ids
    body_report['newCutBoundsMeters'] = [seam.min(0).tolist(), seam.max(0).tolist()]
    body_report['leftForearmRegionRemoved'] = 12
    # Fine fuzz is authored as disconnected six-point tapered fibers. Find its
    # actual root support on the unchanged dense Body before subsetting strands.
    if not np.array_equal(np.asarray(fuzz.matrix_world), np.asarray(body.matrix_world)):
        raise RuntimeError('Body/fuzz local coordinate systems differ')
    p = np.asarray([v.co[:] for v in fuzz.data.shape_keys.key_blocks['Basis'].data], np.float32)
    if len(p) % 6:
        raise RuntimeError('Unexpected fine-fuzz component layout')
    if any(len({v//6 for v in face.vertices}) != 1 for face in fuzz.data.polygons):
        raise RuntimeError('Fine-fuzz faces connect separate strand components')
    body_tree = BVHTree.FromPolygons([Vector(v) for v in original], dense_faces)
    root_regions = []
    distances = []
    for start in range(0, len(p), 6):
        point = Vector(p[start:start+3].mean(0))
        hit, normal, index, distance = body_tree.find_nearest(point)
        if index is None or distance > .0002:
            raise RuntimeError('Fine-fuzz root lost actual Body correspondence')
        root_regions.append(int(regions[index]))
        distances.append(float(distance))
    fuzz_keep = [root_regions[face.vertices[0]//6] != 12 for face in fuzz.data.polygons]
    new_fuzz, fuzz_report = subset(fuzz, fuzz_keep, 'Fine skin fuzz grip coherent', collection)
    new_fuzz['variant'] = 'grip'
    new_fuzz['fur_strands'] = sum(v != 12 for v in root_regions)
    fuzz_report['rootBodyDistanceMaxMeters'] = max(distances)
    fuzz_report['removedStrands'] = sum(v == 12 for v in root_regions)
    fuzz_report['keptStrands'] = sum(v != 12 for v in root_regions)
    deformation = json.loads(bpy.context.scene['deformation_contract'])
    for obj in [new_body, new_fuzz]:
        attach_drivers(obj, rig, deformation)
        obj.hide_render = True
        obj.hide_set(True)
    data = temp.data
    bpy.data.objects.remove(temp, do_unlink=True)
    if data.users == 0:
        bpy.data.meshes.remove(data)
    return [new_body, new_fuzz], {'body': body_report, 'fineFuzz': fuzz_report,
                                 'actualCuffAndPoseReviewRequired': True}
