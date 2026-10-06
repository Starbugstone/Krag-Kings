"""Fresh-process readback of the saved exact-width adapter result."""
import hashlib
import json
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[4]
PROJECT = Path(unreal.Paths.project_dir()).resolve()
PLAN = json.loads((PROJECT / 'probe-plan.json').read_text())
if PROJECT != (ROOT / PLAN['projectDirectory']).resolve() or not PROJECT.is_relative_to(ROOT / 'benchmark/local/groom-probe'):
    raise RuntimeError('Wrong isolated project')
for pin in PLAN['pins']:
    with (ROOT / pin['path']).open('rb') as stream:
        if hashlib.file_digest(stream, 'sha256').hexdigest() != pin['sha256']:
            raise RuntimeError('Pinned native probe input changed')
evidence = PROJECT.parent / 'evidence'
previous = json.loads((evidence / 'import-result.json').read_text())
if previous.get('passed') is not True or (evidence / 'reload-result.json').exists():
    raise RuntimeError('Import did not pass or previous reload must be preserved')
result = {'freshProcess': True, 'regions': [], 'rendered': False, 'skeletalBindingVerified': False}
for entry in previous['fixtures']:
    asset = unreal.load_asset(entry['actual']['asset'])
    actual = json.loads(unreal.GroomProbeLibrary.read_description(asset))
    for key in ['curveCount','pointCount','positionsCentimeters','strandPointCounts','pointWidthsCentimeters',
                'hasPointWidths','hasRootUV','hasColor','builtRadiusMinCentimeters','builtRadiusMaxCentimeters']:
        if actual[key] != entry['actual'][key]:
            raise RuntimeError('Saved native groom changed on reload: ' + entry['region'] + '/' + key)
    result['regions'].append({'region': entry['region'], 'actual': actual, 'savedDataMatches': True})
result['passed'] = True
(evidence / 'reload-result.json').write_text(json.dumps(result, indent=2) + '\n', newline='\n')
unreal.log('KK_GROOM_FIXTURE_RELOAD_COMPLETE')
