import csv
import hashlib
import json
import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
B = ROOT / 'benchmark'

def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
        if hasattr(os, 'posix_fadvise'):
            os.posix_fadvise(stream.fileno(), 0, 0, os.POSIX_FADV_DONTNEED)
    return digest.hexdigest()

def memory(path):
    rows = list(csv.DictReader(path.open()))
    return {'peakPrivateMB': max(float(r['privateMB']) for r in rows),
            'minimumAvailableMB': min(float(r['availableMB']) for r in rows)}

hand = B / 'art/animation/krag-coherent-hand-v1'
review = json.loads((hand / 'actions-review/review.json').read_text())
assert review['sourceSha256'] == sha(hand / 'Krag_CoherentHand_v1.blend')
assert len(review['views']) == 36
for view in review['views']:
    image = hand / 'actions-review' / Path(view['path'].replace('\\', '/')).name
    assert sha(image) == view['sha256']
assert review['recipeSha256'] == sha(hand / 'executed-recipe/review_free_hand.py')
for stream in ['stdout', 'stderr']:
    shutil.copyfile(B / f'local/logs/krag-coherent-hand-v1-actions.{stream}.log',
                    hand / f'evidence/krag-coherent-hand-v1-actions.{stream}.txt')
shutil.copyfile(B / 'local/krag-coherent-hand-v1-actions-memory.csv', hand / 'evidence/krag-coherent-hand-v1-actions-memory.csv')
shutil.copyfile(B / 'local/krag-coherent-hand-v1-actions-contact-sheet.png', hand / 'actions-review/contact-sheet.png')
finding = {
    'status': 'Actual36 posed views completed; natural action hand remains failed',
    'sourceSha256': review['sourceSha256'], 'nativeExit': 0, 'guardExit': 0,
    'individualViewsInspected': ['Idle_00_palm', 'Run_50_palm', 'Run_50_edge', 'Melee_50_palm', 'Melee_50_edge', 'Melee_50_back'],
    'all36ViewsInspectedAsContactSheet': True,
    'contactSheetRows': ['Hit', 'Idle', 'Melee', 'Run', 'Shoot', 'Walk'],
    'contactSheetColumns': ['00back', '00edge', '00palm', '50back', '50edge', '50palm'],
    'findings': ['Idle retains an open relaxed hand; the old broad rest ridge is absent.',
                 'Melee fingers remain too spread with inadequate palm contact; thumb stays outside instead of opposing across the fist.',
                 'Run retains an exaggerated open C curl.',
                 'Palmar deformation creases remain during flexion, and the wrist contour is abrupt.'],
    'memory': memory(B / 'local/krag-coherent-hand-v1-actions-memory.csv'),
    'artisticAcceptance': False, 'engineIntegrated': False,
}
(hand / 'actual-action-review.json').write_text(json.dumps(finding, indent=2) + '\n')
p = hand / 'README.md'
text = p.read_text().replace('The prepared 36-view action review has not run.',
    'All36 action close-ups have now rendered successfully. Six were inspected individually and the full set as a contact sheet. Melee still has excessive finger spread, weak palm contact and a non-opposing thumb; Run remains an open C curl. Palmar flexion creases and the abrupt wrist contour remain defects. See `actual-action-review.json`; the action hand fails natural-pose review.')
p.write_text(text)

out = B / 'evidence/unity/20261006-coherent79-build'
assert not out.exists(), 'Preserve existing evidence'
out.mkdir(parents=True)
log = B / 'local/logs/unity-coherent79-prepare-build-v1.log'
assert 'KRAG_BUILD_RESULT Succeeded 863932701 bytes' in log.read_text(errors='replace')
shutil.copyfile(log, out / 'editor-log.txt')
shutil.copyfile(B / 'local/unity-batch-memory.csv', out / 'memory.csv')
shutil.copyfile(B / 'local/unity-job.json', out / 'executed-job.json')
shutil.copyfile(B / 'local/prepare_unity_coherent79.py', out / 'prepare-import.py')
prep = B / 'local/evidence/unity-coherent79-import/preparation.json'
shutil.copyfile(prep, out / 'import-preparation.json')
preparation = json.loads(prep.read_text())
imported = B / 'unity/Assets/Benchmark/Imported/characters/nib'
for name, digest in preparation['retainedMetaSha256'].items():
    assert sha(imported / name) == digest, 'Retained meta identity changed: ' + name
for species in ['krag', 'nib']:
    shutil.copyfile(B / f'local/evidence/unity/{species}-import.json', out / f'{species}-import.json')
delivery = json.loads((B / 'unreal/evidence/nib-coherent79-corners-v2/delivery.json').read_text())
for name, expected in delivery['files'].items():
    assert sha(imported / name) == expected['sha256'], 'Imported payload differs: ' + name
for name in delivery['sharedDelta']['removed']:
    assert not (imported / name).exists()
source_paths = list((B / 'unity/Assets/Benchmark').rglob('*.cs'))
build = B / 'builds/Unity'
report = {
    'status': 'Actual coherent79 Unity import and Windows build passed; runtime review pending',
    'nativeExit': 0, 'guardExit': 0, 'buildBytes': 863932701,
    'engine': 'Unity6000.4.4f1 / HDRP',
    'nibSourceSha256': delivery['sourceSha256'], 'nibPbrSha256': delivery['pbrSha256'],
    'deliverySha256': sha(B / 'unreal/evidence/nib-coherent79-corners-v2/delivery.json'),
    'importedNibFilesVerified': len(delivery['files']),
    'retainedNibMetasVerified': len(preparation['retainedMetaSha256']),
    'obsoleteTexturePairsArchived': len(preparation['archivedImports']),
    'baselineBackup': preparation['buildArchive'],
    'runtimeDllSha256': sha(build / 'KragKings-Unity_Data/Managed/Assembly-CSharp.dll'),
    'executableSha256': sha(build / 'KragKings-Unity.exe'),
    'memory': memory(out / 'memory.csv'),
    'sourceHashes': {str(p.relative_to(ROOT)): sha(p) for p in source_paths},
    'runtimeVerified': False, 'performanceMeasured': False, 'artisticAcceptance': False,
    'limitation': 'Only Nib content changed. Krag still uses the earlier68-bone shared asset and2sIdle; its newer coordinated whole-body source requires a separate merge/export. Imported curve counts prove retention, not natural acting.',
}
(out / 'build-result.json').write_text(json.dumps(report, indent=2) + '\n')
(out / 'README.md').write_text('# Unity coherent79 build — actual technical integration\n\nThe guarded Unity6000.4.4f1 import and Windows build both exited0 and emitted the required success marker. All115 delivered Nib files match after import,75 retained `.meta` identities remain exact, and the12 obsolete texture/meta pairs are archived. The prior d431 executable is preserved intact.\n\nAllthree Nib variants import79 bones,25 morphs and allseven clips. Idle is6seconds, with14 varying torso curves and16 ear curves; Walk/Run each retain15 torso curves and4 ear curves. These counts establish that animation survived import, not natural-looking movement. Unity reports750166 Natural triangles; see each variant in `nib-import.json` for actual imported totals.\n\nKrag remains on the previous shared68-bone source and2-second Idle. The newer Krag whole-body/hand work is not in this build. Runtime visual, input and performance checks of this executable remain pending, and neither character has artistic acceptance.\n')
attributes = ROOT / '.gitattributes'
text = attributes.read_text()
for ext in ['json', 'csv', 'txt']:
    line = f'benchmark/evidence/unity/20261006-coherent79-build/*.{ext} -text whitespace=cr-at-eol,-blank-at-eof'
    if line not in text:
        text += '\n' + line
attributes.write_text(text.rstrip() + '\n')
print(json.dumps({'unity': report['memory'], 'hand': finding['memory'], 'runtimeDllSha256': report['runtimeDllSha256']}))
