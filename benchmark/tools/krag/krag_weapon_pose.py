"""Authored firearm pose solved in actual rig space, independent of bone roll.

Proposed correction for the measured cross-body muzzle error. The next source
generation must measure the socket direction and render the grip/shoulders.
"""
import math
import bpy
from mathutils import Vector
from krag_locomotion import orient


def pose(rig,aim,kick):
    upper=rig.pose.bones['UpperArm_R']
    lower=rig.pose.bones['LowerArm_R']
    hand=rig.pose.bones['Hand_R']
    bpy.context.view_layer.update()
    shoulder=upper.head.copy();neutral_wrist=hand.head.copy()
    neutral_elbow=lower.head.copy();neutral_hand_rotation=hand.matrix.to_quaternion()
    # The heavy hand cannon is held outside the torso, with a bent elbow and
    # a small backward/upward recoil. Units are actual rig-space metres.
    firing_wrist=Vector((-.43,-.47,1.47))+Vector((0,.035,.020))*kick
    wrist=neutral_wrist.lerp(firing_wrist,aim)
    axis=wrist-shoulder;distance=axis.length;axis.normalize()
    a=upper.bone.length;b=lower.bone.length
    if distance>a+b-1e-6:raise ValueError('Krag firing wrist is unreachable')
    along=(a*a+distance*distance-b*b)/(2*distance)
    height=math.sqrt(max(0,a*a-along*along))
    neutral_axis=(neutral_wrist-shoulder).normalized()
    neutral_pole=neutral_elbow-shoulder
    neutral_pole-=neutral_axis*neutral_pole.dot(neutral_axis)
    neutral_pole.normalize()
    pole=neutral_pole.lerp(Vector((-1,.12,-.45)).normalized(),aim)
    pole-=axis*pole.dot(axis);pole.normalize()
    elbow=shoulder+axis*along+pole*height
    orient(upper,shoulder,elbow);bpy.context.view_layer.update()
    orient(lower,elbow,wrist);bpy.context.view_layer.update()
    rest_forward=(rig.data.bones['WeaponAim'].head_local-rig.data.bones['WeaponMuzzle'].head_local).normalized()
    firing_forward=Vector((0,-1,.07*kick)).normalized()
    aim_rotation=rest_forward.rotation_difference(firing_forward)
    aimed_hand_rotation=aim_rotation@hand.bone.matrix_local.to_quaternion()
    hand_matrix=neutral_hand_rotation.slerp(aimed_hand_rotation,aim).to_matrix().to_4x4()
    hand_matrix.translation=wrist;hand.matrix=hand_matrix
    bpy.context.view_layer.update()
    actual=(rig.pose.bones['WeaponAim'].head-rig.pose.bones['WeaponMuzzle'].head).normalized()
    return {'aimWeight':aim,'kickWeight':kick,'wristErrorMeters':(hand.head-wrist).length,
            'direction':list(actual),'dotIntendedDirection':actual.dot(firing_forward)}
