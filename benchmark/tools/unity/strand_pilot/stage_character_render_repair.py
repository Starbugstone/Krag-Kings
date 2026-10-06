"""Stage the bounded v2 shader/light repair after preserving actual v1 failure."""
from pathlib import Path
import json,hashlib,shutil
ROOT=Path(__file__).resolve().parents[4]
PILOT=ROOT/'benchmark/local/unity-strand-hair-pilot'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    evidence=ROOT/'benchmark/evidence/unity/native-character-render-v1-shader-failed'
    out=PILOT/'prepared-character-render-v2'
    if out.exists():raise RuntimeError('Preserve prior repair preparation')
    previous=json.loads((evidence/'readiness.json').read_text());shader=PILOT/'project/Assets/NativeGroom/NativeFurAuthored.shadergraph'
    recipe=PILOT/'project/Assets/Editor/CharacterRenderProbe.cs'
    if sha(shader)!=sha(evidence/'executed-NativeFurAuthored.shadergraph') or sha(recipe)!=sha(evidence/'executed-CharacterRenderProbe.cs'):
        raise RuntimeError('Staged files differ from preserved failed execution')
    for x in previous['files']:
        p=ROOT/x['path']
        if p not in (shader,recipe):
            if sha(p)!=x['sha256']:raise RuntimeError('Unrelated frozen input changed: '+str(p))
    shutil.copy2(PILOT/'prepared-authored-shader-v2/NativeFurAuthored.shadergraph',shader)
    shutil.copy2(Path(__file__).with_name('CharacterRenderProbe.cs'),recipe)
    job=Path(__file__).with_name('character-render-v2.job.json')
    files=[]
    for x in previous['files']:
        p=ROOT/x['path']
        if p.name=='character-render-v1.job.json':p=job
        files.append({'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p)})
    out.mkdir();(out/'readiness.json').write_text(json.dumps({'status':'Prepared v2 only; native result pending','files':files},indent=2)+'\n')
    print('CHARACTER_RENDER_V2_STAGED',len(files))
if __name__=='__main__':main()
