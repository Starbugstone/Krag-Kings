"""Provisional anatomical arm authoring in character space (+Z up, -Y front).

This is an offline Blender pose solver, not a runtime animation substitute.
It has not passed mesh/motion review. Keep existing actions until an isolated
candidate proves the shoulder paths, silhouette, grip and engine import.
"""
import math

import bpy
from mathutils import Vector


TUNING = {
    'Krag': {
        'Walk': dict(swing=17, elbow=18, elbow_lift=8, abduction=11,
                     weapon_swing=.55, weapon_elbow=24, stance=.62),
        'Run': dict(swing=29, elbow=58, elbow_lift=13, abduction=13,
                    weapon_swing=.48, weapon_elbow=52, stance=.42),
    },
    'Nib': {
        'Walk': dict(swing=20, elbow=16, elbow_lift=9, abduction=7,
                     weapon_swing=.55, weapon_elbow=23, stance=.62),
        'Run': dict(swing=34, elbow=68, elbow_lift=12, abduction=9,
                    weapon_swing=.45, weapon_elbow=58, stance=.32),
    },
}


def put_rotation(rig, name, desired, parent_rotation=None):
    """Write a rig-space rotation through the bone's actual rest frame."""
    bone = rig.data.bones[name]
    pose = rig.pose.bones[name]
    rest = bone.matrix_local.to_quaternion()
    if bone.parent:
        rest_local = bone.parent.matrix_local.to_quaternion().inverted() @ rest
        parent = parent_rotation or rig.pose.bones[bone.parent.name].matrix.to_quaternion()
        basis = rest_local.inverted() @ parent.inverted() @ desired
    else:
        basis = rest.inverted() @ desired
    pose.rotation_mode = 'XYZ'
    pose.rotation_euler = basis.to_euler('XYZ', pose.rotation_euler)


def aligned_rotation(bone, direction, torso_delta):
    """Minimal rest-relative rotation; do not assume a local Euler bend axis."""
    resting_direction = torso_delta @ (bone.tail_local - bone.head_local).normalized()
    return (resting_direction.rotation_difference(direction.normalized()) @
            torso_delta @ bone.matrix_local.to_quaternion())


def pose(rig, species, clip, phase, weapon_side='R'):
    """Author arms opposite the ipsilateral foot's front/back stance position.

    All angles are tuning proposals in degrees. Shoulder abduction is modest;
    elbows flex anatomically toward the front in both species. The gun arm has
    restrained swing. Small clavicle protraction follows the arm, with the
    current torso's rotation layered underneath. Geometry/bind never change.
    """
    spec = TUNING[species][clip]
    chest = rig.pose.bones['Chest']
    torso_delta = chest.matrix.to_quaternion() @ chest.bone.matrix_local.to_quaternion().inverted()
    forward = torso_delta @ Vector((0, -1, 0))
    up = torso_delta @ Vector((0, 0, 1))
    plans = []
    for side, sign in [('L', 1), ('R', -1)]:
        p = (phase + (0 if side == 'L' else .5)) % 1
        # Foot contact is maximum forward at p=0; that arm must be back then.
        # Match the stance/swing partition, with zero slope at both extrema.
        theta = (math.pi*p/spec['stance'] if p < spec['stance'] else
                 math.pi + math.pi*(p-spec['stance'])/(1-spec['stance']))
        opposition = -math.cos(theta)
        carrying = side == weapon_side
        swing = spec['swing'] * opposition * (spec['weapon_swing'] if carrying else 1)
        bend = (spec['weapon_elbow'] if carrying else spec['elbow']) + spec['elbow_lift']*(opposition+1)/2
        clavicle = rig.pose.bones['Clavicle_'+side]
        direction = torso_delta @ (clavicle.bone.tail_local-clavicle.bone.head_local)
        upper_length = rig.data.bones['UpperArm_'+side].length
        protraction = upper_length * (.018 if clip == 'Walk' else .032) * opposition
        elevation = upper_length * .005 * (opposition+1)/2
        desired = direction + forward*protraction + up*elevation
        put_rotation(rig, clavicle.name,
                     direction.rotation_difference(desired) @ torso_delta @
                     clavicle.bone.matrix_local.to_quaternion())
        plans.append((side, sign, swing, bend))
    bpy.context.view_layer.update()

    metrics = []
    for side, sign, swing, bend in plans:
        abduction = math.radians(spec['abduction'])
        def direction(flexion):
            a = math.radians(flexion)
            return torso_delta @ Vector((sign*math.sin(abduction),
                                         -math.sin(a)*math.cos(abduction),
                                         -math.cos(a)*math.cos(abduction)))
        upper = rig.data.bones['UpperArm_'+side]
        lower = rig.data.bones['LowerArm_'+side]
        hand = rig.data.bones['Hand_'+side]
        upper_q = aligned_rotation(upper, direction(swing), torso_delta)
        lower_q = aligned_rotation(lower, direction(swing+bend), torso_delta)
        put_rotation(rig, upper.name, upper_q)
        put_rotation(rig, lower.name, lower_q, upper_q)
        # Preserve the authored neutral wrist/weapon relationship, rather than
        # adding an arbitrary bend around an unknown hand-local axis.
        hand_q = lower_q @ lower.matrix_local.to_quaternion().inverted() @ hand.matrix_local.to_quaternion()
        put_rotation(rig, hand.name, hand_q, lower_q)
        metrics.append(dict(side=side, shoulderFlexionDegrees=swing,
                            sagittalElbowFlexionDegrees=bend,
                            abductionDegrees=spec['abduction']))
    bpy.context.view_layer.update()
    for item in metrics:
        side = item['side']
        for label, name in [('shoulder', 'UpperArm_'), ('elbow', 'LowerArm_'), ('wrist', 'Hand_')]:
            item[label] = list(rig.pose.bones[name+side].head)
    return metrics
