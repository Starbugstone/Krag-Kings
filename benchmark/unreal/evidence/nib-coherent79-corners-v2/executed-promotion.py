"""Curate a verified candidate and publish only its declared portable payload.

Provenance-path edits are explicit, hashed transformations. Geometry, animation
and texture bytes are never rewritten here. Failed/previous inputs stay intact.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
from prepare_plan import ROOT, sha

CANONICAL={'Idle','Walk','Run','Melee','Shoot','Hit','FacePerformance'}


def write(path,data):
    path.write_text(json.dumps(data,indent=2)+'\n',newline='\n')


def inventory(folder):
    return {p.relative_to(folder).as_posix():{'sha256':sha(p),'bytes':p.stat().st_size}
            for p in sorted(folder.rglob('*')) if p.is_file()}


def verify(folder,records):
    actual=inventory(folder)
    if actual!=records:raise RuntimeError('File inventory/hash mismatch: '+str(folder))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--plan',type=Path,required=True)
    parser.add_argument('--curated-pbr',type=Path,required=True)
    parser.add_argument('--evidence',type=Path,required=True)
    parser.add_argument('--publish',action='store_true')
    args=parser.parse_args()
    plan_path=args.plan.resolve();plan=json.loads(plan_path.read_text())
    base=ROOT/plan['outputRoot'];candidate=base/'triangulated'
    pbr=ROOT/plan['reusedInputs']['pbrRoot'];reference=ROOT/plan['reusedInputs']['referenceRoot']
    curated=args.curated_pbr.resolve();evidence=args.evidence.resolve()
    if not curated.is_relative_to(ROOT/'benchmark/art/nib/runtime-derivatives'):
        raise RuntimeError('Durable PBR must be in the authored derivative tree')
    if not evidence.is_relative_to(ROOT/'benchmark/unreal/evidence'):
        raise RuntimeError('Unexpected evidence destination')
    portable=base/'portable'
    for folder in [curated,evidence,portable]:
        if folder.exists():raise RuntimeError('Preserve existing destination '+str(folder))
    for entry in plan['pins']:
        if sha(ROOT/entry['path'])!=entry['sha256']:raise RuntimeError('Frozen input changed '+entry['path'])
    receipts={}
    for stage in plan['stages']:
        receipt=json.loads((base/'receipts'/(stage+'.json')).read_text())
        if receipt['stage']!=stage or receipt['planSha256']!=sha(plan_path):
            raise RuntimeError('Stage identity changed '+stage)
        for entry in receipt['outputs']:
            if sha(ROOT/entry['path'])!=entry['sha256']:raise RuntimeError('Validated output changed '+entry['path'])
        receipts[stage]=receipt
    reports=[base/'triangulation-validation.json',candidate/'roundtrip.json',
             *[base/('variant-'+v+'-validation.json') for v in ['Natural','GripReplacement','LegReplacement']]]
    for path in reports:
        data=json.loads(path.read_text())
        key='structuralValidationPassed' if path.name=='roundtrip.json' else 'passed'
        if data.get(key) is not True or data.get('errors'):
            raise RuntimeError('Missing passing validation '+str(path))
    manifest=json.loads((candidate/'manifest.json').read_text())
    if len(manifest['bones'])!=79 or set(manifest['animations'])!=CANONICAL or len(manifest['variants'])!=3:
        raise RuntimeError('Incomplete coherent Nib contract')
    if (candidate/'manifest.json').read_bytes()!=(candidate/'asset_manifest.json').read_bytes():
        raise RuntimeError('Candidate manifest aliases disagree')
    if sha(pbr/'Nib_Runtime_PBR.blend')!=manifest['sourceSha256']:
        raise RuntimeError('Saved PBR does not match validated FBXs')
    payload={'manifest.json','asset_manifest.json','facial-rig.json'}
    payload.update(v['fbx'] for v in manifest['variants'])
    payload.update(manifest['animations'].values())
    for material in manifest['materials']:
        payload.update(material[c] for c in ['baseColor','normal','roughness','metallic'])
    for relative in payload:
        p=(candidate/relative).resolve()
        if not p.is_relative_to(candidate.resolve()) or not p.is_file():
            raise RuntimeError('Invalid portable path '+relative)
    shared=ROOT/'benchmark/shared/characters/nib'
    previous=inventory(shared)
    if any(Path(name).suffix.lower() not in ['.json','.fbx','.png'] for name in previous):
        raise RuntimeError('Unexpected existing shared file; preserve and inspect')
    evidence.mkdir(parents=True)
    shutil.copytree(pbr,curated)
    verify(curated,inventory(pbr))
    shutil.copytree(base/'receipts',evidence/'stage-receipts')
    shutil.copy2(plan_path,evidence/'executed-plan.json')
    for path in reports:shutil.copy2(path,evidence/path.name)
    (evidence/'reference').mkdir()
    for variant in manifest['variants']:
        shutil.copy2(reference/variant['fbx'],evidence/'reference'/variant['fbx'])
        provenance=candidate/Path(variant['fbx']).with_suffix('.corners.npz')
        shutil.copy2(provenance,evidence/provenance.name)
    shutil.copy2(candidate/'export.json',evidence/'source-pose-contract.json')
    portable.mkdir()
    for relative in sorted(payload):
        out=portable/relative;out.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(candidate/relative,out)
    transformations=[]
    for filename in ['manifest.json','asset_manifest.json']:
        data=json.loads((candidate/filename).read_text())
        changes={
            'source':os.path.relpath(curated/'Nib_Runtime_PBR.blend',shared).replace('\\','/'),
            'authoredSourceReport':os.path.relpath(curated/'pbr-bake-report.json',shared).replace('\\','/'),
            'geometryExport.referenceDirectory':os.path.relpath(evidence/'reference',shared).replace('\\','/')}
        old_values={}
        for field,value in changes.items():
            owner=data;keys=field.split('.')
            for key in keys[:-1]:owner=owner[key]
            old_values[field]=owner[keys[-1]];owner[keys[-1]]=value
        write(portable/filename,data)
        transformations.append({'file':filename,'oldSha256':sha(candidate/filename),'newSha256':sha(portable/filename),
            'scope':'Provenance paths only; runtime contract unchanged','oldValues':old_values,'newValues':changes})
    final=inventory(portable)
    for name,item in final.items():
        if name not in ['manifest.json','asset_manifest.json'] and item['sha256']!=sha(candidate/name):
            raise RuntimeError('Non-provenance payload was changed '+name)
    normalized=json.loads((portable/'manifest.json').read_text())
    if sha((shared/normalized['source']).resolve())!=normalized['sourceSha256']:
        raise RuntimeError('Durable source resolution/hash failed')
    if json.loads((shared/normalized['authoredSourceReport']).resolve().read_text())['candidateSha256']!=normalized['sourceSha256']:
        raise RuntimeError('Durable source report mismatch')
    if (portable/'manifest.json').read_bytes()!=(portable/'asset_manifest.json').read_bytes():
        raise RuntimeError('Final manifest aliases disagree')
    delta={'added':sorted(final.keys()-previous.keys()),'removed':sorted(previous.keys()-final.keys()),
        'changed':sorted(n for n in final.keys()&previous.keys() if final[n]!=previous[n]),
        'unchanged':sorted(n for n in final.keys()&previous.keys() if final[n]==previous[n])}
    result={'schemaVersion':1,'status':'Verified portable delivery staged','published':False,
        'plan':plan_path.relative_to(ROOT).as_posix(),'planSha256':sha(plan_path),'recipeSha256':sha(__file__),
        'sourceSha256':plan['sourceSha256'],'pbrSha256':manifest['sourceSha256'],
        'durablePbr':curated.relative_to(ROOT).as_posix(),'durablePbrFiles':inventory(curated),
        'portableRoot':portable.relative_to(ROOT).as_posix(),'files':final,'previousFiles':previous,
        'sharedDelta':delta,'promotionTransforms':transformations,
        'artisticAcceptance':False,'engineImportVerified':False,
        'validationScope':'Three full variants/79 bones/25 morphs/seven embedded and seven standalone takes;17 skeletal source samples per take. Full-cycle mesh collision/artistic/runtime checks remain required.'}
    write(evidence/'delivery.json',result)
    if args.publish:
        # Build/verify the replacement outside shared, then swap directories at
        # one process boundary. Keep the entire old payload as a durable backup.
        backup=ROOT/'benchmark/local/build-backups'/('nib-before-'+plan['name'])
        ready=base/'ready-to-publish'
        if backup.exists() or ready.exists():raise RuntimeError('Preserve previous publication attempt')
        shutil.copytree(portable,ready);verify(ready,final);verify(shared,previous)
        backup.parent.mkdir(parents=True,exist_ok=True)
        shared.rename(backup)
        try:ready.rename(shared);verify(shared,final)
        except Exception:
            if shared.exists():shared.rename(base/'failed-published-payload')
            backup.rename(shared)
            raise
        result.update({'status':'Technically verified payload published; art acceptance false','published':True,
            'previousSharedBackup':backup.relative_to(ROOT).as_posix()})
        write(evidence/'delivery.json',result)
    print(json.dumps({'published':result['published'],'payloadFiles':len(final),
        'deltaCounts':{k:len(v) for k,v in delta.items()},'receipt':str(evidence/'delivery.json')},indent=2))


if __name__=='__main__':main()
