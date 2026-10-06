"""Freeze a separate tiny UE groom project and guarded jobs; launch nothing."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', required=True)
    parser.add_argument('--restore-point-widths', action='store_true')
    args = parser.parse_args()
    if not args.name.replace('-', '').isalnum():
        raise RuntimeError('Unsafe attempt name')
    output = ROOT / 'benchmark/local/groom-probe' / args.name
    plan_dir = HERE / 'plans' / args.name
    if output.exists() or plan_dir.exists():
        raise RuntimeError('Preserve earlier probe attempt')
    fixture = ROOT / 'benchmark/art/nib/groom-study/native-hair-fixture-v1/fixture.json'
    data = json.loads(fixture.read_text())
    dependencies = [fixture, HERE/'import_fixture.py', HERE/'reload_fixture.py', HERE/'build.ps1', HERE/'prepare.py',
                    ROOT/'benchmark/tools/unreal/BuildConfiguration.xml',
                    *[p for p in (HERE/'project').rglob('*') if p.is_file()]]
    for entry in data['exports']:
        path = fixture.parent / entry['path']
        if sha(path) != entry['sha256']:
            raise RuntimeError('Actual ABC fixture no longer matches receipt')
        dependencies.append(path)
    ast.parse((HERE/'import_fixture.py').read_text())
    pins = [{'path': p.relative_to(ROOT).as_posix(), 'sha256': sha(p), 'bytes': p.stat().st_size}
            for p in sorted(set(dependencies))]
    project = output/'GroomProbe'
    shutil.copytree(HERE/'project', project)
    ubt = project/'Saved/UnrealBuildTool'
    ubt.mkdir(parents=True)
    shutil.copy2(ROOT/'benchmark/tools/unreal/BuildConfiguration.xml', ubt/'BuildConfiguration.xml')
    (output/'evidence').mkdir()
    plan = {'schemaVersion': 1, 'name': args.name, 'pins': pins,
            'projectDirectory': project.relative_to(ROOT).as_posix(),
            'fixture': fixture.relative_to(ROOT).as_posix(),
            'engine': 'D:/Games/UE_5.8', 'status': 'Prepared, no compile/import/render execution',
            'characterBindingVerified': False, 'artisticAcceptance': False, 'sharedChanged': False,
            'restorePointWidthsFromExactSidecar': args.restore_point_widths}
    plan_dir.mkdir(parents=True)
    for path in [plan_dir/'plan.json', project/'probe-plan.json']:
        path.write_text(json.dumps(plan, indent=2)+'\n', newline='\n')
    win = lambda p: 'D:\\Dev\\Krag-Kings\\'+p.replace('/', '\\')
    evidence = (output/'evidence').relative_to(ROOT).as_posix()
    build = {'name': args.name+'-build', 'executable': 'C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe',
        'arguments': ['-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',win('benchmark/tools/unreal/groom_probe/build.ps1'),
                      '-Plan',win((plan_dir/'plan.json').relative_to(ROOT).as_posix())],
        'workingDirectory': 'D:\\Dev\\Krag-Kings', 'minAvailableGB': 10, 'maxPrivateGB': 8,
        'trackProcessTree': True, 'maxTreePrivateGB': 10,
        'stdout': win(evidence+'/build.stdout.log'), 'stderr': win(evidence+'/build.stderr.log'),
        'successLog': win(evidence+'/build.stdout.log'), 'successMarker': 'KK_GROOM_PROBE_BUILD_COMPLETE'}
    imp = {'name': args.name+'-import', 'executable': 'D:\\Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe',
        'arguments': [win(plan['projectDirectory']+'/GroomProbe.uproject'),
            '-ExecutePythonScript='+win('benchmark/tools/unreal/groom_probe/import_fixture.py'),
            '-NullRHI','-unattended','-nosplash','-NoSound','-stdout','-FullStdOutLogOutput','-corelimit=2',
            '-abslog='+win(evidence+'/editor.log')],
        'workingDirectory': 'D:\\Dev\\Krag-Kings', 'minAvailableGB': 10, 'maxPrivateGB': 8,
        'stdout': win(evidence+'/import.stdout.log'), 'stderr': win(evidence+'/import.stderr.log'),
        'successLog': win(evidence+'/import.stdout.log'), 'successMarker': 'KK_GROOM_FIXTURE_IMPORT_COMPLETE'}
    jobs = [('build',build),('import',imp)]
    if args.restore_point_widths:
        reload_job = dict(imp)
        reload_job.update({'name':args.name+'-reload',
            'arguments':[value.replace('import_fixture.py','reload_fixture.py').replace('/editor.log','/reload-editor.log').replace('\\editor.log','\\reload-editor.log') for value in imp['arguments']],
            'stdout':win(evidence+'/reload.stdout.log'),'stderr':win(evidence+'/reload.stderr.log'),
            'successLog':win(evidence+'/reload.stdout.log'),'successMarker':'KK_GROOM_FIXTURE_RELOAD_COMPLETE'})
        jobs.append(('reload',reload_job))
    for name, job in jobs:
        (plan_dir/(name+'.job.json')).write_text(json.dumps(job, indent=2)+'\n', newline='\n')
    print(json.dumps({'prepared': str(plan_dir), 'project': str(project), 'pins': len(pins), 'launched': False}, indent=2))


if __name__ == '__main__':
    main()
