"""Fit provisional oral volume to the existing broad exterior envelope.

The closed bite height and jaw angle are retained. A wider anterior lower
arch carries its short canines, and a rounded paired-lip residual makes room
for that arch during opening instead of lengthening exposed tusks.
"""
from pathlib import Path
import sys
import numpy as np
import bpy
from mathutils import Matrix
HERE = Path(__file__).resolve().parent
for path in (HERE, HERE.parent/'ironjaw_wip', HERE.parent/'v9j_wip'):
    sys.path.insert(0, str(path))
from replacement_surface import coordinates
from profile_and_lip import membership, member, ordered_rim, distances, smooth
from exterior_canines_v9t import apply as refit_canines
from paired_lip_curve import lower_arc


def lateral_arch(points):
    p = np.asarray(points, float)
    q = p.copy()
    q[:,0] *= 1+.34*np.exp(-(abs(p[:,0])/.066)**4)
    return q


def fit_volume(head, face, oral):
    op = coordinates(oral.data, 'Basis').astype(float)
    jaw_id = oral.vertex_groups['Jaw'].index
    jaw = np.asarray([any(g.group == jaw_id and g.weight > .999 for g in v.groups) for v in oral.data.vertices])
    tongue_materials = {i for i,m in enumerate(oral.data.materials) if m.name.startswith('Krag_OralTongue')}
    tongue = np.zeros(len(op), bool)
    for polygon in oral.data.polygons:
        if polygon.material_index in tongue_materials:
            tongue[list(polygon.vertices)] = True
    if jaw.sum() < 1000 or tongue.sum() < 1000 or np.any(jaw & tongue):
        raise RuntimeError('Expected separate rigid lower arch and articulated tongue domains')
    revised = op.copy(); revised[jaw] = lateral_arch(op[jaw])
    # Preserve the seated posterior tongue, widening and bringing the oral
    # floor forward beneath the incisors. The closed bite height stays intact.
    tp = op[tongue]; t = (tp[:,1].max()-tp[:,1])/max(np.ptp(tp[:,1]), 1e-10)
    forward = smooth((t-.2)/.65)
    revised[tongue,0] *= 1+.20*forward
    revised[tongue,1] -= .010*forward
    revised[tongue,2] += .003*forward
    delta = revised-op
    for key in oral.data.shape_keys.key_blocks:
        values = coordinates(oral.data, key.name).astype(float)+delta
        key.data.foreach_set('co', values.astype(np.float32).ravel())
    oral.data.vertices.foreach_set('co', revised.astype(np.float32).ravel()); oral.data.update()
    # Move the existing root neighborhood with the same arch map before
    # refitting the unchanged short crown profile to its actual new gingiva.
    fp = coordinates(face.data, 'Basis').astype(float)
    face_jaw = face.vertex_groups['Jaw'].index
    crowns = np.asarray([any(g.group == face_jaw and g.weight > .999 for g in v.groups) for v in face.data.vertices])
    if crowns.sum() != 816:
        raise RuntimeError('Expected two preserved17x24 crowns')
    crown_delta = lateral_arch(fp[crowns])-fp[crowns]
    for key in face.data.shape_keys.key_blocks:
        values = coordinates(face.data, key.name).astype(float)
        values[crowns] += crown_delta
        key.data.foreach_set('co', values.astype(np.float32).ravel())
    face.data.vertices.foreach_set('co', coordinates(face.data, 'Basis').ravel()); face.data.update()
    report = refit_canines(head, face, oral)
    if not np.array_equal(revised[jaw,2], op[jaw,2]):
        raise RuntimeError('Anterior arch fit changed the closed bite height')
    return dict(method='Monotone anterior lower-arch expansion with unchanged bite height; supported anterior tongue-floor fit',
                lowerArchVertices=int(jaw.sum()), tongueVertices=int(tongue.sum()),
                maximumOralPointChangeMeters=float(np.linalg.norm(delta, axis=1).max()),
                lowerArchHeightExact=True, upperDentalArchExact=True,
                tongueAnteriorShiftMeters=.010, tongueAnteriorRiseMeters=.003,
                canines=report, closedAndOpenContactStillRequireActualReview=True)


def lip_residual(head, rig, ocular_held):
    rig.animation_data.action = bpy.data.actions['FacePerformance']
    bpy.context.scene.frame_set(146); bpy.context.view_layer.update()
    jaw_pose = rig.pose.bones['Jaw'].matrix_basis.copy()
    keys = head.data.shape_keys
    amount = float(keys.key_blocks['JawOpen'].value)
    if not .90 < amount < 1.01:
        raise RuntimeError('Expected unchanged full-range JawOpen activation')
    rig.animation_data.action = None
    for bone in rig.pose.bones:
        bone.matrix_basis = Matrix.Identity(4)
    rig.pose.bones['Jaw'].matrix_basis = jaw_pose
    driver_states = [(d, d.mute) for d in keys.animation_data.drivers]
    for driver, _ in driver_states:
        driver.mute = True
    for key in keys.key_blocks:
        key.value = 0
    keys.key_blocks['JawOpen'].value = amount
    bpy.context.view_layer.update()
    points = coordinates(head.data, 'Basis').astype(float)
    old_delta = coordinates(head.data, 'JawOpen').astype(float)-points
    masks = membership(head.data)
    upper = member(masks,33) & member(masks,7)
    lower = member(masks,24) & member(masks,7)
    edges = np.asarray([e.vertices[:] for e in head.data.edges], int)
    lower_order = ordered_rim(edges, lower, points)
    upper_order = ordered_rim(edges, upper, points)
    corners = upper & lower
    if corners.sum() != 2:
        raise RuntimeError('Actual upper/lower oral rims must meet in two commissures')
    group_names = [g.name for g in head.vertex_groups]
    skin = np.asarray([np.asarray(rig.pose.bones[n].matrix @ rig.data.bones[n].matrix_local.inverted(), float) for n in group_names])
    weights = np.zeros((len(points),len(group_names)))
    for vertex in head.data.vertices:
        for group in vertex.groups:
            weights[vertex.index, group.group] = group.weight
    matrices = np.einsum('ij,jkl->ikl', weights, skin)
    rotations, translations = matrices[:,:3,:3], matrices[:,:3,3]
    posed = np.einsum('ijk,ik->ij', rotations, points+old_delta*amount)+translations
    target = posed.copy()
    half_width = max(abs(points[lower_order,0]))
    # Real commissures participate in full opening; the central upper lip and
    # nasal anatomy remain still. Six millimetres is a bounded acting proposal.
    target[upper_order,2] -= .006*smooth((abs(points[upper_order,0])/half_width-.60)/.40)
    center = lower_order[np.argmin(abs(points[lower_order,0]))]
    bottom = posed[center].copy()
    curve_reports = []
    for sign in (-1,1):
        side = lower_order[points[lower_order,0]*sign >= -1e-5]
        corner = lower_order[0 if sign < 0 else -1]
        width = abs(points[corner,0])
        u = np.clip(abs(points[side,0])/width, 0, 1)
        # A broad rounded lower arc replaces the diagonal wedge. Endpoint
        # positions are shared with the actual upper rim, never disconnected.
        values, curve_report = lower_arc(u, bottom[2], target[corner,2], u, posed[side,2])
        target[side,2] = values
        curve_reports.append(dict(side=sign, **curve_report))
    seed = upper | lower
    distance = distances(points, edges, seed)
    fixed = (distance >= .040) | ocular_held | member(masks,11) | seed
    delta = np.zeros_like(points); delta[seed] = target[seed]-posed[seed]
    a,b = edges.T
    weight = 1/np.maximum(np.linalg.norm(points[a]-points[b],axis=1),.00005)
    diagonal = np.bincount(a,weight,len(points))+np.bincount(b,weight,len(points))
    unknown = np.flatnonzero(~fixed)
    converged = False
    for iteration in range(2200):
        neighbor = np.zeros_like(delta)
        for axis in range(3):
            neighbor[:,axis] = np.bincount(a,weight*delta[b,axis],len(points)) + np.bincount(b,weight*delta[a,axis],len(points))
        proposed = neighbor[unknown]/diagonal[unknown,None]
        error = float(abs(proposed-delta[unknown]).max())
        delta[unknown] += .85*(proposed-delta[unknown])
        if error < .0000003:
            converged = True; break
    if not converged:
        raise RuntimeError('Bounded paired-lip tissue interpolation did not converge')
    source_delta = np.linalg.solve(rotations,delta[:,:,None])[:,:,0]/amount
    maximum = float(np.linalg.norm(source_delta,axis=1).max())
    if maximum > .025:
        raise RuntimeError('Paired-lip residual exceeds25mm: '+str(maximum))
    revised = points+old_delta+source_delta
    keys.key_blocks['JawOpen'].data.foreach_set('co',revised.astype(np.float32).ravel())
    head.data.update(); bpy.context.view_layer.update()
    evaluated = head.evaluated_get(bpy.context.evaluated_depsgraph_get()); mesh = evaluated.to_mesh()
    actual = np.asarray([v.co[:] for v in mesh.vertices]); evaluated.to_mesh_clear()
    reproduction = float(np.linalg.norm(actual-(posed+delta),axis=1).max())
    if reproduction > .000004:
        raise RuntimeError('Actual lip evaluation does not reproduce the inverse-skin residual')
    for driver,state in driver_states:
        driver.mute = state
    return dict(method='Full-angle paired-rim target with shared commissures, continuous tissue support and inverse actual skinning',
                jawRotationDegrees=float(np.degrees(jaw_pose.to_quaternion().angle)), driverValue=amount,
                maximumSourceResidualMeters=maximum, actualReproductionErrorMeters=reproduction,
                iterations=iteration+1, heldNoseAndOcularVertices=True, finiteCornerCurves=curve_reports,
                actualOpenLipVolumeAndDentalContactPending=True)
