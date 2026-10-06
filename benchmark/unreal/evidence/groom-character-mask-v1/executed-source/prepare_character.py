"""Freeze the next bounded compile/mesh-mask boundary; does not launch Unreal."""
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
    parser.add_argument('--delivery',required=True)
    args=parser.parse_args()
    if not args.name.replace('-','').isalnum():raise RuntimeError('Unsafe attempt name')
    delivery_path=(ROOT/args.delivery).resolve()
    delivery=json.loads(delivery_path.read_text())
    if not delivery['bindingMask']['passed'] or delivery['variants']!=['Nib_Natural']:
        raise RuntimeError('Expected the validated isolated Natural target')
    output=ROOT/'benchmark/local/groom-probe'/args.name
    plans=HERE/'plans'/args.name
    if output.exists() or plans.exists():raise RuntimeError('Preserve earlier attempt')
    required=[delivery_path]
    for entry in [delivery['manifest'],delivery['fbx'],delivery['sourceSnapshot'],delivery['nativeGroomReport'],*delivery['checks'].values()]:
        path=ROOT/entry['path']
        if sha(path)!=entry['sha256']:raise RuntimeError('Delivery evidence/payload differs: '+entry['path'])
        required.append(path)
    required += [HERE/name for name in ('prepare_character.py','build.ps1','import_character_mesh.py','character_coordinates.py')]
    required += [ROOT/'benchmark/tools/unreal/BuildConfiguration.xml']
    required += [path for path in (HERE/'project').rglob('*') if path.is_file()]
    for path in required:
        if path.suffix=='.py':ast.parse(path.read_text())
    pins=[{'path':path.relative_to(ROOT).as_posix(),'sha256':sha(path),'bytes':path.stat().st_size} for path in sorted(set(required))]
    project=output/'GroomProbe'
    shutil.copytree(HERE/'project',project)
    ubt=project/'Saved/UnrealBuildTool';ubt.mkdir(parents=True)
    shutil.copyfile(ROOT/'benchmark/tools/unreal/BuildConfiguration.xml',ubt/'BuildConfiguration.xml')
    (output/'evidence').mkdir()
    plan={'schemaVersion':1,'name':args.name,'engine':'D:/Games/UE_5.8','pins':pins,
          'projectDirectory':project.relative_to(ROOT).as_posix(),'meshManifest':delivery['manifest']['path'],
          'groomSourceReport':delivery['nativeGroomReport']['path'],'delivery':args.delivery,
          'status':'Prepared; native compile/import not executed','maskAttribute':'KKGroomBindable',
          'geometryScope':'Natural only; exact22oldhead/eargroomobjectsremoved; body/facialfuzzretained',
          'bindingPending':True,'rendered':False,'sharedChanged':False,'artisticAcceptance':False}
    plans.mkdir(parents=True)
    for path in [plans/'plan.json',project/'character-plan.json']:
        path.write_text(json.dumps(plan,indent=2)+'\n',newline='\n')
    win=lambda path:'D:\\Dev\\Krag-Kings\\'+path.replace('/','\\')
    evidence=(output/'evidence').relative_to(ROOT).as_posix()
    common={'workingDirectory':'D:\\Dev\\Krag-Kings','minAvailableGB':10,'maxPrivateGB':8}
    build={**common,'name':args.name+'-build','executable':'C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe',
           'arguments':['-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',win('benchmark/tools/unreal/groom_probe/build.ps1'),
                        '-Plan',win((plans/'plan.json').relative_to(ROOT).as_posix())],
           'trackProcessTree':True,'maxTreePrivateGB':10,
           'stdout':win(evidence+'/build.stdout.log'),'stderr':win(evidence+'/build.stderr.log'),
           'successLog':win(evidence+'/build.stdout.log'),'successMarker':'KK_GROOM_PROBE_BUILD_COMPLETE'}
    mesh={**common,'name':args.name+'-mesh','executable':'D:\\Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe',
          'arguments':[win(plan['projectDirectory']+'/GroomProbe.uproject'),
                       '-ExecutePythonScript='+win('benchmark/tools/unreal/groom_probe/import_character_mesh.py'),
                       '-NullRHI','-unattended','-nosplash','-NoSound','-stdout','-FullStdOutLogOutput','-corelimit=2',
                       '-abslog='+win(evidence+'/mesh-editor.log')],
          'stdout':win(evidence+'/mesh.stdout.log'),'stderr':win(evidence+'/mesh.stderr.log'),
          'successLog':win(evidence+'/mesh.stdout.log'),'successMarker':'KK_GROOM_CHARACTER_MESH_COMPLETE'}
    for name,job in [('build',build),('mesh',mesh)]:
        (plans/(name+'.job.json')).write_text(json.dumps(job,indent=2)+'\n',newline='\n')
    print(json.dumps({'prepared':str(plans),'pins':len(pins),'stages':['build','mesh'],'launched':False},indent=2))


if __name__=='__main__':main()
