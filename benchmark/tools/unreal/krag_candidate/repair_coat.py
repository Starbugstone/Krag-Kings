"""Preserve three authored coat constants in a new, otherwise identical PBR copy.

Run only through a frozen guarded plan. The failed bake and its images remain
untouched; the 104 existing maps are copied byte for byte, never rebaked.
"""
import argparse
import copy
import json
from pathlib import Path
import shutil
import sys

import bpy

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(Path(__file__).parent))
from bake_runtime import integrity, image_inventory
from snapshot_source import sha
sys.path.insert(0, str(ROOT / 'benchmark/tools/nib/v5_wip/pbr'))
from bake_fields import principled
from portable_save import expected_maps, save_and_validate_pbr

SOCKETS = {'coatWeight': 'Coat Weight', 'coatRoughness': 'Coat Roughness', 'coatIor': 'Coat IOR'}


def constants(material):
    shader = principled(material)
    result = {}
    for field, name in SOCKETS.items():
        socket = shader.inputs[name]
        if socket.is_linked:
            raise RuntimeError('Cannot replace an authored coat field with a scalar: ' + material.name + '/' + name)
        result[field] = float(socket.default_value)
    if result['coatWeight'] > 0:
        if shader.inputs['Coat Normal'].is_linked:
            raise RuntimeError('A separate authored coat normal needs its own portable contract')
        tint = shader.inputs['Coat Tint']
        if tint.is_linked or tuple(tint.default_value) != (1.0, 1.0, 1.0, 1.0):
            raise RuntimeError('Tinted coat is outside this scalar-only correction')
    return result


def shader_signature(material):
    """Record graph/defaults except the three intentionally changed sockets."""
    nodes = []
    for node in material.node_tree.nodes:
        inputs = {}
        for socket in node.inputs:
            if node.type == 'BSDF_PRINCIPLED' and socket.name in SOCKETS.values():
                continue
            if hasattr(socket, 'default_value'):
                value = socket.default_value
                inputs[socket.identifier] = list(value) if hasattr(value, '__len__') and not isinstance(value, str) else value
        image = None
        if node.type == 'TEX_IMAGE' and node.image:
            path = Path(bpy.path.abspath(node.image.filepath, library=node.image.library))
            image = {'file': path.name, 'sha256': sha(path), 'colorSpace': node.image.colorspace_settings.name}
        nodes.append({'name': node.name, 'type': node.bl_idname, 'inputs': inputs, 'image': image})
    links = sorted((link.from_node.name, link.from_socket.identifier, link.to_node.name, link.to_socket.identifier)
                   for link in material.node_tree.links)
    return {'nodes': nodes, 'links': links}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--source-sha256', required=True)
    parser.add_argument('--pbr', type=Path, required=True)
    parser.add_argument('--pbr-sha256', required=True)
    parser.add_argument('--bake-report', type=Path, required=True)
    parser.add_argument('--contract', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    if args.out.exists() or sha(args.source) != args.source_sha256 or sha(args.pbr) != args.pbr_sha256:
        raise RuntimeError('Pinned source differs or isolated destination already exists')
    original_report = json.loads(args.bake_report.read_text())
    contract = json.loads(args.contract.read_text())
    if original_report['candidateSha256'] != args.pbr_sha256 or original_report['sourceSha256'] != args.source_sha256:
        raise RuntimeError('Bake provenance differs from the actual selected inputs')
    if contract['pbr_blend_sha256'] != args.pbr_sha256:
        raise RuntimeError('PBR selection contract differs')

    bpy.ops.wm.open_mainfile(filepath=str(args.source))
    authored = {entry['name']: constants(bpy.data.materials[entry['sourceMaterial']])
                for entry in original_report['materials']}
    bpy.ops.wm.open_mainfile(filepath=str(args.pbr))
    before = integrity(bpy.data.objects['Krag_Rig'])
    materials, _ = image_inventory()
    graph_before = {m.name: shader_signature(m) for m in materials}
    before_constants = {m.name: constants(m) for m in materials}
    if set(graph_before) != set(authored):
        raise RuntimeError('Assigned material inventory differs')
    changes = []
    for material in materials:
        values = authored[material.name]
        shader = principled(material)
        for field, socket in SOCKETS.items():
            old = float(shader.inputs[socket].default_value)
            shader.inputs[socket].default_value = values[field]
            if old != values[field]:
                changes.append({'material': material.name, 'socket': socket, 'before': old, 'after': values[field]})
    if not any(change['socket'] == 'Coat Weight' for change in changes):
        raise RuntimeError('Expected missing coat was not reproduced in the saved failed PBR')

    texture_dir = args.out / 'textures'
    texture_dir.mkdir(parents=True)
    maps = expected_maps(original_report)
    for filename, entry in maps.items():
        source = args.pbr.parent / 'textures' / filename
        if sha(source) != entry['sha256']:
            raise RuntimeError('Pinned baked map differs: ' + filename)
        shutil.copy2(source, texture_dir / filename)
    report = copy.deepcopy(original_report)
    report['preCoatCandidateSha256'] = args.pbr_sha256
    report['correction'] = {'kind': 'Authored scalar coat restoration only', 'changes': changes,
        'sourceConstants': authored, 'failedPbrConstants': before_constants,
        'mapFilesByteIdentical': len(maps), 'rebaked': False, 'artisticAcceptance': False}
    surface = {}
    for entry in report['materials']:
        values = authored[entry['name']]
        if values['coatWeight'] > 0:
            properties = {'hasCoatParameters': True, **values}
            entry.update(properties)
            surface[entry['name']] = properties
    target = args.out / 'Krag_Runtime_PBR.blend'
    report['savedImageValidation'] = save_and_validate_pbr(target, report, image_inventory=image_inventory)
    if integrity(bpy.data.objects['Krag_Rig']) != before:
        raise RuntimeError('Coat correction changed rig, geometry, fields, drivers or actions')
    materials, _ = image_inventory()
    if {m.name: shader_signature(m) for m in materials} != graph_before:
        raise RuntimeError('Coat correction changed another shader input, node, link or map')
    if {m.name: constants(m) for m in materials} != authored:
        raise RuntimeError('Saved coat constants no longer match the actual authored source')
    for filename, entry in maps.items():
        if sha(texture_dir / filename) != entry['sha256']:
            raise RuntimeError('Copied texture differs')
    report['candidateSha256'] = sha(target)
    report['correction'].update({'savedGraphExceptThreeCoatSocketsExact': True,
        'savedRigGeometryFieldsDriversActionsExact': True, 'savedAuthoredCoatConstantsExact': True})
    contract.update({'pbr_blend_sha256': report['candidateSha256'], 'material_surface': surface})
    (args.out / 'pbr-bake-report.json').write_text(json.dumps(report, indent=2) + '\n', newline='\n')
    (args.out / 'krag_asset_contract.json').write_text(json.dumps(contract, indent=2) + '\n', newline='\n')
    if sha(args.source) != args.source_sha256 or sha(args.pbr) != args.pbr_sha256:
        raise RuntimeError('Original source changed during correction')
    print('KRAG_COAT_REPAIR_COMPLETE', flush=True)


if __name__ == '__main__':
    main()
