"""Read-only inspection of the first actual UE skeletal/animation import.
Run in the real editor under the heavy-task guard; does not reimport or save assets.
"""
import json
from pathlib import Path
import unreal

base='/Game/Benchmark/Characters/krag/Krag_Natural'
mesh=unreal.EditorAssetLibrary.load_asset(base+'/Krag_Natural')
if not isinstance(mesh,unreal.SkeletalMesh):
    raise RuntimeError('The saved Krag Natural skeletal mesh is absent')
report={'mesh':mesh.get_path_name(),'bones':[str(n) for n in unreal.KKBenchmarkAssets.get_mesh_bone_names(mesh)],'morphs':[str(m.get_name()) for m in mesh.get_editor_property('morph_targets')],'clips':{}}
for name in ('Idle','Walk','Run','Melee','Shoot','Hit','FacePerformance'):
    clip=unreal.EditorAssetLibrary.load_asset(base+'/Animations/'+name+'/'+name)
    if not isinstance(clip,unreal.AnimSequence):
        report['clips'][name]={'error':'Saved animation absent'}
        continue
    item={'asset':clip.get_path_name(),'lengthSeconds':clip.get_play_length(),'tracks':[str(n) for n in unreal.KKBenchmarkAssets.get_animation_bone_names(clip)],'varyingFace':[str(n) for n in unreal.KKBenchmarkAssets.get_facially_animated_bones(clip,mesh)],'limbTranslationRatios':{str(k):[float(v.x),float(v.y)] for k,v in unreal.KKBenchmarkAssets.get_animation_limb_translation_ratios(clip,mesh).items()}}
    item['importSettings']={}
    data=clip.get_editor_property('asset_import_data')
    for setting in ('animation_length','frame_import_range','use_default_sample_rate','custom_sample_rate','import_bone_tracks','preserve_local_transform','convert_scene','convert_scene_unit'):
        try:item['importSettings'][setting]=str(data.get_editor_property(setting))
        except Exception as error:item['importSettings'][setting]='unavailable: '+str(error)
    report['clips'][name]=item
out=Path(unreal.Paths.project_dir()).resolve().parents[1]/'unreal/evidence/first-import-animation-inspection.json'
out.write_text(json.dumps(report,indent=2),encoding='utf-8')
unreal.log('KK_ANIMATION_INSPECTION_COMPLETE '+str(out))
