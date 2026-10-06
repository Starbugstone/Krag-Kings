"""Run one frozen, isolated candidate stage inside the guarded Blender process."""
import argparse
import hashlib
import json
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[4]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def local(relative):
    path = (ROOT / relative).resolve()
    if not path.is_relative_to(ROOT):
        raise RuntimeError('Path escapes project: ' + relative)
    return path


def verify(entries):
    for entry in entries:
        path = local(entry['path'])
        if not path.is_file() or sha(path) != entry['sha256']:
            raise RuntimeError('Frozen input changed: ' + entry['path'])


def invoke(script, args):
    path = local(script)
    sys.argv = [str(path), '--'] + [str(x) for x in args]
    runpy.run_path(str(path), run_name='__main__')


def collect(paths):
    files = []
    for path in paths:
        path = local(path)
        files.extend(sorted(p for p in path.rglob('*') if p.is_file()) if path.is_dir() else [path])
    return [{'path': p.relative_to(ROOT).as_posix(), 'sha256': sha(p), 'bytes': p.stat().st_size}
            for p in sorted(set(files))]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--stage', required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    plan = json.loads(args.plan.read_text())
    if not plan['executionReady']:
        raise RuntimeError('Preparation only: ' + plan['executionBlockedReason'])
    verify(plan['pins'])
    stage = plan['stages'][args.stage]
    base = local(plan['outputRoot'])
    if not base.is_relative_to((ROOT/'benchmark/local/candidates').resolve()):
        raise RuntimeError('Candidate output must be isolated')
    receipt = base / 'receipts' / (args.stage + '.json')
    if receipt.exists():
        raise RuntimeError('Preserve prior stage receipt; choose a fresh attempt')
    checked = set()
    def verify_dependency(dependency):
        if dependency in checked:
            return
        for ancestor in plan['stages'][dependency]['dependencies']:
            verify_dependency(ancestor)
        prior = json.loads((base / 'receipts' / (dependency + '.json')).read_text())
        if prior['planSha256'] != sha(args.plan) or prior['stage'] != dependency:
            raise RuntimeError('Dependency belongs to a different frozen plan')
        verify(prior['outputs'])
        checked.add(dependency)
    for dependency in stage['dependencies']:
        verify_dependency(dependency)
    for path in stage.get('freshOutputs', []):
        if local(path).exists():
            raise RuntimeError('Preserve earlier output: ' + path)
    output = base / 'pbr'
    baked = output / 'Nib_Runtime_PBR.blend'
    bake_report = output / 'pbr-bake-report.json'
    reference = base / 'reference'
    final = base / 'triangulated'
    snapshot = base / 'source-contract.json'
    pbr_snapshot = base / 'pbr-contract.json'
    cards = local(plan['cardTextureDirectory'])
    if args.stage in ['snapshot-source', 'snapshot-pbr']:
        source = local(plan['source']) if args.stage == 'snapshot-source' else baked
        source_sha = plan['sourceSha256'] if args.stage == 'snapshot-source' else json.loads(bake_report.read_text())['candidateSha256']
        command = ['--source', source, '--source-sha256', source_sha, '--output', snapshot if args.stage == 'snapshot-source' else pbr_snapshot]
        if args.stage == 'snapshot-pbr':
            command += ['--compare', snapshot]
        invoke('benchmark/tools/unreal/nib_candidate/snapshot_source.py', command)
    elif args.stage == 'bake':
        invoke('benchmark/tools/nib/v5_wip/pbr/prepare_runtime_pbr.py', [
            '--source', local(plan['source']), '--source-report', local(plan['sourceReport']),
            '--out', output, '--reference-textures', local(plan['referenceTextures']),
            '--card-texture-dir', cards])
    elif args.stage in ['reference', 'triangles']:
        command = ['--source', baked, '--source-report', bake_report,
            '--out', reference if args.stage == 'reference' else final,
            '--texture-dir', output/'textures', '--card-texture-dir', cards,
            '--baseline-dir', reference]
        if args.stage == 'triangles':
            command += ['--triangulate']
        invoke('benchmark/tools/nib/export_nib.py', command)
        if args.stage == 'triangles':
            # Feed the actual full-mesh/standalone exports to the existing strict
            # source-pose roundtrip checker; no duplicate animation export.
            report = json.loads(pbr_snapshot.read_text())
            manifest = json.loads((final/'manifest.json').read_text())
            if report['sourceSha256'] != manifest['sourceSha256']:
                raise RuntimeError('Export source differs from audited PBR source')
            for material in manifest['materials']:
                for channel in ['baseColor', 'normal', 'roughness', 'metallic']:
                    relative = Path(material[channel])
                    if relative.is_absolute() or len(relative.parts) != 2 or relative.parts[0] != 'textures':
                        raise RuntimeError('Material path escapes textures directory')
                    if not (final/relative).is_file():
                        raise RuntimeError('Missing portable material texture')
                if material.get('alphaMode') == 'MASK':
                    original = next(m for m in report['groomMaterials'] if m['name'] == material['name'])
                    if any(material.get(key) != value for key, value in original.items()):
                        raise RuntimeError('Masked material contract changed in export')
                    for channel in ['baseColor', 'normal', 'roughness', 'metallic']:
                        if sha(final/material[channel]) != sha(cards/Path(material[channel]).name):
                            raise RuntimeError('Original groom atlas bytes changed')
            report['bindReference'] = {'file':'Nib_Natural.fbx', 'sha256':sha(final/'Nib_Natural.fbx')}
            if set(manifest['animations']) != set(report['clips']):
                raise RuntimeError('Standalone clip contract is incomplete')
            for name, entry in report['clips'].items():
                entry['file'] = manifest['animations'][name]
                entry['sha256'] = sha(final/entry['file'])
            (final/'export.json').write_text(json.dumps(report,indent=2)+'\n',newline='\n')
    elif args.stage == 'validate-payload':
        # Plain argparse in this raw-FBX tool does not use Blender's -- split.
        path = local('benchmark/tools/nib/v5_wip/validate_triangulated_payload.py')
        sys.argv = [str(path), '--source-dir',str(reference), '--candidate-dir',str(final),
                    '--output',str(base/'triangulation-validation.json')]
        runpy.run_path(str(path),run_name='__main__')
    elif args.stage.startswith('validate-variant-'):
        label = {'natural':'Natural','grip':'GripReplacement','leg':'LegReplacement'}[args.stage.rsplit('-',1)[-1]]
        invoke('benchmark/tools/unreal/nib_candidate/validate_variant.py', [
            '--directory',final,'--source-contract',pbr_snapshot,'--variant','Nib_'+label,
            '--output',base/('variant-'+label+'-validation.json')])
    elif args.stage == 'validate-clips':
        invoke('benchmark/tools/animation/validate_motion_candidate.py',['--directory', final])
    else:
        raise RuntimeError('Unknown stage')
    verify(plan['pins'])
    receipt.parent.mkdir(parents=True,exist_ok=True)
    result = {'stage':args.stage,'planSha256':sha(args.plan),'outputs':collect(stage['outputs']),
        'artisticAcceptance':False,'sharedAssetsChanged':False,'engineImportVerified':False}
    receipt.write_text(json.dumps(result,indent=2)+'\n',newline='\n')
    print('NIB_CANDIDATE_STAGE_COMPLETE '+args.stage,flush=True)


if __name__ == '__main__':
    main()
