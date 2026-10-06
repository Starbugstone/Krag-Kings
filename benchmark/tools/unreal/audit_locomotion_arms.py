"""Read existing single-take FBXs without Blender/Unreal or changing asset data.

Uses the existing raw FBX reader. These are exported-source measurements, not a
claim of engine-pose equivalence or anatomically acceptable animation.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location(
    "fbx_measure", ROOT / "benchmark/tools/krag/audit_fbx_weapon_aim.py")
FBX = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FBX)


def audit(path, species, clip):
    objects, edges = FBX.read(path)
    models = {i: o for i, o in objects.items() if o['name'] == 'Model'}
    names = {FBX.label(o): i for i, o in models.items()}
    props = {i: FBX.properties(o) for i, o in models.items()}
    stacks = [o for o in objects.values() if o['name'] == 'AnimationStack']
    if len(stacks) != 1:
        raise ValueError('Expected a single exported take')
    channels = {}
    for edge in edges:
        if edge[0] != 'OP' or edge[2] not in models or objects.get(edge[1], {}).get('name') != 'AnimationCurveNode':
            continue
        for row in edges:
            if row[0] != 'OP' or row[2] != edge[1] or objects.get(row[1], {}).get('name') != 'AnimationCurve':
                continue
            curve = objects[row[1]]
            channels[(edge[2], edge[3], row[3][-1])] = (
                FBX.children(curve, 'KeyTime')[0]['props'][0] / FBX.TICKS,
                FBX.children(curve, 'KeyValueFloat')[0]['props'][0])
    parents = {e[1]: e[2] for e in edges if e[0] == 'OO' and e[1] in models and e[2] in models}

    def matrix(model, time, cache):
        if model in cache:
            return cache[model]
        p = props[model]
        if p.get('RotationOrder', [0])[0] != 0:
            raise ValueError('Unsupported non-XYZ rotation order')
        for key in ('RotationPivot', 'RotationOffset', 'ScalingPivot', 'ScalingOffset'):
            if np.linalg.norm(p.get(key, [0, 0, 0])) > 1e-9:
                raise ValueError('Unsupported nonzero pivot: ' + key)
        vectors = {}
        for key, default in [('Lcl Translation', [0, 0, 0]), ('Lcl Rotation', [0, 0, 0]), ('Lcl Scaling', [1, 1, 1])]:
            value = np.asarray(p.get(key, default), dtype=float)
            for i, axis in enumerate('XYZ'):
                curve = channels.get((model, key, axis))
                if curve is not None:
                    value[i] = np.interp(time, *curve)
            vectors[key] = value
        m = np.eye(4)
        m[:3, :3] = FBX.euler(p.get('PreRotation', [0, 0, 0])) @ FBX.euler(vectors['Lcl Rotation']) @ FBX.euler(p.get('PostRotation', [0, 0, 0])).T @ np.diag(vectors['Lcl Scaling'])
        m[:3, 3] = vectors['Lcl Translation']
        if model in parents:
            m = matrix(parents[model], time, cache) @ m
        cache[model] = m
        return m

    start = min(float(c[0][0]) for c in channels.values())
    end = max(float(c[0][-1]) for c in channels.values())
    samples = []
    for normalized in np.linspace(0, 1, 37):
        cache = {}
        time = start + normalized * (end-start)
        inverse = np.linalg.inv(matrix(names[species + '_Rig'], time, cache))
        arms = {}
        for side in ('L', 'R'):
            points = [(inverse @ matrix(names[b + '_' + side], time, cache))[:3, 3] for b in ('UpperArm', 'LowerArm', 'Hand')]
            upper, lower = points[1]-points[0], points[2]-points[1]
            bend = float(np.degrees(np.arccos(np.clip(upper @ lower / np.linalg.norm(upper) / np.linalg.norm(lower), -1, 1))))
            line = points[2]-points[0]
            pole = points[1]-points[0]-line * ((points[1]-points[0]) @ line / (line @ line))
            arms[side] = {'shoulder': points[0].tolist(), 'elbow': points[1].tolist(), 'wrist': points[2].tolist(), 'elbowBendDegrees': bend, 'elbowPoleOffset': pole.tolist()}
        samples.append({'normalizedTime': float(normalized), 'arms': arms})
    ranges = {}
    for side in ('L', 'R'):
        ranges[side] = {}
        for name in ('elbowBendDegrees', 'elbowPoleOffset', 'wrist'):
            values = np.asarray([s['arms'][side][name] for s in samples])
            ranges[side][name] = {'min': values.min(axis=0).tolist(), 'max': values.max(axis=0).tolist()}
    return {'file': str(path.relative_to(ROOT)), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'species': species, 'clip': clip, 'take': FBX.label(stacks[0]), 'fileDurationSeconds': end-start, 'ranges': ranges, 'samples': samples}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = {
        'method': 'Raw single-take FBX XYZ matrices with PreRotation/PostRotation and zero pivots; sample 37 points; express joints in exported armature coordinates (metres, source forward -Y, up Z). Elbow bend 0 means straight. Elbow pole is perpendicular offset from shoulder-wrist line.',
        'limitations': ['No editor launched.', 'Linear evaluation between exported samples is diagnostic; no new animation is authored.', 'No matching actual engine quaternion samples are available; this does not establish exact source/engine pose equivalence.', 'Anatomical acceptance requires visual temporal review, not these ranges alone.'],
        'clips': [audit(ROOT / 'benchmark/shared/characters' / species.lower() / 'animations' / (clip + '.fbx'), species, clip) for species in ('Krag', 'Nib') for clip in ('Walk', 'Run')]
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps([{'species': c['species'], 'clip': c['clip'], 'ranges': c['ranges']} for c in result['clips']], indent=2))
