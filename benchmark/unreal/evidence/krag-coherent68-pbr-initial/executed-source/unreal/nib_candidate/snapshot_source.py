"""Read-only exact source/PBR contracts plus 17 skeletal samples per take.

This uses the same disposable neutral-channel completion as the production FBX
exporter. It does not save the source, bake materials, or establish artistic fit.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import bpy
import numpy as np
from bpy_extras.anim_utils import action_get_channelbag_for_slot

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'benchmark/tools/animation'))
import export_contract


def sha(path):
    # Large source/FBX files must not allocate a second full payload just to hash.
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def action_hash(rig, action):
    export_contract.select_action(bpy, rig, action)
    bag = action_get_channelbag_for_slot(action, rig.animation_data.action_slot)
    if bag is None:
        raise RuntimeError('No object channel bag: ' + action.name)
    curves = [(c.data_path, c.array_index, c.extrapolation,
               [(tuple(k.co), tuple(k.handle_left), tuple(k.handle_right),
                 k.interpolation, k.handle_left_type, k.handle_right_type,
                 k.easing, k.amplitude, k.back, k.period) for k in c.keyframe_points])
              for c in bag.fcurves]
    return hashlib.sha256(json.dumps({'frameRange': list(action.frame_range),
        'curves': sorted(curves)}, separators=(',', ':')).encode()).hexdigest()


def geometry_hash(obj):
    """Exclude UV/material changes required by PBR; retain all deformation data."""
    h = hashlib.sha256()
    mesh = obj.data
    values = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
    mesh.vertices.foreach_get('co', values)
    h.update(values.tobytes())
    for key in mesh.shape_keys.key_blocks if mesh.shape_keys else []:
        key.data.foreach_get('co', values)
        h.update(key.name.encode()); h.update(values.tobytes())
    payload = {'faces': [list(p.vertices) for p in mesh.polygons],
        'groups': [g.name for g in obj.vertex_groups],
        'weights': [[(g.group, g.weight) for g in v.groups] for v in mesh.vertices],
        'basis': [list(row) for row in obj.matrix_basis],
        'parentInverse': [list(row) for row in obj.matrix_parent_inverse],
        'parent': obj.parent.name if obj.parent else None,
        'parentType': obj.parent_type, 'parentBone': obj.parent_bone,
        'variant': obj.get('variant', 'all'), 'region': obj.get('bone', '')}
    h.update(json.dumps(payload, separators=(',', ':')).encode())
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--source-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--compare', type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    if sha(args.source) != args.source_sha256:
        raise RuntimeError('Pinned source has changed')
    if args.output.exists():
        raise RuntimeError('Preserve prior source snapshot')
    bpy.ops.wm.open_mainfile(filepath=str(args.source))
    scene = bpy.context.scene
    rig = bpy.data.objects['Nib_Rig']
    if len(rig.data.bones) != 79:
        raise RuntimeError('Expected full coherent 79-bone rig')
    required = {'Hand_L':'ForearmTwist_L', 'Hand_R':'ForearmTwist_R',
                'ForearmTwist_L':'LowerArm_L', 'ForearmTwist_R':'LowerArm_R',
                'EarTip_L':'Ear_L', 'EarTip_R':'Ear_R'}
    parents = {b.name: b.parent.name if b.parent else None for b in rig.data.bones}
    if any(parents.get(name) != parent for name, parent in required.items()):
        raise RuntimeError('Expanded hierarchy contract differs')
    actions = {name: action_hash(rig, bpy.data.actions[name]) for name in export_contract.CLIPS}
    rest = {b.name: (rig.matrix_world @ b.matrix_local).copy() for b in rig.data.bones}
    source_bones = {b.name: {'matrix': [list(row) for row in b.matrix_local],
        'parent': parents[b.name], 'connected': b.use_connect,
        'rotationMode': rig.pose.bones[b.name].rotation_mode} for b in rig.data.bones}
    geometry = {o.name: geometry_hash(o) for o in
        bpy.data.collections['Nib_Authored_Components'].objects if o.type == 'MESH'}
    report = {'source': str(args.source), 'sourceSha256': args.source_sha256,
        'recipeSha256': sha(__file__), 'actionContractRecipeSha256': sha(export_contract.__file__),
        'rig': {'world': [list(row) for row in rig.matrix_world], 'bones': source_bones,
                'actions': actions}, 'geometryWeightsMorphs': geometry,
        'bones': list(rest), 'sourceParents': parents,
        'sourceConnected': {b.name: b.use_connect for b in rig.data.bones},
        'sourceRest': {name: [list(row) for row in m] for name, m in rest.items()},
        'groomMaterials': json.loads(scene.get('nib_groom_material_contract', '[]')),
        'deformation': json.loads(scene['deformation_contract']),
        'clips': {}, 'artisticAcceptance': False, 'sharedAssetsChanged': False}
    if args.compare:
        original = json.loads(args.compare.read_text())
        for key in ['rig', 'geometryWeightsMorphs', 'groomMaterials', 'deformation']:
            if report[key] != original[key]:
                raise RuntimeError('PBR preparation changed ' + key)
        report['comparedSourceSnapshotSha256'] = sha(args.compare)
        report['pbrRetainsRigActionsGeometryWeightsMorphs'] = True
    locomotion, contract = export_contract.prepare(bpy, json.loads(scene['locomotion_contract']))
    report['locomotion'] = locomotion; report['actionContract'] = contract
    if rig.animation_data:
        for track in rig.animation_data.nla_tracks:
            track.mute = True
    fps = scene.render.fps / scene.render.fps_base
    for name in export_contract.CLIPS:
        action = bpy.data.actions[name]
        export_contract.select_action(bpy, rig, action)
        first, last = (int(v) for v in action.frame_range)
        samples = []
        for index in range(17):
            frame = round(first + (last - first) * index / 16)
            scene.frame_set(frame); bpy.context.view_layer.update()
            joints = {}
            for bone in rig.pose.bones:
                world = rig.matrix_world @ bone.matrix
                joints[bone.name] = {'head': list(world.translation),
                    'worldScale': list(world.to_scale()),
                    'deformationQuaternion': list((world @ rest[bone.name].inverted()).to_quaternion())}
            samples.append({'frame': frame, 'bones': joints})
        report['clips'][name] = {'frameRange': [first, last], 'fps': fps, 'sourceSamples': samples}
    if sha(args.source) != args.source_sha256:
        raise RuntimeError('Read-only snapshot changed source')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n', newline='\n')
    print('NIB_COHERENT_SOURCE_SNAPSHOT_COMPLETE', flush=True)


if __name__ == '__main__':
    main()
