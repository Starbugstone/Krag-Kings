"""Fetch pinned public assets only. Never import/install/extract downloaded content."""
import hashlib
import json
from pathlib import Path
import time
import urllib.request
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[3]
PLAN = Path(__file__).with_name('network-download-plan.json')


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(data)
    return result.hexdigest()


def main():
    plan = json.loads(PLAN.read_text())
    output = ROOT / plan['output']
    output.mkdir(parents=True, exist_ok=True)
    receipt_path = output / 'download-receipt.json'
    if receipt_path.exists():
        raise RuntimeError('Completed receipt already exists; preserve this attempt')
    results = []
    cap = plan['maxMiBPerSecond'] * 1024 * 1024
    for item in plan['files']:
        target = output / item['name']
        expected = item.get('sha256')
        if target.exists():
            prior = json.loads(target.with_suffix(target.suffix + '.download.json').read_text())
            checksum = digest(target)
            if checksum != prior['sha256'] or (expected and checksum != expected):
                raise RuntimeError('Existing downloaded content changed: ' + target.name)
            results.append(prior)
            continue
        partial = target.with_suffix(target.suffix + '.partial')
        # An interrupted partial is never accepted or silently used as a complete file.
        if partial.exists():
            partial.rename(partial.with_name(partial.name + '.' + str(time.time_ns())))
        request = urllib.request.Request(item['url'], headers={
            'User-Agent': 'KragKings-local-reference-download-only'})
        started = time.monotonic()
        checksum = hashlib.sha256()
        count = 0
        next_update = started
        with urllib.request.urlopen(request, timeout=90) as response, partial.open('wb') as stream:
            while block := response.read(1024 * 1024):
                stream.write(block)
                checksum.update(block)
                count += len(block)
                delay = count / cap - (time.monotonic() - started)
                if delay > 0:
                    time.sleep(delay)
                if time.monotonic() >= next_update:
                    print('DOWNLOAD_PROGRESS', item['name'], count, flush=True)
                    next_update = time.monotonic() + 20
        value = checksum.hexdigest()
        if expected and value != expected:
            raise RuntimeError('Official hash mismatch: ' + item['name'])
        if item.get('bytes') and count != item['bytes']:
            raise RuntimeError('Official size mismatch: ' + item['name'])
        partial.rename(target)
        result = dict(item, sha256=value, actualBytes=count,
                      utc=datetime.now(timezone.utc).isoformat(),
                      elapsedSeconds=time.monotonic() - started)
        target.with_suffix(target.suffix + '.download.json').write_text(json.dumps(result, indent=2) + '\n')
        results.append(result)
        print('DOWNLOAD_VERIFIED', item['name'], count, value, flush=True)
    receipt_path.write_text(json.dumps({
        'planSha256': digest(PLAN), 'recipeSha256': digest(Path(__file__)),
        'files': results, 'networkOnly': True, 'extracted': False,
        'dependenciesInstalled': False, 'nativeCompilation': False,
        'torchImported': False, 'inferenceExecuted': False,
        'sharedAssetsChanged': False
    }, indent=2) + '\n')
    print('TRIPOSR_NETWORK_ONLY_COMPLETE', flush=True)


if __name__ == '__main__':
    main()
