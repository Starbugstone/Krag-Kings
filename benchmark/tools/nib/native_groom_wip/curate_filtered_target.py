"""Retain the completed six-stage common groom target without changing its bytes."""
import csv
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / 'benchmark/local/candidates/nib-native-groom-filtered-v1'
DEST = ROOT / 'benchmark/art/nib/groom-study/native-filtered-target-v1'
STAGES = ['source', 'snapshot', 'reference', 'triangles', 'payload', 'variant']


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def record(path):
    return {'path': path.relative_to(ROOT).as_posix(), 'sha256': sha(path),
            'bytes': path.stat().st_size}


def main():
    if DEST.exists():
        raise RuntimeError('Preserve previous curated target')
    plan = ROOT / 'benchmark/tools/nib/native_groom_wip/filtered-plan-v1.json'
    for name in STAGES:
        receipt = json.loads((SOURCE / 'receipts' / (name + '.json')).read_text())
        if receipt['planSha256'] != sha(plan):
            raise RuntimeError('Wrong frozen plan ' + name)
        for output in receipt['outputs']:
            path = ROOT / output['path']
            if sha(path) != output['sha256'] or path.stat().st_size != output['bytes']:
                raise RuntimeError('Stage output changed: ' + output['path'])
    checks = {name: json.loads((SOURCE / (name + '-validation.json')).read_text())
              for name in ['payload', 'binding-mask', 'variant']}
    if not all(value['passed'] for value in checks.values()):
        raise RuntimeError('An actual validation failed')
    shutil.copytree(SOURCE, DEST)
    for file in SOURCE.rglob('*'):
        if file.is_file() and sha(file) != sha(DEST / file.relative_to(SOURCE)):
            raise RuntimeError('Curated copy changed bytes')
    execution = DEST / 'execution'
    execution.mkdir()
    memory = {}
    for name in STAGES:
        stem = 'nib-native-filtered-' + name + '-v1'
        log = ROOT / 'benchmark/local' / (stem + '.log')
        if 'NIB_NATIVE_FILTERED_STAGE_COMPLETE ' + name not in log.read_text():
            raise RuntimeError('Native completion marker absent: ' + name)
        for suffix in ['.log', '.stderr.log', '-memory.csv']:
            original = ROOT / 'benchmark/local' / (stem + suffix)
            shutil.copy2(original, execution / original.name)
            if sha(original) != sha(execution / original.name):
                raise RuntimeError('Raw execution evidence changed')
        with (execution / (stem + '-memory.csv')).open(newline='') as stream:
            samples = list(csv.DictReader(stream))
        memory[name] = {'peakPrivateMB': max(int(r['treePrivateMB']) for r in samples),
                        'minimumAvailableMB': min(int(r['availableMB']) for r in samples),
                        'peakCommitPercent': max(int(r['commitPercent']) for r in samples)}
    (DEST / '.gitattributes').write_text(
        '*.npz filter=lfs diff=lfs merge=lfs -text\n'
        'source-contract.json filter=lfs diff=lfs merge=lfs -text\n'
        'triangulated/export.json filter=lfs diff=lfs merge=lfs -text\n'
        'execution/*.log -text whitespace=cr-at-eol,-blank-at-eol,-blank-at-eof\n'
        'execution/*.csv -text whitespace=cr-at-eol,-blank-at-eol,-blank-at-eof\n', newline='\n')
    source_report = json.loads((DEST / 'source/source.json').read_text())
    manifest = json.loads((DEST / 'triangulated/manifest.json').read_text())
    variant = checks['variant']
    shapes = checks['payload']['variants'][0]['shapeTargets']
    receipt = {
        'status': 'actual isolated Natural target verified; not engine-bound or artistically accepted',
        'originalOutputRoot': SOURCE.relative_to(ROOT).as_posix(),
        'durableOutputRoot': DEST.relative_to(ROOT).as_posix(),
        'plan': record(plan),
        'filteredSource': record(DEST / 'source/Nib_NativeGroom_FilteredTarget_PBR.blend'),
        'sourceReport': record(DEST / 'source/source.json'),
        'sourceSnapshot': record(DEST / 'source-contract.json'),
        'manifest': record(DEST / 'triangulated/manifest.json'),
        'fbx': record(DEST / 'triangulated/Nib_Natural.fbx'),
        'nativeGroomReport': record(ROOT / 'benchmark/art/nib/groom-study/native-character-pilot-v1/source.json'),
        'nativeGroomSource': record(ROOT / 'benchmark/art/nib/groom-study/native-character-pilot-v1/Nib_NativeGroom_Pilot_v1.blend'),
        'variants': [v['name'] for v in manifest['variants']],
        'retainedSourceMeshes': 400, 'removedControlGroomObjects': 22,
        'geometry': {'vertices': variant['vertices'], 'triangles': variant['triangles'],
                     'bones': variant['boneCount'], 'morphs': len(variant['morphMaximumAbsoluteDeltaMeters'])},
        'maximumMorphDeltaRoundingMeters': max(s['denseDeltaMaxErrorMeters'] for s in shapes),
        'maximumPosePositionErrorMeters': max(c['maximumPosePositionErrorMeters'] for c in variant['clips'].values()),
        'maximumPoseRotationErrorDegrees': max(c['maximumPoseRotationErrorDegrees'] for c in variant['clips'].values()),
        'bindingMask': checks['binding-mask'],
        'coordinateContract': source_report['coordinateContract'],
        'animationReuse': manifest['animationReuse'],
        'stageMemory': memory,
        'checks': {key: record(DEST / (key + '-validation.json')) for key in checks},
        'files': [record(f) for f in sorted(DEST.rglob('*')) if f.is_file()],
        'standaloneClipsReexported': False,
        'runtimeActorCoordinateMappingVerified': False,
        'engineImported': False, 'runtimeBindingVerified': False,
        'artisticAcceptance': False, 'sharedChanged': False,
        'limitations': [
            'Existing face/body fine fuzz, chin cards, ear-base ridges, anatomy and clothing failures retained.',
            'Native groom geometry is external to the FBX; pair with the exact native source/report/sidecars.',
            'Raw mask proof does not prove engine attribute-buffer import or animated root binding.',
            'FBX morph deltas have bounded float32 rounding, not byte-exact sparse payloads.',
            'Pose check samples 17 frames per embedded take; not whole-cycle collision or visual acceptance.'
        ]
    }
    (DEST / 'delivery.json').write_text(json.dumps(receipt, indent=2) + '\n', newline='\n')
    print(json.dumps({'delivery': record(DEST / 'delivery.json'), 'fbx': receipt['fbx'],
                      'manifest': receipt['manifest'], 'memory': memory}, indent=2))


if __name__ == '__main__':
    main()
