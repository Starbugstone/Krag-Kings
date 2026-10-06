"""Consume an explicitly reviewed hash/license inventory inside the task venv only."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT/'benchmark/local/triposr-reference-v1'
DOWNLOADED = ROOT/'benchmark/local/triposr-downloads-v1'
def sha(path):
    checksum = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            checksum.update(block)
    return checksum.hexdigest()


def extract_pinned(archive, target):
    if target.exists():
        raise RuntimeError('Preserve prior extracted source')
    target.mkdir(parents=True)
    with zipfile.ZipFile(archive) as zipped:
        prefix = zipped.namelist()[0].split('/')[0]
        for item in zipped.infolist():
            relative = Path(*item.filename.split('/')[1:])
            if item.filename.split('/')[0] != prefix or '..' in relative.parts:
                raise RuntimeError('Archive member escapes pinned source root')
            if item.is_dir() or not relative.parts:
                continue
            destination = target/relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            with zipped.open(item) as src, destination.open('wb') as dst:
                shutil.copyfileobj(src, dst, 1024*1024)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--inventory-sha256', required=True)
    args = parser.parse_args()
    if os.name != 'nt':
        raise RuntimeError('Windows task environment only')
    inventory_path = BASE/'dependency-license-inventory.json'
    if sha(inventory_path) != args.inventory_sha256:
        raise RuntimeError('Inventory is not the exact reviewed file')
    inventory = json.loads(inventory_path.read_text(encoding='utf-8'))
    lock = BASE/'windows-reference.lock'
    if sha(lock) != inventory['lockSha256']:
        raise RuntimeError('Resolved lock changed')
    if (BASE/'installation.json').exists():
        raise RuntimeError('Preserve prior installation receipt')
    receipt = json.loads((DOWNLOADED/'download-receipt.json').read_text(encoding='utf-8'))
    for entry in receipt['files']:
        if sha(DOWNLOADED/entry['name']) != entry['sha256']:
            raise RuntimeError('Pinned downloaded content changed: '+entry['name'])
    python = BASE/'venv/Scripts/python.exe'
    env = dict(os.environ)
    env.pop('PYTHONPATH', None)
    env.update({'PYTHONNOUSERSITE':'1','PIP_DISABLE_PIP_VERSION_CHECK':'1','PIP_CONFIG_FILE':os.devnull,
        'PIP_INDEX_URL':'https://pypi.org/simple','PIP_EXTRA_INDEX_URL':'',
        'PIP_CACHE_DIR':str(BASE/'cache/pip'),'TMP':str(BASE/'temp'),'TEMP':str(BASE/'temp'),
        'HF_HOME':str(BASE/'cache/huggingface'),'TORCH_HOME':str(BASE/'cache/torch'),
        'TORCH_EXTENSIONS_DIR':str(BASE/'cache/torch-extensions'),
        'MAX_JOBS':'2','OMP_NUM_THREADS':'2','DISTUTILS_USE_SDK':'1'})
    def run(command, cwd=BASE):
        print('ISOLATED_INSTALL_COMMAND', json.dumps([str(x) for x in command]), flush=True)
        subprocess.run([str(x) for x in command], cwd=cwd, env=env, check=True)
    run([python,'-m','pip','install','--require-hashes','--no-deps','--no-build-isolation','-r',lock])
    tripo = BASE/'sources/TripoSR'
    cubes = BASE/'sources/torchmcubes'
    extract_pinned(DOWNLOADED/'TripoSR-107cefdc.zip', tripo)
    extract_pinned(DOWNLOADED/'torchmcubes-bc36b08c.zip', cubes)
    setup = Path(__file__).with_name('setup_torchmcubes_cpu.py')
    shutil.copy2(setup, cubes/'setup_cpu_reference.py')
    vcvars = Path('D:/DevTools/VS2022BuildTools/VC/Auxiliary/Build/vcvars64.bat')
    if not vcvars.is_file():
        raise RuntimeError('Existing VS2022 toolchain is unavailable')
    batch = BASE/'build-cpu-extension.cmd'
    batch.write_text('@echo off\ncall "'+str(vcvars)+'"\nif errorlevel 1 exit /b %errorlevel%\n"'
        +str(python)+'" "'+str(cubes/'setup_cpu_reference.py')+'" bdist_wheel --dist-dir "'
        +str(BASE/'downloads')+'"\nexit /b %errorlevel%\n', encoding='utf-8', newline='\r\n')
    run(['cmd.exe','/d','/c',batch], cubes)
    wheels = list((BASE/'downloads').glob('torchmcubes-*.whl'))
    if len(wheels) != 1:
        raise RuntimeError('Expected one pinned native extension wheel')
    run([python,'-m','pip','install','--no-index','--no-deps',wheels[0]])
    run([python,'-m','pip','check'])
    run([python,'-c',"import torch,torchmcubes; a=torch.arange(16,dtype=torch.float32); x,y,z=torch.meshgrid(a,a,a,indexing='ij'); v,f=torchmcubes.marching_cubes((x-7.5)**2+(y-7.5)**2+(z-7.5)**2,25.0); assert len(v)>0 and len(f)>0; print('CPU_EXTENSION_SMOKE',torch.__version__,len(v),len(f))"])
    # Only config data is seeded: TripoSR already contains DINO weights.
    hub = BASE/'cache/huggingface/hub/models--facebook--dino-vitb16'
    revision = 'f205d5d8e640a89a2b8ef0369670dfc37cc07fc2'
    snapshot = hub/'snapshots'/revision
    snapshot.mkdir(parents=True)
    shutil.copy2(DOWNLOADED/'dino-config.json', snapshot/'config.json')
    (hub/'refs').mkdir()
    (hub/'refs/main').write_text(revision)
    model = BASE/'models/TripoSR'
    model.mkdir()
    # Same-volume hardlinks avoid another1.6GB checkpoint copy; immutable hashes
    # are checked again before any future model load.
    os.link(DOWNLOADED/'model.ckpt', model/'model.ckpt')
    shutil.copy2(DOWNLOADED/'triposr-config.yaml',model/'config.yaml')
    result = {'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'inventorySha256':sha(inventory_path),'lockSha256':sha(lock),
        'recipeSha256':sha(__file__),'cpuExtensionRecipeSha256':sha(setup),
        'cpuExtensionWheel':str(wheels[0]),'cpuExtensionWheelSha256':sha(wheels[0]),
        'cpuExtensionSmokePassed':True,'pipCheckPassed':True,'inferenceExecuted':False,
        'systemPythonModified':False,'globalPathChanged':False,'gpuDriverChanged':False,
        'sourceArchives':[{k:x[k] for k in ['name','sha256']} for x in receipt['files'] if x['name'].endswith('.zip')]}
    (BASE/'installation.json').write_text(json.dumps(result,indent=2)+'\n')
    print('TRIPOSR_ISOLATED_INSTALL_COMPLETE',flush=True)


if __name__=='__main__':
    main()
