"""Execute one frozen review/export/roundtrip stage without changing shared data."""
import argparse
import json
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(Path(__file__).parents[1] / 'nib_candidate'))
from run_stage import sha, local, verify, collect, invoke


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--stage', required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    plan = json.loads(args.plan.read_text())
    verify(plan['pins'])
    base = local(plan['outputRoot'])
    if not base.is_relative_to((ROOT / 'benchmark/local/candidates').resolve()):
        raise RuntimeError('Delivery output must remain isolated')
    stage = plan['stages'][args.stage]
    receipt = base / 'receipts' / (args.stage + '.json')
    if receipt.exists():
        raise RuntimeError('Preserve previous execution receipt')
    checked = set()
    def dependency(name):
        if name in checked:
            return
        for ancestor in plan['stages'][name]['dependencies']:
            dependency(ancestor)
        data = json.loads((base / 'receipts' / (name + '.json')).read_text())
        if data['planSha256'] != sha(args.plan) or data['stage'] != name:
            raise RuntimeError('Dependency belongs to another frozen attempt')
        verify(data['outputs'])
        checked.add(name)
    for name in stage['dependencies']:
        dependency(name)
    for path in stage['freshOutputs']:
        if local(path).exists():
            raise RuntimeError('Preserve earlier output: ' + path)
    final = base / 'triangulated'
    reference = base / 'reference'
    if args.stage == 'snapshot-coat':
        invoke('benchmark/tools/unreal/krag_candidate/snapshot_source.py',
               ['--source', local(plan['pbrSource']), '--source-sha256', plan['pbrSourceSha256'],
                '--selection-contract', local(plan['selectionContract']),
                '--compare', local(plan['originalSourceSnapshot']), '--output', local(plan['pbrSnapshot'])])
    elif args.stage.startswith('review-'):
        invoke('benchmark/tools/unreal/krag_candidate/review_materials.py',
               ['--plan', args.plan, '--side', args.stage.removeprefix('review-')])
    elif args.stage in ('reference', 'triangles'):
        if args.stage == 'reference':
            review_path = local(plan['reusedMaterialReview']) if 'reusedMaterialReview' in plan else base / 'material-review.json'
            review = json.loads(review_path.read_text())
            if review.get('materialTransferAccepted') is not True:
                raise RuntimeError('Matched material images require an actual recorded inspection')
            if 'reusedMaterialReview' in plan:
                if review.get('candidateSha256') != plan['pbrSourceSha256']:
                    raise RuntimeError('Inspected optical correction is not the export source')
            elif review.get('planSha256') != sha(args.plan):
                raise RuntimeError('Material review comes from another frozen attempt')
            for side in ['source', 'baked']:
                report_path = local(review[side+'Report']) if 'reusedMaterialReview' in plan else base / ('review-' + side) / 'review.json'
                if review['reviewReportHashes'][side] != sha(report_path):
                    raise RuntimeError('Inspected material view set changed')
        command = ['--export-only', '--source-runtime', local(plan['pbrSource']),
                   '--contract', local(plan['pbrSelectionContract']),
                   '--texture-source-dir', local(plan['pbrSource']).parent / 'textures',
                   '--output-dir', reference if args.stage == 'reference' else final]
        if args.stage == 'triangles':
            command += ['--triangulate', '--baseline-dir', reference]
        invoke('benchmark/tools/krag/export_krag.py', command)
        if args.stage == 'triangles':
            manifest = json.loads((final / 'manifest.json').read_text())
            source = json.loads(local(plan['pbrSnapshot']).read_text())
            report = json.loads(local(plan['pbrBakeReport']).read_text())
            if manifest['sourceSha256'] != source['sourceSha256']:
                raise RuntimeError('Export source differs from the verified PBR source')
            if {v['name'] for v in manifest['variants']} != set(plan['variants']):
                raise RuntimeError('Full five-variant inventory differs')
            expected = {entry['name']: entry for entry in report['materials']}
            if {entry['name'] for entry in manifest['materials']} != set(expected):
                raise RuntimeError('Exported material-role set differs from the baked source')
            for entry in manifest['materials']:
                for field in ['hasCoatParameters', 'coatWeight', 'coatRoughness', 'coatIor']:
                    if entry.get(field) != expected[entry['name']].get(field):
                        raise RuntimeError('Optical material metadata changed during export')
                for channel in ['baseColor', 'normal', 'roughness', 'metallic']:
                    path = Path(entry[channel])
                    if path.is_absolute() or len(path.parts) != 2 or path.parts[0] != 'textures':
                        raise RuntimeError('Texture escapes portable root')
                    if entry[channel] != expected[entry['name']][channel]:
                        raise RuntimeError('Material texture mapping changed')
                    if sha(final / path) != expected[entry['name']]['mapHashes'][channel]:
                        raise RuntimeError('Baked texture bytes changed during export')
            if set(manifest['animations']) != set(source['clips']):
                raise RuntimeError('Canonical standalone clip coverage differs')
            source['bindReference'] = {'file': 'Krag_Natural.fbx',
                                       'sha256': sha(final / 'Krag_Natural.fbx')}
            for name, clip in source['clips'].items():
                clip['file'] = manifest['animations'][name]
                clip['sha256'] = sha(final / clip['file'])
            (final / 'export.json').write_text(json.dumps(source, indent=2) + '\n', newline='\n')
    elif args.stage == 'validate-payload':
        script = local('benchmark/tools/nib/v5_wip/validate_triangulated_payload.py')
        sys.argv = [str(script), '--source-dir', str(reference), '--candidate-dir', str(final),
                    '--output', str(base / 'triangulation-validation.json'), '--names', *plan['variants']]
        runpy.run_path(str(script), run_name='__main__')
    elif args.stage.startswith('validate-variant-'):
        invoke('benchmark/tools/unreal/nib_candidate/validate_variant.py',
               ['--directory', final, '--source-contract', local(plan['pbrSnapshot']),
                '--variant', stage['variant'], '--expected-bones', '68',
                '--output', local(stage['outputs'][0])])
    elif args.stage == 'validate-clips':
        invoke('benchmark/tools/animation/validate_motion_candidate.py', ['--directory', final])
    else:
        raise RuntimeError('Unknown delivery stage')
    verify(plan['pins'])
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps({'stage': args.stage, 'planSha256': sha(args.plan),
        'outputs': collect(stage['outputs']), 'artisticAcceptance': False,
        'sharedAssetsChanged': False, 'engineImportVerified': False}, indent=2) + '\n', newline='\n')
    print('KRAG_DELIVERY_STAGE_COMPLETE ' + args.stage, flush=True)


if __name__ == '__main__':
    main()
