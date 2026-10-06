"""Read-only future rig/translation audit; no asset import, save or mutation.

Requires the native parent/reference-transform helpers to have been compiled.
The explicit source contract comes from the isolated motion exporter. This
checks hierarchy and captures actual local curves, not rendered pose parity.
"""
import hashlib
import json
import math
from pathlib import Path
import re

CLIPS = ('Idle', 'Walk', 'Run', 'Melee', 'Shoot', 'Hit', 'FacePerformance')
CONTROLS = ('Root', 'Pelvis', 'TongueTip', 'Ear_L', 'Ear_R', 'EarTip_L',
            'EarTip_R', 'LowerArm_L', 'LowerArm_R', 'ForearmTwist_L',
            'ForearmTwist_R', 'Hand_L', 'Hand_R')


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def hierarchy_errors(source, imported, allowed_wrappers):
    """UE FName is case-insensitive; extra wrapper roots are explicit only."""
    normalize = lambda data: {str(k).casefold(): str(v).casefold() if v and str(v).casefold() != 'none' else None for k, v in data.items()}
    expected, actual = normalize(source), normalize(imported)
    wrappers = {name.casefold() for name in allowed_wrappers}
    errors = []
    if len(expected) != len(source) or len(actual) != len(imported):
        errors.append('Bone names collide after FName case folding')
    for name in sorted(set(actual) - set(expected)):
        if name not in wrappers:
            errors.append('Unexpected imported bone: ' + name)
        elif actual[name] is not None and actual[name] not in wrappers:
            errors.append('Allowed wrapper is not above the authored hierarchy: ' + name)
    for name, parent in expected.items():
        if name not in actual:
            errors.append('Missing authored bone: ' + name)
        elif parent is not None and actual[name] != parent:
            errors.append(f'Wrong parent for {name}: {actual[name]} != {parent}')
        elif parent is None:
            cursor = actual[name]
            seen = {name}
            while cursor is not None:
                if cursor not in wrappers or cursor not in actual or cursor in seen:
                    errors.append('Invalid imported wrapper chain above ' + name)
                    break
                seen.add(cursor)
                cursor = actual[cursor]
    return errors


def transform_data(value):
    p = value.get_editor_property('translation')
    q = value.get_editor_property('rotation')
    s = value.get_editor_property('scale3d')
    return {'translation': [float(p.x), float(p.y), float(p.z)],
            'rotationXYZW': [float(q.x), float(q.y), float(q.z), float(q.w)],
            'scale': [float(s.x), float(s.y), float(s.z)]}


def main():
    import unreal
    match = re.search(r'(?:^|\s)-KKRigAuditSpec=(?:"([^"]+)"|(\S+))', unreal.SystemLibrary.get_command_line())
    if not match:
        raise RuntimeError('An explicit -KKRigAuditSpec file is required')
    spec_path = Path(match.group(1) or match.group(2))
    spec = json.loads(spec_path.read_text(encoding='utf-8-sig'))
    output = Path(spec['outputFile'])
    if output.exists():
        raise RuntimeError('Use a fresh audit output; preserve previous evidence')
    contract_path = Path(spec['sourceContract'])
    if sha256(contract_path) != spec['sourceContractSha256']:
        raise RuntimeError('Frozen source rig contract changed')
    contract = json.loads(contract_path.read_text(encoding='utf-8-sig'))
    if set(contract['clips']) != set(CLIPS):
        raise RuntimeError('Source contract must contain exactly seven runtime clips')
    mesh = unreal.EditorAssetLibrary.load_asset(spec['mesh'])
    if not isinstance(mesh, unreal.SkeletalMesh):
        raise RuntimeError('Explicit imported skeletal mesh is missing')
    helpers = unreal.KKBenchmarkAssets
    if not hasattr(helpers, 'get_mesh_bone_parents'):
        raise RuntimeError('Compile the prepared native rig-audit helpers first')
    parents = {str(k): None if str(v).casefold() == 'none' else str(v)
               for k, v in helpers.get_mesh_bone_parents(mesh).items()}
    reference = {str(k): transform_data(v) for k, v in helpers.get_mesh_bone_reference_transforms(mesh).items()}
    errors = hierarchy_errors(contract['sourceParents'], parents, spec.get('allowedRootWrappers', []))
    report = {'mesh': mesh.get_path_name(), 'sourceContractSha256': sha256(contract_path),
              'auditSpecSha256': sha256(spec_path), 'authoredBoneCount': len(contract['sourceParents']),
              'importedBoneCount': len(parents), 'parents': parents, 'referenceLocalTransforms': reference,
              'sourceWorldRestMatrices': contract['sourceRest'], 'clips': {}, 'errors': errors,
              'assetMutation': False, 'rendered': False, 'poseParityEstablished': False,
              'artisticAcceptance': False,
              'translationUnits': 'Imported local units. Parent/root scale and actor/mesh transforms must be applied before interpreting meters.'}
    try:
        for name in CLIPS:
            path = spec['clips'][name]
            clip = unreal.EditorAssetLibrary.load_asset(path)
            if not isinstance(clip, unreal.AnimSequence):
                errors.append('Missing imported clip: ' + name)
                continue
            track_names = {str(b).casefold(): b for b in helpers.get_animation_bone_names(clip)}
            source_clip = contract['clips'][name]
            expected_duration = (source_clip['frameRange'][1] - source_clip['frameRange'][0]) / source_clip['fps']
            details = {'asset': clip.get_path_name(), 'durationSeconds': float(clip.get_play_length()),
                       'sourceDurationSeconds': expected_duration, 'trackCount': len(track_names), 'controls': {}}
            details['durationToleranceSeconds'] = 1.0 / source_clip['fps'] + 1e-6
            if abs(details['durationSeconds'] - expected_duration) > details['durationToleranceSeconds']:
                errors.append(name + ': duration differs from source by more than one source frame')
            for bone in CONTROLS:
                if bone.casefold() not in {n.casefold() for n in contract['sourceParents']}:
                    continue
                if bone.casefold() not in track_names:
                    errors.append(name + ': missing authored control track ' + bone)
                    continue
                values = [transform_data(v) for v in helpers.get_animation_bone_track_samples(clip, track_names[bone.casefold()])]
                if not values:
                    errors.append(name + ': empty control track ' + bone)
                    continue
                translation_span = math.sqrt(sum((max(v['translation'][axis] for v in values) - min(v['translation'][axis] for v in values)) ** 2 for axis in range(3)))
                indices = sorted({round((len(values) - 1) * i / 16) for i in range(17)})
                details['controls'][bone] = {'keyCount': len(values), 'localTranslationSpanImportedUnits': translation_span,
                    'sampledKeys': [{'index': i, **values[i]} for i in indices]}
            report['clips'][name] = details
        if sha256(contract_path) != spec['sourceContractSha256']:
            errors.append('Source contract changed during inspection')
    except Exception as error:
        errors.append('Inspection exception: ' + str(error))
        raise
    finally:
        report['hierarchyTracksAndDurationPassed'] = not errors
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    if errors:
        raise RuntimeError('Rig audit failed: ' + '; '.join(errors))
    unreal.log('KK_RIG_AUDIT_COMPLETE ' + str(output))


if __name__ == '__main__':
    main()
