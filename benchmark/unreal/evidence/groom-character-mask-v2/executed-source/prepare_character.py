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
    parser.add_argument('--reuse-compiled-plan')
    parser.add_argument('--compiled-evidence')
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
    required += [HERE/name for name in ('prepare_character.py','build.ps1','import_character_mesh.py','character_coordinates.py','audit_armature_wrapper.py')]
    required += [ROOT/'benchmark/tools/unreal/BuildConfiguration.xml']
    required += [path for path in (HERE/'project').rglob('*') if path.is_file()]
    reuse=None
    project=output/'GroomProbe'
    if args.reuse_compiled_plan:
        if not args.compiled_evidence:raise RuntimeError('Actual successful compile evidence is required')
        old_plan_path=ROOT/args.reuse_compiled_plan
        old=json.loads(old_plan_path.read_text())
        compile_evidence_path=ROOT/args.compiled_evidence
        compiled=json.loads(compile_evidence_path.read_text())['stages']['build']
        if compiled['nativeExit']!=0 or compiled['guardExit']!=0 or not compiled['completionMarkerPresent']:
            raise RuntimeError('Previous native compile did not pass')
        project=(ROOT/old['projectDirectory']).resolve()
        if not project.is_relative_to(ROOT/'benchmark/local/groom-probe'):
            raise RuntimeError('Refuse external editor-project reuse')
        prefix=(HERE/'project').relative_to(ROOT).as_posix()+'/'
        for pin in old['pins']:
            if pin['path'].startswith(prefix):
                if sha(ROOT/pin['path'])!=pin['sha256'] or sha(project/pin['path'][len(prefix):])!=pin['sha256']:
                    raise RuntimeError('Native project source changed; a new compile is required')
        binaries=[project/'Binaries/Win64/UnrealEditor-GroomProbe.dll',project/'Binaries/Win64/UnrealEditor.modules']
        if not all(path.is_file() for path in binaries):raise RuntimeError('Validated native module is unavailable')
        if sha(project/'character-plan.json')!=sha(old_plan_path):raise RuntimeError('Active project recipe differs; inspect before replacing it')
        required += [old_plan_path,compile_evidence_path,*binaries]
        reuse={'previousPlan':args.reuse_compiled_plan,'actualCompileEvidence':args.compiled_evidence,
               'nativeSourceAndCopiedProjectExact':True,'newCompileExecuted':False,
               'previousActivePlanSha256':sha(old_plan_path)}
    for path in required:
        if path.suffix=='.py':ast.parse(path.read_text())
    pins=[{'path':path.relative_to(ROOT).as_posix(),'sha256':sha(path),'bytes':path.stat().st_size} for path in sorted(set(required))]
    if reuse:
        output.mkdir(parents=True)
        shutil.copyfile(project/'character-plan.json',output/'previous-active-character-plan.json')
    else:
        shutil.copytree(HERE/'project',project)
        ubt=project/'Saved/UnrealBuildTool';ubt.mkdir(parents=True)
        shutil.copyfile(ROOT/'benchmark/tools/unreal/BuildConfiguration.xml',ubt/'BuildConfiguration.xml')
    (output/'evidence').mkdir()
    plan={'schemaVersion':1,'name':args.name,'engine':'D:/Games/UE_5.8','pins':pins,
          'projectDirectory':project.relative_to(ROOT).as_posix(),'meshManifest':delivery['manifest']['path'],
          'groomSourceReport':delivery['nativeGroomReport']['path'],'delivery':args.delivery,
          'evidenceDirectory':(output/'evidence').relative_to(ROOT).as_posix(),'reusedCompiledEditor':reuse,
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
    jobs=[('mesh',mesh)] if reuse else [('build',build),('mesh',mesh)]
    for name,job in jobs:
        (plans/(name+'.job.json')).write_text(json.dumps(job,indent=2)+'\n',newline='\n')
    print(json.dumps({'prepared':str(plans),'pins':len(pins),'stages':[name for name,_ in jobs],'launched':False},indent=2))


if __name__=='__main__':main()
