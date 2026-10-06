"""Download pinned public pilot weights only after actual small kernels pass."""
import hashlib
import json
from pathlib import Path
import shutil
import urllib.request

ROOT=Path(__file__).resolve().parents[4]
pilot=ROOT/'benchmark/local/trellis-original-pilot-v1'
probe=json.loads((pilot/'kernel-probe/result.json').read_text())
assert probe['status']=='Small native kernels passed; full inference remains untested'
assert len(probe['checks'])==3
manifest=json.loads((ROOT/'benchmark/local/trellis-original-feasibility/mesh-stage-manifest.json').read_text())
output=pilot/'weights';output.mkdir(exist_ok=True)
records=[]
def download(url,destination,expected=None,expected_size=None):
    if destination.exists():
        h=hashlib.sha256()
        with destination.open('rb') as stream:
            for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
        if expected and h.hexdigest()==expected and destination.stat().st_size==expected_size:
            return {'url':url,'path':str(destination),'sha256':expected,'bytes':expected_size,'reusedVerifiedFile':True}
        raise RuntimeError('Preserve existing unverified output: '+str(destination))
    temp=destination.with_suffix(destination.suffix+'.partial')
    assert not temp.exists(), 'Preserve previous partial download'
    destination.parent.mkdir(parents=True,exist_ok=True)
    h=hashlib.sha256();size=0
    with urllib.request.urlopen(url,timeout=60) as source,temp.open('xb') as stream:
        etag=source.headers.get('ETag');length=source.headers.get('Content-Length')
        for block in iter(lambda:source.read(1024*1024),b''):
            stream.write(block);h.update(block);size+=len(block)
    assert expected_size is None or size==expected_size, 'Size mismatch'
    assert not length or size==int(length), 'HTTP size mismatch'
    assert expected is None or h.hexdigest()==expected, 'Pinned weight hash mismatch'
    temp.rename(destination)
    return {'url':url,'path':str(destination),'sha256':h.hexdigest(),'bytes':size,'etag':etag,'upstreamHashPinned':expected is not None}
for stage in manifest:
    weight=stage['weight'];relative=weight['rfilename']
    url='https://huggingface.co/microsoft/TRELLIS-image-large/resolve/25e0d31ffbebe4b5a97464dd851910efc3002d96/'+relative
    result=download(url,output/relative,weight['lfs']['sha256'],weight['size']);result['role']=stage['role'];records.append(result)
    config=Path(relative).with_suffix('.json')
    original=ROOT/'benchmark/local/trellis-original-feasibility/configs'/config.name
    assert hashlib.sha256(original.read_bytes()).hexdigest()==stage['configSha256']
    shutil.copyfile(original,output/config)
    (output/'download-receipt.json').write_text(json.dumps({'status':'partial','files':records},indent=2)+'\n')
    print('PINNED_WEIGHT_READY',stage['role'],result['bytes'],flush=True)
url='https://dl.fbaipublicfiles.com/dinov2/dinov2_vitl14/dinov2_vitl14_reg4_pretrain.pth'
records.append(download(url,output/'dinov2_vitl14_reg4_pretrain.pth'))
report={'status':'Actual public pilot weights downloaded; inference has not run','files':records,
        'sourceConceptUploaded':False,'modelRevision':'25e0d31ffbebe4b5a97464dd851910efc3002d96'}
(output/'download-receipt.json').write_text(json.dumps(report,indent=2)+'\n')
print('TRELLIS_ORIGINAL_WEIGHTS_READY',flush=True)
