"""Create a distinct, measured runtime candidate; never overwrite pinned v7 files."""
import bpy,json,hashlib,sys,gc
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from runtime_reduction import reduce_object,correspondence,statistics

ROOT=Path(__file__).resolve().parents[3];ART=ROOT/'benchmark/art/krag';OUT=ROOT/'benchmark/shared/characters/krag'
SOURCE=ART/'Krag_Runtime.blend';TARGET=ART/'Krag_Runtime_Optimized_v7.blend';REPORT=ART/'runtime-reduction-v7.json'
sys.path.insert(0,str(ROOT/'benchmark/tools/nib/v5_wip'))
from posed_skin_check import collect_poses,compare_posed_skin
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
receipt=json.loads((OUT/'delivery-v7.json').read_text());contract=json.loads((OUT/'krag_asset_contract.json').read_text())
assert sha(SOURCE)==receipt['runtimeSha256'],'Pinned v7 Runtime differs from delivery receipt'
assert sha(ART/'Krag_Master.blend')==receipt['sourceSha256'],'Pinned v7 Master differs from delivery receipt'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE),load_ui=False)
rig=bpy.data.objects['Krag_Rig'];bind_before={b.name:[list(row) for row in b.matrix_local] for b in rig.data.bones}
active_action=rig.animation_data.action;rig.animation_data.action=None
for bone in rig.pose.bones:bone.location=(0,0,0);bone.rotation_mode='XYZ';bone.rotation_euler=(0,0,0);bone.scale=(1,1,1)
pose_samples=collect_poses(rig,contract['deformation'])
modules={o.get('module'):o for o in bpy.data.objects if o.type=='MESH' and 'module' in o}
visibility={g:(o.hide_render,o.hide_get()) for g,o in modules.items()}
report={'status':'in progress','sourceRuntimeSha256':receipt['runtimeSha256'],'masterSha256':receipt['sourceSha256'],
        'candidate':str(TARGET),'method':'Per-module collapse with fixed UV/material/boundary vertices and barycentric source-morph transfer',
        'sampledSurfaceErrorIsNotExactHausdorffBound':True,'modules':[],'artisticAcceptance':False}
report['toolHashes']={str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__).resolve(),Path(__file__).parent/'runtime_reduction.py',ROOT/'benchmark/tools/nib/v5_wip/posed_skin_check.py']}

def budget(name,current):
    if name=='Head':return 180000
    if name=='Body':return 188000
    if name.startswith('BioArm_'):return 15000
    if name.startswith('BioForearm_'):return 45000
    if name=='Garments':return 162000
    if name.startswith('BioLowerLeg_'):return 7000
    if name.startswith('Boot_'):return 30000
    if name.startswith('TrouserLeg_'):return 4000
    if name=='Scarf':return 16000
    # Preserve eyes, lids, fingers' small detail parts and all authored hard-surface mechanisms.
    return current

try:
    for group,source in list(modules.items()):
        count=sum(len(p.vertices)-2 for p in source.data.polygons);limit=budget(group,count)
        print('OPTIMIZE',group,count,'target',limit,flush=True)
        tolerances={'surface_limit':.0008,'morph_limit':.001} if group=='Head' else {'surface_limit':.0018,'morph_limit':.0015}
        if group in ['Garments','Scarf'] or group.startswith(('Boot_','TrouserLeg_','BioLowerLeg_')):tolerances={'surface_limit':.0025,'morph_limit':.0015}
        objects_before=set(bpy.data.objects)
        try:
            result,entry=reduce_object(source,rig,limit,contract['deformation'],**tolerances)
            if result!=source:
                entry['posedSkinComparison']=compare_posed_skin(source,result,rig,pose_samples,correspondence,statistics,max_error=.0025 if group=='Head' else .004,raise_on_failure=False)
                if not entry['posedSkinComparison']['passed']:raise RuntimeError(f'{group}: posed skin discrepancy {entry["posedSkinComparison"]["maxMeters"]}m exceeds limit')
        except RuntimeError as reduction_error:
            # A technical derivative may retain difficult regions at source density.
            # Never relax measured deformation/surface thresholds to hit a proposed budget.
            for failed_object in set(bpy.data.objects)-objects_before:
                failed_mesh=failed_object.data if failed_object.type=='MESH' else None
                bpy.data.objects.remove(failed_object,do_unlink=True)
                if failed_mesh and failed_mesh.users==0:bpy.data.meshes.remove(failed_mesh)
            result,entry=reduce_object(source,rig,count,contract['deformation'],**tolerances)
            entry['requestedTriangles']=limit;entry['denseRegionPreservedReason']=str(reduction_error)
            print('PRESERVE ORIGINAL REGION',group,str(reduction_error),flush=True)
        report['modules'].append(entry);REPORT.write_text(json.dumps(report,indent=2),newline='\n')
        if result!=source:
            old_data=source.data;original_name=source.name;bpy.data.objects.remove(source,do_unlink=True)
            if old_data.users==0:bpy.data.meshes.remove(old_data)
            result.name=original_name;modules[group]=result
        result.hide_render,result_hidden=visibility[group];result.hide_set(result_hidden)
        gc.collect()
    report['runtimeTrianglesAllModules']=sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in modules.values())
    report['trianglesByVariant']={name:sum(sum(len(p.vertices)-2 for p in o.data.polygons) for group,o in modules.items() if group not in data['off'] or group=='Weapon_R') for name,data in contract['variants'].items()}
    bind_after={b.name:[list(row) for row in b.matrix_local] for b in rig.data.bones}
    assert bind_before==bind_after,'Reference rig matrices changed during reduction'
    report['restBindUnchanged']=True;report['boneCount']=len(bind_after)
    rig.animation_data.action=active_action;bpy.context.scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=str(TARGET),compress=True)
    assert sha(SOURCE)==receipt['runtimeSha256'];assert sha(ART/'Krag_Master.blend')==receipt['sourceSha256']
    report['candidateSha256']=sha(TARGET);report['status']='Derived candidate generated; needs actual render, FBX roundtrip and engine import checks'
    contract['runtime_triangles_all_modules']=report['runtimeTrianglesAllModules'];contract['runtime_derivative_sha256']=report['candidateSha256'];contract['runtime_derivative']=str(TARGET)
    contract['runtime_derivative_status']='Unaccepted derived candidate; structural/surface transfer checks only'
    for name,count in report['trianglesByVariant'].items():contract['variants'][name]['runtime_triangles']=count
    (ART/'runtime-candidate-v7.contract.json').write_text(json.dumps(contract,indent=2),newline='\n')
    REPORT.write_text(json.dumps(report,indent=2),newline='\n');print('OPTIMIZED CANDIDATE SAVED',json.dumps(report['trianglesByVariant']),flush=True)
except Exception as error:
    report['status']='failed; pinned sources and shared exports untouched';report['error']=str(error);REPORT.write_text(json.dumps(report,indent=2),newline='\n');raise
