"""Explicit anatomical digit planes after the actual v2 audit.

The prior rotation-order construction left up to35 degrees of lateral spread
in a closed phalanx. Each chain now uses one explicit hand-relative bend plane;
these proposals still require actual skin/contact review before promotion.
"""
import math
import bpy
from mathutils import Matrix
from humanoid_arms import put_rotation
from pose_refinement import frame


def digit_rotations(rig, digit, amount, across, along, palm):
    first = rig.data.bones[f'Finger1_{digit}_L']
    ref = (first.tail_local - first.head_local).normalized()
    rest_yaw = math.atan2(ref.dot(across), ref.dot(along))
    closed_yaw = math.radians([-8, -2, 2, 7][digit])
    yaw = rest_yaw * (1 - amount) + closed_yaw * amount
    direction_flat = along * math.cos(yaw) + across * math.sin(yaw)
    hinge = across * math.cos(yaw) - along * math.sin(yaw)
    total = 0.
    result = []
    for relaxed, closed in zip([10, 17, 6], [83, 101, 70]):
        total += math.radians(relaxed * (1 - amount) + closed * amount)
        direction = direction_flat * math.cos(total) + palm * math.sin(total)
        normal = hinge.cross(direction).normalized()
        result.append(Matrix((hinge, direction, normal)).transposed().to_quaternion())
    return result


def apply(rig, clip, phase):
    hand = rig.pose.bones['Hand_L']
    delta = hand.matrix.to_quaternion() @ hand.bone.matrix_local.to_quaternion().inverted()
    across, along, palm = frame(rig)
    amount = .35 if clip == 'Run' else .06
    if clip == 'Melee':
        amount = .06 + .94 * math.sin(math.pi * min(1., max(0., phase))) ** .65
    if clip == 'Hit':
        amount = .15 + .16 * math.sin(math.pi * phase) ** 2
    changed = []
    for digit in range(4):
        parent = hand.matrix.to_quaternion()
        for segment, rotation in enumerate(digit_rotations(rig, digit, amount, across, along, palm), 1):
            name = f'Finger{segment}_{digit}_L'
            desired = delta @ rotation
            put_rotation(rig, name, desired, parent)
            changed.append(name)
            parent = desired
    bpy.context.view_layer.update()
    joints = []
    for digit in (3, 2):
        bone = rig.data.bones[f'Finger1_{digit}_L']
        rotation = digit_rotations(rig, digit, 1., across, along, palm)[0]
        change = rotation @ bone.matrix_local.to_quaternion().inverted()
        joints.append(bone.head_local + change @ (bone.tail_local - bone.head_local))
    contact = (joints[0] + joints[1]) * .5 + palm * .014 - along * .005
    hand_delta = hand.matrix @ hand.bone.matrix_local.inverted()
    first, second = rig.pose.bones['Thumb1_L'], rig.pose.bones['Thumb2_L']
    base, target = hand_delta @ first.bone.head_local, hand_delta @ contact
    direction = target - base
    distance = direction.length
    l1, l2 = first.bone.length, second.bone.length
    if not abs(l1 - l2) + .0001 < distance < l1 + l2 - .0001:
        raise RuntimeError('Thumb contact is not reachable')
    direction.normalize()
    # Opposition brings the thumb across the palmar face of the fist rather
    # than retaining a radially splayed metacarpal through the whole action.
    pole = delta @ (palm * .89 - across * .45).normalized()
    pole -= direction * pole.dot(direction)
    if pole.length < 1e-7:
        raise RuntimeError('Degenerate thumb opposition plane')
    pole.normalize()
    span = (l1*l1 - l2*l2 + distance*distance) / (2*distance)
    joint = base + direction*span + pole*math.sqrt(max(0., l1*l1 - span*span))
    parent = hand.matrix.to_quaternion()
    for bone, vector in ((first, joint-base), (second, target-joint)):
        rest = delta @ bone.bone.matrix_local.to_quaternion()
        reference = delta @ (bone.bone.tail_local-bone.bone.head_local).normalized()
        full = reference.rotation_difference(vector.normalized()) @ rest
        desired = rest.slerp(full, amount)
        put_rotation(rig, bone.name, desired, parent)
        parent = desired
        changed.append(bone.name)
    bpy.context.view_layer.update()
    if amount > .99999 and (second.tail-target).length > 1e-5:
        raise RuntimeError('Full thumb pose does not attain the explicit target')
    return changed
