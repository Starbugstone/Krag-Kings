"""Create a separate runtime derivative, leaving pinned v4b assets untouched."""
import bpy, gc, hashlib, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/'benchmark/tools/krag'))
sys.path.insert(0,str(Path(__file__).parent))
from runtime_reduction import reduce_object,attach_portable_drivers,correspondence,statistics
from reduce_fur import reduce_fur
from posed_skin_check import collect_poses,compare_posed_skin

ART=ROOT/'benchmark/art/nib'
SOURCE=ART/'Nib_Master.blend'
TARGET=ART/'Nib_Runtime_Optimized_v4b.blend'
REPORT=ART/'v5-study/runtime-reduction-v4b.json'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source_hash=json.loads((ART/'source-report.json').read_text())['sourceSha256']
assert sha(SOURCE)==source_hash,'Pinned source has changed'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE),load_ui=False)
rig=bpy.data.objects['Nib_Rig'];scene=bpy.context.scene
collection=bpy.data.collections['Nib_Authored_Components']
deformation=json.loads(scene['deformation_contract'])
bind_before={b.name:[list(row) for row in b.matrix_local] for b in rig.data.bones}
previous_action=rig.animation_data.action;rig.animation_data.action=None
for bone in rig.pose.bones:
    bone.location=(0,0,0);bone.rotation_mode='XYZ';bone.rotation_euler=(0,0,0);bone.scale=(1,1,1)
sources=[o for o in collection.objects if o.type=='MESH']
pose_samples=collect_poses(rig,deformation)
report={'status':'in progress','sourceSha256':source_hash,'candidate':str(TARGET),
        'artisticAcceptance':False,'components':[],
        'method':'Component-aware reduction; body/cloth collapse and barycentric morph transfer; every fur guide retained with fewer longitudinal segments.',
        'surfaceErrorIsSampledNotExactHausdorff':True}
report['codeSha256']={str(path.relative_to(ROOT)):sha(path) for path in [Path(__file__),Path(__file__).parent/'reduce_fur.py',Path(__file__).parent/'posed_skin_check.py',ROOT/'benchmark/tools/krag/runtime_reduction.py']}

def visible(o,variant):
    tag=o.get('variant','all');region=o.get('bone','')
    if tag=='all':return True
    if tag=='organic':return variant!='grip'
    if tag=='natural':
        if variant=='grip' and (region in ['Arm_L','LowerArm_L','Hand_L'] or (region.endswith('_L') and any(region.startswith(n) for n in ['Finger_','Index','Middle','Ring','Little','Thumb']))):return False
        if variant=='leg' and region in ['Shin_R','Foot_R']:return False
        return True
    return tag==variant

def budget(obj,current):
    tag=obj.get('bone','');name=obj.name.lower()
    if tag=='BodyAnatomy':return 180000
    # Preserve facial anatomy, eyes, mouth and finger shape for the first trial.
    if tag=='FaceSurface' or any(word in name for word in ['eyeball','iris','pupil','nostril','tooth','tongue','gum','eyebrow','chin fur']):return current
    if obj.get('fur_strands'):return current
    mats=[m.name for m in obj.data.materials]
    if current>700 and any(m in mats for m in ['Nib_Cloth','Nib_Workwear']):return max(450,int(current*.28))
    if current>1000 and 'Nib_Leather' in mats and not tag.startswith(('Hand_','Finger_')):return max(700,int(current*.45))
    return current

try:
    for source in sources:
        count=sum(len(p.vertices)-2 for p in source.data.polygons)
        target=budget(source,count)
        if not source.get('fur_strands') and target>=count:continue
        print('NIB_RUNTIME_REDUCE',source.name,count,'target',target,flush=True)
        old_visibility=(source.hide_render,source.hide_get());old_collections=list(source.users_collection)
        if source.get('fur_strands'):
            # Fine fuzz remains tightly fitted; longer head/ear strands permit a
            # larger measured chord error, subject to the real portrait review.
            limit=.00025 if source.name.startswith('Fine skin fuzz') else .0025
            result,entry=reduce_fur(source,rig,deformation,attach_portable_drivers,max_chord_error=limit)
        else:
            tolerance=.0013 if source.get('bone')=='BodyAnatomy' else .002
            before_objects=set(bpy.data.objects)
            try:
                result,entry=reduce_object(source,rig,target,deformation,surface_limit=tolerance,morph_limit=.0008)
            except RuntimeError as error:
                # Minor cloth/gear regions may be cheaper to retain than to
                # damage or repeatedly retry. Body failures remain explicit.
                if source.get('bone')=='BodyAnatomy':raise
                for created in set(bpy.data.objects)-before_objects:
                    data=created.data if created.type=='MESH' else None
                    bpy.data.objects.remove(created,do_unlink=True)
                    if data is not None and data.users==0:bpy.data.meshes.remove(data)
                result=source
                entry={'name':source.name,'sourceTriangles':count,'runtimeTriangles':count,
                       'reduced':False,'retainedAtSourceDensity':True,'rejectedReductionReason':str(error)}
            if source.get('bone')=='BodyAnatomy' or source.name=='Draped desert scarf':
                entry['posedSkinComparison']=compare_posed_skin(source,result,rig,pose_samples,correspondence,statistics,raise_on_failure=False)
                if not entry['posedSkinComparison']['passed']:
                    report['components'].append(entry);REPORT.write_text(json.dumps(report,indent=2))
                    raise RuntimeError(f'{source.name}: posed skin discrepancy exceeds the 3.5 mm review-candidate limit')
        report['components'].append(entry);REPORT.write_text(json.dumps(report,indent=2))
        if result!=source:
            original_name=source.name;old_data=source.data
            bpy.data.objects.remove(source,do_unlink=True)
            if old_data.users==0:bpy.data.meshes.remove(old_data)
            for c in list(result.users_collection):c.objects.unlink(result)
            for c in old_collections:c.objects.link(result)
            result.name=original_name
        result.hide_render=old_visibility[0];result.hide_set(old_visibility[1])
        gc.collect()
    active=[o for o in collection.objects if o.type=='MESH']
    report['trianglesByVariant']={variant:sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in active if visible(o,variant)) for variant in ['natural','grip','leg']}
    report['variantVertices']={variant:sum(len(o.data.vertices) for o in active if visible(o,variant)) for variant in ['natural','grip','leg']}
    bind_after={b.name:[list(row) for row in b.matrix_local] for b in rig.data.bones}
    assert bind_before==bind_after,'Reference bones changed'
    report['restBindUnchanged']=True;report['boneCount']=len(bind_after)
    report['candidateTargetMet']=max(report['trianglesByVariant'].values())<=350000
    rig.animation_data.action=previous_action;scene.frame_set(1)
    scene['runtime_reduction_source_sha256']=source_hash
    scene['runtime_quality_status']='Derived v4b integration candidate; source likeness remains artistically unaccepted.'
    bpy.ops.wm.save_as_mainfile(filepath=str(TARGET),compress=True)
    assert sha(SOURCE)==source_hash,'Pinned source changed during derivative generation'
    report['candidateSha256']=sha(TARGET)
    report['status']='Derived candidate generated; visual, deformation, FBX and engine validation pending.'
    REPORT.write_text(json.dumps(report,indent=2));print('NIB_RUNTIME_CANDIDATE',json.dumps(report['trianglesByVariant']),flush=True)
except Exception as error:
    report['status']='Failed; pinned source/shared outputs untouched';report['error']=str(error)
    REPORT.write_text(json.dumps(report,indent=2));raise
