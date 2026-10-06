"""Freeze a separate project for full native strands; never launch or change the saved mask project."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import shutil

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--name',required=True)
    parser.add_argument('--mesh-evidence',required=True)
    args=parser.parse_args()
    if not args.name.replace('-','').isalnum():raise RuntimeError('Unsafe attempt name')
    mesh_evidence=ROOT/args.mesh_evidence
    result=json.loads((mesh_evidence/'result.json').read_text())
    raw_path=mesh_evidence/'execution/mesh-result.json'
    raw=json.loads(raw_path.read_text(encoding='utf-8-sig'))
    if result['stage']['guardExit']!=0 or not raw['passed'] or raw['sourceToMeshAxes']['boneCount']!=79:
        raise RuntimeError('Require actual masked79 target origin pass')
    old_plan=json.loads((mesh_evidence/'executed-plan/plan.json').read_text())
    source_path=ROOT/old_plan['groomSourceReport']
    source=json.loads(source_path.read_text())
    if source['curveCount']!=26000 or source['pointCount']!=234000:
        raise RuntimeError('Keep exact frozen26k pilot')
    output=ROOT/'benchmark/local/groom-probe'/args.name
    plans=HERE/'plans'/args.name
    if output.exists() or plans.exists():raise RuntimeError('Preserve previous attempt')
    required=[mesh_evidence/'result.json',raw_path,mesh_evidence/'executed-plan/plan.json',source_path]
    for pin in old_plan['pins']:
        if pin['path']==old_plan['groomSourceReport'] and sha(source_path)!=pin['sha256']:
            raise RuntimeError('Frozen native source report changed')
    for entry in source['exports']:
        path=source_path.parent/entry['path']
        if sha(path)!=entry['sha256']:raise RuntimeError('ABC payload changed')
        required.append(path)
    for region in source['regions']:
        for meta in region['files'].values():
            path=source_path.parent/region['dataDirectory']/meta['path']
            if sha(path)!=meta['sha256'] or path.stat().st_size!=meta['bytes']:
                raise RuntimeError('Native strand sidecar changed')
            required.append(path)
    for entry in result['savedPackages']:
        path=ROOT/entry['path']
        if sha(path)!=entry['sha256']:raise RuntimeError('Saved masked target changed')
        required.append(path)
    scripts=['prepare_character_binding.py','build.ps1','import_character_grooms.py','character_coordinates.py']
    required += [HERE/name for name in scripts]
    required += [path for path in (HERE/'project').rglob('*') if path.is_file()]
    required.append(ROOT/'benchmark/tools/unreal/BuildConfiguration.xml')
    for path in required:
        if path.suffix=='.py':ast.parse(path.read_text())
    project=output/'GroomProbe'
    shutil.copytree(HERE/'project',project)
    target_dir=project/'Content/Character';target_dir.mkdir(parents=True)
    copied=[]
    for entry in result['savedPackages']:
        path=ROOT/entry['path'];destination=target_dir/path.name
        shutil.copyfile(path,destination)
        if sha(destination)!=entry['sha256']:raise RuntimeError('Target copy changed')
        copied.append({'path':destination.relative_to(ROOT).as_posix(),'sha256':entry['sha256'],'bytes':entry['bytes']})
        required.append(destination)
    ubt=project/'Saved/UnrealBuildTool';ubt.mkdir(parents=True)
    shutil.copyfile(ROOT/'benchmark/tools/unreal/BuildConfiguration.xml',ubt/'BuildConfiguration.xml')
    evidence=output/'evidence';evidence.mkdir()
    pins=[{'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(set(required))]
    plan={'schemaVersion':1,'name':args.name,'engine':'D:/Games/UE_5.8','pins':pins,
          'projectDirectory':project.relative_to(ROOT).as_posix(),
          'evidenceDirectory':evidence.relative_to(ROOT).as_posix(),
          'actualMeshResult':raw_path.relative_to(ROOT).as_posix(),
          'groomSourceReport':source_path.relative_to(ROOT).as_posix(),
          'copiedTargetPackages':copied,'maskAttribute':'KKGroomBindable',
          'positionToleranceCentimeters':0.0002,
          'positionToleranceReason':'2 micrometers; frozen native ABC roundtrip measured0.954 micrometers, allows the additional float32 centimeters conversion; tiny fixture gate unchanged',
          'rootProjectionToleranceCentimeters':0.01,
          'rootProjectionToleranceReason':'0.1mm surface-contact gate includes native half-precision barycentric encoding; not a character alignment offset or auto-fit',
          'conversion':{'rotationEulerDegrees':[-90,0,0],'scale':[100,100,-100],
                        'axes':'ABC(x,z,-y) meters -> verified mesh(100x,-100y,100z) centimeters'},
          'status':'Prepared compile/import/binding/reload only; native execution pending',
          'simulation':False,'globalInterpolation':False,'rendered':False,'sharedChanged':False,'artisticAcceptance':False}
    plans.mkdir(parents=True)
    for path in [plans/'plan.json',project/'groom-character-plan.json']:
        path.write_text(json.dumps(plan,indent=2)+'\n',newline='\n')
    win=lambda value:'D:\\Dev\\Krag-Kings\\'+value.replace('/','\\')
    evid=evidence.relative_to(ROOT).as_posix()
    common={'workingDirectory':'D:\\Dev\\Krag-Kings','minAvailableGB':10,'maxPrivateGB':8}
    build={**common,'name':args.name+'-build','executable':'C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe',
           'arguments':['-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',
                        win('benchmark/tools/unreal/groom_probe/build.ps1'),'-Plan',win((plans/'plan.json').relative_to(ROOT).as_posix())],
           'trackProcessTree':True,'maxTreePrivateGB':10,
           'stdout':win(evid+'/build.stdout.log'),'stderr':win(evid+'/build.stderr.log'),
           'successLog':win(evid+'/build.stdout.log'),'successMarker':'KK_GROOM_PROBE_BUILD_COMPLETE'}
    jobs={'build':build}
    for stage in ['grooms','reload']:
        argv=[win(plan['projectDirectory']+'/GroomProbe.uproject'),
              '-ExecutePythonScript='+win('benchmark/tools/unreal/groom_probe/import_character_grooms.py'),
              '-NullRHI','-unattended','-nosplash','-NoSound','-stdout','-FullStdOutLogOutput','-corelimit=2',
              '-abslog='+win(evid+'/'+stage+'-editor.log')]
        if stage=='reload':argv.append('-KKGroomReload')
        jobs[stage]={**common,'name':args.name+'-'+stage,'executable':'D:\\Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe',
                     'arguments':argv,'stdout':win(evid+'/'+stage+'.stdout.log'),'stderr':win(evid+'/'+stage+'.stderr.log'),
                     'successLog':win(evid+'/'+stage+'.stdout.log'),
                     'successMarker':'KK_GROOM_CHARACTER_'+('RELOAD' if stage=='reload' else 'BINDING')+'_COMPLETE'}
    for name,job in jobs.items():(plans/(name+'.job.json')).write_text(json.dumps(job,indent=2)+'\n',newline='\n')
    print(json.dumps({'prepared':str(plans),'pins':len(pins),'stages':list(jobs),'launched':False},indent=2))


if __name__=='__main__':main()
