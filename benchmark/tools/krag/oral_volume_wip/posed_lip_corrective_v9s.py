"""Author the broad mandibular lip target at the existing full jaw angle."""
from pathlib import Path
import sys
import numpy as np
import bpy
from mathutils import Matrix
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent/'ironjaw_wip'))
from profile_and_lip import membership, member, ordered_rim, extend_residual
from replacement_surface import coordinates
from broad_oral_v9s import lower_rim_target


def apply(head, rig):
    rig.animation_data.action = bpy.data.actions['FacePerformance']
    bpy.context.scene.frame_set(146)
    bpy.context.view_layer.update()
    jaw_pose = rig.pose.bones['Jaw'].matrix_basis.copy()
    amount = float(head.data.shape_keys.key_blocks['JawOpen'].value)
    if not .90 < amount < 1.01:
        raise RuntimeError('Expected unchanged full-range JawOpen driver activation')
    rig.animation_data.action = None
    for bone in rig.pose.bones:
        bone.matrix_basis = Matrix.Identity(4)
    rig.pose.bones['Jaw'].matrix_basis = jaw_pose
    keys = head.data.shape_keys
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
    upper = member(masks, 33) & member(masks, 7)
    lower = member(masks, 24) & member(masks, 7)
    edges = np.asarray([e.vertices[:] for e in head.data.edges], int)
    order = ordered_rim(edges, lower, points)
    group_names = [group.name for group in head.vertex_groups]
    skin = np.asarray([np.asarray(rig.pose.bones[name].matrix @ rig.data.bones[name].matrix_local.inverted(), float)
                       for name in group_names])
    weights = np.zeros((len(points), len(group_names)))
    for vertex in head.data.vertices:
        for group in vertex.groups:
            weights[vertex.index, group.group] = group.weight
    matrices = np.einsum('ij,jkl->ikl', weights, skin)
    rotations, translations = matrices[:, :3, :3], matrices[:, :3, 3]
    posed = np.einsum('ijk,ik->ij', rotations, points+old_delta*amount)+translations
    jaw = skin[group_names.index('Jaw')]
    rigid_jaw = points@jaw[:3, :3].T+jaw[:3, 3]
    targets = lower_rim_target(order, points, posed, rigid_jaw)
    posed_delta, report = extend_residual(points, edges, order, targets, posed,
                                         member(masks, 33) | member(masks, 11))
    source_delta = np.linalg.solve(rotations, posed_delta[:, :, None])[:, :, 0]/amount
    maximum = float(np.linalg.norm(source_delta, axis=1).max())
    if maximum > .040:
        raise RuntimeError('Posed lip correction exceeds40mm; inspect original support before saving')
    revised = points+old_delta+source_delta
    keys.key_blocks['JawOpen'].data.foreach_set('co', revised.astype(np.float32).ravel())
    head.data.update(); bpy.context.view_layer.update()
    evaluated = head.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    actual = np.asarray([v.co[:] for v in mesh.vertices])
    evaluated.to_mesh_clear()
    expected = posed+posed_delta
    error = float(np.linalg.norm(actual-expected, axis=1).max())
    if error > .000004:
        raise RuntimeError('Actual saved-source skin evaluation differs from solved lip residual: '+str(error))
    for driver, state in driver_states:
        driver.mute = state
    report.update({'method': 'Posed residual through inverse actual linear-blend skinning; no duplicate jaw rotation',
                   'unchangedJawRotationDegrees': float(np.degrees(jaw_pose.to_quaternion().angle)),
                   'unchangedDriverValue': amount, 'lowerRimVertices': len(order),
                   'maximumSourceResidualChangeMeters': maximum,
                   'actualBlenderReproductionErrorMeters': error,
                   'upperLipNoseHeld': True, 'actualMouthAcceptance': False})
    return report
