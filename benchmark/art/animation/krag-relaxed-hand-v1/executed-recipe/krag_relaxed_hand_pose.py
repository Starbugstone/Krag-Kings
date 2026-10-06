"""Rest-aware free-hand posture; source proposal requiring native mesh review.

The Krag has two segments per digit. Derive palmar flexion from its actual
knuckle row and hand axis rather than interpolating an arbitrary fist IK.
"""
import math
import bpy
from mathutils import Vector
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
    # A relaxed thumb rests beside the index, with visible pad clearance.
    # It is not a fist-contact claim. Solve on the exact two-segment chain.
    index = rig.pose.bones['Finger1_3_L']
    target = index.head.lerp(index.tail, .46 if running else .40)
    target += delta @ (palm*.018 - axis*.025)
    first = rig.pose.bones['Thumb1_L']; second = rig.pose.bones['Thumb2_L']
    base = first.head.copy(); direction = target-base; distance = direction.length
    a, b = first.bone.length, second.bone.length
    if not abs(a-b)+.0001 < distance < a+b-.0001:
        raise RuntimeError('Relaxed Krag thumb target is unreachable')
    direction.normalize()
    along = (a*a+distance*distance-b*b)/(2*distance)
    pole = delta @ (-axis)
    pole -= direction * pole.dot(direction)
    pole.normalize()
    joint = base + direction*along + pole*math.sqrt(max(0., a*a-along*along))
    parent = hand.matrix.to_quaternion()
    for bone, vector in [(first, joint-base), (second, target-joint)]:
        reference = delta @ (bone.bone.tail_local-bone.bone.head_local).normalized()
        desired = reference.rotation_difference(vector.normalized()) @ delta @ bone.bone.matrix_local.to_quaternion()
        put_rotation(rig, bone.name, desired, parent)
        parent = desired
        changed.append(bone.name)
    bpy.context.view_layer.update()
    error = (second.tail-target).length
    if error > 2e-5:
        raise RuntimeError('Relaxed Krag thumb missed proposed target')
    for digit in range(4):
        endpoints[str(digit)] = list(rig.pose.bones[f'Finger2_{digit}_L'].tail)
    return changed, {'clip':clip, 'palmAxisRest':list(palm), 'knuckleAxisRest':list(axis),
                     'fingertips':endpoints, 'thumbTarget':list(target),
                     'thumbErrorMeters':error, 'surfaceContactProven':False}
