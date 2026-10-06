"""Rest-aware free-hand posture; source proposal requiring native mesh review.

The Krag has two segments per digit. Derive palmar flexion from its actual
knuckle row and hand axis rather than interpolating an arbitrary fist IK.
"""
import math
import bpy
from mathutils import Vector, Quaternion
from humanoid_arms import put_rotation


def pose(rig, clip):
    hand = rig.pose.bones['Hand_L']
    delta = hand.matrix.to_quaternion() @ hand.bone.matrix_local.to_quaternion().inverted()
    axis = (rig.data.bones['Finger1_0_L'].head_local -
            rig.data.bones['Finger1_3_L'].head_local).normalized()
    long = hand.bone.tail_local - hand.bone.head_local
    long -= axis * long.dot(axis)
    long.normalize()
    palm = axis.cross(long).normalized()
    if palm.dot(Vector((-1, 0, 0))) < .8:
        raise RuntimeError('Measured Krag palmar frame differs from source')
    running = clip == 'Run'
    changed = []
    endpoints = {}
    for digit in range(4):
        # Digit 0 is the little finger; digit 3 is the index.
        angles = ((42 + (3-digit)*2, 56 + (3-digit)*3) if running else
                  (12 + (3-digit)*3, 22 + (3-digit)*3))
        first = rig.data.bones['Finger1_'+str(digit)+'_L']
        rest_first = (first.tail_local-first.head_local).normalized()
        lateral = rest_first.dot(axis) * (.12 if running else .32)
        total = 0.
        parent = hand.matrix.to_quaternion()
        for segment, angle in enumerate(angles, 1):
            name = f'Finger{segment}_{digit}_L'
            bone = rig.data.bones[name]
            total += math.radians(angle)
            direction = (long*math.cos(total) + palm*math.sin(total) + axis*lateral).normalized()
            rest_direction = (bone.tail_local-bone.head_local).normalized()
            desired = delta @ rest_direction.rotation_difference(direction) @ bone.matrix_local.to_quaternion()
            put_rotation(rig, name, desired, parent)
            parent = desired
            changed.append(name)
    bpy.context.view_layer.update()
    # The first proposal pulled the thumb approximately 124mm across the
    # palm and folded the thenar web. Preserve its native abduction and bend
    # plane instead; relaxed locomotion does not require thumb-index contact.
    first = rig.data.bones['Thumb1_L']
    second = rig.data.bones['Thumb2_L']
    first_axis = (first.tail_local-first.head_local).normalized()
    second_axis = (second.tail_local-second.head_local).normalized()
    bend_axis = first_axis.cross(second_axis)
    if bend_axis.length < .02:
        raise RuntimeError('Native thumb bend plane is numerically ambiguous')
    bend_axis.normalize()
    angles = (8, 15) if running else (4, 8)
    total = 0.
    parent = hand.matrix.to_quaternion()
    for bone, angle in zip([first, second], angles):
        total += angle
        desired = delta @ Quaternion(bend_axis, math.radians(total)) @ bone.matrix_local.to_quaternion()
        put_rotation(rig, bone.name, desired, parent)
        parent = desired
        changed.append(bone.name)
    bpy.context.view_layer.update()
    for digit in range(4):
        endpoints[str(digit)] = list(rig.pose.bones[f'Finger2_{digit}_L'].tail)
    return changed, {'clip':clip, 'palmAxisRest':list(palm), 'knuckleAxisRest':list(axis),
                     'fingertips':endpoints, 'thumbTip':list(rig.pose.bones['Thumb2_L'].tail),
                     'thumbIncrementalFlexionDegrees':angles, 'thumbBendAxisRest':list(bend_axis),
                     'thumbRestAbductionRetained':True, 'surfaceContactProven':False}
