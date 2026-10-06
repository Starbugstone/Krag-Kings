"""Audit binary FBX polygons and geometry payloads without loading Blender/Unreal.

Vertex and sparse-shape payload hashes let a pretriangulated derivative demonstrate
that its point data survived. Polygon/loop-normal/UV-index hashes may change with
triangulation; their equivalence still requires the artist's roundtrip checks.
"""
import argparse
from array import array
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct
import sys
import zlib


def inspect(path):
    geometry = []
    with Path(path).open('rb') as stream:
        header = stream.read(27)
        if not header.startswith(b'Kaydara FBX Binary'):
            raise ValueError('Binary FBX required')
        version = struct.unpack_from('<I', header, 23)[0]
        record_size, record_format = (25, '<QQQB') if version >= 7500 else (13, '<IIIB')

        def prop(node_name):
            kind = stream.read(1)
            scalar = {b'Y': '<h', b'C': '<?', b'I': '<i', b'F': '<f', b'D': '<d', b'L': '<q'}
            if kind in scalar:
                fmt = scalar[kind]
                return struct.unpack(fmt, stream.read(struct.calcsize(fmt)))[0]
            if kind in (b'S', b'R'):
                length = struct.unpack('<I', stream.read(4))[0]
                value = stream.read(length)
                return value.decode('utf-8', 'replace') if kind == b'S' else {'bytes': length}
            if kind in (b'f', b'd', b'l', b'i', b'b', b'c'):
                count, encoding, length = struct.unpack('<III', stream.read(12))
                data = stream.read(length)
                if encoding == 1:
                    data = zlib.decompress(data)
                elif encoding != 0:
                    raise ValueError('Unknown FBX array encoding')
                result = {'count': count, 'type': kind.decode(), 'sha256': hashlib.sha256(data).hexdigest()}
                if node_name == 'PolygonVertexIndex':
                    indices = array('i');indices.frombytes(data)
                    if sys.byteorder != 'little':indices.byteswap()
                    sizes = Counter();size = 0
                    for value in indices:
                        size += 1
                        if value < 0:
                            sizes[size] += 1;size = 0
                    if size:
                        raise ValueError('Unterminated polygon')
                    result['polygonSizes'] = dict(sorted(sizes.items()))
                return result
            raise ValueError('Unexpected property kind ' + repr(kind))

        def node(parent=''):
            raw = stream.read(record_size)
            if len(raw) != record_size:
                return None
            end, count, _, name_length = struct.unpack(record_format, raw)
            if not end:
                return None
            name = stream.read(name_length).decode()
            if (not parent and name != 'Objects') or (parent == 'Objects' and name != 'Geometry'):
                stream.seek(end)
                return None
            properties = [prop(name) for _ in range(count)]
            children = []
            while stream.tell() < end - record_size:
                child = node(name)
                if child is not None:children.append(child)
            stream.seek(end)
            item = {'name': name, 'properties': properties, 'children': children}
            if name == 'Geometry':geometry.append(item)
            return item

        while stream.tell() < Path(path).stat().st_size - record_size:
            position = stream.tell()
            node()
            if stream.tell() == position + record_size:
                break
    meshes, shapes = [], []
    for item in geometry:
        props = item['properties']
        if len(props) < 3:continue
        result = {'name': props[1].split('\x00', 1)[0], 'attributes': {c['name']: c['properties'] for c in item['children'] if c['properties'] and isinstance(c['properties'][0], dict)}}
        if props[2] == 'Mesh':
            indices = result['attributes']['PolygonVertexIndex'][0]
            sizes = indices['polygonSizes']
            result['polygonCount'] = sum(sizes.values())
            result['triangleCount'] = sum((n - 2) * total for n, total in sizes.items())
            result['allTriangles'] = bool(sizes) and set(sizes) == {3}
            result['vertexCount'] = result['attributes']['Vertices'][0]['count'] // 3
            result['layers'] = [c for c in item['children'] if c['name'] in ('LayerElementUV', 'LayerElementNormal')]
            meshes.append(result)
        elif props[2] == 'Shape':shapes.append(result)
    return {'file': str(path), 'sha256': hashlib.sha256(Path(path).read_bytes()).hexdigest(), 'fbxVersion': version, 'meshes': meshes, 'shapeCount': len(shapes), 'shapes': shapes, 'allMeshesTriangular': bool(meshes) and all(m['allTriangles'] for m in meshes)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('files', nargs='+', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    results = [inspect(path) for path in args.files]
    data = json.dumps(results, indent=2)
    if args.output:args.output.write_text(data + '\n')
    else:print(data)
