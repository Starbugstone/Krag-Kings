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

parser = argparse.ArgumentParser()
parser.add_argument('--source', type=Path, required=True)
parser.add_argument('--species', choices=['Krag', 'Nib'], required=True)
parser.add_argument('--output', type=Path, required=True)
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
_, jog = acclaim_motion.load(data/'104.asf', data/'104_01.amc')
canonical = Matrix(acclaim_motion.CANONICAL)
source_directions = {name: canonical @ Vector(bone['direction']) for name, bone in asf['bones'].items()}


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


def retarget_rotations(quats):
    desired = {}
    for name, source in body_map.items():
        if name.startswith(('UpperArm', 'LowerArm', 'Thigh', 'Shin')):
            direction = quats[source] @ source_directions[source]
            # Preserve the existing anatomical rest roll while reproducing
            # measured human segment directions, independent of Euler axes.
            desired[name] = rest_directions[name].rotation_difference(direction) @ rest[name]
        else:
            desired[name] = quats[source] @ neutral[source].inverted() @ rest[name]
    for side in ['L', 'R']:
        for name, parent in [('Hand_'+side, 'LowerArm_'+side), ('Toe_'+side, 'Foot_'+side)]:
            if name in rest: desired[name] = desired[parent] @ rest[parent].inverted() @ rest[name]
    for name in body_names:
        bone = rig.pose.bones[name]
        bone.location = (0, 0, 0); bone.scale = (1, 1, 1)
        put_rotation(rig, name, desired[name], desired.get(bone.parent.name) if bone.parent else None)


def pose_body(quats, residual):
    retarget_rotations(quats)
    pelvis = rig.pose.bones['Pelvis']
    pelvis.location = pelvis.bone.matrix_local.to_3x3().inverted() @ (residual*leg_scale)
    bpy.context.view_layer.update()


def foot_clearance(side):
    bone = rig.pose.bones['Foot_'+side]
    delta = bone.matrix @ bone.bone.matrix_local.inverted()
    head = bone.bone.head_local
    toe = rig.data.bones['Toe_'+side].head_local if 'Toe_'+side in rig.data.bones else bone.bone.tail_local
    length = abs(toe.y-head.y)
    # Source ground is Z=0. Fixed boot-sole anchors are proposals to validate
    # against the actual boot and replacement meshes before promotion.
    anchors = [Vector((head.x, head.y+length*.35, 0)),
               Vector((toe.x, toe.y, 0))]
    return min((delta @ p).z for p in anchors)


def fixed_idle_feet():
    """Soft-kneed weight shift over stationary feet; no root skating."""
    errors = []
    for side in ['L', 'R']:
        upper, lower, foot = [rig.pose.bones[name+'_'+side] for name in ['Thigh', 'Shin', 'Foot']]
        hip = upper.head.copy(); target = foot.bone.head_local.copy()
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


for clip, samples, first, last, frames in [
        ('Walk', walk, 212, 360, 30 if args.species == 'Krag' else 24),
        ('Run', jog, 91, 191, 24 if args.species == 'Krag' else 18)]:
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
        pose_body(quats, residual)
        poses.append({'quats': quats, 'residual': residual,
                      'clearance': min(foot_clearance('L'), foot_clearance('R'))})
    # Preserve measured flight-height variation while removing sole penetration.
    # The constant offset is derived from the lowest retargeted sole, not a
    # forced deep knee bend. A later contact-fit pass must assess sliding.
    ground_offset = -min(p['clearance'] for p in poses)
    evidence = []
    for index, pose in enumerate(poses):
        scene.frame_set(index+1)
        residual = pose['residual'].copy(); residual.z += ground_offset/leg_scale
        pose_body(pose['quats'], residual)
        for name in body_names:
            bone = rig.pose.bones[name]
            for channel in ['location', 'rotation_euler', 'scale']:
                bone.keyframe_insert(channel, frame=index+1, group=name)
        evidence.append({'frame': index+1,
                         'joints': {name: {'head': list(rig.pose.bones[name].head),
                                           'tail': list(rig.pose.bones[name].tail)}
                                    for name in body_names},
                         'soleClearance': {side: foot_clearance(side) for side in ['L', 'R']}})
    for curve in bag.fcurves:
        if any(curve.data_path.startswith(rig.pose.bones[name].path_from_id()+'.') for name in body_names):
            for key in curve.keyframe_points: key.interpolation = 'LINEAR'
    action['clip_duration_seconds'] = frames/30
    action['motion_source'] = 'CMU 104_02' if clip == 'Walk' else 'CMU 104_01'
    start, end = Vector(samples[first-1]['heads']['root']), Vector(samples[last-1]['heads']['root'])
    proposal_speed = Vector((end.x-start.x, end.y-start.y, 0)).length*leg_scale/(frames/30)
    report['clips'][clip] = {'frames': frames, 'durationSeconds': frames/30,
                             'sourceFrames': [first, last], 'sourceFps': 120,
                             'proposedSpeedMetersPerSecond': proposal_speed,
                             'groundOffsetMeters': ground_offset,
                             'contactFitAccepted': False, 'samples': evidence}

# A restrained six-second standing performance. Body shape, facial controls and
# the weapon grip are retained. Species differences remain tuning proposals.
original = bpy.data.actions['Idle']; action = original.copy()
original.name = 'Preserved_Idle_BeforeHumanMotion'; action.name = 'Idle'; action.use_fake_user = True
rig.animation_data.action = action; bag = remove_body_curves(action, rig.animation_data.action_slot)
old_start, old_end = original.frame_range
for curve in bag.fcurves:
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

for name, visibility in mesh_visibility.items(): bpy.data.objects[name].hide_viewport = visibility
rig.animation_data.action = bpy.data.actions['Walk']; scene.frame_set(1)
if geometry_digest() != before_geometry: raise AssertionError('Motion study changed mesh/shape coordinates')
if before_bind != {b.name: [list(row) for row in b.matrix_local] for b in rig.data.bones}:
    raise AssertionError('Motion study changed source bind skeleton')
output = args.output/(args.species+'_HumanMotion_Study_v1.blend')
bpy.ops.wm.save_as_mainfile(filepath=str(output), compress=True)
report.update(output=str(output), outputSha256=sha(output), preservedMeshComponents=len(before_geometry),
              preservedBindBones=len(before_bind), geometryPreserved=True,
              idleRevised=True, engineExported=False)
if sha(args.source) != source_sha: raise AssertionError('Input master changed')
(args.output/'motion-study.json').write_text(json.dumps(report, indent=2)+'\n')
print('KRAG_KINGS_HUMAN_MOTION_STUDY_COMPLETE', flush=True)
