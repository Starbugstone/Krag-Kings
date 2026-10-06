"""Proof-gated Shoot-only refresh; preserves saved skeletal meshes and other clips.
Run one guarded editor process per Krag variant after the artist's raw invariant
proof and corrected shared inputs have been promoted. No full FBX mesh reimport.
"""
import copy
import hashlib
import json
import math
import re
import shutil
import sys
from datetime import datetime,timezone
from pathlib import Path
import unreal
sys.path.insert(0,str(Path(__file__).resolve().parent))
import import_shared_assets as shared

BONES={'upperarm_r','lowerarm_r','hand_r'}
EXPECTED_FILES={'Krag_Natural.fbx','Krag_Crusher.fbx','Krag_IronJaw.fbx','Krag_Piston.fbx','animations/Shoot.fbx'}
METADATA_FILES={'manifest.json','krag_asset_contract.json'}

def validate_metadata(old_inputs,new_inputs,promotion):
    backup=shared.BENCHMARK.parent/promotion['backup']
    evidence={}
    for name in METADATA_FILES:
        key='characters/krag/'+name
        old_path=backup/name;new_path=shared.SHARED/'characters/krag'/name
        if shared.sha256(old_path)!=old_inputs[key]['sha256'] or shared.sha256(new_path)!=new_inputs[key]['sha256']:
            raise RuntimeError('Metadata baseline/promoted hash mismatch: '+name)
        old=json.loads(old_path.read_text(encoding='utf-8-sig'));new=json.loads(new_path.read_text(encoding='utf-8-sig'))
        repair=new.pop('animationRepair',None)
        if not repair or repair.get('kind')!='Shoot right-arm aim only' or {b.casefold() for b in repair.get('changedBones',[])}!=BONES or repair.get('changedChannel')!='Shoot / Lcl Rotation / XYZ KeyValueFloat' or repair.get('artisticAcceptance') is not False:
            raise RuntimeError('Unexpected animation repair metadata: '+name)
        if name=='manifest.json':
            if new['runtimeDerivative']['sha256']!=repair['sourceRuntimeSha256']:raise RuntimeError('Aim source hash metadata mismatch')
            new['runtimeDerivative']['sha256']=old['runtimeDerivative']['sha256']
            new['status']=old['status']
        else:
            if new['runtime_derivative_sha256']!=repair['sourceRuntimeSha256']:raise RuntimeError('Aim source hash metadata mismatch')
            new['runtime_derivative_sha256']=old['runtime_derivative_sha256']
        if old!=new:raise RuntimeError('Runtime contract fields changed outside source provenance/status: '+name)
        evidence[key]={'previousSha256':old_inputs[key]['sha256'],'newSha256':new_inputs[key]['sha256'],'runtimeContractUnchanged':True}
    return evidence

def validate_proof(proof,old_inputs,new_inputs,metadata=None):
    if proof.get('identityTestOnly') is not False or len(proof.get('files',[]))!=5:
        raise RuntimeError('A completed five-file Shoot patch proof is required')
    if set(old_inputs)!=set(new_inputs):raise RuntimeError('Character input file set changed; clip-only refresh refused')
    verified={}
    for item in proof['files']:
        path=re.sub(r'/+','/',item['target'].replace('\\','/'))
        relative='animations/Shoot.fbx' if path.endswith('/animations/Shoot.fbx') else path.rsplit('/',1)[-1]
        if relative not in EXPECTED_FILES or relative in verified:raise RuntimeError('Unexpected/duplicate file in raw patch proof: '+relative)
        key='characters/krag/'+relative
        if old_inputs[key]['sha256']!=item['sourceSha256'] or new_inputs[key]['sha256']!=item['targetSha256']:
            raise RuntimeError('Raw proof old/new hashes do not match engine receipt/promoted input: '+relative)
        for flag in ('unchangedAllOtherTreeProperties','unchangedGeometryMorphsUVNormalsWeightsBindAndOtherTakes','sourceAndDonorBindMatricesByteIdentical','sourceAndDonorRotationBasisMatch','targetSampleTimesPreservedByteIdentical'):
            if item.get(flag) is not True:raise RuntimeError('Missing raw invariance proof '+flag+' for '+relative)
        changes=item.get('changes',[])
        if len(changes)!=9 or {(c['bone'].casefold(),c['axis']) for c in changes}!={(b,a) for b in BONES for a in 'XYZ'}:
            raise RuntimeError('Patch must enumerate exactly the nine permitted right-arm rotation arrays')
        if item.get('allowedRotationArrays')!=9 or not 1<=item.get('changedRotationArrays',0)<=9:
            raise RuntimeError('Raw patch has no valid changed-curve count')
        if any(c.get('stack')!='Shoot' or c.get('channel')!='Lcl Rotation' or c.get('property')!='KeyValueFloat' or not c.get('rawTreeChildIndexPath') or 'curveObjectId' not in c for c in changes):
            raise RuntimeError('Unapproved curve property in patch proof')
        verified[key]=item
    differences={key for key in old_inputs if old_inputs[key]!=new_inputs[key]}
    allowed=set(verified)|set(metadata or {})
    if differences!=allowed:raise RuntimeError('Shared edits exceed the five proof-covered FBXs and verified provenance-only JSON: '+str(sorted(differences^allowed)))
    return verified

def curve_snapshot(clip):
    result={}
    for bone in shared.unreal.KKBenchmarkAssets.get_animation_bone_names(clip):
        samples=[]
        for key in shared.unreal.KKBenchmarkAssets.get_animation_bone_track_samples(clip,bone):
            q=key.get_editor_property('rotation');p=key.get_editor_property('translation');s=key.get_editor_property('scale3d')
            samples.append({'rotation':[float(q.x),float(q.y),float(q.z),float(q.w)],'translation':[float(p.x),float(p.y),float(p.z)],'scale':[float(s.x),float(s.y),float(s.z)]})
        result[str(bone).casefold()]=samples
    return result

def compare_curves(before,after):
    if set(before)!=set(after):raise RuntimeError('Imported Shoot track set changed')
    changes={}
    for bone,old_keys in before.items():
        keys=after[bone]
        if len(keys)!=len(old_keys) or not keys:raise RuntimeError('Imported Shoot sample count changed: '+bone)
        max_angle=0.0
        for old,new in zip(old_keys,keys):
            for channel in ('translation','scale'):
                if max(abs(a-b) for a,b in zip(old[channel],new[channel]))>1e-5:
                    raise RuntimeError('Shoot translation/scale changed outside allowed rotation repair: '+bone)
            qa,qb=old['rotation'],new['rotation']
            norm=math.sqrt(sum(x*x for x in qa)*sum(x*x for x in qb))
            if norm<1e-10:raise RuntimeError('Invalid imported quaternion: '+bone)
            angle=math.degrees(2*math.acos(min(1.0,abs(sum(a*b for a,b in zip(qa,qb)))/norm)))
            max_angle=max(max_angle,angle)
        if bone not in BONES and max_angle>.001:raise RuntimeError('Imported rotation changed on unapproved bone: '+bone)
        if bone in BONES:changes[bone]={'maximumAngularChangeDegrees':max_angle,'samples':len(keys)}
    if set(changes)!=BONES or max(v['maximumAngularChangeDegrees'] for v in changes.values())<.01:
        raise RuntimeError('Corrected limb rotation motion did not reach the imported Shoot clip')
    return changes

def main():
    name=shared.option('KKRefreshVariant')
    proof_path=Path(shared.option('KKRefreshProof') or '')
    if name not in {Path(p).stem for p in EXPECTED_FILES if not p.startswith('animations/')} or not proof_path.is_file():
        raise RuntimeError('Explicit Krag variant and raw patch proof file required')
    shared.SOURCE_SNAPSHOT=shared.source_snapshot()
    receipt_path=shared.RECEIPT_DIR/(name+'.json')
    previous=json.loads(receipt_path.read_text(encoding='utf-8'))
    if previous['variant']!=name or previous['recipe']!=shared.VARIANT_RECIPE or previous['engine']!=shared.REPORT['engine']:
        raise RuntimeError('Saved variant recipe/engine mismatch')
    if shared.package_snapshot('krag',name)!=previous['packages']:
        raise RuntimeError('Saved packages differ from previous validated receipt; restore/inspect before clip refresh')
    proof=json.loads(proof_path.read_text(encoding='utf-8-sig'))
    promotion_path=Path(shared.option('KKRefreshPromotion') or '')
    if not promotion_path.is_file():raise RuntimeError('Root promotion receipt with preserved old metadata is required')
    promotion=json.loads(promotion_path.read_text(encoding='utf-8-sig'))
    current_inputs=shared.character_inputs('krag')
    metadata=validate_metadata(previous['characterInputs'],current_inputs,promotion)
    validate_proof(proof,previous['characterInputs'],current_inputs,metadata)
    progress=shared.BENCHMARK/'unreal/evidence/import-progress.json'
    progress.write_text(json.dumps({'complete':False,'stage':'Shoot-only refresh','variant':name}))
    original_clip=shared.load(previous['descriptor']['shoot'])
    before=curve_snapshot(original_clip)
    attempt=shared.BENCHMARK/'local/unreal-clip-refresh'/(name+'-'+datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S'))
    attempt.mkdir(parents=True,exist_ok=False)
    shutil.copy2(receipt_path,attempt/'previous-receipt.json')
    clip_package='Content/'+previous['descriptor']['shoot'].split('.',1)[0].removeprefix('/Game/')+'.uasset'
    shutil.copy2(shared.PROJECT/clip_package,attempt/'previous-Shoot.uasset')
    (attempt/'previous-curves.json').write_text(json.dumps(before))
    descriptors=shared.species('krag',only_variant=name,validate_saved=True,refresh_clip='Shoot',write_receipts=False)
    if len(descriptors)!=1:raise RuntimeError('Refresh returned unexpected variant count')
    descriptor=descriptors[0]
    after=curve_snapshot(shared.load(descriptor['shoot']))
    (attempt/'updated-curves.json').write_text(json.dumps(after))
    changed=compare_curves(before,after)
    current=shared.package_snapshot('krag',name)
    if set(current)!=set(previous['packages']):raise RuntimeError('Refresh changed generated package set')
    package_changes={key for key in current if current[key]!=previous['packages'][key]}
    if package_changes!={clip_package}:raise RuntimeError('Refresh changed packages outside Shoot: '+str(sorted(package_changes)))
    if shared.source_snapshot()!=shared.SOURCE_SNAPSHOT:raise RuntimeError('Shared source changed during clip refresh')
    validation=shared.REPORT['meshes'][-1]
    validation['shoot_only_refresh']={'rawProof':str(proof_path),'rawProofSha256':shared.sha256(proof_path),'promotionReceiptSha256':shared.sha256(promotion_path),'metadata':metadata,'updatedBones':changed,'changedPackage':clip_package,'fullSkeletalFbxReimport':False,'allOtherSavedPackagesByteIdentical':True}
    shared.write_variant_receipt('krag',descriptor,validation)
    (attempt/'refresh-result.json').write_text(json.dumps(validation['shoot_only_refresh'],indent=2))
    out=shared.BENCHMARK/'unreal/evidence'/('shoot-refresh-'+name+'.json')
    out.write_text(json.dumps(validation,indent=2))
    unreal.log('KK_SHOOT_REFRESH_COMPLETE '+name)

if __name__=='__main__':main()
