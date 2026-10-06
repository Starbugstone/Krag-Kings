"""Saved terrain/collision inspection; opt-in repair persists section/physics rebuild and required material usage."""
import json
import sys
from pathlib import Path
import unreal
benchmark=Path(unreal.Paths.project_dir()).resolve().parents[1]
repair='-KKRepairRenderAssets' in unreal.SystemLibrary.get_command_line()
out=benchmark/'unreal/evidence'/('render-asset-repair.json' if repair else 'terrain-runtime-inspection.json')
terrain=unreal.EditorAssetLibrary.load_asset('/Game/Benchmark/Environment/Dunes')
report={'repairRequested':repair,'asset':terrain.get_path_name(),'bounds':str(terrain.get_bounds()),'boundingBox':str(terrain.get_bounding_box())}
body=terrain.get_editor_property('body_setup')
report['collisionTraceFlag']=str(body.get_editor_property('collision_trace_flag'))
report['lodCount']=terrain.get_num_lods()
report['triangles']=terrain.get_num_triangles(0)
static=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
report['sectionCollision']=[static.is_section_collision_enabled(terrain,0,i) for i in range(terrain.get_num_sections(0))]
out.write_text(json.dumps(report,indent=2))
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
def hit_dict(hit):
 if hit is None:return {'blockingHit':False}
 v=hit.to_tuple()
 return {'blockingHit':bool(v[0]),'initialOverlap':bool(v[1]),'distance':float(v[3]),'point':str(v[5]),'normal':str(v[7]),'actor':str(v[9])}
def inspect_traces():
 ground=actors.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector(0,0,0))
 try:
  comp=ground.static_mesh_component
  comp.set_mobility(unreal.ComponentMobility.MOVABLE)
  comp.set_static_mesh(terrain)
  comp.set_collision_profile_name('BlockAll')
  result={'componentBounds':str(ground.get_actor_bounds(False)),'collisionEnabled':str(comp.get_collision_enabled()),'objectType':str(comp.get_collision_object_type()),'traces':{}}
  for x,y in [(-135,0),(120,-10),(0,0),(1000,0)]:
   for complex_trace in [False,True]:
    start,end=unreal.Vector(x,y,6000),unreal.Vector(x,y,-6000)
    hit=unreal.SystemLibrary.line_trace_single(world,start,end,unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,complex_trace,[],unreal.DrawDebugTrace.NONE,True)
    result['traces'][str((x,y,complex_trace,'Visibility'))]=hit_dict(hit)
    hit=unreal.SystemLibrary.line_trace_single_for_objects(world,start,end,[unreal.ObjectTypeQuery.OBJECT_TYPE_QUERY1],complex_trace,[],unreal.DrawDebugTrace.NONE,True)
    result['traces'][str((x,y,complex_trace,'WorldStatic'))]=hit_dict(hit)
    if complex_trace:
     hit=unreal.SystemLibrary.line_trace_single(world,end,start,unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,True,[],unreal.DrawDebugTrace.NONE,True)
     result['traces'][str((x,y,True,'UpwardVisibility'))]=hit_dict(hit)
  return result
 finally:actors.destroy_actor(ground)
report['before']=inspect_traces()
out.write_text(json.dumps(report,indent=2))
if repair:
 # SetSectionCollision invokes StaticMesh.PostEditChange in installed UE source,
 # rebuilding saved physics after the previously changed BodySetup trace flag.
 for i in range(terrain.get_num_sections(0)):static.enable_section_collision(terrain,True,0,i)
 if not unreal.EditorAssetLibrary.save_loaded_asset(terrain,only_if_is_dirty=False):raise RuntimeError('Terrain physics rebuild save failed')
 report['after']=inspect_traces()
if repair:
 data=unreal.EditorAssetLibrary.load_asset('/Game/Benchmark/DA_Benchmark')
 report['meshRotationBefore']=str(data.get_editor_property('mesh_rotation'))
 data.set_editor_property('mesh_rotation',unreal.Rotator(roll=0.0,pitch=0.0,yaw=-90.0))
 if not unreal.EditorAssetLibrary.save_loaded_asset(data,only_if_is_dirty=False):raise RuntimeError('Data-asset rotation repair save failed')
 rotation=data.get_editor_property('mesh_rotation')
 report['meshRotationAfter']={'pitch':rotation.pitch,'yaw':rotation.yaw,'roll':rotation.roll}
 if abs(rotation.pitch)>1e-5 or abs(rotation.roll)>1e-5 or abs(rotation.yaw+90)>1e-5:raise RuntimeError('Incorrect named mesh rotation after save')
report['materials']={}
for species in ['krag','nib']:
 for path in unreal.EditorAssetLibrary.list_assets('/Game/Benchmark/Characters/'+species+'/Materials',recursive=False,include_folder=False):
  material=unreal.EditorAssetLibrary.load_asset(path)
  if not isinstance(material,unreal.Material):continue
  usages=[unreal.MaterialUsage.MATUSAGE_SKELETAL_MESH,unreal.MaterialUsage.MATUSAGE_MORPH_TARGETS]
  record={'before':{str(u):unreal.MaterialEditingLibrary.has_material_usage(material,u) for u in usages}}
  if repair:
   for usage in usages:unreal.MaterialEditingLibrary.set_base_material_usage(material,usage,True)
   unreal.MaterialEditingLibrary.recompile_material(material)
   if not unreal.EditorAssetLibrary.save_loaded_asset(material,only_if_is_dirty=False):raise RuntimeError('Material save failed: '+path)
   record['after']={str(u):unreal.MaterialEditingLibrary.has_material_usage(material,u) for u in usages}
  report['materials'][path]=record
out.write_text(json.dumps(report,indent=2))
if repair and not all(v['blockingHit'] for k,v in report['after']['traces'].items() if 'UpwardVisibility' not in k):raise RuntimeError('Terrain still fails one or more actual simple/complex channel traces after rebuild')
unreal.log('KK_TERRAIN_INSPECTION_COMPLETE '+str(out))
