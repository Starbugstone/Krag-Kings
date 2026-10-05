"""Fetch an archived distributor build compatible with the existing NVENC driver.

FFmpeg 9.0.2 was tested locally and requires NVENC API 13.1; this laptop has 13.0.
No graphics-driver or OBS configuration change is needed for this portable tool.
"""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import urllib.request

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'benchmark/local/capture'
VERSION = '8.0.1'
PINNED_SHA256 = 'a0c715acca3839bfd203e600a7775b83cfe3ff928a4eceb9ca54f2982365901c'
API = f'https://api.github.com/repos/GyanD/codexffmpeg/releases/tags/{VERSION}'
with urllib.request.urlopen(API, timeout=30) as response:
    release = json.load(response)
asset = next(a for a in release['assets'] if a['name'] == f'ffmpeg-{VERSION}-essentials_build.7z')
expected = asset['digest'].removeprefix('sha256:')
if len(expected) != 64:
    raise RuntimeError('Distributor release API did not provide a SHA-256 digest')
if expected != PINNED_SHA256:
    raise RuntimeError('Distributor asset differs from the verified pinned 8.0.1 build')
OUT.mkdir(parents=True, exist_ok=True)
archive = OUT / asset['name']
if not archive.exists() or hashlib.sha256(archive.read_bytes()).hexdigest() != expected:
    with urllib.request.urlopen(asset['browser_download_url'], timeout=60) as source, archive.open('wb') as target:
        shutil.copyfileobj(source, target, 256 * 1024)
actual = hashlib.sha256(archive.read_bytes()).hexdigest()
if actual != expected:
    raise RuntimeError('Archived FFmpeg checksum mismatch')
destination = OUT / 'ffmpeg-compatible'
subprocess.run(['7z', 'x', str(archive), '-o' + str(destination), '-y', '-mmt=2'], check=True, stdout=subprocess.DEVNULL)
executable = next(destination.rglob('ffmpeg.exe'))
record = {'version': VERSION, 'release': release['html_url'], 'archive': asset['browser_download_url'],
          'sha256': actual, 'verification': 'GitHub distributor release asset digest',
          'reason': 'FFmpeg 9 NVENC encoder requires a newer driver API than installed',
          'license': 'GPLv3; retained in local package', 'shipped_with_game': False,
          'executable': str(executable.relative_to(ROOT))}
(OUT / 'ffmpeg-compatible-source.json').write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps(record, indent=2))
