"""Freeze a fresh export attempt while reusing hash-verified actual bake/reference.

Executed plans, successful inputs and failed partial exports remain untouched.
Only the new triangle/validation stages can write into the new isolated root.
"""
import argparse
import json
from pathlib import Path
from prepare_plan import ROOT, TOOLS, sha


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--prior-plan',type=Path,required=True)
    parser.add_argument('--name',required=True)
    args=parser.parse_args()
    if not args.name.replace('-','').isalnum():raise RuntimeError('Unsafe candidate name')
    original=args.prior_plan.resolve()
    old=json.loads(original.read_text())
    oldbase=ROOT/old['outputRoot']
    if not oldbase.resolve().is_relative_to((ROOT/'benchmark/local/candidates').resolve()):
        raise RuntimeError('Reuse only isolated outputs')
    destination=TOOLS/'plans'/args.name
    output='benchmark/local/candidates/'+args.name
    if destination.exists() or (ROOT/output).exists():raise RuntimeError('Preserve previous plan/output')
    pinned={}
    def pin(path,expected=None):
        path=path.resolve()
        if not path.is_relative_to(ROOT):raise RuntimeError('Pinned input outside project')
        digest=sha(path)
        if expected and digest!=expected:raise RuntimeError('Changed completed input: '+str(path))
        relative=path.relative_to(ROOT).as_posix()
        pinned[relative]={'path':relative,'sha256':digest,'bytes':path.stat().st_size}
    pin(original)
    completed=[]
    # Verify receipts against their actual original frozen plan, not today's
    # edited scripts. Today's exporter and helpers receive separate new pins.
    for stage in ['snapshot-source','bake','snapshot-pbr','reference']:
        receipt_path=oldbase/'receipts'/(stage+'.json')
        receipt=json.loads(receipt_path.read_text())
        if receipt['planSha256']!=sha(original) or receipt['stage']!=stage:
            raise RuntimeError('Completed receipt is from another plan')
        pin(receipt_path)
        for entry in receipt['outputs']:pin(ROOT/entry['path'],entry['sha256'])
        completed.append({'stage':stage,'receipt':receipt_path.relative_to(ROOT).as_posix(),'receiptSha256':sha(receipt_path)})
    # Preserve source/card authority from the original executed plan; do not
    # silently substitute current similarly named images or authored sources.
    for entry in old['pins']:
        if not entry['path'].startswith('benchmark/tools/'):
            pin(ROOT/entry['path'],entry['sha256'])
    scripts=[*TOOLS.glob('*.py'),ROOT/'benchmark/tools/nib/export_nib.py',
        *[ROOT/'benchmark/tools/nib/v5_wip'/name for name in [
            'preserve_fbx_point_payloads.py','validate_triangulated_payload.py',
            'triangulate_corners.py','triangle_corner_contract.py']],
        ROOT/'benchmark/tools/animation/export_contract.py',
        ROOT/'benchmark/tools/animation/validate_motion_candidate.py']
    for script in scripts:pin(script)
    stages={
        'triangles':{'dependencies':[],'outputs':[output+'/triangulated']},
        'validate-payload':{'dependencies':['triangles'],'outputs':[output+'/triangulation-validation.json']},
        **{'validate-variant-'+short:{'dependencies':['validate-payload'],
            'outputs':[output+'/variant-'+label+'-validation.json']}
            for short,label in [('natural','Natural'),('grip','GripReplacement'),('leg','LegReplacement')]},
        'validate-clips':{'dependencies':['validate-payload'],'outputs':[output+'/triangulated/roundtrip.json']}}
    for stage in stages.values():stage['freshOutputs']=stage['outputs'][:]
    plan={key:old[key] for key in ['source','sourceSha256','sourceReport','cardTextureDirectory','referenceTextures']}
    plan.update({'schemaVersion':1,'name':args.name,'outputRoot':output,'executionReady':True,
        'executionBlockedReason':'','status':'Prepared corrected export only; not executed',
        'artisticAcceptance':False,'sharedPromotionAuthorized':False,
        'priorPlan':original.relative_to(ROOT).as_posix(),'priorPlanSha256':sha(original),
        'reusedCompletedStages':completed,
        'reusedInputs':{'pbrRoot':old['outputRoot']+'/pbr','referenceRoot':old['outputRoot']+'/reference',
            'sourceSnapshot':old['outputRoot']+'/source-contract.json','pbrSnapshot':old['outputRoot']+'/pbr-contract.json'},
        'pins':[pinned[key] for key in sorted(pinned)],'stages':stages})
    destination.mkdir(parents=True)
    (destination/'plan.json').write_text(json.dumps(plan,indent=2)+'\n',newline='\n')
    win=lambda path:'D:\\Dev\\Krag-Kings\\'+path.replace('/','\\')
    for name in stages:
        log='benchmark/local/logs/'+args.name+'-'+name
        job={'name':args.name+'-'+name,'executable':'D:\\Program Files\\Blender Foundation\\Blender 5.2\\blender.exe',
            'arguments':['--background','--threads','4','--python-exit-code','2','--python',
                win('benchmark/tools/unreal/nib_candidate/run_stage.py'),'--','--plan',
                win((destination/'plan.json').relative_to(ROOT).as_posix()),'--stage',name],
            'workingDirectory':'D:\\Dev\\Krag-Kings','minAvailableGB':10,'maxPrivateGB':8,
            'stdout':win(log+'.log'),'stderr':win(log+'.stderr.log'),'successLog':win(log+'.log'),
            'successMarker':'NIB_CANDIDATE_STAGE_COMPLETE '+name}
        (destination/(name+'.job.json')).write_text(json.dumps(job,indent=2)+'\n',newline='\n')
    print(json.dumps({'plan':str(destination/'plan.json'),'reusedCompletedStages':len(completed),
        'pinnedFiles':len(pinned),'jobCount':len(stages),'executed':False},indent=2))


if __name__=='__main__':main()
