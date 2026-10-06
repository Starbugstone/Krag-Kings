"""Anatomical hand controls in the saved Nib bind, in degrees.

Angles are proposed MCP/PIP/DIP flexion, not extra Euler rotation on an already
curled bind. Call after the arm/hand world pose has been evaluated. No keys or
mesh changes are made here. Actual posed contact remains an authoring check.
"""
import math

import bpy
from mathutils import Quaternion, Vector

from humanoid_arms import put_rotation


RELAXED = {'Index': (12, 22, 8), 'Middle': (15, 28, 10),
           'Ring': (18, 30, 10), 'Little': (20, 32, 12)}


def pose(rig, angles, thumb_flexion=(5, 8), opposition=12, side='L'):
    if side not in ('L', 'R'):
        raise ValueError('Hand side must be L or R')
    sign = 1 if side == 'L' else -1
    hand = rig.pose.bones['Hand_'+side]
    delta = hand.matrix.to_quaternion() @ hand.bone.matrix_local.to_quaternion().inverted()
    # Axial rotations reverse under reflection; keep flexion directed into
    # each palm rather than extending the mirrored right fingers backwards.
    axis = sign*(rig.data.bones['Index1_'+side].head_local -
                 rig.data.bones['Little1_'+side].head_local).normalized()
    changed = []
    for finger, joint_angles in angles.items():
        total = 0.
        parent = hand.matrix.to_quaternion()
        first = rig.data.bones[finger+'1_'+side]
        reference = first.tail_local-first.head_local
        reference -= axis*reference.dot(axis)
        reference.normalize()
        for segment, angle in enumerate(joint_angles, 1):
            bone = rig.pose.bones[finger+str(segment)+'_'+side]
            total += angle
            direction = bone.bone.tail_local-bone.bone.head_local
            direction -= axis*direction.dot(axis)
            direction.normalize()
            bind_bend = math.atan2(axis.dot(reference.cross(direction)), reference.dot(direction))
            desired = (delta @ Quaternion(axis, math.radians(total)-bind_bend) @
                       bone.bone.matrix_local.to_quaternion())
            put_rotation(rig, bone.name, desired, parent)
            parent = desired
            changed.append(bone.name)
    total = 0.
    parent = hand.matrix.to_quaternion()
    for segment, angle in enumerate(thumb_flexion, 1):
        bone = rig.pose.bones['Thumb'+str(segment)+'_'+side]
        total += angle
        desired = (delta @ Quaternion(axis, math.radians(total)) @
                   Quaternion(Vector((0, -sign, 0)), math.radians(opposition)) @
                   bone.bone.matrix_local.to_quaternion())
        put_rotation(rig, bone.name, desired, parent)
        parent = desired
        changed.append(bone.name)
    bpy.context.view_layer.update()
    return changed
