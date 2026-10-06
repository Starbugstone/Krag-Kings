"""Actual NullRHI editor/API and shared terrain import check; never rendering evidence."""
import json
import sys
from pathlib import Path
import unreal

script_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(script_dir))
import import_shared_assets as shared

report = {'engine': unreal.SystemLibrary.get_engine_version(), 'renderer': 'NullRHI', 'is_render_evidence': False}
report['native_variant_struct'] = type(unreal.KKCharacterVariant()).__name__
report['native_driver_struct'] = type(unreal.KKMorphDriver()).__name__
options = shared.mesh_options(True)
report['morph_import_enabled'] = options.get_editor_property('skeletal_mesh_import_data').get_editor_property('import_morph_targets')
report['custom_animation_attributes_enabled'] = options.get_editor_property('anim_sequence_import_data').get_editor_property('import_custom_attribute')
report['animation_scene_unit_conversion_enabled'] = options.get_editor_property('anim_sequence_import_data').get_editor_property('convert_scene_unit')
terrain_file = shared.SHARED / 'environment' / 'Dunes.fbx'
objects = shared.imported_task(terrain_file, shared.DEST + '/Environment', shared.mesh_options(False))
terrain = next(o for o in objects if isinstance(o, unreal.StaticMesh))
body = terrain.get_editor_property('body_setup')
body.set_editor_property('collision_trace_flag', unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
shared.save(terrain)
report['terrain_asset'] = terrain.get_path_name()
report['terrain_collision'] = str(body.get_editor_property('collision_trace_flag'))
environment = shared.SHARED / 'environment'
color = next(environment.rglob('Sand_BaseColor.png'))
sand = shared.material('Sand', color.parent, shared.DEST + '/Environment/Materials')
terrain.set_material(0, sand)
shared.save(terrain)
sounds, dust = shared.contact_assets()
report['sand_material'] = sand.get_path_name()
report['footstep_sound_counts'] = {name: len(waves) for name, waves in sounds.items()}
report['dust_material'] = dust.get_path_name()
report['weapon_flash_material'] = shared.weapon_flash_material().get_path_name()
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
unreal.EditorAssetLibrary.make_directory(shared.DEST + '/Maps')
map_path = shared.DEST + '/Maps/Dunes'
if not unreal.EditorAssetLibrary.does_asset_exist(map_path):
    if not levels.new_level(map_path):
        raise RuntimeError('Blank runtime level creation failed')
if not levels.save_current_level():
    raise RuntimeError('Runtime level save failed')
report['map_created'] = unreal.EditorAssetLibrary.does_asset_exist(map_path)
output = shared.BENCHMARK / 'unreal' / 'evidence' / 'editor-probe.json'
output.write_text(json.dumps(report, indent=2), encoding='utf-8')
unreal.log('KK_EDITOR_PROBE_COMPLETE ' + str(output))
