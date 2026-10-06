"""Freeze the coherent68 source and three initial material stages; launch nothing."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).parent


def sha(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for data in iter(lambda: stream.read(1024*1024), b''): value.update(data)
    return value.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', required=True)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--source-sha256', required=True)
    parser.add_argument('--selection-contract', type=Path, required=True)
    parser.add_argument('--source-report', type=Path, required=True)
    args = parser.parse_args()
    source, contract, report = (p.resolve() for p in [args.source, args.selection_contract, args.source_report])
    if not args.name.replace('-', '').isalnum(): raise RuntimeError('Unsafe candidate name')
    if sha(source) != args.source_sha256: raise RuntimeError('Saved source hash differs')
    data = json.loads(contract.read_text())
    if data['source_blend_sha256'] != args.source_sha256 or data['bone_count'] != 68:
        raise RuntimeError('Source selection contract differs')
    if json.loads(report.read_text())['output']['sha256'] != args.source_sha256:
        raise RuntimeError('Actual saved/reopened merge report differs')
    dest = HERE/'plans'/args.name
    if dest.exists(): raise RuntimeError('Preserve frozen plan')
    dependencies = [*HERE.glob('*.py'),
        ROOT/'benchmark/tools/unreal/nib_candidate/snapshot_source.py',
        ROOT/'benchmark/tools/unreal/nib_candidate/run_stage.py',
        ROOT/'benchmark/tools/animation/export_contract.py',
        ROOT/'benchmark/tools/animation/krag_hand_rebuild/morph_drivers.py',
        ROOT/'benchmark/tools/nib/v5_wip/pbr/bake_fields.py',
        ROOT/'benchmark/tools/nib/v5_wip/pbr/portable_save.py']
    pins = [{'path': p.relative_to(ROOT).as_posix(), 'bytes': p.stat().st_size, 'sha256': sha(p)}
            for p in sorted(set([source, contract, report, *dependencies]))]
    base = 'benchmark/local/candidates/'+args.name
    stages = {'snapshot-source': {'dependencies': [], 'outputs': [base+'/source-contract.json']},
              'bake': {'dependencies': ['snapshot-source'], 'outputs': [base+'/pbr']},
              'snapshot-pbr': {'dependencies': ['bake'], 'outputs': [base+'/pbr-contract.json']}}
    plan = {'schemaVersion': 1, 'name': args.name, 'source': source.relative_to(ROOT).as_posix(),
        'sourceSha256': args.source_sha256, 'selectionContract': contract.relative_to(ROOT).as_posix(),
        'sourceReport': report.relative_to(ROOT).as_posix(), 'outputRoot': base,
        'pins': pins, 'stages': stages, 'authoredVariants': list(data['variants']),
        'status': 'Prepared source/PBR stages only; full matching exports and review follow actual bake proof',
        'artisticAcceptance': False, 'sharedPromotionAuthorized': False}
    dest.mkdir(parents=True)
    (dest/'plan.json').write_text(json.dumps(plan, indent=2)+'\n', newline='\n')
    win = lambda path: 'D:\\Dev\\Krag-Kings\\'+path.replace('/', '\\')
    for stage in stages:
        log = 'benchmark/local/logs/'+args.name+'-'+stage
        job = {'name': args.name+'-'+stage,
            'executable': 'D:\\Program Files\\Blender Foundation\\Blender 5.2\\blender.exe',
            'arguments': ['--background','--threads','4','--python-exit-code','2','--python',
                win('benchmark/tools/unreal/krag_candidate/run_stage.py'), '--', '--plan',
                win((dest/'plan.json').relative_to(ROOT).as_posix()), '--stage', stage],
            'workingDirectory': 'D:\\Dev\\Krag-Kings', 'minAvailableGB': 10, 'maxPrivateGB': 8,
            'stdout': win(log+'.log'), 'stderr': win(log+'.stderr.log'),
            'successLog': win(log+'.log'), 'successMarker': 'KRAG_CANDIDATE_STAGE_COMPLETE '+stage}
        (dest/(stage+'.job.json')).write_text(json.dumps(job, indent=2)+'\n', newline='\n')
    print(json.dumps({'plan': str(dest/'plan.json'), 'pins': len(pins), 'stages': list(stages)}, indent=2))


if __name__ == '__main__': main()
