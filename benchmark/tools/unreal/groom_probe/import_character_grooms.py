"""Isolated regional Groom import/binding or fresh-process reload; no scene/render claim."""
import array
import gc
import hashlib
import json
from pathlib import Path
import struct
import sys
import unreal

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PROJECT = Path(unreal.Paths.project_dir()).resolve()
PLAN = json.loads((PROJECT / 'groom-character-plan.json').read_text())


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def checked_json(text):
    value = json.loads(text)
    if value.get('error'):
        raise RuntimeError(value['error'])
    return value


def binary(region, name, folder):
    meta = region['files'][name]
    path = folder / region['dataDirectory'] / meta['path']
    if sha(path) != meta['sha256'] or path.stat().st_size != meta['bytes']:
        raise RuntimeError('Frozen strand binary differs: ' + str(path))
    code = {'float32-le': 'f', 'int32-le': 'i'}[meta['dtype']]
    result = array.array(code)
    with path.open('rb') as stream:
        result.fromfile(stream, meta['bytes'] // 4)
    if sys.byteorder != 'little':
        result.byteswap()
    expected = 1
    for count in meta['shape']:
        expected *= count
    if len(result) != expected:
        raise RuntimeError('Binary shape differs')
    return result


def description_summary(actual, positions, counts, widths, colors):
    if not actual.get('valid') or actual['pointCount'] != len(widths) or actual['curveCount'] != len(counts):
        raise RuntimeError('Native strand/point counts differ')
    if actual['strandPointCounts'] != list(counts):
        raise RuntimeError('Native strand ordering/topology differs')
    if not actual['hasPointWidths'] or not actual['hasColor']:
        raise RuntimeError('Explicit per-point taper/color missing after adapter/reload')
    if any(len(actual[key]) != len(widths) for key in ('positionsCentimeters','pointWidthsCentimeters','pointColorsLinearRgb')):
        raise RuntimeError('Native point payload length differs')
    position_error = max(abs(a-b) for p,q in zip(positions, actual['positionsCentimeters']) for a,b in zip(p,q))
    width_error = max(abs(a-b) for a,b in zip(widths, actual['pointWidthsCentimeters']))
    color_error = max(abs(a-b) for p,q in zip(colors, actual['pointColorsLinearRgb']) for a,b in zip(p,q))
    if position_error > PLAN['positionToleranceCentimeters'] or width_error > 1e-8 or color_error != 0:
        raise RuntimeError('Native position/taper/linear color differs from exact sidecars')
    if not actual.get('builtStrandsAvailable') or actual['builtCurveCount'] != len(counts):
        raise RuntimeError('Native derived strands missing or decimated')
    if abs(actual['builtRadiusMinCentimeters'] - min(widths)/2) > 1e-8 or abs(actual['builtRadiusMaxCentimeters'] - max(widths)/2) > 1e-8:
        raise RuntimeError('Derived native radius range differs')
    sample_indices = [0, len(widths)//2, len(widths)-1]
    summary = {key:value for key,value in actual.items() if key not in (
        'positionsCentimeters','pointWidthsCentimeters','pointColorsLinearRgb','strandPointCounts','strandWidthsCentimeters','groupIds')}
    summary.update({'maximumPositionComponentErrorCentimeters':position_error,
                    'maximumDiameterErrorCentimeters':width_error,'maximumLinearColorError':color_error,
                    'samples':[{'index':i,'positionCentimeters':actual['positionsCentimeters'][i],
                                'diameterCentimeters':actual['pointWidthsCentimeters'][i],
                                'linearRgb':actual['pointColorsLinearRgb'][i]} for i in sample_indices]})
    for field in ('positionsCentimeters','pointWidthsCentimeters','pointColorsLinearRgb'):
        h = hashlib.sha256()
        for value in actual[field]:
            values = value if isinstance(value,list) else [value]
            h.update(struct.pack('<' + 'f'*len(values), *values))
        summary[field+'Float32Sha256'] = h.hexdigest()
    return summary


def main():
    if PROJECT != (ROOT / PLAN['projectDirectory']).resolve() or not PROJECT.is_relative_to(ROOT / 'benchmark/local/groom-probe'):
        raise RuntimeError('Refuse nonisolated Groom project')
    for pin in PLAN['pins']:
        if sha(ROOT/pin['path']) != pin['sha256']:
            raise RuntimeError('Frozen input changed: ' + pin['path'])
    reload_only = '-KKGroomReload' in unreal.SystemLibrary.get_command_line()
    diagnostic_region = PLAN.get('diagnosticRegion')
    if reload_only and diagnostic_region:
        raise RuntimeError('Diagnostic-only stage does not save bindings for reload')
    stage = 'reload' if reload_only else 'grooms'
    evidence = ROOT / PLAN['evidenceDirectory']
    if (evidence/(stage+'-result.json')).exists():
        raise RuntimeError('Preserve completed attempt')
    source_path = ROOT / PLAN['groomSourceReport']
    source = json.loads(source_path.read_text())
    mesh_report = json.loads((ROOT/PLAN['actualMeshResult']).read_text(encoding='utf-8-sig'))
    if not mesh_report['passed']:
        raise RuntimeError('Actual mesh origin/mask gate has not passed')
    mesh = unreal.load_asset(mesh_report['mesh']['asset'])
    if not isinstance(mesh, unreal.SkeletalMesh) or not mesh.get_editor_property('skeleton'):
        raise RuntimeError('Saved mesh/skeleton dependency unavailable')
    # Rebuild/read the imported render mask in this fresh process; do not accept a stored flag alone.
    mask = checked_json(unreal.GroomCharacterLibrary.enable_and_read_binding_mask(mesh, PLAN['maskAttribute']))
    sys.path.insert(0,str(HERE))
    from character_coordinates import normalize_verified_wrapper, match_rest_positions
    bones, wrapper = normalize_verified_wrapper(source['preservedRig']['bones'], mask['bones'], mesh_report['rawWrapperAudit'])
    axes = match_rest_positions(source['preservedRig']['bones'], bones)
    if axes['axes'] != mesh_report['sourceToMeshAxes']['axes']:
        raise RuntimeError('Saved target coordinate axes changed')
    report = {'engine':unreal.SystemLibrary.get_engine_version(),'stage':stage,'regions':[],
              'meshMaskFreshProcessVerified':True,'sourceToMeshAxes':axes,'importedWrapper':wrapper,
              'curveCount':0,'pointCount':0,'simulation':False,'globalInterpolation':False,
              'lod0CurveAndPointDecimation':1,'rendered':False,'posedDeformationVerified':False,
              'performanceMeasured':False,'artisticAcceptance':False,'sharedChanged':False}
    exports = {item['region']:item for item in source['exports']}
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    previous = json.loads((evidence/'grooms-result.json').read_text()) if reload_only else None
    for region in source['regions']:
        name = region['name']
        if diagnostic_region and name != diagnostic_region:
            continue
        p = binary(region,'positions',source_path.parent)
        c = binary(region,'colorLinearRgb',source_path.parent)
        positions = [(p[i]*100,-p[i+1]*100,p[i+2]*100) for i in range(0,len(p),3)]
        colors = [(c[i],c[i+1],c[i+2]) for i in range(0,len(c),3)]
        widths = [v*200 for v in binary(region,'radii',source_path.parent)]
        counts = binary(region,'curveCounts',source_path.parent)
        del p,c
        asset_path = '/Game/Grooms/'+name
        binding_path = '/Game/Grooms/'+name+'_Binding'
        item = {'region':name,'groom':asset_path,'binding':binding_path,'sourceAbcSha256':exports[name]['sha256']}
        report['regions'].append(item)
        def progress():
            (evidence/(stage+'-progress.json')).write_text(json.dumps(report,indent=2)+'\n',newline='\n')
        if reload_only:
            groom = unreal.load_asset(asset_path)
            binding = unreal.load_asset(binding_path)
            if not isinstance(groom,unreal.GroomAsset) or not isinstance(binding,unreal.GroomBindingAsset):
                raise RuntimeError('Saved groom/binding dependency unavailable: '+name)
        else:
            if unreal.EditorAssetLibrary.does_asset_exist(asset_path) or unreal.EditorAssetLibrary.does_asset_exist(binding_path):
                raise RuntimeError('Refuse to replace earlier groom attempt')
            options = unreal.GroomImportOptions()
            conversion = unreal.GroomConversionSettings()
            # ABC=(x,z,-y). UE row-vector scale then roll(-90) maps it to (100x,-100y,100z).
            conversion.set_editor_property('rotation',unreal.Vector(-90,0,0))
            conversion.set_editor_property('scale',unreal.Vector(100,100,-100))
            options.set_editor_property('conversion_settings',conversion)
            task = unreal.AssetImportTask()
            for key,value in {'filename':str(source_path.parent/exports[name]['path']),
                'destination_path':'/Game/Grooms','destination_name':name,'automated':True,
                'replace_existing':False,'save':False,'factory':unreal.HairStrandsFactory(),'options':options}.items():
                task.set_editor_property(key,value)
            tools.import_asset_tasks([task])
            assets = [unreal.load_asset(path) for path in task.get_editor_property('imported_object_paths')]
            found = [value for value in assets if isinstance(value,unreal.GroomAsset)]
            if len(found) != 1:
                raise RuntimeError('Expected one actual GroomAsset: '+name)
            groom = found[0]
            before = checked_json(unreal.GroomProbeLibrary.read_description(groom))
            item['stockImported'] = {key:before[key] for key in ('pointCount','curveCount','hasPointWidths','hasColor','hasRootUV')}
            item['stockPositionErrorCentimeters'] = max(abs(a-b) for x,y in zip(positions,before['positionsCentimeters']) for a,b in zip(x,y))
            progress()
            del before
            item['sidecarAdapter'] = checked_json(unreal.GroomCharacterLibrary.apply_verified_strand_sidecar(
                groom,[unreal.Vector(*v) for v in positions],list(counts),widths,
                [unreal.Vector(*v) for v in colors],PLAN['positionToleranceCentimeters']))
            progress()
            binding = tools.create_asset(name+'_Binding','/Game/Grooms',unreal.GroomBindingAsset,unreal.GroomBindingFactory())
            item['projection'] = checked_json(unreal.GroomCharacterLibrary.build_masked_binding(binding,groom,mesh,PLAN['maskAttribute']))
        if reload_only:
            item['projection'] = checked_json(unreal.GroomCharacterLibrary.read_binding_projection(binding,PLAN['maskAttribute']))
        actual = checked_json(unreal.GroomProbeLibrary.read_description(groom))
        item['description'] = description_summary(actual,positions,counts,widths,colors)
        progress()
        groups = item['projection']['groups']
        if sum(g['roots'] for g in groups) != region['curveCount'] or not all(g['allProjectedTrianglesEligible'] for g in groups):
            raise RuntimeError('Root projection counts/eligible surfaces differ')
        if diagnostic_region:
            if any('worstDecodedRoot' not in group or 'worstSurfaceRoot' not in group for group in groups):
                raise RuntimeError('Diagnostic native triangle evidence missing')
            report.update({'diagnosticOnly':True,'groomPackagesSaved':False,
                           'originalContactGateCentimeters':PLAN['rootProjectionToleranceCentimeters'],
                           'originalContactGatePassed':all(g['maximumRootProjectionDistanceCentimeters'] <= PLAN['rootProjectionToleranceCentimeters'] for g in groups),
                           'acceptedFullBindingPipeline':False})
            (evidence/'projection-diagnostic.json').write_text(json.dumps(report,indent=2)+'\n',newline='\n')
            unreal.log('KK_GROOM_CHARACTER_PROJECTION_DIAGNOSTIC_COMPLETE')
            return
        if max(g['maximumRootProjectionDistanceCentimeters'] for g in groups) > PLAN['rootProjectionToleranceCentimeters']:
            raise RuntimeError('Root projection exceeds explicit 0.1mm surface tolerance')
        if reload_only:
            old = next(x for x in previous['regions'] if x['region']==name)
            for key in ('positionsCentimetersFloat32Sha256','pointWidthsCentimetersFloat32Sha256','pointColorsLinearRgbFloat32Sha256'):
                if old['description'][key] != item['description'][key]:
                    raise RuntimeError('Saved native strand payload changed: '+key)
        else:
            for asset in (groom,binding):
                if not unreal.EditorAssetLibrary.save_loaded_asset(asset,only_if_is_dirty=False):
                    raise RuntimeError('Native groom/binding package save failed')
        report['curveCount'] += region['curveCount']
        report['pointCount'] += region['pointCount']
        progress()
        del positions,colors,widths,counts,actual
        gc.collect()
    if report['curveCount'] != 26000 or report['pointCount'] != 234000:
        raise RuntimeError('Frozen 26k pilot totals changed')
    report['passed'] = True
    (evidence/(stage+'-result.json')).write_text(json.dumps(report,indent=2)+'\n',newline='\n')
    unreal.log('KK_GROOM_CHARACTER_'+('RELOAD' if reload_only else 'BINDING')+'_COMPLETE')


main()
