"""Execute one pinned material-preparation stage in an isolated guarded process."""
import argparse
import json
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(Path(__file__).parents[1]/'nib_candidate'))
from run_stage import sha, local, verify, collect


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--stage', choices=['snapshot-source', 'bake', 'snapshot-pbr'], required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    plan = json.loads(args.plan.read_text()); verify(plan['pins'])
    base = local(plan['outputRoot'])
    if not base.is_relative_to((ROOT/'benchmark/local/candidates').resolve()):
        raise RuntimeError('Candidate output must remain isolated')
    stage = plan['stages'][args.stage]; receipt = base/'receipts'/(args.stage+'.json')
    if receipt.exists(): raise RuntimeError('Preserve earlier execution receipt')
    checked = set()
    def dependency(name):
        if name in checked: return
        for ancestor in plan['stages'][name]['dependencies']: dependency(ancestor)
        data = json.loads((base/'receipts'/(name+'.json')).read_text())
        if data['planSha256'] != sha(args.plan) or data['stage'] != name:
            raise RuntimeError('Dependency receipt belongs to a different plan')
        verify(data['outputs']); checked.add(name)
    for name in stage['dependencies']: dependency(name)
    if any(local(path).exists() for path in stage['outputs']):
        raise RuntimeError('Preserve previous candidate output')
    pbr = base/'pbr'; baked = pbr/'Krag_Runtime_PBR.blend'
    if args.stage == 'bake':
        script = Path(__file__).with_name('bake_runtime.py')
        command = ['--source', local(plan['source']), '--source-sha256', plan['sourceSha256'],
                   '--selection-contract', local(plan['selectionContract']),
                   '--source-contract', base/'source-contract.json', '--out', pbr]
    else:
        script = Path(__file__).with_name('snapshot_source.py')
        command = ['--source', baked if args.stage == 'snapshot-pbr' else local(plan['source']),
                   '--source-sha256', sha(baked) if args.stage == 'snapshot-pbr' else plan['sourceSha256'],
                   '--selection-contract', local(plan['selectionContract']),
                   '--output', local(stage['outputs'][0])]
        if args.stage == 'snapshot-pbr': command += ['--compare', base/'source-contract.json']
    sys.argv = [str(script), '--'] + list(map(str, command))
    runpy.run_path(str(script), run_name='__main__')
    verify(plan['pins'])
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps({'planSha256': sha(args.plan), 'stage': args.stage,
        'outputs': collect(stage['outputs']), 'nativeStagePassed': True,
        'artisticAcceptance': False, 'sharedAssetsChanged': False}, indent=2)+'\n', newline='\n')
    print('KRAG_CANDIDATE_STAGE_COMPLETE '+args.stage, flush=True)


if __name__ == '__main__': main()
