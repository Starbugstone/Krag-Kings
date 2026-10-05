"""Read FBX AnimationStack/Layer/model connections without loading/decompressing meshes.

Blender imports one Action per animated datablock; those are not FBX take counts.
This read-only audit distinguishes skeletal and shape-channel tracks per actual take.
"""
import argparse
import json
from pathlib import Path
import struct


def inspect(path):
    with Path(path).open('rb') as stream:
        header = stream.read(27)
        if not header.startswith(b'Kaydara FBX Binary'):
            raise ValueError('Expected binary FBX: ' + str(path))
        version = struct.unpack_from('<I', header, 23)[0]
        size = 25 if version >= 7500 else 13
        fmt = '<QQQB' if version >= 7500 else '<IIIB'

        def prop():
            kind = stream.read(1)
            scalars = {b'Y': ('<h', 2), b'C': ('<?', 1), b'I': ('<i', 4), b'F': ('<f', 4), b'D': ('<d', 8), b'L': ('<q', 8)}
            if kind in scalars:
                shape, count = scalars[kind]
                return struct.unpack(shape, stream.read(count))[0]
            if kind in (b'S', b'R'):
                count = struct.unpack('<I', stream.read(4))[0]
                data = stream.read(count)
                return data.decode('utf-8', errors='replace') if kind == b'S' else {'bytes': count}
            if kind in (b'f', b'd', b'l', b'i', b'b', b'c'):
                count, encoding, length = struct.unpack('<III', stream.read(12))
                stream.seek(length, 1)
                return {'array': kind.decode(), 'length': count, 'encoding': encoding}
            raise ValueError('Unexpected FBX property type: ' + repr(kind))

        def node(allowed=None):
            raw = stream.read(size)
            if len(raw) != size:
                return None
            end, count, properties_size, name_length = struct.unpack(fmt, raw)
            if end == 0:
                return None
            name = stream.read(name_length).decode()
            if allowed is not None and name not in allowed:
                stream.seek(end)
                return {'name': name, 'properties': [], 'children': []}
            properties = [prop() for _ in range(count)]
            children = []
            allowed_children = {'AnimationStack', 'AnimationLayer', 'AnimationCurveNode', 'Model', 'Deformer'} if name == 'Objects' else None
            while stream.tell() < end - size:
                child = node(allowed_children)
                if child is not None:
                    children.append(child)
            stream.seek(end)
            return {'name': name, 'properties': properties, 'children': children}

        roots = []
        while True:
            item = node({'Objects', 'Connections'})
            if item is None:
                break
            roots.append(item)
    objects = next(r['children'] for r in roots if r['name'] == 'Objects')
    connections = next(r['children'] for r in roots if r['name'] == 'Connections')
    by_id = {o['properties'][0]: o for o in objects if o['properties'] and isinstance(o['properties'][0], int)}
    edges = [c['properties'] for c in connections if c['name'] == 'C']

    def label(obj):
        return obj['properties'][1].split('\x00', 1)[0]

    stacks = []
    for obj in objects:
        if obj['name'] != 'AnimationStack' or not obj['properties']:
            continue
        stack_id = obj['properties'][0]
        layers = {e[1] for e in edges if len(e) >= 3 and e[2] == stack_id and by_id.get(e[1], {}).get('name') == 'AnimationLayer'}
        nodes = {e[1] for e in edges if len(e) >= 3 and e[2] in layers and by_id.get(e[1], {}).get('name') == 'AnimationCurveNode'}
        targets = {e[2] for e in edges if len(e) >= 3 and e[1] in nodes and e[2] in by_id and e[2] not in layers}
        models = [by_id[t] for t in targets if by_id[t]['name'] == 'Model']
        bones = [label(m) for m in models if m['properties'][2] in ('LimbNode', 'Root')]
        shapes = [label(by_id[t]) for t in targets if by_id[t]['name'] == 'Deformer' and by_id[t]['properties'][2] == 'BlendShapeChannel']
        stacks.append({'name': label(obj), 'layerCount': len(layers), 'curveNodeCount': len(nodes), 'skeletalBoneCount': len(bones), 'skeletalBones': sorted(bones), 'shapeChannelCount': len(shapes)})
    return {'file': str(path), 'fbxVersion': version, 'animationStackCount': len(stacks), 'stacks': stacks}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('files', nargs='+', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    report = [inspect(path) for path in args.files]
    data = json.dumps(report, indent=2)
    if args.output:
        args.output.write_text(data + '\n')
    else:
        print(data)
