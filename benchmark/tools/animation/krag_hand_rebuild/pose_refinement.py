"""Prepared digit convergence and thumb opposition on the coherent Krag hand.

Offline authoring proposals, requiring actual skin/contact views. Body, wrist,
binds and facial animation are untouched. No solver runs in either game.
"""
import math
import bpy
from mathutils import Quaternion
from humanoid_arms import put_rotation


def frame(rig):
    hand = rig.data.bones['Hand_L']
    across = (rig.data.bones['Finger1_0_L'].head_local -
              rig.data.bones['Finger1_3_L'].head_local).normalized()
    along = hand.tail_local - hand.head_local
    along -= across * along.dot(across)
    along.normalize()
    return across, along, across.cross(along).normalized()


def digit_rotations(rig, digit, amount, across, along, palm):
    first = rig.data.bones[f'Finger1_{digit}_L']
    reference = (first.tail_local - first.head_local).normalized()
    planar = reference - palm * reference.dot(palm)
    planar.normalize()
    # As the fist closes, the four digits converge instead of retaining the
    # spread of the anatomical rest hand. Preserve slight natural spread.
    converge = Quaternion().slerp(planar.rotation_difference(along), .92 * amount)
    sagittal = reference - across * reference.dot(across)
    sagittal.normalize()
    angles = [14 + 62 * amount, 24 + 66 * amount, 8 + 41 * amount]
    total = 0.
    result = []
    for segment, angle in enumerate(angles, 1):
        bone = rig.data.bones[f'Finger{segment}_{digit}_L']
        direction = bone.tail_local - bone.head_local
        direction -= across * direction.dot(across)
        direction.normalize()
        bind = math.atan2(across.dot(sagittal.cross(direction)), sagittal.dot(direction))
        total += math.radians(angle + (3 - digit) * .6)
        result.append(converge @ Quaternion(across, total - bind) @ bone.matrix_local.to_quaternion())
    return result


def apply(rig, clip, phase):
    hand = rig.pose.bones['Hand_L']
    delta = hand.matrix.to_quaternion() @ hand.bone.matrix_local.to_quaternion().inverted()
    across, along, palm = frame(rig)
    amount = .36 if clip == 'Run' else .06
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
    # A fixed full-closure target makes the opening/closing path deterministic
    # rather than chasing the still-extended fingers during anticipation.
    joints = []
    for digit in (3, 2):
        bone = rig.data.bones[f'Finger1_{digit}_L']
        rotation = digit_rotations(rig, digit, 1., across, along, palm)[0]
        change = rotation @ bone.matrix_local.to_quaternion().inverted()
        joints.append(bone.head_local + change @ (bone.tail_local - bone.head_local))
    contact = (joints[0] + joints[1]) * .5 + palm * .012 - along * .005
    hand_delta = hand.matrix @ hand.bone.matrix_local.inverted()
    first = rig.pose.bones['Thumb1_L']
    second = rig.pose.bones['Thumb2_L']
    base = hand_delta @ first.bone.head_local
    target = hand_delta @ contact
    direction = target - base
    distance = direction.length
    l1, l2 = first.bone.length, second.bone.length
    if not abs(l1 - l2) + .0001 < distance < l1 + l2 - .0001:
        raise RuntimeError(f'Anatomical thumb opposition target is unreachable: {distance} / {l1}, {l2}')
    direction.normalize()
    radial = delta @ -across
    radial -= direction * radial.dot(direction)
    if radial.length < 1e-7:
        raise RuntimeError('Degenerate thumb opposition plane')
    radial.normalize()
    span = (l1 * l1 - l2 * l2 + distance * distance) / (2 * distance)
    joint = base + direction * span + radial * math.sqrt(max(0., l1 * l1 - span * span))
    parent = hand.matrix.to_quaternion()
    for bone, vector in ((first, joint - base), (second, target - joint)):
        rest = delta @ bone.bone.matrix_local.to_quaternion()
        reference = delta @ (bone.bone.tail_local - bone.bone.head_local).normalized()
        full = reference.rotation_difference(vector.normalized()) @ rest
        desired = rest.slerp(full, amount)
        put_rotation(rig, bone.name, desired, parent)
        parent = desired
        changed.append(bone.name)
    bpy.context.view_layer.update()
    return changed
