"""Freeze source/recipes/maps and write guarded jobs; this never launches Blender."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
TOOLS=Path(__file__).parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--source-report',type=Path,required=True)
    parser.add_argument('--source-sha256',required=True)
    parser.add_argument('--name',required=True)
    parser.add_argument('--blocked-reason',required=True,help='Use a new frozen plan after the actual source defect is resolved; empty only when ready for scheduling')
    args=parser.parse_args()
    if not args.name.replace('-','').isalnum():raise RuntimeError('Safe candidate name required')
    source=args.source.resolve();report=args.source_report.resolve()
    if sha(source)!=args.source_sha256:raise RuntimeError('Source hash mismatch')
    data=json.loads(report.read_text())
    if (data.get('candidateSha256') or data.get('outputSha256') or data.get('sourceSha256'))!=args.source_sha256:
        raise RuntimeError('Source report mismatch')
    dest=TOOLS/'plans'/args.name
    if dest.exists():raise RuntimeError('Preserve existing frozen plan')
    base='benchmark/local/candidates/'+args.name
    cards=ROOT/'benchmark/art/nib/groom-study/coherent79-v2-runtime-wide-nap/textures'
    references=ROOT/'benchmark/shared/characters/nib/textures'
    scripts=[*TOOLS.glob('*.py'), ROOT/'benchmark/tools/nib/export_nib.py',
        ROOT/'benchmark/tools/nib/v5_wip/pbr/prepare_runtime_pbr.py',ROOT/'benchmark/tools/nib/v5_wip/pbr/bake_fields.py',
        ROOT/'benchmark/tools/nib/v5_wip/preserve_fbx_point_payloads.py',ROOT/'benchmark/tools/nib/v5_wip/validate_triangulated_payload.py',
        ROOT/'benchmark/tools/animation/export_contract.py',ROOT/'benchmark/tools/animation/validate_motion_candidate.py']
    pins=[{'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p),'bytes':p.stat().st_size}
          for p in sorted(set([source,report,*scripts,*cards.glob('*.png'),*references.glob('*.png')]))]
    specs={
      'snapshot-source':([],['source-contract.json']),
      'bake':(['snapshot-source'],['pbr']),
      'snapshot-pbr':(['bake'],['pbr-contract.json']),
      'reference':(['snapshot-pbr'],['reference']),
      'triangles':(['reference'],['triangulated']),
      'validate-payload':(['triangles'],['triangulation-validation.json']),
      'validate-variant-natural':(['validate-payload'],['variant-Natural-validation.json']),
      'validate-variant-grip':(['validate-payload'],['variant-GripReplacement-validation.json']),
      'validate-variant-leg':(['validate-payload'],['variant-LegReplacement-validation.json']),
      'validate-clips':(['validate-payload'],['triangulated/roundtrip.json'])}
    stages={name:{'dependencies':deps,'outputs':[base+'/'+p for p in paths],
                  'freshOutputs':[base+'/'+p for p in paths]} for name,(deps,paths) in specs.items()}
    plan={'schemaVersion':1,'name':args.name,'source':source.relative_to(ROOT).as_posix(),
          'sourceSha256':args.source_sha256,'sourceReport':report.relative_to(ROOT).as_posix(),
          'cardTextureDirectory':cards.relative_to(ROOT).as_posix(),'referenceTextures':references.relative_to(ROOT).as_posix(),
          'outputRoot':base,'executionReady':not bool(args.blocked_reason),'executionBlockedReason':args.blocked_reason,
          'status':'Prepared only; no bake/export/import/visual acceptance from this plan',
          'artisticAcceptance':False,'sharedPromotionAuthorized':False,'pins':pins,'stages':stages}
    dest.mkdir(parents=True)
    (dest/'plan.json').write_text(json.dumps(plan,indent=2)+'\n',newline='\n')
    win=lambda path:'D:\\Dev\\Krag-Kings\\'+path.replace('/','\\')
    for stage in stages:
        log='benchmark/local/logs/'+args.name+'-'+stage
        spec={'name':args.name+'-'+stage,'executable':'D:\\Program Files\\Blender Foundation\\Blender 5.2\\blender.exe',
            'arguments':['--background','--threads','4','--python-exit-code','2','--python',
                         win('benchmark/tools/unreal/nib_candidate/run_stage.py'),'--','--plan',
                         win((dest/'plan.json').relative_to(ROOT).as_posix()),'--stage',stage],
            'workingDirectory':'D:\\Dev\\Krag-Kings','minAvailableGB':10,'maxPrivateGB':8,
            'stdout':win(log+'.log'),'stderr':win(log+'.stderr.log'),'successLog':win(log+'.log'),
            'successMarker':'NIB_CANDIDATE_STAGE_COMPLETE '+stage}
        (dest/(stage+'.job.json')).write_text(json.dumps(spec,indent=2)+'\n',newline='\n')
    print(json.dumps({'plan':str(dest/'plan.json'),'sourceSha256':args.source_sha256,
        'executionReady':plan['executionReady'],'pinnedFiles':len(pins),'jobCount':len(stages)},indent=2))


if __name__=='__main__':main()
