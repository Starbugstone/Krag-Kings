"""Prepared natural thumb contact for an authored Nib fist.

This offline two-bone fit crosses the thumb over the index/middle proximal
phalanges. It adds no rig bones and is not accepted before actual skin review.
"""
import math
from mathutils import Vector, Quaternion
from humanoid_arms import put_rotation


def closed_target(rig, side='L', mcp_flexion=82, pad_clearance=.008):
    sign=1 if side=='L' else -1
    axis=sign*(rig.data.bones['Index1_'+side].head_local-
               rig.data.bones['Little1_'+side].head_local).normalized()
    turn=Quaternion(axis,math.radians(mcp_flexion))
    heads=[]
    for name in ['Index','Middle']:
        bone=rig.data.bones[name+'1_'+side]
        heads.append(bone.head_local+turn@(bone.tail_local-bone.head_local))
    return (heads[0]+heads[1])*.5+Vector((0,-pad_clearance,.001))


def pose(rig, amount, side='L', pad_clearance=.008):
    import bpy
    if side not in ('L','R') or not 0 <= amount <= 1:
        raise ValueError('Invalid thumb side or interpolation')
    hand=rig.pose.bones['Hand_'+side]
    delta=hand.matrix.to_quaternion()@hand.bone.matrix_local.to_quaternion().inverted()
    first=rig.pose.bones['Thumb1_'+side];second=rig.pose.bones['Thumb2_'+side]
    base=first.head.copy()
    # Use the full-closure target throughout anticipation. Current fingers
    # are still extended early in the clip and would give an unreachable
    # moving target. Interpolate the thumb's rotations as closure develops.
    hand_delta=hand.matrix@hand.bone.matrix_local.inverted()
    target=hand_delta@closed_target(rig,side,pad_clearance=pad_clearance)
    direction=target-base
    length=direction.length
    l1=first.bone.length;l2=second.bone.length
    if length<abs(l1-l2)+.0001 or length>l1+l2-.0001:
        raise RuntimeError('Proposed fist thumb contact is unreachable')
    direction.normalize()
    radial=delta@Vector((-1 if side=='L' else 1,0,0))
    radial-=direction*radial.dot(direction)
    if radial.length<1e-6:raise RuntimeError('Thumb bend plane is degenerate')
    radial.normalize()
    along=(l1*l1-l2*l2+length*length)/(2*length)
    elbow=base+direction*along+radial*math.sqrt(max(0,l1*l1-along*along))
    wanted=[]
    for bone,axis in [(first,elbow-base),(second,target-elbow)]:
        rest=bone.bone.matrix_local.to_quaternion()
        reference=delta@(bone.bone.tail_local-bone.bone.head_local).normalized()
        full=reference.rotation_difference(axis.normalized())@delta@rest
        wanted.append(bone.matrix.to_quaternion().slerp(full,amount))
    put_rotation(rig,first.name,wanted[0],hand.matrix.to_quaternion())
    put_rotation(rig,second.name,wanted[1],wanted[0])
    bpy.context.view_layer.update()
    return {'target':list(target),'actualTip':list(second.tail),'amount':amount,
            'targetErrorMeters':(second.tail-target).length,
            'padClearanceProposalMeters':pad_clearance}
