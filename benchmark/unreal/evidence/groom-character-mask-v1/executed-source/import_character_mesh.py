"""Prepared isolated Natural target import and actual binding-mask/axis checks."""
import hashlib
import json
from pathlib import Path
import sys
import unreal

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
sys.path.insert(0,str(HERE))
from character_coordinates import match_rest_positions


def main():
    project=Path(unreal.Paths.project_dir()).resolve()
    plan=json.loads((project/'character-plan.json').read_text())
    if project!=(ROOT/plan['projectDirectory']).resolve() or not project.is_relative_to(ROOT/'benchmark/local/groom-probe'):
        raise RuntimeError('Character probe must remain isolated')
    for pin in plan['pins']:
        with (ROOT/pin['path']).open('rb') as stream:
            if hashlib.file_digest(stream,'sha256').hexdigest()!=pin['sha256']:
                raise RuntimeError('Frozen character probe input changed: '+pin['path'])
    evidence=project.parent/'evidence'
    result_path=evidence/'mesh-result.json'
    if result_path.exists():raise RuntimeError('Preserve earlier character mesh check')
    manifest_path=ROOT/plan['meshManifest']
    manifest=json.loads(manifest_path.read_text())
    if len(manifest['variants'])!=1 or manifest['variants'][0]['name']!='Nib_Natural':
        raise RuntimeError('Expected the specifically filtered Natural-only payload')
    variant=manifest['variants'][0]
    options=unreal.FbxImportUI()
    for key,value in {'automated_import_should_detect_type':False,
                      'mesh_type_to_import':unreal.FBXImportType.FBXIT_SKELETAL_MESH,
                      'import_as_skeletal':True,'import_mesh':True,'import_animations':False,
                      'import_materials':False,'import_textures':False,'create_physics_asset':False}.items():
        options.set_editor_property(key,value)
    data=options.get_editor_property('skeletal_mesh_import_data')
    for key,value in {'convert_scene':True,'convert_scene_unit':True,'force_front_x_axis':False,
                      'import_uniform_scale':1.,'import_morph_targets':True,'import_vertex_attributes':True,
                      'normal_import_method':unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS}.items():
        data.set_editor_property(key,value)
    task=unreal.AssetImportTask()
    for key,value in {'filename':str(manifest_path.parent/variant['fbx']),
                      'destination_path':'/Game/Character','destination_name':'Nib_Natural_Filtered',
                      'automated':True,'replace_existing':False,'save':False,'options':options,
                      'factory':unreal.FbxFactory()}.items():
        task.set_editor_property(key,value)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    loaded=[unreal.load_asset(path) for path in task.get_editor_property('imported_object_paths')]
    meshes=[asset for asset in loaded if isinstance(asset,unreal.SkeletalMesh)]
    if len(meshes)!=1:raise RuntimeError('Expected exactly one actual cleaned skeletal mesh')
    mesh=meshes[0]
    actual=json.loads(unreal.GroomCharacterLibrary.enable_and_read_binding_mask(mesh,'KKGroomBindable'))
    (evidence/'mesh-progress.json').write_text(json.dumps(actual,indent=2)+'\n')
    if 'error' in actual:raise RuntimeError(actual['error'])
    source=json.loads((ROOT/plan['groomSourceReport']).read_text())
    conversion=match_rest_positions(source['preservedRig']['bones'],actual['bones'])
    if actual['morphTargets']!=len(variant['morphs']):raise RuntimeError('Morph count differs')
    skeleton=mesh.get_editor_property('skeleton')
    if not skeleton:raise RuntimeError('Missing new matching skeleton')
    for asset in [skeleton,mesh]:
        if not unreal.EditorAssetLibrary.save_loaded_asset(asset,only_if_is_dirty=False):
            raise RuntimeError('Cannot save target/dependency '+asset.get_path_name())
    result={'mesh':actual,'sourceToMeshAxes':conversion,'meshManifest':plan['meshManifest'],
            'meshSourceSha256':next(pin['sha256'] for pin in plan['pins'] if pin['path']==(manifest_path.parent/variant['fbx']).relative_to(ROOT).as_posix()),
            'skeleton':skeleton.get_path_name(),'animationImportPending':True,
            'bindingPending':True,'rendered':False,'artisticAcceptance':False,'sharedChanged':False,'passed':True}
    result_path.write_text(json.dumps(result,indent=2)+'\n')
    unreal.log('KK_GROOM_CHARACTER_MESH_COMPLETE')


main()
