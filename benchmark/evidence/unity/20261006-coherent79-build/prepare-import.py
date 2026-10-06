"""Preserve the runnable baseline and archive only manifest-removed imports."""
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DELIVERY = ROOT / 'benchmark/unreal/evidence/nib-coherent79-corners-v2/delivery.json'
IMPORTED = ROOT / 'benchmark/unity/Assets/Benchmark/Imported/characters/nib'
SHARED = ROOT / 'benchmark/shared/characters/nib'
OUT = ROOT / 'benchmark/local/evidence/unity-coherent79-import'
BACKUP = ROOT / 'benchmark/local/build-backups/unity-d431-before-coherent79'
BUILD = ROOT / 'benchmark/builds/Unity'

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
        if hasattr(os, 'posix_fadvise'):
            os.posix_fadvise(f.fileno(), 0, 0, os.POSIX_FADV_DONTNEED)
    return h.hexdigest()

delivery = json.loads(DELIVERY.read_text())
assert delivery['published']
assert not BACKUP.exists(), 'Existing baseline archive must not be overwritten'
assert not OUT.exists(), 'Existing preparation evidence must not be overwritten'
for rel, expected in delivery['files'].items():
    path = SHARED / rel
    assert path.stat().st_size == expected['bytes'] and sha(path) == expected['sha256'], rel
removed = delivery['sharedDelta']['removed']
assert len(removed) == 12
records = []
for rel in removed:
    path = IMPORTED / rel
    assert rel.startswith('textures/') and rel.endswith('.png')
    assert not (SHARED / rel).exists()
    assert sha(path) == delivery['previousFiles'][rel]['sha256'], rel
    meta = Path(str(path) + '.meta')
    assert meta.is_file(), str(meta)
    records.append({'path': rel, 'sha256': sha(path), 'metaSha256': sha(meta)})
dll = BUILD / 'KragKings-Unity_Data/Managed/Assembly-CSharp.dll'
assert sha(dll) == '0359dd69269323b72c5e8ebdce6730fef4bb14c48176d5f0215982c8debf66b2'
receipt = {
    'previousBuild': 'd4315c2b22dd47328984db4acf9bbc22',
    'deliverySha256': sha(DELIVERY),
    'buildArchive': str(BACKUP.relative_to(ROOT)),
    'previousRuntimeDllSha256': sha(dll),
    'previousExecutableSha256': sha(BUILD / 'KragKings-Unity.exe'),
    'archivedImports': records,
    'retainedMetaSha256': {
        str(p.relative_to(IMPORTED)): sha(p)
        for p in IMPORTED.rglob('*.meta')
        if str(p.relative_to(IMPORTED))[:-5] not in removed
    },
    'note': 'Entire old build moved intact; only twelve hash-matched removed textures and their meta files archived. Retained asset identities unchanged.',
}
OUT.mkdir(parents=True)
(OUT / 'preparation.json').write_text(json.dumps(receipt, indent=2) + '\n')
BUILD.rename(BACKUP)
for record in records:
    for suffix in ('', '.meta'):
        src = IMPORTED / (record['path'] + suffix)
        dst = OUT / 'obsolete-imports' / (record['path'] + suffix)
        dst.parent.mkdir(parents=True, exist_ok=True)
        src.rename(dst)
(OUT / 'prepared.flag').write_text('Baseline preserved and stale import reconciliation completed.\n')
print(json.dumps({'status': 'prepared', 'baseline': str(BACKUP), 'archivedTextures': len(records), 'retainedMetas': len(receipt['retainedMetaSha256'])}))
