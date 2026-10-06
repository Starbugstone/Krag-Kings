"""Actual native Alembic Groom import/readback in a disposable project only."""
import hashlib
import json
from pathlib import Path
import unreal

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PROJECT = Path(unreal.Paths.project_dir()).resolve()
PLAN = json.loads((PROJECT / 'probe-plan.json').read_text())


def sha(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''): value.update(chunk)
    return value.hexdigest()


def main():
    if PROJECT != (ROOT / PLAN['projectDirectory']).resolve() or not PROJECT.is_relative_to(ROOT / 'benchmark/local'):
        raise RuntimeError('Groom fixture must not modify the benchmark project')
    for pin in PLAN['pins']:
        if sha(ROOT / pin['path']) != pin['sha256']:
            raise RuntimeError('Frozen fixture/probe source changed: ' + pin['path'])
    fixture_path = ROOT / PLAN['fixture']
    fixture = json.loads(fixture_path.read_text())
    evidence = PROJECT.parent / 'evidence'
    evidence.mkdir(exist_ok=True)
    if (evidence / 'import-result.json').exists():
        raise RuntimeError('Preserve previous fixture attempt')
    report = {'engine': unreal.SystemLibrary.get_engine_version(), 'fixtures': [],
              'skeletalBindingVerified': False, 'rendered': False, 'performanceMeasured': False,
              'artisticAcceptance': False, 'sharedChanged': False}
    expected = {item['name']: item for item in fixture['fixtures']}
    for entry in fixture['exports']:
        source = fixture_path.parent / entry['path']
        if sha(source) != entry['sha256']:
            raise RuntimeError('Native ABC fixture differs')
        name = entry['region']
        options = unreal.GroomImportOptions()
        conversion = unreal.GroomConversionSettings()
        conversion.set_editor_property('rotation', unreal.Vector(0, 0, 0))
        conversion.set_editor_property('scale', unreal.Vector(100, 100, 100))
        options.set_editor_property('conversion_settings', conversion)
        task = unreal.AssetImportTask()
        task.set_editor_property('filename', str(source))
        task.set_editor_property('destination_path', '/Game/Fixture')
        task.set_editor_property('destination_name', name)
        task.set_editor_property('automated', True)
        task.set_editor_property('replace_existing', False)
        task.set_editor_property('save', True)
        task.set_editor_property('factory', unreal.HairStrandsFactory())
        task.set_editor_property('options', options)
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        assets = [unreal.load_asset(path) for path in task.get_editor_property('imported_object_paths')]
        grooms = [asset for asset in assets if isinstance(asset, unreal.GroomAsset)]
        if len(grooms) != 1:
            raise RuntimeError('Expected exactly one real GroomAsset for ' + name)
        actual = json.loads(unreal.GroomProbeLibrary.read_description(grooms[0]))
        reference = expected[name]
        result = {'region': name, 'sourceSha256': entry['sha256'], 'actual': actual,
                  'conversion': {'rotationDegrees': [0, 0, 0], 'scale': [100, 100, 100]},
                  'coordinateContract': 'ABC(x,z,-y) metres retained in importer coordinates, scaled to centimetres'}
        report['fixtures'].append(result)
        # Write raw readback before any gate, so an actual failure stays reviewable.
        (evidence / 'import-progress.json').write_text(json.dumps(report, indent=2) + '\n', newline='\n')
        if not actual.get('valid') or actual['curveCount'] != reference['curveCount'] or actual['pointCount'] != reference['pointCount']:
            raise RuntimeError('Imported native point/strand counts differ')
        if actual['strandPointCounts'] != [b-a for a,b in zip(reference['curveOffsets'], reference['curveOffsets'][1:])]:
            raise RuntimeError('Imported strand topology differs')
        points = [[p[0]*100, p[2]*100, -p[1]*100] for p in reference['pointsBlenderMeters']]
        widths = [r*200 for r in reference['radiusMeters']]
        if PLAN.get('restorePointWidthsFromExactSidecar'):
            result['stockImporterReadback'] = actual
            error = unreal.GroomProbeLibrary.restore_point_widths(grooms[0],
                [unreal.Vector(*p) for p in points], actual['strandPointCounts'], widths)
            if error:
                raise RuntimeError('Exact native sidecar width adapter failed: ' + error)
            actual = json.loads(unreal.GroomProbeLibrary.read_description(grooms[0]))
            result['actual'] = actual
            result['widthAdapter'] = 'Verified point order/topology/centimetres; commit exact sidecar diameter to native vertex Width; rebuild derived data'
            (evidence / 'import-progress.json').write_text(json.dumps(report, indent=2) + '\n', newline='\n')
        if not actual['hasPointWidths'] or len(actual['pointWidthsCentimeters']) != len(widths):
            raise RuntimeError('Standard point widths were lost; do not accept fallback diameter')
        position_error = max(abs(a-b) for p,q in zip(points,actual['positionsCentimeters']) for a,b in zip(p,q))
        width_error = max(abs(a-b) for a,b in zip(widths,actual['pointWidthsCentimeters']))
        result.update({'maximumPositionComponentErrorCentimeters': position_error,
                       'maximumWidthErrorCentimeters': width_error})
        if position_error > 1e-5 or width_error > 1e-7:
            raise RuntimeError('Imported positions/widths differ from pinned native fixture')
        if PLAN.get('restorePointWidthsFromExactSidecar'):
            if not actual.get('builtStrandsAvailable') or abs(actual['builtRadiusMinCentimeters'] - min(widths)*.5) > 1e-7 or abs(actual['builtRadiusMaxCentimeters'] - max(widths)*.5) > 1e-7:
                raise RuntimeError('Derived strand radius range differs from the exact source taper')
        if actual['hasRootUV'] or actual['hasColor']:
            raise RuntimeError('Unexpected generated/root attributes need attribution before claiming source preservation')
        if not unreal.EditorAssetLibrary.save_loaded_asset(grooms[0], only_if_is_dirty=False):
            raise RuntimeError('Groom package save failed')
    report['passed'] = True
    (evidence / 'import-result.json').write_text(json.dumps(report, indent=2) + '\n', newline='\n')
    unreal.log('KK_GROOM_FIXTURE_IMPORT_COMPLETE')


main()
