"""Import the shared FBX/PBR benchmark assets in the real Unreal Editor.
Run after compiling KragKingsBenchmarkEditor, via build_demo.ps1 -Stage Import.
Fails on absent meshes, materials, clips, map save or data asset creation.
"""
import gc
import hashlib
import json
import re
from pathlib import Path
import unreal

PROJECT = Path(unreal.Paths.project_dir()).resolve()
BENCHMARK = PROJECT.parents[1]
SHARED = BENCHMARK / 'shared'
DEST = '/Game/Benchmark'
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
REPORT = {'engine': unreal.SystemLibrary.get_engine_version(), 'meshes': [], 'materials': [], 'warnings': []}
REPORT['import_resource_controls'] = {'requestedLogicalCoreLimit': 2 if '-corelimit=2' in unreal.SystemLibrary.get_command_line().lower() else None,
                                      'renderer': 'NullRHI' if '-nullrhi' in unreal.SystemLibrary.get_command_line().lower() else 'enabled',
                                      'scope': 'Importer process only; runtime/performance jobs are unchanged'}
CLIPS = ('Idle', 'Walk', 'Run', 'Melee', 'Shoot', 'Hit')
FACIAL_CLIPS = ('FacePerformance',)
REUSE_MATERIALS = '-KKReuseMaterials' in unreal.SystemLibrary.get_command_line()
CACHE_FILE = BENCHMARK / 'local' / 'unreal-material-cache.json'
MATERIAL_CACHE = json.loads(CACHE_FILE.read_text(encoding='utf-8')) if CACHE_FILE.exists() else {}
SOURCE_SNAPSHOT = {}
RECEIPT_DIR = BENCHMARK / 'local' / 'unreal-variant-cache'
VARIANT_RECIPE = 'skeletal-v2-explicit-dependencies-casefold-tracks'


def option(name):
    match = re.search(r'(?:^|\s)-' + re.escape(name) + r'=([^\s"]+)', unreal.SystemLibrary.get_command_line(), re.IGNORECASE)
    return match.group(1) if match else None


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def source_snapshot():
    # Record actual portable inputs before any import; generated engine assets are separate.
    extensions = {'.fbx', '.png', '.json', '.wav'}
    return {str(path.relative_to(SHARED)).replace('\\', '/'): {
        'sha256': sha256(path), 'bytes': path.stat().st_size,
    } for path in sorted(SHARED.rglob('*')) if path.is_file() and path.suffix.lower() in extensions}


def package_snapshot(folder, variant_name):
    directory = PROJECT / 'Content' / 'Benchmark' / 'Characters' / folder / variant_name
    return {str(p.relative_to(PROJECT)).replace('\\', '/'): {'sha256': sha256(p), 'bytes': p.stat().st_size}
            for p in sorted(directory.rglob('*.uasset'))}


def character_inputs(folder):
    prefix = 'characters/' + folder + '/'
    return {key: value for key, value in SOURCE_SNAPSHOT.items() if key.startswith(prefix)}


def write_variant_receipt(folder, descriptor, validation):
    name = descriptor['id']
    packages = package_snapshot(folder, name)
    if len(packages) < 10:
        raise RuntimeError(f'{name}: expected saved mesh, Skeleton, PhysicsAsset and seven clips')
    receipt = {'schemaVersion': 1, 'recipe': VARIANT_RECIPE, 'engine': REPORT['engine'],
               'folder': folder, 'variant': name, 'characterInputs': character_inputs(folder),
               'packages': packages, 'descriptor': descriptor, 'validation': validation,
               'rendered': False, 'artisticallyAccepted': False}
    RECEIPT_DIR.mkdir(parents=True, exist_ok=True)
    output = RECEIPT_DIR / (name + '.json')
    temporary = output.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    temporary.replace(output)


def read_variant_receipt(folder, name):
    path = RECEIPT_DIR / (name + '.json')
    if not path.exists():
        raise RuntimeError('Missing validated variant receipt: ' + str(path))
    receipt = json.loads(path.read_text(encoding='utf-8'))
    if receipt.get('variant') != name or receipt.get('folder') != folder or receipt.get('descriptor', {}).get('id') != name:
        raise RuntimeError(name + ': receipt identity mismatch')
    if receipt.get('recipe') != VARIANT_RECIPE or receipt.get('engine') != REPORT['engine']:
        raise RuntimeError(name + ': importer recipe or engine changed; validate/reimport before assembly')
    if receipt['characterInputs'] != character_inputs(folder):
        raise RuntimeError(name + ': shared character inputs changed after validation')
    if receipt['packages'] != package_snapshot(folder, name):
        raise RuntimeError(name + ': generated packages changed after validation')
    return receipt


def cache_material(asset_path, signature, provenance):
    MATERIAL_CACHE[asset_path] = {'signature': signature, 'provenance': provenance}
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = CACHE_FILE.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(MATERIAL_CACHE, indent=2), encoding='utf-8')
    temporary.replace(CACHE_FILE)


def material_signature(name, tex_dir):
    # Bump the recipe when shader wiring or sampling changes.
    inputs = {'recipe': 'pbr-v1-opengl-normal-subsurface', 'name': name, 'textures': {}}
    for kind in ('BaseColor', 'Normal', 'Roughness', 'Metallic'):
        path = tex_dir / (name + '_' + kind + '.png')
        if path.exists():
            inputs['textures'][kind] = sha256(path)
    return hashlib.sha256(json.dumps(inputs, sort_keys=True).encode('utf-8')).hexdigest()


def load(path):
    return unreal.EditorAssetLibrary.load_asset(path)


def save(obj):
    if not unreal.EditorAssetLibrary.save_loaded_asset(obj, only_if_is_dirty=False):
        raise RuntimeError('Could not save ' + obj.get_path_name())


def imported_task(filename, destination, options=None):
    task = unreal.AssetImportTask()
    task.set_editor_property('filename', str(filename))
    task.set_editor_property('destination_path', destination)
    task.set_editor_property('automated', True)
    task.set_editor_property('replace_existing', True)
    task.set_editor_property('save', True)
    if options is not None:
        task.set_editor_property('options', options)
        task.set_editor_property('factory', unreal.FbxFactory())
    TOOLS.import_asset_tasks([task])
    paths = task.get_editor_property('imported_object_paths')
    if not paths:
        raise RuntimeError('Import produced no assets: ' + str(filename))
    return [asset for path in paths if (asset := load(path)) is not None]


def texture(path, destination, kind):
    if not path.exists():
        raise RuntimeError('Required PBR texture missing: ' + str(path))
    objs = imported_task(path, destination)
    tex = next((o for o in objs if isinstance(o, unreal.Texture2D)), None)
    if tex is None:
        raise RuntimeError('Texture import failed: ' + str(path))
    tex.set_editor_property('srgb', kind == 'BaseColor')
    if kind == 'Normal':
        tex.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_NORMALMAP)
        # Shared maps use Blender/OpenGL +Y tangent normals. Unreal expects -Y.
        tex.set_editor_property('flip_green_channel', True)
    elif kind in ('Roughness', 'Metallic'):
        tex.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_MASKS)
    save(tex)
    return tex


def expression(mat, cls, x=0, y=0):
    return unreal.MaterialEditingLibrary.create_material_expression(mat, cls, x, y)


def connect(mat, node, output, prop):
    if not unreal.MaterialEditingLibrary.connect_material_property(node, output, prop):
        raise RuntimeError('Material connection failed: ' + mat.get_name() + ' ' + str(prop))


def weapon_flash_material():
    destination = DEST + '/Effects'
    mat = load(destination + '/M_WeaponFlash')
    if mat is None:
        mat = TOOLS.create_asset('M_WeaponFlash', destination, unreal.Material, unreal.MaterialFactoryNew())
    unreal.MaterialEditingLibrary.delete_all_material_expressions(mat)
    mat.set_editor_property('blend_mode', unreal.BlendMode.BLEND_ADDITIVE)
    mat.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
    color = expression(mat, unreal.MaterialExpressionConstant3Vector, -400, 0)
    # Physical daylight exposure EV~12.7 needs luminance-scale emission.
    color.set_editor_property('constant', unreal.LinearColor(100000.0, 40000.0, 6500.0, 1))
    connect(mat, color, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    fade = expression(mat, unreal.MaterialExpressionScalarParameter, -400, 180)
    fade.set_editor_property('parameter_name', 'Intensity')
    fade.set_editor_property('default_value', 1.0)
    connect(mat, fade, '', unreal.MaterialProperty.MP_OPACITY)
    unreal.MaterialEditingLibrary.recompile_material(mat)
    save(mat)
    return mat


def material(name, tex_dir, destination):
    asset_path = destination + '/M_' + name
    mat = load(asset_path)
    signature = material_signature(name, tex_dir)
    cached = MATERIAL_CACHE.get(asset_path, {})
    if mat is not None and cached.get('signature') == signature:
        REPORT.setdefault('reused_materials', []).append({'asset': asset_path, 'signature': signature, 'reason': 'matching input/recipe hash'})
        REPORT['materials'].append(mat.get_path_name())
        return mat
    if mat is not None and REUSE_MATERIALS and not cached:
        # Explicit one-time recovery of materials saved during the pinned failed import.
        # Later imports require matching content hashes and do not rely on this flag.
        cache_material(asset_path, signature, 'seeded from explicitly pinned prior import')
        REPORT.setdefault('reused_materials', []).append({'asset': asset_path, 'signature': signature, 'reason': 'explicit pinned prior import seed'})
        REPORT['materials'].append(mat.get_path_name())
        return mat
    if mat is None:
        mat = TOOLS.create_asset('M_' + name, destination, unreal.Material, unreal.MaterialFactoryNew())
    unreal.MaterialEditingLibrary.delete_all_material_expressions(mat)
    props = {
        'BaseColor': unreal.MaterialProperty.MP_BASE_COLOR,
        'Normal': unreal.MaterialProperty.MP_NORMAL,
        'Roughness': unreal.MaterialProperty.MP_ROUGHNESS,
        'Metallic': unreal.MaterialProperty.MP_METALLIC,
    }
    for i, (kind, prop) in enumerate(props.items()):
        source = tex_dir / (name + '_' + kind + '.png')
        if kind == 'Metallic' and not source.exists() and name.lower() == 'sand':
            node = expression(mat, unreal.MaterialExpressionConstant, -400, i * 180)
            node.set_editor_property('r', 0.0)
            connect(mat, node, '', prop)
            continue
        tex = texture(source, destination + '/Textures', kind)
        node = expression(mat, unreal.MaterialExpressionTextureSample, -400, i * 180)
        node.set_editor_property('texture', tex)
        node.set_editor_property('sampler_type', unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL if kind == 'Normal' else unreal.MaterialSamplerType.SAMPLERTYPE_COLOR if kind == 'BaseColor' else unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
        connect(mat, node, 'RGB' if kind in ('BaseColor', 'Normal') else 'R', prop)
    if any(word in name.lower() for word in ('skin', 'muzzle', 'earinner')):
        mat.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_SUBSURFACE)
        scatter = expression(mat, unreal.MaterialExpressionConstant3Vector, -400, 800)
        scatter.set_editor_property('constant', unreal.LinearColor(0.28, 0.15, 0.075, 1))
        connect(mat, scatter, '', unreal.MaterialProperty.MP_SUBSURFACE_COLOR)
        strength = expression(mat, unreal.MaterialExpressionConstant, -400, 980)
        strength.set_editor_property('r', 0.22)
        connect(mat, strength, '', unreal.MaterialProperty.MP_OPACITY)
    else:
        mat.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_DEFAULT_LIT)
    if name.lower() != 'sand':
        unreal.MaterialEditingLibrary.set_material_usage(mat, unreal.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    unreal.MaterialEditingLibrary.recompile_material(mat)
    save(mat)
    cache_material(asset_path, signature, 'imported and saved successfully')
    REPORT['materials'].append(mat.get_path_name())
    return mat


def mesh_options(skeletal):
    opts = unreal.FbxImportUI()
    opts.set_editor_property('automated_import_should_detect_type', False)
    opts.set_editor_property('mesh_type_to_import', unreal.FBXImportType.FBXIT_SKELETAL_MESH if skeletal else unreal.FBXImportType.FBXIT_STATIC_MESH)
    opts.set_editor_property('import_as_skeletal', skeletal)
    opts.set_editor_property('import_mesh', True)
    opts.set_editor_property('import_animations', skeletal)
    opts.set_editor_property('import_materials', False)
    opts.set_editor_property('import_textures', False)
    opts.set_editor_property('create_physics_asset', skeletal)
    data = opts.get_editor_property('skeletal_mesh_import_data' if skeletal else 'static_mesh_import_data')
    data.set_editor_property('convert_scene', True)
    data.set_editor_property('convert_scene_unit', True)
    data.set_editor_property('force_front_x_axis', False)
    data.set_editor_property('import_uniform_scale', 1.0)
    data.set_editor_property('normal_import_method', unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS)
    if skeletal:
        data.set_editor_property('import_morph_targets', True)
        anim_data = opts.get_editor_property('anim_sequence_import_data')
        # Animation-only imports read their own transform settings. Unreal's
        # FbxAssetImportData defaults unit conversion off, unlike our mesh setup.
        anim_data.set_editor_property('convert_scene', True)
        anim_data.set_editor_property('convert_scene_unit', True)
        anim_data.set_editor_property('force_front_x_axis', False)
        anim_data.set_editor_property('import_uniform_scale', 1.0)
        anim_data.set_editor_property('import_bone_tracks', True)
        anim_data.set_editor_property('import_custom_attribute', True)
        anim_data.set_editor_property('delete_existing_morph_target_curves', True)
    else:
        data.set_editor_property('combine_meshes', True)
        data.set_editor_property('auto_generate_collision', False)
        data.set_editor_property('generate_lightmap_u_vs', False)
    return opts


def contact_assets():
    source = SHARED / 'audio'
    manifest = json.loads((source / 'manifest.json').read_text(encoding='utf-8-sig'))
    sounds = {}
    for species_name in ('Krag', 'Nib'):
        sounds[species_name] = []
        for filename in manifest['species'][species_name]['sandSteps']:
            objects = imported_task(source / filename, DEST + '/Audio/' + species_name)
            wave = next((o for o in objects if isinstance(o, unreal.SoundWave)), None)
            if wave is None:
                raise RuntimeError('Footstep WAV import failed: ' + filename)
            wave.set_editor_property('volume', float(manifest['species'][species_name].get('runtimeGain', 1.0)))
            save(wave)
            sounds[species_name].append(wave)
    destination = DEST + '/Effects'
    mat = load(destination + '/M_SandDust') or TOOLS.create_asset('M_SandDust', destination, unreal.Material, unreal.MaterialFactoryNew())
    unreal.MaterialEditingLibrary.delete_all_material_expressions(mat)
    mat.set_editor_property('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT)
    mat.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_DEFAULT_LIT)
    mat.set_editor_property('two_sided', True)
    color = expression(mat, unreal.MaterialExpressionConstant3Vector, -300, 0)
    color.set_editor_property('constant', unreal.LinearColor(.43, .31, .19, 1))
    connect(mat, color, '', unreal.MaterialProperty.MP_BASE_COLOR)
    mask = texture(SHARED / 'effects' / 'SandDustMask.png', destination, 'BaseColor')
    sample = expression(mat, unreal.MaterialExpressionTextureSample, -600, 200)
    sample.set_editor_property('texture', mask)
    opacity = expression(mat, unreal.MaterialExpressionScalarParameter, -600, 400)
    opacity.set_editor_property('parameter_name', 'Opacity')
    opacity.set_editor_property('default_value', 0.2)
    multiply = expression(mat, unreal.MaterialExpressionMultiply, -300, 220)
    unreal.MaterialEditingLibrary.connect_material_expressions(sample, 'A', multiply, 'A')
    unreal.MaterialEditingLibrary.connect_material_expressions(opacity, '', multiply, 'B')
    connect(mat, multiply, '', unreal.MaterialProperty.MP_OPACITY)
    unreal.MaterialEditingLibrary.recompile_material(mat)
    save(mat)
    REPORT['contact_audio'] = {name: [wave.get_path_name() for wave in waves] for name, waves in sounds.items()}
    REPORT['dust_material'] = mat.get_path_name()
    REPORT['contact_status'] = 'Shared candidates; runtime synchronization, appearance and listening review pending'
    return sounds, mat


def action_audio_assets():
    source = SHARED / 'audio'
    manifest = json.loads((source / 'action-audio.json').read_text(encoding='utf-8-sig'))
    if manifest.get('schemaVersion') != 1:
        raise RuntimeError('Unsupported action audio schema')
    assets = {}
    for name in ('Krag_Shot', 'Nib_Shot', 'Krag_Hit', 'Nib_Hit'):
        spec = next((entry for entry in manifest.get('effects', []) if entry.get('name') == name), None)
        if not spec:
            raise RuntimeError('Missing shared action audio: ' + name)
        filename = source / spec['file']
        if sha256(filename) != spec['sha256']:
            raise RuntimeError('Shared action WAV does not match its recorded hash: ' + name)
        expected_gain = .55 if name.endswith('_Shot') else .6
        if abs(float(spec['runtimeGain']) - expected_gain) > 1.e-6:
            raise RuntimeError('Action gain changed; update both engines together: ' + name)
        objects = imported_task(filename, DEST + '/Audio/Actions')
        sound = next((obj for obj in objects if isinstance(obj, unreal.SoundWave)), None)
        if sound is None:
            raise RuntimeError('Action WAV import failed: ' + name)
        # The unit applies the shared .55/.6 gain once at the authored event time.
        sound.set_editor_property('volume', 1.0)
        save(sound)
        assets[name] = sound
    REPORT['action_audio'] = {'assets': {name: sound.get_path_name() for name, sound in assets.items()},
                             'shot_gain': .55, 'hit_gain': .6, 'hit_normalized_time': .22,
                             'shot_timing': 'character weapon.fireTimesNormalized',
                             'attenuation': 'linear, inner 4m, outer 60m',
                             'status': 'Shared candidates; game mix/synchronization/listening review pending'}
    return assets



# Keep only paths and plain Python values while importing subsequent meshes. A
# reflected variant struct strongly references its mesh/animations and defeats GC.
VARIANT_ASSETS = ('mesh', 'idle', 'walk', 'run', 'melee', 'shoot', 'hit', 'face_performance')
VARIANT_STRINGS = ('id', 'label', 'weapon_muzzle_bone', 'weapon_aim_bone')
VARIANT_FLOATS = ('walk_speed_meters', 'run_speed_meters', 'walk_cycle_seconds',
                  'run_cycle_seconds', 'walk_stance_fraction', 'run_stance_fraction')
VARIANT_ARRAYS = ('fire_times_normalized', 'walk_left_contacts', 'walk_right_contacts',
                  'run_left_contacts', 'run_right_contacts')


def variant_descriptor(variant):
    result = {key: variant.get_editor_property(key).get_path_name() for key in VARIANT_ASSETS}
    result.update({key: str(variant.get_editor_property(key)) for key in VARIANT_STRINGS})
    result.update({key: float(variant.get_editor_property(key)) for key in VARIANT_FLOATS})
    result.update({key: [float(value) for value in variant.get_editor_property(key)] for key in VARIANT_ARRAYS})
    result['morph_drivers'] = [dict(
        **{key: str(driver.get_editor_property(key)) for key in ('morph', 'bone', 'channel', 'kind')},
        **{key: float(driver.get_editor_property(key)) for key in ('start', 'end', 'max_weight')},
    ) for driver in variant.get_editor_property('morph_drivers')]
    return result


def restore_variant(descriptor, validation):
    variant = unreal.KKCharacterVariant()
    for key in VARIANT_ASSETS:
        asset = load(descriptor[key])
        if asset is None:
            raise RuntimeError('Saved character asset cannot be reloaded: ' + descriptor[key])
        variant.set_editor_property(key, asset)
    mesh = variant.get_editor_property('mesh')
    for dependency in ('skeleton', 'physics_asset'):
        if mesh.get_editor_property(dependency) is None:
            raise RuntimeError(descriptor['id'] + ': saved ' + dependency + ' is missing on final reload')
    slots = mesh.get_editor_property('materials')
    bindings = validation.get('material_bindings', [])
    if len(slots) != len(bindings):
        raise RuntimeError(descriptor['id'] + ': material count changed on final reload')
    for binding in bindings:
        actual = slots[binding['slot']].get_editor_property('material_interface')
        if actual is None or actual.get_path_name() != binding['asset']:
            raise RuntimeError(descriptor['id'] + ': material binding did not survive final package reload')
    validation['material_bindings_verified_after_reload'] = True
    for key in VARIANT_STRINGS + VARIANT_FLOATS + VARIANT_ARRAYS:
        variant.set_editor_property(key, descriptor[key])
    drivers = []
    for spec in descriptor['morph_drivers']:
        driver = unreal.KKMorphDriver()
        for key, value in spec.items():
            driver.set_editor_property(key, value)
        drivers.append(driver)
    variant.set_editor_property('morph_drivers', drivers)
    return variant


def species(folder, only_variant=None, validate_saved=False):
    source = SHARED / 'characters' / folder
    manifest_path = next((p for p in (source / 'manifest.json', source / 'asset_manifest.json', source / 'krag_asset_contract.json') if p.exists()), None)
    manifest = json.loads(manifest_path.read_text(encoding='utf-8-sig')) if manifest_path else {}
    deformation = manifest.get('deformation')
    if deformation is None and (source / 'facial-rig.json').exists():
        deformation = json.loads((source / 'facial-rig.json').read_text(encoding='utf-8-sig'))
    deformation = deformation or {}
    if deformation and (deformation.get('schemaVersion') != 1 or deformation.get('faceRoot') != 'FaceRoot'):
        raise RuntimeError('Unsupported deformation schema or facial root for ' + folder)
    entries = manifest.get('variants', [])
    if isinstance(entries, list) and entries and all(isinstance(e, dict) and e.get('fbx') for e in entries):
        files = [source / e['fbx'] for e in entries]
    elif isinstance(entries, dict) and entries and all(isinstance(e, dict) and e.get('file') for e in entries.values()):
        files = [BENCHMARK.parent / e['file'] if e['file'].startswith('benchmark/') else source / e['file'] for e in entries.values()]
    else:
        files = [p for p in sorted(source.glob('*.fbx')) if p.stem.lower() not in ('krag_weapon', 'nib_weapon')]
    if any(not p.exists() for p in files):
        raise RuntimeError('Manifest character file missing: ' + str([str(p) for p in files if not p.exists()]))
    if not files:
        raise RuntimeError('No shared character FBXs: ' + str(source))
    if only_variant:
        files = [p for p in files if p.stem == only_variant]
        if len(files) != 1:
            raise RuntimeError('Requested variant is absent from species manifest: ' + only_variant)
    material_map = {}
    for color in sorted((source / 'textures').glob('*_BaseColor.png')):
        name = color.stem.removesuffix('_BaseColor')
        material_map[name] = material(name, color.parent, DEST + '/Characters/' + folder + '/Materials')
    if not material_map:
        raise RuntimeError('No PBR materials found for ' + folder)
    variants = []
    # Natural first, mandatory crusher second; names define the review order only.
    order = {'Natural': 0, 'Crusher': 1, 'GripReplacement': 1, 'LegReplacement': 2, 'IronJaw': 2, 'Piston': 3, 'Weapon': 4}
    files.sort(key=lambda p: order.get(p.stem.split('_', 1)[-1], 100))
    def import_variant(fbx):
        variant_entry = next((e for e in entries if isinstance(e, dict) and e.get('fbx') and (source / e['fbx']).resolve() == fbx.resolve()), {}) if isinstance(entries, list) else {}
        variant_deformation = variant_entry.get('deformation', deformation)
        if variant_deformation and (variant_deformation.get('schemaVersion') != 1 or variant_deformation.get('faceRoot') != 'FaceRoot'):
            raise RuntimeError('Unsupported deformation override for ' + fbx.stem)
        destination = DEST + '/Characters/' + folder + '/' + fbx.stem
        character_options = mesh_options(True)
        # Explicit single-take files carry the validated binds and are imported below.
        # Avoid constructing duplicate embedded animation assets for every mesh variant.
        if manifest.get('animations'):
            character_options.set_editor_property('import_animations', False)
        if validate_saved:
            objects = [load(destination + '/' + fbx.stem)]
        else:
            objects = imported_task(fbx, destination, character_options)
        # Some FBX importer versions report only the primary object, so query the package folder too.
        objects.extend(load(p) for p in unreal.EditorAssetLibrary.list_assets(destination, recursive=True, include_folder=False))
        meshes = [o for o in objects if isinstance(o, unreal.SkeletalMesh)]
        if not meshes:
            raise RuntimeError('Skeletal mesh missing after import: ' + str(fbx))
        mesh = meshes[0]
        # Legacy FBX tasks report/save the primary mesh but can leave newly
        # generated Skeleton and PhysicsAsset packages unsaved. Persist them
        # before animation import so the saved sample reloads independently.
        dependencies = {}
        for property_name in ('skeleton', 'physics_asset'):
            dependency = mesh.get_editor_property(property_name)
            if dependency is None:
                raise RuntimeError(f'{fbx.stem}: imported mesh has no {property_name}')
            if not validate_saved:
                save(dependency)
            package = dependency.get_path_name().split('.', 1)[0]
            if not package.startswith('/Game/'):
                raise RuntimeError(f'{fbx.stem}: unexpected generated dependency path {package}')
            disk_file = PROJECT / 'Content' / (package.removeprefix('/Game/') + '.uasset')
            if not disk_file.is_file():
                raise RuntimeError(f'{fbx.stem}: dependency save left no package on disk: {package}')
            dependencies[property_name] = dependency.get_path_name()
        slots = mesh.get_editor_property('materials')
        slots_changed = False
        binding_repairs = []
        for slot_index in range(len(slots)):
            # Reflected Array iteration returns value-struct wrappers. Assign the
            # edited struct back by index or the material binding can be lost.
            slot = slots[slot_index]
            name = str(slot.get_editor_property('imported_material_slot_name'))
            if name not in material_map:
                name = str(slot.get_editor_property('material_slot_name'))
            if name not in material_map:
                raise RuntimeError('Unmapped PBR material slot ' + name + ' in ' + fbx.stem)
            actual = slot.get_editor_property('material_interface')
            expected_path = material_map[name].get_path_name()
            actual_path = actual.get_path_name() if actual else None
            if actual_path != expected_path:
                binding_repairs.append({'slot': slot_index, 'name': name,
                                        'previous': actual_path, 'expected': expected_path})
                slot.set_editor_property('material_interface', material_map[name])
                slots[slot_index] = slot
                slots_changed = True
        if slots_changed:
            mesh.set_editor_property('materials', slots)
            save(mesh)
        material_bindings = []
        for slot_index, slot in enumerate(mesh.get_editor_property('materials')):
            name = str(slot.get_editor_property('imported_material_slot_name'))
            if name not in material_map:
                name = str(slot.get_editor_property('material_slot_name'))
            actual = slot.get_editor_property('material_interface')
            if actual is None or actual.get_path_name() != material_map[name].get_path_name():
                raise RuntimeError(f'{fbx.stem}: indexed material assignment did not persist for {name}')
            material_bindings.append({'slot': slot_index, 'name': name, 'asset': actual.get_path_name()})
        anims = [o for o in objects if isinstance(o, unreal.AnimSequence)]
        explicit_clips = manifest.get('animations', {})
        explicit_animations = {}
        for clip_name, relative_file in explicit_clips.items():
            if clip_name not in CLIPS + FACIAL_CLIPS:
                continue
            clip_file = BENCHMARK.parent / relative_file if relative_file.startswith('benchmark/') else source / relative_file
            if not clip_file.exists():
                raise RuntimeError('Manifest animation FBX missing: ' + str(clip_file))
            anim_opts = mesh_options(True)
            anim_opts.set_editor_property('mesh_type_to_import', unreal.FBXImportType.FBXIT_ANIMATION)
            anim_opts.set_editor_property('import_mesh', False)
            anim_opts.set_editor_property('skeleton', mesh.get_editor_property('skeleton'))
            if validate_saved:
                imported_anims = [o for o in [load(destination + '/Animations/' + clip_name + '/' + clip_name)] if isinstance(o, unreal.AnimSequence)]
            else:
                imported_anims = [o for o in imported_task(clip_file, destination + '/Animations/' + clip_name, anim_opts) if isinstance(o, unreal.AnimSequence)]
            if not imported_anims:
                raise RuntimeError('No animation sequence imported: ' + str(clip_file))
            explicit_animations[clip_name] = imported_anims[0]
        variant = unreal.KKCharacterVariant()
        variant.set_editor_property('id', fbx.stem)
        variant.set_editor_property('label', fbx.stem.replace('_', ' / '))
        variant.set_editor_property('mesh', mesh)
        locomotion = manifest.get('locomotion', {})
        variant.set_editor_property('walk_speed_meters', float(locomotion.get('Walk', {}).get('speedMetersPerSecond', 1.15 if folder == 'krag' else 0.9)))
        variant.set_editor_property('run_speed_meters', float(locomotion.get('Run', {}).get('speedMetersPerSecond', 3.2 if folder == 'krag' else 2.7)))
        variant.set_editor_property('walk_cycle_seconds', float(locomotion.get('Walk', {}).get('cycleSeconds', 0)))
        variant.set_editor_property('run_cycle_seconds', float(locomotion.get('Run', {}).get('cycleSeconds', 0)))
        for gait in ('Walk', 'Run'):
            details = locomotion.get(gait, {})
            variant.set_editor_property(gait.lower() + '_stance_fraction', float(details.get('stanceFraction', .62 if gait == 'Walk' else .42 if folder == 'krag' else .32)))
            variant.set_editor_property(gait.lower() + '_left_contacts', details.get('leftContacts', [0.0]))
            variant.set_editor_property(gait.lower() + '_right_contacts', details.get('rightContacts', [0.5]))
        morph_names = [m.get_name() for m in mesh.get_editor_property('morph_targets')]
        bone_names = [str(n) for n in unreal.KKBenchmarkAssets.get_mesh_bone_names(mesh)]
        bone_scales = {str(name): [float(scale.x), float(scale.y), float(scale.z)]
                       for name, scale in unreal.KKBenchmarkAssets.get_mesh_bone_reference_scales(mesh).items()}
        size = unreal.KKBenchmarkAssets.get_mesh_imported_size_meters(mesh)
        if not .5 < size.z < 5:
            raise RuntimeError(f'{fbx.stem}: imported height {size.z}m indicates an invalid unit scale')
        weapon = manifest.get('weapon', {})
        for source_key, property_name in (('muzzleBone', 'weapon_muzzle_bone'), ('aimBone', 'weapon_aim_bone')):
            bone = weapon.get(source_key)
            if not bone or bone not in bone_names:
                raise RuntimeError(f'{fbx.stem}: missing imported weapon marker {source_key}: {bone}')
            variant.set_editor_property(property_name, bone)
        fire_times = weapon.get('fireTimesNormalized', [])
        if not fire_times or any(not 0 <= float(t) < 1 for t in fire_times) or list(fire_times) != sorted(set(fire_times)):
            raise RuntimeError(f'{fbx.stem}: expected unique ascending normalized fire times')
        variant.set_editor_property('fire_times_normalized', fire_times)
        if variant_deformation and 'FaceRoot' not in bone_names:
            raise RuntimeError('Declared facial rig has no imported FaceRoot bone: ' + fbx.stem)
        drivers = []
        for spec in variant_deformation.get('drivers', []):
            if spec['channel'] not in ('rotationMagnitudeDegrees', 'translationDistanceMeters'):
                raise RuntimeError('Unsupported corrective channel: ' + spec['channel'])
            if spec.get('kind') not in ('facial', 'body'):
                raise RuntimeError('Corrective must classify facial/body kind: ' + spec['morph'])
            if float(spec['end']) <= float(spec['start']):
                raise RuntimeError('Corrective end must exceed start: ' + spec['morph'])
            if spec['bone'] not in bone_names:
                raise RuntimeError('Corrective control bone was not exported: ' + spec['bone'] + ' in ' + fbx.stem)
            candidates = [n for n in morph_names if n == spec['morph']]
            if not candidates:
                candidates = [n for n in morph_names if n.endswith('_' + spec['morph'])]
            if len(candidates) != 1:
                raise RuntimeError(f'Expected one imported morph {spec["morph"]} in {fbx.stem}; found {candidates}')
            driver = unreal.KKMorphDriver()
            for key in ('bone', 'channel', 'kind', 'start', 'end'):
                driver.set_editor_property(key, spec[key])
            driver.set_editor_property('morph', candidates[0])
            driver.set_editor_property('max_weight', float(spec.get('maxWeight', 1.0)))
            drivers.append(driver)
        variant.set_editor_property('morph_drivers', drivers)
        clip_paths = {}
        clip_validation = {}
        for name in CLIPS:
            candidates = [explicit_animations[name]] if name in explicit_animations else [a for a in anims if a.get_name().lower().endswith(name.lower()) or ('_' + name.lower() + '_') in a.get_name().lower()]
            if not candidates:
                raise RuntimeError('Missing ' + name + ' animation in ' + fbx.stem + '; saw ' + str([a.get_name() for a in anims]))
            clip = candidates[0]
            tracks = [str(n) for n in unreal.KKBenchmarkAssets.get_animation_bone_names(clip)]
            facial = [str(n) for n in unreal.KKBenchmarkAssets.get_facially_animated_bones(clip, mesh)]
            # Unreal FName equality ignores case; Sequencer DataModel emits
            # lowercase track display strings even when mesh bone names retain case.
            has_pelvis = any(track.casefold() == 'pelvis' for track in tracks)
            if not has_pelvis or not facial:
                failure = {'variant': fbx.stem, 'clip': name, 'asset': clip.get_path_name(),
                           'lengthSeconds': clip.get_play_length(), 'tracks': tracks,
                           'varyingFacialBones': facial, 'meshBones': bone_names,
                           'savedDependencies': dependencies,
                           'missingPelvisTrack': not has_pelvis, 'missingFacialVariation': not facial}
                (BENCHMARK / 'unreal' / 'evidence' / 'import-validation-failure.json').write_text(json.dumps(failure, indent=2), encoding='utf-8')
                raise RuntimeError(f'{fbx.stem}/{name}: missing skeletal pelvis track or varying FaceRoot performance; exact track data saved to import-validation-failure.json')
            ratios = {str(bone): [float(bounds.x), float(bounds.y)] for bone, bounds in unreal.KKBenchmarkAssets.get_animation_limb_translation_ratios(clip, mesh).items()}
            if len(ratios) < 4 or any(low < .1 or high > 10 for low, high in ratios.values()):
                raise RuntimeError(f'{fbx.stem}/{name}: animation/bind limb lengths indicate a unit mismatch: {ratios}')
            clip_validation[name] = {'bone_track_count': len(tracks), 'varying_facial_bones': facial, 'local_limb_translation_to_bind_length_ranges': ratios}
            variant.set_editor_property(name.lower(), clip)
            clip_paths[name] = clip.get_path_name()
        for name in FACIAL_CLIPS:
            if name in explicit_animations:
                variant.set_editor_property('face_performance', explicit_animations[name])
                clip_paths[name] = explicit_animations[name].get_path_name()
                facial = [str(n) for n in unreal.KKBenchmarkAssets.get_facially_animated_bones(explicit_animations[name], mesh)]
                if not facial:
                    raise RuntimeError(f'{fbx.stem}/{name}: no varying imported facial controls')
                clip_validation[name] = {'varying_facial_bones': facial}
            else:
                raise RuntimeError(f'{fbx.stem}: required facial acting clip {name} not supplied')
        REPORT['meshes'].append({'source': str(fbx), 'asset': mesh.get_path_name(), 'size_meters': [float(size.x), float(size.y), float(size.z)], 'clips': clip_paths, 'clip_validation': clip_validation, 'bones': bone_names, 'reference_bone_local_scales': bone_scales, 'morphs': morph_names, 'corrective_driver_count': len(drivers), 'saved_dependencies': dependencies, 'material_bindings': material_bindings, 'material_binding_repairs': binding_repairs})
        descriptor = variant_descriptor(variant)
        write_variant_receipt(folder, descriptor, REPORT['meshes'][-1])
        return descriptor

    for fbx in files:
        # Import in a function scope: no previous mesh, skeleton, options or animation
        # wrapper survives into the next expensive FBX triangulation step.
        variants.append(import_variant(fbx))
        gc.collect()
        unreal.collect_garbage()
        progress = BENCHMARK / 'unreal' / 'evidence' / 'import-progress.json'
        progress.write_text(json.dumps({'complete': False, 'latest_completed_variant': fbx.stem,
                                        'validated_meshes': REPORT['meshes'],
                                        'note': 'Per-variant import validation only; final data asset/map not yet complete'}, indent=2), encoding='utf-8')
        unreal.log('KK_VARIANT_IMPORTED_AND_RELEASED ' + fbx.stem)
    return variants


def main():
    global SOURCE_SNAPSHOT
    unreal.log('KK_IMPORT_BEGIN shared assets=' + str(SHARED))
    for folder in ('krag', 'nib'):
        content = PROJECT / 'Content' / 'Benchmark' / 'Characters' / folder
        for existing_mesh in content.glob('*/*.uasset'):
            if existing_mesh.stem != existing_mesh.parent.name or not existing_mesh.stem.startswith(('Krag_', 'Nib_')):
                continue
            missing = [kind for kind in ('Skeleton', 'PhysicsAsset') if not existing_mesh.with_name(existing_mesh.stem + '_' + kind + '.uasset').is_file()]
            if missing:
                raise RuntimeError(f'Incomplete generated dependency cache for {existing_mesh.stem}: {missing}. Run Prepare-ImportCache.ps1 -Apply before editor startup to preserve/archive it and rebuild.')
    progress = BENCHMARK / 'unreal' / 'evidence' / 'import-progress.json'
    progress.parent.mkdir(parents=True, exist_ok=True)
    progress.write_text(json.dumps({'complete': False, 'stage': 'started', 'import_resource_controls': REPORT['import_resource_controls']}, indent=2), encoding='utf-8')
    SOURCE_SNAPSHOT = source_snapshot()
    snapshot_file = BENCHMARK / 'unreal' / 'evidence' / 'import-source-snapshot.json'
    snapshot_file.parent.mkdir(parents=True, exist_ok=True)
    snapshot_file.write_text(json.dumps({'engine': REPORT['engine'], 'importerSha256': sha256(Path(__file__)), 'inputs': SOURCE_SNAPSHOT}, indent=2), encoding='utf-8')
    requested_import = option('KKImportVariant')
    requested_saved = option('KKValidateSavedVariant')
    assemble_only = '-kkassemble' in unreal.SystemLibrary.get_command_line().lower()
    if sum(bool(value) for value in (requested_import, requested_saved, assemble_only)) > 1:
        raise RuntimeError('Choose exactly one isolated import, saved validation, or assembly mode')
    requested = requested_import or requested_saved
    if requested:
        folder = requested.split('_', 1)[0].lower()
        if folder not in ('krag', 'nib') or not re.fullmatch(r'[A-Za-z0-9_]+', requested):
            raise RuntimeError('Invalid requested character variant')
        if requested_saved:
            # Only reuse packages with a previous semantic pass against these
            # exact sources. They will be loaded and checked again, not reimported.
            receipt_file = RECEIPT_DIR / (requested + '.json')
            if receipt_file.exists():
                read_variant_receipt(folder, requested)
            else:
                previous = json.loads((BENCHMARK / 'unreal/evidence/character-import-batch-progress.json').read_text(encoding='utf-8'))
                previous_snapshot = json.loads((BENCHMARK / 'unreal/evidence/character-import-batch-source-snapshot.json').read_text(encoding='utf-8'))['inputs']
                matching = [entry for entry in previous['validated_meshes'] if Path(entry['source']).stem == requested]
                prefix = 'characters/' + folder + '/'
                if len(matching) != 1 or character_inputs(folder) != {key: value for key, value in previous_snapshot.items() if key.startswith(prefix)}:
                    raise RuntimeError(requested + ': no prior semantic pass against unchanged character sources')
        species(folder, only_variant=requested, validate_saved=bool(requested_saved))
        if source_snapshot() != SOURCE_SNAPSHOT:
            (RECEIPT_DIR / (requested + '.json')).unlink(missing_ok=True)
            raise RuntimeError('Shared files changed during isolated variant validation')
        progress.write_text(json.dumps({'complete': False, 'isolated_variant_complete': requested,
                                        'validated_meshes': REPORT['meshes'],
                                        'note': 'Fresh editor process; final assembly remains separate'}, indent=2), encoding='utf-8')
        unreal.log('KK_VARIANT_COMPLETE ' + requested)
        return
    if assemble_only:
        descriptors = {}
        for folder in ('krag', 'nib'):
            manifest = json.loads((SHARED / 'characters' / folder / 'manifest.json').read_text(encoding='utf-8-sig'))
            names = [Path(entry['fbx']).stem for entry in manifest['variants']]
            descriptors[folder] = []
            for name in names:
                receipt = read_variant_receipt(folder, name)
                descriptors[folder].append(receipt['descriptor'])
                REPORT['meshes'].append(receipt['validation'])
        krags, nibs = descriptors['krag'], descriptors['nib']
        REPORT['character_import_mode'] = 'one guarded editor process per variant; verified generated package/source hashes before assembly'
    else:
        krags, nibs = species('krag'), species('nib')
    # Environment producer preserves this stable filename in its shared directory.
    candidates = list((SHARED / 'environment').rglob('Dunes.fbx'))
    if len(candidates) != 1:
        raise RuntimeError('Expected one shared environment/Dunes.fbx, found ' + str(candidates))
    terrain_file = candidates[0]
    terrain_objects = imported_task(terrain_file, DEST + '/Environment', mesh_options(False))
    terrain = next(o for o in terrain_objects if isinstance(o, unreal.StaticMesh))
    body = terrain.get_editor_property('body_setup')
    body.set_editor_property('collision_trace_flag', unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    sand_candidates = list((SHARED / 'environment').rglob('*_BaseColor.png'))
    if not sand_candidates:
        raise RuntimeError('Shared sand PBR texture missing')
    color = next((p for p in sand_candidates if 'sand' in p.name.lower()), sand_candidates[0])
    sand = material(color.stem.removesuffix('_BaseColor'), color.parent, DEST + '/Environment/Materials')
    terrain.set_material(0, sand)
    save(terrain)
    factory = unreal.DataAssetFactory()
    factory.set_editor_property('data_asset_class', unreal.KKBenchmarkAssets)
    data = load(DEST + '/DA_Benchmark') or TOOLS.create_asset('DA_Benchmark', DEST, unreal.KKBenchmarkAssets, factory)
    data.set_editor_property('terrain', terrain)
    data.set_editor_property('sand_material', sand)
    sounds, dust = contact_assets()
    data.set_editor_property('krag_sand_steps', sounds['Krag'])
    data.set_editor_property('nib_sand_steps', sounds['Nib'])
    for name, sound in action_audio_assets().items():
        data.set_editor_property(name.lower(), sound)
    data.set_editor_property('sand_dust_material', dust)
    data.set_editor_property('weapon_flash_material', weapon_flash_material())
    # Blender -Y source forward convention: review this rotation in actual editor before accepting render.
    data.set_editor_property('mesh_rotation', unreal.Rotator(0, -90, 0))
    validations = {entry['asset']: entry for entry in REPORT['meshes']}
    data.set_editor_property('krags', [restore_variant(entry, validations[entry['mesh']]) for entry in krags])
    data.set_editor_property('nibs', [restore_variant(entry, validations[entry['mesh']]) for entry in nibs])
    save(data)
    level_path = DEST + '/Maps/Dunes'
    unreal.EditorAssetLibrary.make_directory(DEST + '/Maps')
    levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if unreal.EditorAssetLibrary.does_asset_exist(level_path):
        if not levels.load_level(level_path): raise RuntimeError('Map load failed')
    elif not levels.new_level(level_path):
        raise RuntimeError('Map creation failed')
    if not levels.save_current_level(): raise RuntimeError('Map save failed')
    unreal.EditorAssetLibrary.save_directory(DEST, only_if_is_dirty=True, recursive=True)
    if source_snapshot() != SOURCE_SNAPSHOT:
        raise RuntimeError('Shared source files changed during import; discard this mixed-source result and rerun against pinned files.')
    REPORT['source_snapshot'] = str(snapshot_file)
    REPORT['source_inputs_unchanged_during_import'] = True
    progress = BENCHMARK / 'unreal' / 'evidence' / 'import-progress.json'
    progress.write_text(json.dumps({'complete': True, 'validated_meshes': REPORT['meshes']}, indent=2), encoding='utf-8')
    out = BENCHMARK / 'unreal' / 'evidence' / 'import-report.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(REPORT, indent=2), encoding='utf-8')
    unreal.log('KK_IMPORT_COMPLETE ' + str(out))


if __name__ == '__main__':
    main()
