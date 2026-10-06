"""Stage exact existing Nib PBR dependencies into the isolated strand pilot.

No production project, source textures or package files are modified.
"""
from pathlib import Path
import hashlib,json,re,shutil

ROOT=Path(__file__).resolve().parents[4]
PILOT=ROOT/'benchmark/local/unity-strand-hair-pilot'
SOURCE=ROOT/'benchmark/unity'
PROJECT=PILOT/'project'
OUT=PILOT/'prepared-character-render-v1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    if OUT.exists():raise RuntimeError('Preserve existing preparation')
    index={}
    for p in (SOURCE/'Assets').rglob('*.meta'):
        match=re.search(r'^guid: ([a-f0-9]{32})$',p.read_text(errors='strict'),re.M)
        if match:index[match[1]]=p.with_suffix('')
    pending=list((SOURCE/'Assets/Benchmark/Generated').glob('Nib_*.mat'))
    pending.append(SOURCE/'Assets/Benchmark/Generated/NibSkinProfile.asset')
    copied={};external=set()
    while pending:
        src=pending.pop();relative=src.relative_to(SOURCE).as_posix()
        if relative in copied:continue
        if src.suffix not in ('.mat','.asset','.png'):raise RuntimeError(f'Unexpected dependency {src}')
        if not src.is_file():raise RuntimeError(f'Missing dependency {src}')
        if src.suffix in ('.mat','.asset'):
            for guid in set(re.findall(r'guid: ([a-f0-9]{32})',src.read_text())):
                if guid in index:pending.append(index[guid])
                else:external.add(guid)
        for file in (src,Path(str(src)+'.meta')):
            dst=PROJECT/file.relative_to(SOURCE);dst.parent.mkdir(parents=True,exist_ok=True)
            if dst.exists() and sha(dst)!=sha(file):raise RuntimeError(f'Conflicting isolated asset {dst}')
            if not dst.exists():shutil.copy2(file,dst)
            copied[file.relative_to(SOURCE).as_posix()]=sha(dst)
    graph=PILOT/'prepared-authored-shader-v1/NativeFurAuthored.shadergraph'
    shader=PROJECT/'Assets/NativeGroom/NativeFurAuthored.shadergraph'
    if shader.exists() and sha(shader)!=sha(graph):raise RuntimeError('Conflicting shader')
    shutil.copy2(graph,shader)
    recipe=Path(__file__).with_name('CharacterRenderProbe.cs')
    shutil.copy2(recipe,PROJECT/'Assets/Editor'/recipe.name)
    OUT.mkdir()
    receipt={'status':'Prepared only; full character GPU render pending','materialFiles':[p for p in copied if p.endswith('.mat')],
             'copiedFiles':copied,'packageOrBuiltinGuids':sorted(external),'shaderSha256':sha(graph),'recipeSha256':sha(recipe),
             'importReceiptSha256':sha(PILOT/'character-import-v3/import.json')}
    (OUT/'preparation.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print('CHARACTER_RENDER_STAGED',len(copied),'files')
if __name__=='__main__':main()
