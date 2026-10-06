"""Network-only U2Net staging; no model/session import or inference."""
import hashlib
import json
from pathlib import Path
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / 'benchmark/local/triposr-reference-v1/matte-model-download'
COMMIT = 'ac7e1c817ecab7c7dff5ce6b1abba61cd213ff29'
URL = 'https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2net.onnx'
EXPECTED_MD5 = '60024c5c889badc19c04ad937298a77b'


def main():
    if OUTPUT.exists():
        raise RuntimeError('Preserve any previous download attempt')
    OUTPUT.mkdir()
    started = time.monotonic()
    count = 0
    md5 = hashlib.md5()
    sha = hashlib.sha256()
    partial = OUTPUT / 'u2net.onnx.partial'
    request = urllib.request.Request(URL, headers={'User-Agent':'KragKings-local-matte-model-download'})
    with urllib.request.urlopen(request, timeout=90) as response, partial.open('wb') as destination:
        while chunk := response.read(1024 * 1024):
            destination.write(chunk)
            count += len(chunk)
            md5.update(chunk)
            sha.update(chunk)
            delay = count / (8 * 1024 * 1024) - (time.monotonic() - started)
            if delay > 0:
                time.sleep(delay)
    if count != 175997641 or md5.hexdigest() != EXPECTED_MD5:
        raise RuntimeError('The release asset differs from the installed rembg model pin')
    partial.rename(OUTPUT / 'u2net.onnx')
    license_url = f'https://raw.githubusercontent.com/xuebinqin/U-2-Net/{COMMIT}/LICENSE'
    with urllib.request.urlopen(license_url, timeout=45) as response:
        license_payload = response.read()
    if b'Apache License' not in license_payload:
        raise RuntimeError('Unexpected upstream license payload')
    (OUTPUT / 'U2Net-LICENSE').write_bytes(license_payload)
    receipt = {'url':URL, 'releaseAssetID':85857932, 'bytes':count,
               'sha256':sha.hexdigest(), 'installedRembgExpectedMD5':EXPECTED_MD5,
               'actualMD5':md5.hexdigest(), 'upstreamCommit':COMMIT,
               'upstreamLicense':'Apache-2.0', 'licenseURL':license_url,
               'licenseSha256':hashlib.sha256(license_payload).hexdigest(),
               'rembgVersion':'2.0.60', 'rembgLicense':'MIT',
               'recipeSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               'networkOnly':True, 'modelExecuted':False, 'taskLocalCacheOnly':True,
               'elapsedSeconds':time.monotonic()-started}
    (OUTPUT / 'download-receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print('U2NET_NETWORK_DOWNLOAD_VERIFIED', sha.hexdigest(), flush=True)


if __name__ == '__main__':
    main()
