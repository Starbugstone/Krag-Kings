"""Repin full exports to an actual inspected coat correction; launch nothing."""
import argparse
import json
from pathlib import Path
from prepare_delivery import ROOT, TOOLS, sha


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--old-delivery-plan', type=Path, required=True)
    parser.add_argument('--coat-plan', type=Path, required=True)
    parser.add_argument('--name', required=True)
    args = parser.parse_args()
    if not args.name.replace('-', '').isalnum(): raise RuntimeError('Unsafe plan name')
    old = json.loads(args.old_delivery_plan.read_text())
    coat = json.loads(args.coat_plan.read_text())
    base = ROOT / coat['outputRoot']
    dest = TOOLS/'plans'/args.name
    output = 'benchmark/local/candidates/'+args.name
    if dest.exists() or (ROOT/output).exists(): raise RuntimeError('Preserve previous attempt')
    pins = {}
    def pin(path, expected=None):
        path = path.resolve(); digest = sha(path)
        if expected and digest != expected: raise RuntimeError('Frozen actual input changed: '+str(path))
        relative = path.relative_to(ROOT).as_posix()
        pins[relative] = {'path': relative, 'sha256': digest, 'bytes': path.stat().st_size}
    for item in old['pins']:
        if not item['path'].startswith('benchmark/tools/'):
            pin(ROOT/item['path'],item['sha256'])
    pin(args.coat_plan); pin(args.old_delivery_plan)
    for stage in ['repair','review']:
        receipt_path = base/'receipts'/(stage+'.json'); receipt=json.loads(receipt_path.read_text())
        if receipt['planSha256'] != sha(args.coat_plan) or receipt['stage'] != stage:
            raise RuntimeError('Coat completion receipt differs')
        pin(receipt_path)
        for item in receipt['outputs']: pin(ROOT/item['path'],item['sha256'])
    review_path=base/'material-review.json';review=json.loads(review_path.read_text());pin(review_path)
    if review.get('materialTransferAccepted') is not True: raise RuntimeError('Actual coat view review failed')
    for side in ['source','baked']:pin(ROOT/review[side+'Report'],review['reviewReportHashes'][side])
    for item in old['pins']:
        if item['path'].startswith('benchmark/tools/') and item['path'].endswith('.py'):pin(ROOT/item['path'])
    for path in [Path(__file__),TOOLS/'snapshot_source.py',TOOLS/'bake_runtime.py',
                 ROOT/'benchmark/tools/unreal/nib_candidate/snapshot_source.py',
                 ROOT/'benchmark/tools/animation/krag_hand_rebuild/morph_drivers.py']:pin(path)
    plan = dict(old)
    plan.update({'name':args.name,'outputRoot':output,'pbrSource':coat['pbrSource'],
        'pbrSourceSha256':review['candidateSha256'],'pbrSelectionContract':coat['outputRoot']+'/pbr/krag_asset_contract.json',
        'pbrBakeReport':coat['outputRoot']+'/pbr/pbr-bake-report.json','pbrSnapshot':output+'/pbr-contract.json',
        'originalSourceSnapshot':'benchmark/local/candidates/krag-coherent68-motion-fe152-v1/source-contract.json',
        'reusedMaterialReview':review_path.relative_to(ROOT).as_posix(),
        'status':'Prepared export/roundtrip stages after actual scalar correction and two-view optical pass'})
    plan.pop('materialInspectionGate',None)
    stages={'snapshot-coat':{'dependencies':[],'outputs':[plan['pbrSnapshot']]}}
    for name, old_stage in old['stages'].items():
        if name.startswith('review-'):continue
        stage=dict(old_stage)
        stage['outputs']=[path.replace(old['outputRoot'],output) for path in old_stage['outputs']]
        if name=='reference':stage['dependencies']=['snapshot-coat']
        stages[name]=stage
    for stage in stages.values():stage['freshOutputs']=stage['outputs'][:]
    plan.update({'stages':stages,'pins':[pins[key] for key in sorted(pins)]})
    dest.mkdir(parents=True);(dest/'plan.json').write_text(json.dumps(plan,indent=2)+'\n',newline='\n')
    win=lambda p:'D:\\Dev\\Krag-Kings\\'+p.replace('/','\\')
    for name in stages:
        log='benchmark/local/logs/'+args.name+'-'+name
        job={'name':args.name+'-'+name,'executable':'D:\\Program Files\\Blender Foundation\\Blender 5.2\\blender.exe',
            'arguments':['--background','--threads','4','--python-exit-code','2','--python',
                win('benchmark/tools/unreal/krag_candidate/run_delivery_stage.py'),'--','--plan',
                win((dest/'plan.json').relative_to(ROOT).as_posix()),'--stage',name],
            'workingDirectory':'D:\\Dev\\Krag-Kings','minAvailableGB':10,'maxPrivateGB':8,
            'stdout':win(log+'.log'),'stderr':win(log+'.stderr.log'),
            'successLog':win(log+'.log'),'successMarker':'KRAG_DELIVERY_STAGE_COMPLETE '+name}
        (dest/(name+'.job.json')).write_text(json.dumps(job,indent=2)+'\n',newline='\n')
    print(json.dumps({'prepared':str(dest/'plan.json'),'pins':len(pins),'stages':list(stages),'executed':False},indent=2))


if __name__ == '__main__':main()
