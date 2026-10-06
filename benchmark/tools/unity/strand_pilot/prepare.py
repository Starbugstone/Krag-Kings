"""Prepare an isolated, version-pinned native strand package probe; never edits the demo."""
from pathlib import Path
import hashlib,json,shutil,subprocess
REPO=Path(__file__).resolve().parents[4]
LOCAL=REPO/'benchmark/local/unity-strand-hair-pilot'
PIN={'source':'75a7f446209896bc1bce0da2682cfdbdf30ce447','digital-human':'8d61864050277f2c4574df7b31beb70093a8c263'}
for name,expected in PIN.items():
    actual=subprocess.check_output(['git','-C',str(LOCAL/name),'rev-parse','HEAD'],text=True).strip()
    if actual!=expected:raise RuntimeError(f'{name}: commit changed')
    if subprocess.check_output(['git','-C',str(LOCAL/name),'status','--porcelain'],text=True).strip():raise RuntimeError(f'{name}: source modified')
project=LOCAL/'project'
if project.exists():raise RuntimeError('Preserve the existing pilot; refusing to overwrite')
(project/'Assets/Editor').mkdir(parents=True)
(project/'Packages').mkdir()
shutil.copytree(REPO/'benchmark/unity/ProjectSettings',project/'ProjectSettings')
shutil.copytree(REPO/'benchmark/unity/Assets/Settings',project/'Assets/Settings')
shutil.copy2(REPO/'benchmark/unity/Assets/Settings.meta',project/'Assets/Settings.meta')
# Local package locations refer to the exact clean source pins checked above.
deps=json.loads((REPO/'benchmark/unity/Packages/manifest.json').read_text())['dependencies']
deps.update({'com.unity.demoteam.hair':'file:../../source','com.unity.demoteam.digital-human':'file:../../digital-human'})
for module in ('physics','wind','animation','audio','imgui','jsonserialize'):
    deps[f'com.unity.modules.{module}']='1.0.0'
(project/'Packages/manifest.json').write_text(json.dumps({'dependencies':deps},indent=2)+'\n')
shutil.copy2(Path(__file__).with_name('CompatibilityProbe.cs'),project/'Assets/Editor/CompatibilityProbe.cs')
asm={'name':'KragKings.StrandPilot.Editor','includePlatforms':['Editor'],'references':['Unity.DemoTeam.Hair.Runtime','Unity.DemoTeam.Hair.Editor','Unity.DemoTeam.DigitalHuman.Runtime','Unity.RenderPipelines.HighDefinition.Runtime','Unity.RenderPipelines.Core.Runtime'],'allowUnsafeCode':False}
(project/'Assets/Editor/StrandPilot.Editor.asmdef').write_text(json.dumps(asm,indent=2)+'\n')
receipt={'status':'Prepared only; native compilation not run','pins':PIN,'settingsSource':'benchmark/unity','files':{str(p.relative_to(project)):hashlib.sha256(p.read_bytes()).hexdigest() for p in project.rglob('*') if p.is_file()},'licenses':'Both upstream packages are Unity Companion licensed; used only in the Unity pilot. Authored Blender curves remain independent.'}
(LOCAL/'preparation.json').write_text(json.dumps(receipt,indent=2)+'\n')
print('KK_STRAND_PILOT_PREPARED',project)
