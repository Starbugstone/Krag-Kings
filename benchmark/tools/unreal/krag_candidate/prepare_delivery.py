"""Freeze matching review/full-FBX stages from actual completed PBR receipts."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TOOLS = Path(__file__).parent


def sha(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(data)
    return result.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--initial-plan', type=Path, required=True)
    parser.add_argument('--name', required=True)
    args = parser.parse_args()
    if not args.name.replace('-', '').isalnum():
        raise RuntimeError('Unsafe plan name')
    old_path = args.initial_plan.resolve()
    old = json.loads(old_path.read_text())
    base = (ROOT / old['outputRoot']).resolve()
    destination = TOOLS / 'plans' / args.name
    output = 'benchmark/local/candidates/' + args.name
    if not base.is_relative_to((ROOT / 'benchmark/local/candidates').resolve()):
        raise RuntimeError('Only isolated actual PBR inputs may be reused')
    if destination.exists() or (ROOT / output).exists():
        raise RuntimeError('Preserve prior plan and outputs')
    pins = {}
    def pin(path, expected=None):
        path = Path(path).resolve()
        if not path.is_relative_to(ROOT):
            raise RuntimeError('Input is outside the project')
        digest = sha(path)
        if expected and digest != expected:
            raise RuntimeError('Completed input changed: ' + str(path))
        relative = path.relative_to(ROOT).as_posix()
        pins[relative] = {'path': relative, 'sha256': digest, 'bytes': path.stat().st_size}
    pin(old_path)
    completed = []
    for name in ['snapshot-source', 'bake', 'snapshot-pbr']:
        path = base / 'receipts' / (name + '.json')
        receipt = json.loads(path.read_text())
        if receipt['stage'] != name or receipt['planSha256'] != sha(old_path) or not receipt['nativeStagePassed']:
            raise RuntimeError('Completed stage proof belongs to a different attempt')
        pin(path)
        for item in receipt['outputs']:
            pin(ROOT / item['path'], item['sha256'])
        completed.append({'stage': name, 'receipt': path.relative_to(ROOT).as_posix(), 'sha256': sha(path)})
    for item in old['pins']:
        if not item['path'].startswith('benchmark/tools/'):
            pin(ROOT / item['path'], item['sha256'])
    source = json.loads((base / 'source-contract.json').read_text())
    baked = json.loads((base / 'pbr-contract.json').read_text())
    for key in ['rig', 'geometryWeightsMorphs', 'fields', 'correctiveDriverContracts', 'clips', 'locomotion']:
        if source[key] != baked[key]:
            raise RuntimeError('Saved PBR comparison differs: ' + key)
    for image in source['connectedSourceImages']:
        if image['storage'] == 'file':
            relative = image['path'].replace('\\', '/').split('/Krag-Kings/', 1)[1]
            pin(ROOT / relative, image['sha256'])
    scripts = [
        TOOLS / 'prepare_delivery.py', TOOLS / 'run_delivery_stage.py', TOOLS / 'review_materials.py',
        ROOT / 'benchmark/tools/krag/export_krag.py',
        ROOT / 'benchmark/tools/krag/material_cache.py',
        ROOT / 'benchmark/tools/krag/triangulate_runtime_mesh.py',
        ROOT / 'benchmark/tools/unreal/nib_candidate/run_stage.py',
        ROOT / 'benchmark/tools/unreal/nib_candidate/validate_variant.py',
        ROOT / 'benchmark/tools/animation/export_contract.py',
        ROOT / 'benchmark/tools/animation/validate_motion_candidate.py',
        *[ROOT / 'benchmark/tools/nib/v5_wip' / name for name in [
            'triangulate_corners.py', 'triangle_corner_contract.py',
            'preserve_fbx_point_payloads.py', 'validate_triangulated_payload.py']],
    ]
    for path in scripts:
        pin(path)
    stages = {
        'review-source': {'dependencies': [], 'outputs': [output + '/review-source']},
        'review-baked': {'dependencies': [], 'outputs': [output + '/review-baked']},
        'reference': {'dependencies': ['review-source', 'review-baked'], 'outputs': [output + '/reference']},
        'triangles': {'dependencies': ['reference'], 'outputs': [output + '/triangulated']},
        'validate-payload': {'dependencies': ['triangles'], 'outputs': [output + '/triangulation-validation.json']},
        **{'validate-variant-' + name.removeprefix('Krag_').lower(): {
            'dependencies': ['validate-payload'], 'variant': name,
            'outputs': [output + '/' + name + '-validation.json']}
           for name in old['authoredVariants']},
        'validate-clips': {'dependencies': ['validate-payload'], 'outputs': [output + '/triangulated/roundtrip.json']},
    }
    for stage in stages.values():
        stage['freshOutputs'] = stage['outputs'][:]
    plan = {'schemaVersion': 1, 'name': args.name, 'outputRoot': output,
            'source': old['source'], 'sourceSha256': old['sourceSha256'],
            'selectionContract': old['selectionContract'],
            'pbrSource': (base / 'pbr/Krag_Runtime_PBR.blend').relative_to(ROOT).as_posix(),
            'pbrSelectionContract': (base / 'pbr/krag_asset_contract.json').relative_to(ROOT).as_posix(),
            'pbrSnapshot': (base / 'pbr-contract.json').relative_to(ROOT).as_posix(),
            'pbrBakeReport': (base / 'pbr/pbr-bake-report.json').relative_to(ROOT).as_posix(),
            'reusedCompletedStages': completed, 'variants': old['authoredVariants'],
            'pins': [pins[key] for key in sorted(pins)], 'stages': stages,
            'status': 'Prepared; no native review/export stage executed',
            'materialInspectionGate': output + '/material-review.json',
            'artisticAcceptance': False, 'sharedPromotionAuthorized': False}
    destination.mkdir(parents=True)
    (destination / 'plan.json').write_text(json.dumps(plan, indent=2) + '\n', newline='\n')
    win = lambda relative: 'D:\\Dev\\Krag-Kings\\' + relative.replace('/', '\\')
    for name in stages:
        stem = 'benchmark/local/logs/' + args.name + '-' + name
        job = {'name': args.name + '-' + name,
               'executable': 'D:\\Program Files\\Blender Foundation\\Blender 5.2\\blender.exe',
               'arguments': ['--background', '--threads', '4', '--python-exit-code', '2', '--python',
                             win('benchmark/tools/unreal/krag_candidate/run_delivery_stage.py'),
                             '--', '--plan', win((destination / 'plan.json').relative_to(ROOT).as_posix()),
                             '--stage', name],
               'workingDirectory': 'D:\\Dev\\Krag-Kings', 'minAvailableGB': 10, 'maxPrivateGB': 8,
               'stdout': win(stem + '.log'), 'stderr': win(stem + '.stderr.log'),
               'successLog': win(stem + '.log'), 'successMarker': 'KRAG_DELIVERY_STAGE_COMPLETE ' + name}
        (destination / (name + '.job.json')).write_text(json.dumps(job, indent=2) + '\n', newline='\n')
    print(json.dumps({'preparedPlan': str(destination / 'plan.json'), 'nativeStageCount': len(stages),
                      'pinnedFiles': len(pins), 'executed': False}, indent=2))


if __name__ == '__main__':
    main()
