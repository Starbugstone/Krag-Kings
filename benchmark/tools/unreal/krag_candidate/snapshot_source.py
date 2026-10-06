"""Read-only coherent68 source/PBR rig, geometry and sampled-pose contract."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import bpy

ROOT = Path(__file__).resolve().parents[4]
spec = importlib.util.spec_from_file_location('nib_snapshot_helpers', Path(__file__).parents[1]/'nib_candidate/snapshot_source.py')
common = importlib.util.module_from_spec(spec); spec.loader.exec_module(common)
sha, action_hash, geometry_hash = common.sha, common.action_hash, common.geometry_hash
export_contract = common.export_contract
sys.path.insert(0, str(ROOT/'benchmark/tools/animation/krag_hand_rebuild'))
from morph_drivers import contract as driver_contract


def authored_fields(obj):
    result = {}
    for attr in obj.data.attributes:
        if not attr.name.startswith('Krag_') or attr.domain != 'POINT': continue
        if attr.data_type not in ('FLOAT', 'FLOAT_VECTOR'):
            raise RuntimeError('Unsupported authored point field: '+attr.name)
        width = 3 if attr.data_type == 'FLOAT_VECTOR' else 1
        values = common.np.empty(len(attr.data)*width, dtype=common.np.float32)
        attr.data.foreach_get('vector' if width == 3 else 'value', values)
        result[attr.name] = {'type': attr.data_type, 'sha256': hashlib.sha256(values.tobytes()).hexdigest()}
    return result


def source_images(objects):
    images, visited = set(), set()
    def visit(tree):
        if tree is None or tree.as_pointer() in visited: return
        visited.add(tree.as_pointer())
        for node in tree.nodes:
            if node.type == 'TEX_IMAGE' and node.image: images.add(node.image)
            if node.type == 'GROUP': visit(node.node_tree)
    for obj in objects:
        for material in obj.data.materials:
            if material and material.use_nodes: visit(material.node_tree)
    result = []
    for image in sorted(images, key=lambda item: item.name):
        if image.packed_file:
            value = {'storage': 'packed', 'sha256': hashlib.sha256(image.packed_file.data).hexdigest()}
        else:
            path = Path(bpy.path.abspath(image.filepath, library=image.library)).resolve()
            if image.source != 'FILE' or not path.is_file():
                raise RuntimeError('Unresolved assigned source image: '+image.name)
            value = {'storage': 'file', 'path': str(path), 'sha256': sha(path)}
        result.append({'name': image.name, 'colorSpace': image.colorspace_settings.name, **value})
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--source-sha256', required=True)
    parser.add_argument('--selection-contract', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--compare', type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    if sha(args.source) != args.source_sha256 or args.output.exists():
        raise RuntimeError('Source changed or snapshot already exists')
    selection = json.loads(args.selection_contract.read_text())
    bpy.ops.wm.open_mainfile(filepath=str(args.source))
    scene = bpy.context.scene; rig = bpy.data.objects['Krag_Rig']
    modules = {o['module']: o for o in bpy.data.objects if o.type == 'MESH' and 'module' in o}
    if set(modules) != set(selection['modules']):
        raise RuntimeError('Actual module inventory differs from pinned current selection')
    if len(rig.data.bones) != 68 or set(rig.data.bones.keys()) != set(selection['bones']):
        raise RuntimeError('Current full68 bind inventory differs')
    parents = {b.name: b.parent.name if b.parent else None for b in rig.data.bones}
    rest = {b.name: (rig.matrix_world @ b.matrix_local).copy() for b in rig.data.bones}
    actions = {name: action_hash(rig, bpy.data.actions[name]) for name in export_contract.CLIPS}
    geometry = {name: geometry_hash(obj) for name, obj in modules.items()}
    bones = {b.name: {'matrix': [list(row) for row in b.matrix_local],
        'parent': parents[b.name], 'connected': b.use_connect,
        'rotationMode': rig.pose.bones[b.name].rotation_mode} for b in rig.data.bones}
    fields = {name: authored_fields(obj) for name, obj in modules.items()}
    drivers = {name: driver_contract(obj.data.shape_keys) for name, obj in modules.items()
               if obj.data.shape_keys}
    if 'Krag_SkinRegion' not in fields['Head'] or 'Krag_IrisCoord' not in fields['Face']:
        raise RuntimeError('Missing authored skin/ocular fields')
    report = {'source': str(args.source), 'sourceSha256': args.source_sha256,
        'selectionContractSha256': sha(args.selection_contract),
        'rig': {'world': [list(row) for row in rig.matrix_world], 'bones': bones, 'actions': actions},
        'geometryWeightsMorphs': geometry, 'bones': list(rest), 'sourceParents': parents,
        'sourceConnected': {b.name: b.use_connect for b in rig.data.bones},
        'sourceRest': {n: [list(row) for row in m] for n, m in rest.items()},
        'deformation': selection['deformation'], 'modules': list(modules), 'fields': fields,
        'correctiveDriverContracts': drivers,
        'connectedSourceImages': source_images(modules.values()),
        'materialsByModule': {n: [m.name for m in o.data.materials] for n, o in modules.items()},
        'clips': {}, 'artisticAcceptance': False, 'sharedAssetsChanged': False}
    if args.compare:
        original = json.loads(args.compare.read_text())
        for key in ['rig', 'geometryWeightsMorphs', 'deformation', 'modules', 'fields', 'correctiveDriverContracts']:
            if report[key] != original[key]:
                raise RuntimeError('PBR preparation changed ' + key)
        report['pbrRetainsRigActionsGeometryWeightsMorphs'] = True
        report['comparedSourceSnapshotSha256'] = sha(args.compare)
    locomotion, action_report = export_contract.prepare(bpy, selection['locomotionCycles'])
    report['locomotion'] = locomotion; report['actionContract'] = action_report
    for track in rig.animation_data.nla_tracks: track.mute = True
    fps = scene.render.fps / scene.render.fps_base
    for name in export_contract.CLIPS:
        action = bpy.data.actions[name]; export_contract.select_action(bpy, rig, action)
        first, last = map(int, action.frame_range); samples = []
        for index in range(17):
            frame = round(first+(last-first)*index/16)
            scene.frame_set(frame); bpy.context.view_layer.update()
            joints = {}
            for bone in rig.pose.bones:
                world = rig.matrix_world @ bone.matrix
                joints[bone.name] = {'head': list(world.translation), 'worldScale': list(world.to_scale()),
                    'deformationQuaternion': list((world @ rest[bone.name].inverted()).to_quaternion())}
            samples.append({'frame': frame, 'bones': joints})
        report['clips'][name] = {'frameRange': [first, last], 'fps': fps, 'sourceSamples': samples}
    if sha(args.source) != args.source_sha256: raise RuntimeError('Read-only snapshot changed source')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2)+'\n', newline='\n')
    print('KRAG_COHERENT_SOURCE_SNAPSHOT_COMPLETE', flush=True)


if __name__ == '__main__': main()
