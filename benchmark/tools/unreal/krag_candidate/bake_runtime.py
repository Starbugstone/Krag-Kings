"""Bake the actual module surfaces; preserve the source rig/actions and point data.

Per-module atlases preserve object-space skin/detail fields. Material slots keep
their original skin/metal role while sharing that module's packed UV maps.
This never edits the authored source or the currently shared assets.
"""
import argparse
import json
from pathlib import Path
import sys

import bpy

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(Path(__file__).parent))
from snapshot_source import sha, action_hash, geometry_hash, authored_fields, driver_contract
sys.path.insert(0, str(ROOT/'benchmark/tools/nib/v5_wip/pbr'))
from bake_fields import make_face_uv, bake_maps, portable_material
from portable_save import save_and_validate_pbr


def modules():
    return {o['module']: o for o in bpy.data.objects if o.type == 'MESH' and 'module' in o}


def image_inventory():
    materials = {m for obj in modules().values() for m in obj.data.materials if m}
    images = {n.image for m in materials if m.use_nodes for n in m.node_tree.nodes
              if n.type == 'TEX_IMAGE' and n.image}
    return materials, images


def integrity(rig):
    from export_contract import CLIPS
    return {'geometry': {n: geometry_hash(o) for n, o in modules().items()},
        'fields': {n: authored_fields(o) for n, o in modules().items()},
        'drivers': {n: driver_contract(o.data.shape_keys) for n, o in modules().items() if o.data.shape_keys},
        'actions': {name: action_hash(rig, bpy.data.actions[name]) for name in CLIPS},
        'bind': {b.name: {'matrix': [list(r) for r in b.matrix_local],
                        'parent': b.parent.name if b.parent else None, 'connected': b.use_connect}
                 for b in rig.data.bones}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--source-sha256', required=True)
    parser.add_argument('--selection-contract', type=Path, required=True)
    parser.add_argument('--source-contract', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    if sha(args.source) != args.source_sha256 or args.out.exists():
        raise RuntimeError('Pinned source changed or candidate output already exists')
    contract = json.loads(args.selection_contract.read_text())
    snapshot = json.loads(args.source_contract.read_text())
    if contract['source_blend_sha256'] != args.source_sha256:
        raise RuntimeError('Selection contract does not describe the actual source')
    if snapshot['sourceSha256'] != args.source_sha256 or snapshot['selectionContractSha256'] != sha(args.selection_contract):
        raise RuntimeError('Source snapshot does not match this candidate')
    def verify_images():
        for entry in snapshot['connectedSourceImages']:
            if entry['storage'] == 'file' and sha(Path(entry['path'])) != entry['sha256']:
                raise RuntimeError('Assigned source image changed: '+entry['name'])
    verify_images()
    bpy.ops.wm.open_mainfile(filepath=str(args.source))
    rig = bpy.data.objects['Krag_Rig']; scene = bpy.context.scene
    if set(modules()) != set(contract['modules']) or len(rig.data.bones) != 68:
        raise RuntimeError('Actual module/rig inventory differs')
    original = integrity(rig)
    target = args.out/'Krag_Runtime_PBR.blend'; textures = args.out/'textures'
    textures.mkdir(parents=True)
    visibility = {o.name: o.hide_render for o in bpy.data.objects}
    for obj in bpy.data.objects:
        if obj.type == 'MESH': obj.hide_render = True
    materials = []; material_maps = {}; module_reports = []
    for name, obj in sorted(modules().items()):
        active_modifiers = [m.name for m in obj.modifiers
                            if m.type != 'ARMATURE' and (m.show_render or m.show_viewport)]
        if active_modifiers:
            raise RuntimeError('Unresolved evaluated geometry on '+name+': '+str(active_modifiers))
        original_slots = list(obj.data.materials)
        if not original_slots or None in original_slots:
            raise RuntimeError('Missing source material slots on '+name)
        # Shader UV remapping must not mutate other modules' shared materials.
        private = {m: m.copy() for m in set(original_slots)}
        for index, material in enumerate(original_slots): obj.data.materials[index] = private[material]
        source_uv = make_face_uv(obj)
        size = 4096 if name == 'Head' else (2048 if any('Skin' in m.name for m in original_slots) or name == 'Face' else 1024)
        atlas = 'Krag_'+name+'_SurfaceAtlas'
        maps = bake_maps(obj, atlas, textures,
                         {'BaseColor': size, 'Normal': size, 'Roughness': 1024, 'Metallic': 1024})
        generated = {}
        for material in dict.fromkeys(original_slots):
            material_name = material.name+'_'+name+'_Atlas'
            if bpy.data.materials.get(material_name):
                raise RuntimeError('Candidate material name already exists: '+material_name)
            generated[material] = portable_material(material_name, textures, maps, private[material])
            material_maps[material_name] = {channel: entry['file'] for channel, entry in maps.items()}
            material_entry = {'name': material_name,
                **{key: 'textures/'+maps[channel]['file'] for key, channel in
                   [('baseColor','BaseColor'),('normal','Normal'),('roughness','Roughness'),('metallic','Metallic')]},
                'mapHashes': {key: maps[channel]['sha256'] for key, channel in
                   [('baseColor','BaseColor'),('normal','Normal'),('roughness','Roughness'),('metallic','Metallic')]},
                'sourceMaterial': material.name, 'sourceModule': name}
            materials.append(material_entry)
        for index, material in enumerate(original_slots): obj.data.materials[index] = generated[material]
        # The authored .blend retains the old sampling UVs. Remove that layer
        # from this derivative after baking so FBX UV0 is the packed atlas.
        obj.data.uv_layers.remove(obj.data.uv_layers[source_uv])
        obj.data.uv_layers.active = obj.data.uv_layers['UVMap']
        obj.data.uv_layers.active.active_render = True
        obj['runtime_uv_atlas'] = True
        obj.hide_render = True; obj.select_set(False)
        module_reports.append({'module': name, 'sourceSamplingUvDuringBake': source_uv,
                               'sourceUvRemovedAfterBakeForPackedExportUv0': True, 'maps': maps,
                               'materials': [generated[m].name for m in original_slots]})
        print('KRAG_SURFACE_ATLAS_COMPLETE '+name, flush=True)
    for obj in bpy.data.objects:
        if obj.name in visibility: obj.hide_render = visibility[obj.name]
    from export_contract import CLIPS, select_action
    select_action(bpy, rig, bpy.data.actions['Idle']); scene.frame_set(1)
    if integrity(rig) != original: raise RuntimeError('PBR preparation changed authored deformation data')
    report = {'source': str(args.source), 'sourceSha256': args.source_sha256,
        'selectionContractSha256': sha(args.selection_contract), 'materials': materials,
        'modules': module_reports, 'rigActionsGeometryWeightsMorphsUnchanged': True,
        'method': 'Actual per-module surface atlases; original material roles retained',
        'artisticAcceptance': False, 'sharedAssetsChanged': False}
    report['savedImageValidation'] = save_and_validate_pbr(target, report, image_inventory=image_inventory)
    rig = bpy.data.objects['Krag_Rig']
    if integrity(rig) != original: raise RuntimeError('Reopened PBR lost source deformation data')
    if sha(args.source) != args.source_sha256: raise RuntimeError('Authored source was modified')
    verify_images()
    report['candidateSha256'] = sha(target)
    contract.update({'source_blend_sha256': args.source_sha256, 'pbr_blend_sha256': report['candidateSha256'],
                     'source': str(args.source), 'material_maps': material_maps, 'materials': list(material_maps),
                     'locomotionCycles': json.loads(bpy.context.scene['locomotion_contract']),
                     'clips': CLIPS, 'bone_count': len(rig.data.bones)})
    (args.out/'krag_asset_contract.json').write_text(json.dumps(contract, indent=2)+'\n', newline='\n')
    (args.out/'pbr-bake-report.json').write_text(json.dumps(report, indent=2)+'\n', newline='\n')
    print('KRAG_COHERENT_PBR_BAKE_COMPLETE', flush=True)


if __name__ == '__main__': main()
