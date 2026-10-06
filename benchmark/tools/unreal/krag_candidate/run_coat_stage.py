"""Execute a pinned scalar-only coat correction or its two matched views."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(Path(__file__).parents[1] / 'nib_candidate'))
from run_stage import sha, local, verify, collect, invoke


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--stage', choices=['repair', 'review'], required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    plan = json.loads(args.plan.read_text())
    verify(plan['pins'])
    base = local(plan['outputRoot'])
    if not base.is_relative_to((ROOT / 'benchmark/local/candidates').resolve()):
        raise RuntimeError('Candidate must remain isolated')
    receipt = base / 'receipts' / (args.stage + '.json')
    if receipt.exists():
        raise RuntimeError('Preserve existing execution receipt')
    if args.stage == 'repair':
        invoke('benchmark/tools/unreal/krag_candidate/repair_coat.py', [
            '--source', local(plan['source']), '--source-sha256', plan['sourceSha256'],
            '--pbr', local(plan['failedPbrSource']), '--pbr-sha256', plan['failedPbrSha256'],
            '--bake-report', local(plan['failedBakeReport']), '--contract', local(plan['failedPbrContract']),
            '--out', base / 'pbr'])
        outputs = [str((base / 'pbr').relative_to(ROOT))]
    else:
        prior = json.loads((base / 'receipts/repair.json').read_text())
        if prior['planSha256'] != sha(args.plan):
            raise RuntimeError('Repair comes from a different frozen plan')
        verify(prior['outputs'])
        invoke('benchmark/tools/unreal/krag_candidate/review_materials.py', ['--plan', args.plan, '--side', 'baked'])
        outputs = [str((base / 'review-baked').relative_to(ROOT))]
    verify(plan['pins'])
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps({'stage': args.stage, 'planSha256': sha(args.plan),
        'outputs': collect(outputs), 'artisticAcceptance': False, 'sharedAssetsChanged': False,
        'engineImportVerified': False}, indent=2) + '\n', newline='\n')
    print('KRAG_COAT_STAGE_COMPLETE ' + args.stage, flush=True)


if __name__ == '__main__':
    main()
