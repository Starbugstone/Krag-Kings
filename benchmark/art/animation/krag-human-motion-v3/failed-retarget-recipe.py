"""Isolated full-body motion study; original character/master and exports stay fixed.

Retargets acquired human joint directions and coordinated trunk rotations, then
grounds the character's actual foot frame. All motion/stance tuning is provisional
until the saved character and imported clips have been reviewed in motion.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy
from bpy_extras.anim_utils import action_get_channelbag_for_slot
from mathutils import Matrix, Quaternion, Vector
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import acclaim_motion
from humanoid_arms import put_rotation
import sole_geometry

parser = argparse.ArgumentParser()
parser.add_argument('--source', type=Path, required=True)
parser.add_argument('--species', choices=['Krag', 'Nib'], required=True)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--generation', default='v3')
args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
if args.output.exists(): raise RuntimeError('Preserve previous study output')
args.output.mkdir(parents=True)
root = Path(__file__).resolve().parents[2]
data = root/'art/animation/cmu'
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
source_sha = sha(args.source)
bpy.ops.wm.open_mainfile(filepath=str(args.source))
rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and 'Pelvis' in o.data.bones)
scene = bpy.context.scene
scene.render.fps = 30
sole_clouds, sole_records = sole_geometry.capture(rig, args.species)
mesh_visibility = {o.name: o.hide_viewport for o in bpy.data.objects if o.type == 'MESH'}
for name in mesh_visibility: bpy.data.objects[name].hide_viewport = True
for track in rig.animation_data.nla_tracks: track.mute = True


def geometry_digest():
    result = {}
    for obj in bpy.data.objects:
        if obj.type != 'MESH': continue
        vertices = np.empty(len(obj.data.vertices)*3, dtype=np.float32)
        obj.data.vertices.foreach_get('co', vertices)
        digest = hashlib.sha256(vertices.tobytes())
        for key in obj.data.shape_keys.key_blocks if obj.data.shape_keys else []:
            key.data.foreach_get('co', vertices); digest.update(vertices.tobytes())
        result[obj.name] = digest.hexdigest()
    return result


before_geometry = geometry_digest()
before_bind = {b.name: [list(row) for row in b.matrix_local] for b in rig.data.bones}
asf, walk = acclaim_motion.load(data/'104.asf', data/'104_02.amc')
jog_asf, jog = acclaim_motion.load(data/'09.asf', data/'09_01.amc')
canonical = Matrix(acclaim_motion.CANONICAL)
source_directions = {name: canonical @ Vector(bone['direction']) for name, bone in asf['bones'].items()}
jog_directions = {name: canonical @ Vector(bone['direction']) for name, bone in jog_asf['bones'].items()}


def heading(samples, first, last):
    a, b = samples[first-1]['heads']['root'], samples[last-1]['heads']['root']
    return Quaternion(Vector((0, 0, 1)), -math.atan2(b[0]-a[0], -(b[1]-a[1])))


walk_heading = heading(walk, 212, 360)
neutral = {name: walk_heading @ Matrix(rotation).to_quaternion()
           for name, rotation in walk[759]['rotations'].items()}
body_map = {'Pelvis': 'root', 'Spine': 'upperback', 'Chest': 'thorax',
            'Neck': 'lowerneck', 'Head': 'head'}
for side, prefix in [('L', 'l'), ('R', 'r')]:
    for target, source in [('Clavicle', 'clavicle'), ('UpperArm', 'humerus'),
                           ('LowerArm', 'radius'), ('Thigh', 'femur'),
                           ('Shin', 'tibia'), ('Foot', 'foot')]:
        body_map[target+'_'+side] = prefix+source
body_names = list(body_map)+['Hand_L', 'Hand_R', 'Toe_L', 'Toe_R']
body_names = [name for name in body_names if name in rig.data.bones]
rest = {name: rig.data.bones[name].matrix_local.to_quaternion() for name in body_names}
rest_directions = {name: (rig.data.bones[name].tail_local-rig.data.bones[name].head_local).normalized()
                   for name in body_names}
leg_scale = sum(rig.data.bones[n+'_L'].length for n in ['Thigh', 'Shin']) / sum(asf['bones'][n]['length'] for n in ['lfemur', 'ltibia'])
report = {'source': str(args.source), 'sourceSha256': source_sha, 'species': args.species,
          'recipeSha256': sha(Path(__file__)), 'sourceScaleByLegChain': leg_scale,
          'status': 'Actual isolated source study; visual/motion/import acceptance pending',
          'soleGeometry': sole_records, 'soleHelperSha256': sha(Path(sole_geometry.__file__)),
          'sharedAssetsChanged': False, 'artisticAcceptance': False, 'clips': {}}


def remove_body_curves(action, slot):
    bag = action_get_channelbag_for_slot(action, slot)
    if bag is None: raise RuntimeError('No rig channel bag')
    paths = {rig.pose.bones[name].path_from_id() for name in body_names}
    for curve in list(bag.fcurves):
        if any(curve.data_path.startswith(path+'.') for path in paths): bag.fcurves.remove(curve)
    return bag


def source_pose(samples, first, last, phase):
    at = first-1+(last-first)*phase
    lower = int(at); upper = min(lower+1, len(samples)-1); fraction = at-lower
    a, b = samples[lower], samples[upper]
    alignment = heading(samples, first, last)
    fade = phase*phase*(3-2*phase)
    quats = {}
    for name in a['rotations']:
        q = Matrix(a['rotations'][name]).to_quaternion().slerp(Matrix(b['rotations'][name]).to_quaternion(), fraction)
        q0 = Matrix(samples[first-1]['rotations'][name]).to_quaternion()
        q1 = Matrix(samples[last-1]['rotations'][name]).to_quaternion()
        correction = Quaternion().slerp(q0 @ q1.inverted(), fade)
        quats[name] = alignment @ correction @ q
    root_at = Vector(a['heads']['root']).lerp(Vector(b['heads']['root']), fraction)
    root0, root1 = Vector(samples[first-1]['heads']['root']), Vector(samples[last-1]['heads']['root'])
    residual = alignment @ (root_at-root0.lerp(root1, phase))
    return quats, residual


def retarget_rotations(quats, directions=None):
    directions = directions or source_directions
    desired = {}
    for name, source in body_map.items():
        if name.startswith(('UpperArm', 'LowerArm', 'Thigh', 'Shin')):
            direction = quats[source] @ directions[source]
            # Preserve the existing anatomical rest roll while reproducing
            # measured human segment directions, independent of Euler axes.
            desired[name] = rest_directions[name].rotation_difference(direction) @ rest[name]
        else:
            desired[name] = quats[source] @ neutral[source].inverted() @ rest[name]
    # Relax the free palm toward the body's medial plane. Nib's authored bind
    # has palms facing forward; blindly retaining that roll makes a raised
    # forearm present its palm upward. Use actual rest frames, not local Euler.
    side = 'L'; name = 'LowerArm_'+side
    axis = desired[name] @ Vector((0, 1, 0))
    palm_rest = Vector((-1, 0, 0) if args.species == 'Krag' else (0, -1, 0))
    palm = desired[name] @ rest[name].inverted() @ palm_rest
    medial = desired['Chest'] @ rest['Chest'].inverted() @ Vector((-1, 0, 0))
    palm -= axis*palm.dot(axis); medial -= axis*medial.dot(axis)
    if palm.length > .05 and medial.length > .05:
        palm.normalize(); medial.normalize()
        angle = math.atan2(axis.dot(palm.cross(medial)), palm.dot(medial))
        desired[name] = Quaternion(axis, max(-math.pi/2, min(math.pi/2, angle))) @ desired[name]
    for side in ['L', 'R']:
        for name, parent in [('Hand_'+side, 'LowerArm_'+side), ('Toe_'+side, 'Foot_'+side)]:
            if name in rest: desired[name] = desired[parent] @ rest[parent].inverted() @ rest[name]
    for name in body_names:
        bone = rig.pose.bones[name]
        bone.location = (0, 0, 0); bone.scale = (1, 1, 1)
        put_rotation(rig, name, desired[name], desired.get(bone.parent.name) if bone.parent else None)


def pose_body(quats, residual, directions=None):
    retarget_rotations(quats, directions)
    pelvis = rig.pose.bones['Pelvis']
    pelvis.location = pelvis.bone.matrix_local.to_3x3().inverted() @ (residual*leg_scale)
    bpy.context.view_layer.update()


def foot_clearance(side):
    return sole_geometry.minimum(rig, sole_clouds, side)


def fixed_idle_feet():
    """Soft-kneed weight shift over stationary feet; no root skating."""
    errors = []
    for side in ['L', 'R']:
        upper, lower, foot = [rig.pose.bones[name+'_'+side] for name in ['Thigh', 'Shin', 'Foot']]
        hip = upper.head.copy(); target = foot.bone.head_local.copy()
        target.z -= sole_records[side]['restMinimumZ']
        axis = target-hip; distance = axis.length
        a, b = upper.bone.length, lower.bone.length
        if not abs(a-b)+1e-5 < distance < a+b-1e-5:
            raise RuntimeError('Idle foot target cannot be reached '+side)
        axis.normalize(); along = (a*a+distance*distance-b*b)/(2*distance)
        forward = Vector((0, -1, 0)); forward -= axis*forward.dot(axis); forward.normalize()
        knee = hip+axis*along+forward*math.sqrt(max(0, a*a-along*along))
        upper_q = rest_directions[upper.name].rotation_difference(knee-hip) @ rest[upper.name]
        lower_q = rest_directions[lower.name].rotation_difference(target-knee) @ rest[lower.name]
        put_rotation(rig, upper.name, upper_q)
        put_rotation(rig, lower.name, lower_q, upper_q)
        put_rotation(rig, foot.name, rest[foot.name], lower_q)
        toe_name = 'Toe_'+side
        if toe_name in rest: put_rotation(rig, toe_name, rest[toe_name], rest[foot.name])
        bpy.context.view_layer.update()
        errors.append((foot.head-target).length)
    if max(errors) > 1e-4: raise RuntimeError('Idle planted-foot solve missed target')
    return max(errors)


def relax_free_hand(clip):
    """Partial anatomical curl around the actual finger bend planes.

    Preserve the separate authored right-hand weapon contact and thumb tracks.
    Only the Krag's free left finger chains have verified control semantics here.
    """
    if args.species == 'Nib':
        hand = rig.pose.bones['Hand_L']
        delta = hand.matrix.to_quaternion() @ hand.bone.matrix_local.to_quaternion().inverted()
        multiplier = 1.3 if clip == 'Run' else 1.
        for finger, angles in [('Index', (18, 28, 12)), ('Middle', (22, 32, 15)),
                               ('Ring', (24, 35, 16)), ('Little', (26, 38, 18))]:
            total = 0.; parent = hand.matrix.to_quaternion()
            for segment, angle in enumerate(angles, 1):
                bone = rig.pose.bones[finger+str(segment)+'_L']
                direction = (bone.bone.tail_local-bone.bone.head_local).normalized()
                axis = direction.cross(Vector((0, -1, 0))).normalized()
                total += angle*multiplier
                desired = delta @ Quaternion(axis, math.radians(total)) @ bone.bone.matrix_local.to_quaternion()
                put_rotation(rig, bone.name, desired, parent)
                bone.keyframe_insert('rotation_euler', frame=scene.frame_current, group=bone.name)
                parent = desired
        bpy.context.view_layer.update()
        return
    sys.path.insert(0, str(root/'tools/krag'))
    from krag_grip_v2 import solve_chain
    hand = rig.pose.bones['Hand_L']
    delta = hand.matrix @ hand.bone.matrix_local.inverted()
    strength = .65 if clip == 'Run' else .50
    for digit in range(4):
        first = rig.pose.bones['Finger1_'+str(digit)+'_L']
        second = rig.pose.bones['Finger2_'+str(digit)+'_L']
        for bone in [first, second]: bone.rotation_euler = (0, 0, 0)
        bpy.context.view_layer.update()
        original = [Quaternion(), Quaternion()]
        target = first.bone.head_local+Vector((-.052, 0, .017))
        solve_chain(first, second, delta @ target, delta.to_3x3() @ Vector((0, 0, -1)))
        for bone, initial in zip([first, second], original):
            bone.rotation_euler = initial.slerp(bone.rotation_euler.to_quaternion(), strength).to_euler('XYZ', bone.rotation_euler)
            bone.keyframe_insert('rotation_euler', frame=scene.frame_current, group=bone.name)
        bpy.context.view_layer.update()


def solve_leg(side, target):
    upper, lower, foot = [rig.pose.bones[n+'_'+side] for n in ['Thigh', 'Shin', 'Foot']]
    hip, old_knee = upper.head.copy(), lower.head.copy()
    axis = target-hip; distance = axis.length
    a, b = upper.bone.length, lower.bone.length
    if not abs(a-b)+1e-5 < distance < a+b-1e-5: raise RuntimeError('Unreachable contact target '+side)
    axis.normalize(); along = (a*a+distance*distance-b*b)/(2*distance)
    pole = old_knee-hip; pole -= axis*pole.dot(axis)
    if pole.length < .001: pole = Vector((0, -1, 0)); pole -= axis*pole.dot(axis)
    pole.normalize(); knee = hip+axis*along+pole*math.sqrt(max(0, a*a-along*along))
    foot_q = foot.matrix.to_quaternion()
    toe = rig.pose.bones.get('Toe_'+side); toe_q = toe.matrix.to_quaternion() if toe else None
    upper_q = rest_directions[upper.name].rotation_difference(knee-hip) @ rest[upper.name]
    lower_q = rest_directions[lower.name].rotation_difference(target-knee) @ rest[lower.name]
    put_rotation(rig, upper.name, upper_q)
    put_rotation(rig, lower.name, lower_q, upper_q)
    put_rotation(rig, foot.name, foot_q, lower_q)
    if toe: put_rotation(rig, toe.name, toe_q, foot_q)
    bpy.context.view_layer.update()
    return (foot.head-target).length


def fit_contacts(phase, contacts, anchors, distance):
    """Fit stance feet to constant-speed ground travel; retain swing capture.

    Foot roll is retained. The lowest heel/toe sole anchor remains on the ground.
    Soft transitions blend the inverse-kinematic correction at contact edges.
    """
    targets, weights = {}, {}
    for side in ['L', 'R']:
        middle, half_width, fade = contacts[side]
        offset = (phase-middle+.5)%1-.5
        t = max(0., min(1., (half_width-abs(offset))/fade))
        weight = t*t*(3-2*t); weights[side] = weight
        foot = rig.pose.bones['Foot_'+side]
        target = foot.head.copy()
        planted = Vector((anchors[side].x, anchors[side].y+distance*offset,
                          target.z-foot_clearance(side)))
        targets[side] = target.lerp(planted, weight)
        # Prevent any swing sole from penetrating the provisional ground.
        targets[side].z += max(0., -(foot_clearance(side)+(targets[side].z-target.z)))
    drop = 0.
    for side, target in targets.items():
        hip = rig.pose.bones['Thigh_'+side].head
        maximum = sum(rig.data.bones[n+'_'+side].length for n in ['Thigh', 'Shin'])-.001
        horizontal = (hip.x-target.x)**2+(hip.y-target.y)**2
        if horizontal >= maximum*maximum: raise RuntimeError('Contact stride exceeds anatomical reach')
        drop = min(drop, target.z+math.sqrt(maximum*maximum-horizontal)-hip.z)
    if drop < -.09:
        (args.output/'contact-fit-failure.json').write_text(json.dumps({
            'clip': rig.animation_data.action.name, 'frame': scene.frame_current,
            'phase': phase, 'pelvisDrop': drop, 'weights': weights,
            'targets': {k:list(v) for k,v in targets.items()},
            'hips': {s:list(rig.pose.bones['Thigh_'+s].head) for s in ['L','R']}
        }, indent=2)+'\n')
        raise RuntimeError('Contact fit would force excessive pelvis drop')
    if drop:
        pelvis = rig.pose.bones['Pelvis']
        pelvis.location += pelvis.bone.matrix_local.to_3x3().inverted() @ Vector((0, 0, drop))
        bpy.context.view_layer.update()
    errors = {side: solve_leg(side, target) for side, target in targets.items()}
    return {'weights': weights, 'pelvisDrop': drop, 'targetErrors': errors}


for clip, samples, first, last, frames, directions, source_skeleton in [
        ('Walk', walk, 212, 360, 30 if args.species == 'Krag' else 24, source_directions, asf),
        ('Run', jog, 35, 123, 24 if args.species == 'Krag' else 18, jog_directions, jog_asf)]:
    original = bpy.data.actions.get(clip)
    if original is None: raise RuntimeError('Missing existing body/facial clip '+clip)
    action = original.copy(); original.name = 'Preserved_'+clip+'_BeforeHumanMotion'
    action.name = clip; action.use_fake_user = True
    rig.animation_data.action = action
    slot = rig.animation_data.action_slot
    bag = remove_body_curves(action, slot)
    old_start, old_end = original.frame_range
    # Keep the authored facial and finger performances in normalized time.
    for curve in bag.fcurves:
        for key in curve.keyframe_points:
            for point in [key.co, key.handle_left, key.handle_right]:
                point.x = 1+(point.x-old_start)/(old_end-old_start)*frames
    poses = []
    for index in range(frames+1):
        phase = index/frames
        scene.frame_set(index+1)
        quats, residual = source_pose(samples, first, last, phase)
        pose_body(quats, residual, directions)
        poses.append({'quats': quats, 'residual': residual,
                      'clearance': min(foot_clearance('L'), foot_clearance('R'))})
    # Preserve measured flight-height variation while removing sole penetration.
    # The constant offset is derived from the lowest retargeted sole, not a
    # forced deep knee bend. A later contact-fit pass must assess sliding.
    ground_offset = -min(p['clearance'] for p in poses)
    contacts = ({'L': (.31, .30, .055), 'R': (.81, .30, .055)} if clip == 'Walk'
                else {'L': (.70, .12, .04), 'R': (.20, .12, .04)})
    anchors = {}
    for side, (middle, _, _) in contacts.items():
        quats, residual = source_pose(samples, first, last, middle)
        residual.z += ground_offset/leg_scale
        pose_body(quats, residual, directions)
        anchors[side] = rig.pose.bones['Foot_'+side].head.copy()
    source_leg_scale = sum(rig.data.bones[n+'_L'].length for n in ['Thigh', 'Shin']) / sum(source_skeleton['bones'][n]['length'] for n in ['lfemur', 'ltibia'])
    start, end = Vector(samples[first-1]['heads']['root']), Vector(samples[last-1]['heads']['root'])
    travel_distance = Vector((end.x-start.x, end.y-start.y, 0)).length*source_leg_scale
    evidence = []
    for index, pose in enumerate(poses):
        scene.frame_set(index+1)
        residual = pose['residual'].copy(); residual.z += ground_offset/leg_scale
        pose_body(pose['quats'], residual, directions)
        contact_result = fit_contacts(index/frames, contacts, anchors, travel_distance)
        relax_free_hand(clip)
        for name in body_names:
            bone = rig.pose.bones[name]
            for channel in ['location', 'rotation_euler', 'scale']:
                bone.keyframe_insert(channel, frame=index+1, group=name)
        evidence.append({'frame': index+1, 'contact': contact_result,
                         'joints': {name: {'head': list(rig.pose.bones[name].head),
                                           'tail': list(rig.pose.bones[name].tail)}
                                    for name in body_names},
                         'soleClearance': {side: foot_clearance(side) for side in ['L', 'R']}})
    for curve in bag.fcurves:
        if any(curve.data_path.startswith(rig.pose.bones[name].path_from_id()+'.') for name in body_names):
            for key in curve.keyframe_points: key.interpolation = 'LINEAR'
    action['clip_duration_seconds'] = frames/30
    action['motion_source'] = 'CMU 104_02' if clip == 'Walk' else 'CMU 09_01'
    start, end = Vector(samples[first-1]['heads']['root']), Vector(samples[last-1]['heads']['root'])
    proposal_speed = travel_distance/(frames/30)
    report['clips'][clip] = {'frames': frames, 'durationSeconds': frames/30,
                             'sourceFrames': [first, last], 'sourceFps': 120,
                             'proposedSpeedMetersPerSecond': proposal_speed,
                             'groundOffsetMeters': ground_offset,
                             'sourceClip': action['motion_source'], 'contactTuning': contacts,
                             'contactFitAccepted': False, 'samples': evidence}

# A restrained six-second standing performance. Body shape, facial controls and
# the weapon grip are retained. Species differences remain tuning proposals.
original = bpy.data.actions['Idle']; action = original.copy()
original.name = 'Preserved_Idle_BeforeHumanMotion'; action.name = 'Idle'; action.use_fake_user = True
rig.animation_data.action = action; bag = remove_body_curves(action, rig.animation_data.action_slot)
old_start, old_end = original.frame_range
for curve in bag.fcurves:
    if any(curve.data_path.startswith('pose.bones["LidUpper_'+side+'"].') for side in ['L','R']):
        # Keep blink timing at its authored speed instead of stretching a
        # normal closure into a slow six-second-idle blink. Repeat the original
        # short facial loop while other attention/breathing tracks span six s.
        points = [(float(k.co.x), float(k.co.y)) for k in curve.keyframe_points]
        duration = old_end-old_start
        repeated = {}
        for repeat in range(math.ceil(180/duration)):
            for frame,value in points:
                at = 1+(frame-old_start)+repeat*duration
                if at <= 181: repeated[at] = value
        for key in list(curve.keyframe_points): curve.keyframe_points.remove(key, fast=True)
        for frame,value in sorted(repeated.items()):
            key = curve.keyframe_points.insert(frame, value, options={'FAST'})
            key.interpolation = 'LINEAR'
        curve.update()
        continue
    for key in curve.keyframe_points:
        for point in [key.co, key.handle_left, key.handle_right]: point.x = 1+(point.x-old_start)/(old_end-old_start)*180
idle_samples = []
for index in range(0, 181, 3):
    scene.frame_set(index+1); phase = index/180; wave = math.sin(math.tau*phase)
    breath = math.sin(math.tau*phase*2)*(.6 if args.species == 'Krag' else .45)
    def turn(axis, angle): return Quaternion(Vector(axis), math.radians(angle))
    pelvis_delta = turn((0, 0, 1), wave*1.2) @ turn((0, -1, 0), wave*.55)
    chest_delta = turn((0, 0, 1), -wave*.8) @ turn((1, 0, 0), breath)
    quats = {name: value.copy() for name, value in neutral.items()}
    quats['root'] = pelvis_delta @ neutral['root']
    quats['upperback'] = turn((0, 0, 1), -wave*.25) @ turn((1, 0, 0), breath*.4) @ neutral['upperback']
    for source in ['thorax', 'lclavicle', 'rclavicle', 'lhumerus', 'rhumerus', 'lradius', 'rradius']:
        quats[source] = chest_delta @ neutral[source]
    quats['lowerneck'] = turn((1, 0, 0), -breath*.35) @ neutral['lowerneck']
    quats['head'] = turn((0, 0, 1), wave*(1.3 if args.species == 'Krag' else 2.5)) @ neutral['head']
    retarget_rotations(quats)
    pelvis = rig.pose.bones['Pelvis']
    offset = Vector((wave*(.008 if args.species == 'Krag' else .005), 0,
                     -(.018 if args.species == 'Krag' else .010)+.001*math.sin(math.tau*phase*2)))
    pelvis.location = pelvis.bone.matrix_local.to_3x3().inverted() @ offset
    bpy.context.view_layer.update(); foot_error = fixed_idle_feet()
    relax_free_hand('Idle')
    for name in body_names:
        bone = rig.pose.bones[name]
        for channel in ['location', 'rotation_euler', 'scale']:
            bone.keyframe_insert(channel, frame=index+1, group=name)
    idle_samples.append({'frame': index+1, 'footErrorMeters': foot_error,
                         'pelvis': list(pelvis.head), 'chest': list(rig.pose.bones['Chest'].tail)})
action['clip_duration_seconds'] = 6.0
report['clips']['Idle'] = {'durationSeconds': 6, 'frames': 180,
                           'description': 'Soft standing posture, two breaths, coordinated weight shift and attentive head motion',
                           'maximumFootTargetErrorMeters': max(x['footErrorMeters'] for x in idle_samples),
                           'samples': idle_samples}

if args.species == 'Nib' and 'EarTip_L' in rig.data.bones:
    sys.path.insert(0, str(root/'tools/nib/motion_wip'))
    import ear_motion
    ear_report = ear_motion.author_tracks(rig, ['Idle','Walk','Run'])
    report['earTracksReauthored'] = {name:{k:v for k,v in info.items() if k != 'samples'}
                                   for name,info in ear_report.items()}
    report['earRecipeSha256'] = sha(Path(ear_motion.__file__))

for name, visibility in mesh_visibility.items(): bpy.data.objects[name].hide_viewport = visibility
rig.animation_data.action = bpy.data.actions['Walk']; scene.frame_set(1)
if geometry_digest() != before_geometry: raise AssertionError('Motion study changed mesh/shape coordinates')
if before_bind != {b.name: [list(row) for row in b.matrix_local] for b in rig.data.bones}:
    raise AssertionError('Motion study changed source bind skeleton')
output = args.output/(args.species+'_HumanMotion_Study_'+args.generation+'.blend')
bpy.ops.wm.save_as_mainfile(filepath=str(output), compress=True)
report.update(output=str(output), outputSha256=sha(output), preservedMeshComponents=len(before_geometry),
              preservedBindBones=len(before_bind), geometryPreserved=True,
              idleRevised=True, engineExported=False)
if sha(args.source) != source_sha: raise AssertionError('Input master changed')
(args.output/'motion-study.json').write_text(json.dumps(report, indent=2)+'\n')
print('KRAG_KINGS_HUMAN_MOTION_STUDY_COMPLETE', flush=True)
