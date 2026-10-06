"""Resolve a disposable Windows-only TripoSR environment; no inference/install of runtime deps.

Run as a guarded job. Creates only a new task venv/cache, bootstraps pinned packaging tools,
then downloads dependency metadata/wheels for a dry-run resolution. A separate
reviewed installation step must consume the resulting hashes and licenses.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import urllib.request

ROOT=Path(__file__).resolve().parents[3]
OUTPUT=ROOT/'benchmark/local/triposr-reference-v1'
TRIPO_COMMIT='107cefdc244c39106fa830359024f6a2f1c78871'
MCUBES_COMMIT='bc36b08c62c5931e1dfc666581b3a8589278647f'


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def read_json(url):
    request=urllib.request.Request(url,headers={'User-Agent':'KragKings-isolated-reference-setup'})
    with urllib.request.urlopen(request,timeout=60) as stream:return json.load(stream)


def download(url,path,expected):
    request=urllib.request.Request(url,headers={'User-Agent':'KragKings-isolated-reference-setup'})
    with urllib.request.urlopen(request,timeout=90) as stream,path.open('wb') as out:
        while block:=stream.read(1024*1024):out.write(block)
    if sha(path)!=expected:raise RuntimeError('Downloaded file hash mismatch '+path.name)


def run(command,env):
    print('SETUP_COMMAND',json.dumps([str(x) for x in command]),flush=True)
    subprocess.run([str(x) for x in command],env=env,cwd=OUTPUT,check=True)


def main():
    if os.name!='nt' or sys.version_info[:2]!=(3,10):
        raise RuntimeError('Use the existing Windows Python3.10 only')
    if OUTPUT.exists():raise RuntimeError('Preserve prior setup attempt')
    OUTPUT.mkdir(parents=True)
    paths={name:OUTPUT/name for name in ['cache','temp','models','downloads','licenses','sources','evidence']}
    for path in paths.values():path.mkdir()
    env=dict(os.environ)
    env.update({'PIP_CACHE_DIR':str(paths['cache']/'pip'),'TMP':str(paths['temp']),
        'TEMP':str(paths['temp']),'HF_HOME':str(paths['cache']/'huggingface'),
        'TORCH_HOME':str(paths['cache']/'torch'),'PYTHONNOUSERSITE':'1',
        'PIP_DISABLE_PIP_VERSION_CHECK':'1','MAX_JOBS':'2'})
    env.pop('PYTHONPATH',None)
    bootstrap=[];bootstrap_wheels=[]
    # Explicit build tools avoid an unpinned isolated backend for OmegaConf's
    # pure-Python antlr dependency, which PyPI publishes only as an sdist.
    for name,version in [('pip','25.3'),('setuptools','75.6.0'),('wheel','0.45.1'),('packaging','24.2')]:
        url=f'https://pypi.org/pypi/{name}/{version}/json'
        meta=read_json(url)
        wheel=next(x for x in meta['urls'] if x['filename'].endswith('py3-none-any.whl'))
        bootstrap.append({'name':name,'version':version,'url':wheel['url'],
            'sha256':wheel['digests']['sha256'],
            'license':meta['info'].get('license_expression') or meta['info'].get('license'),
            'classifiers':meta['info'].get('classifiers'), 'metadataSource':url})
        destination=paths['downloads']/wheel['filename']
        download(wheel['url'],destination,wheel['digests']['sha256'])
        bootstrap_wheels.append(destination)
    (OUTPUT/'bootstrap.json').write_text(json.dumps(bootstrap,indent=2)+'\n')
    run([sys.executable,'-m','venv',OUTPUT/'venv'],env)
    python=OUTPUT/'venv/Scripts/python.exe'
    run([python,'-m','pip','install','--no-index','--no-deps',*bootstrap_wheels],env)
    requirements=ROOT/'benchmark/tools/triposr/windows-reference.in'
    download_receipt=ROOT/'benchmark/local/triposr-downloads-v1/download-receipt.json'
    downloaded=json.loads(download_receipt.read_text())
    torch_item=next(x for x in downloaded['files'] if x['name'].startswith('torch-'))
    torch_wheel=download_receipt.parent/torch_item['name']
    if sha(torch_wheel)!=torch_item['sha256']:
        raise RuntimeError('Official Torch wheel changed after network-only download')
    resolved_input=OUTPUT/'requirements-local.in'
    resolved_input.write_text('\n'.join(
        'torch @ '+torch_wheel.as_uri() if line.startswith('torch @ ') else line
        for line in requirements.read_text().splitlines())+'\n')
    report=OUTPUT/'resolution.json'
    run([python,'-m','pip','install','--dry-run','--ignore-installed','--only-binary=:all:',
        '--no-binary=antlr4-python3-runtime','--no-build-isolation',
        '--report',report,'-r',resolved_input],env)
    resolution=json.loads(report.read_text())
    entries=[];lines=[]
    for package in resolution['install']:
        info=package['metadata'];download_info=package['download_info']
        checksum=download_info['archive_info']['hashes']['sha256']
        url=download_info['url']
        if not url.endswith('.whl') and not (
            info['name']=='antlr4-python3-runtime' and info['version']=='4.9.3'
            and checksum=='f224469b4168294902bb1efa80a8bf7855f24c99aef99cbefc1bcd3cce77881b'):
            raise RuntimeError('Unexpected source distribution in resolved installation')
        lines.append(f"{info['name']} @ {url} --hash=sha256:{checksum}")
        entries.append({'name':info['name'],'version':info['version'],'url':url,'sha256':checksum,
            'licenseExpression':info.get('license_expression'),'license':info.get('license'),
            'licenseClassifiers':[x for x in info.get('classifier',[]) if x.startswith('License ::')],
            'requiresPython':info.get('requires_python')})
    (OUTPUT/'windows-reference.lock').write_text('\n'.join(sorted(lines))+'\n')
    inventory={'status':'Resolved only; runtime dependencies, extension and model are not installed',
        'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'python':sys.version,
        'baseInterpreter':sys.executable,'baseInterpreterSha256':sha(sys.executable),
        'requirementsSha256':sha(requirements),'recipeSha256':sha(__file__),
        'lockSha256':sha(OUTPUT/'windows-reference.lock'),'packages':entries,
        'sourceRepositories':[
          {'url':'https://github.com/VAST-AI-Research/TripoSR','commit':TRIPO_COMMIT,'license':'MIT; code and weights'},
          {'url':'https://github.com/tatsy/torchmcubes','commit':MCUBES_COMMIT,
           'license':'MIT per this historical commit README/setup metadata; current master uses different terms',
           'buildPlan':'Separate CPU CppExtension wrapper; no system CUDA Toolkit installation'}],
        'model':{'repo':'stabilityai/TripoSR','filename':'model.ckpt','bytes':1677246742,
          'sha256':'429e2c6b22a0923967459de24d67f05962b235f79cde6b032aa7ed2ffcd970ee','license':'MIT'},
        'inferenceExecuted':False,'existingPythonEnvironmentsModified':False,'sharedAssetsChanged':False}
    (OUTPUT/'dependency-license-inventory.json').write_text(json.dumps(inventory,indent=2)+'\n')
    print('TRIPOSR_REFERENCE_DEPENDENCIES_RESOLVED',flush=True)


if __name__=='__main__':main()
