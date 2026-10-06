"""Verify a pretriangulated FBX keeps point, morph and mapped corner data.

Run with Blender's bundled plain Python (NumPy), not a Blender scene. This
compares actual binary FBX arrays, independently of the exporter's success code.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import zlib
import numpy as np


def geometry(path):
    output = []
    with Path(path).open('rb') as stream:
        header = stream.read(27)
        if not header.startswith(b'Kaydara FBX Binary'):
            raise ValueError('Binary FBX required')
        version = struct.unpack_from('<I', header, 23)[0]
        size, fmt = (25, '<QQQB') if version >= 7500 else (13, '<IIIB')

        def prop():
            kind = stream.read(1)
            scalar = {b'Y':'<h', b'C':'<?', b'I':'<i', b'F':'<f', b'D':'<d', b'L':'<q'}
            if kind in scalar:
                f = scalar[kind]
                return struct.unpack(f, stream.read(struct.calcsize(f)))[0]
            if kind in (b'S', b'R'):
                raw = stream.read(struct.unpack('<I', stream.read(4))[0])
                return raw.decode('utf8', 'replace') if kind == b'S' else raw
            types = {b'f':'<f4', b'd':'<f8', b'i':'<i4', b'l':'<i8', b'b':'u1', b'c':'u1'}
            if kind in types:
                count, encoding, length = struct.unpack('<III', stream.read(12))
                raw = stream.read(length)
                if encoding == 1: raw = zlib.decompress(raw)
                elif encoding != 0: raise ValueError('Invalid array compression')
                value = np.frombuffer(raw, dtype=types[kind])
                if len(value) != count: raise ValueError('FBX array size mismatch')
                return value
            raise ValueError('Unsupported FBX property '+repr(kind))

        def node(parent=''):
            raw = stream.read(size)
            if len(raw) != size: return None
            end, count, _, namelen = struct.unpack(fmt, raw)
            if not end: return None
            name = stream.read(namelen).decode()
            if (not parent and name != 'Objects') or (parent == 'Objects' and name != 'Geometry'):
                stream.seek(end); return None
            props = [prop() for _ in range(count)]
            children = []
            while stream.tell() < end-size:
                child = node(name)
                if child is not None: children.append(child)
            stream.seek(end)
            result = {'name':name, 'props':props, 'children':children}
            if name == 'Geometry': output.append(result)
            return result

        length = Path(path).stat().st_size
        while stream.tell() < length-size:
            before = stream.tell(); node()
            if stream.tell() == before+size: break
    return output


def child(node, name):
    return next(x for x in node['children'] if x['name'] == name)


def data(node, name):
    return child(node, name)['props'][0]


def sha(array):
    return hashlib.sha256(array.tobytes()).hexdigest()


def label(node):
    return node['props'][1].split('\x00', 1)[0]


def polygon_vertices(mesh):
    values = data(mesh, 'PolygonVertexIndex')
    return np.where(values < 0, -values-1, values)


def mapped(layer, value_name, index_name, width, indices):
    values = data(layer, value_name).reshape((-1,width))
    mapping = data(layer, 'MappingInformationType')
    reference = data(layer, 'ReferenceInformationType')
    if mapping in ('ByVertice', 'ByVertex'): selected = indices
    elif mapping == 'ByPolygonVertex': selected = np.arange(len(indices))
    elif mapping == 'AllSame': selected = np.zeros(len(indices),dtype=np.int32)
    else: raise ValueError('Unsupported corner mapping '+mapping)
    if reference == 'IndexToDirect': selected = data(layer,index_name)[selected]
    elif reference != 'Direct': raise ValueError('Unsupported reference '+reference)
    return values[selected]


def uv_corner_set(mesh):
    indices = polygon_vertices(mesh)
    uv = mapped(child(mesh,'LayerElementUV'), 'UV','UVIndex',2,indices)
    materials=child(mesh,'LayerElementMaterial')
    mapping=data(materials,'MappingInformationType')
    values=data(materials,'Materials')
    if mapping=='AllSame': material=np.full(len(indices),values[0])
    elif mapping=='ByPolygon':
        ends=np.flatnonzero(data(mesh,'PolygonVertexIndex')<0)
        material=np.repeat(values,np.diff(np.r_[-1,ends]))
    else: raise ValueError('Unsupported material mapping '+mapping)
    # Float64 FBX UV payloads originate from float32 mesh UVs. Quantization only
    # ignores <0.00000005 texture-coordinate noise, not a whole texel.
    rows = np.empty(len(indices),dtype=[('vertex','<i8'),('material','<i8'),('u','<i8'),('v','<i8')])
    rows['vertex'] = indices
    rows['material'] = material
    rows['u'] = np.rint(uv[:,0]*1e7).astype(np.int64)
    rows['v'] = np.rint(uv[:,1]*1e7).astype(np.int64)
    return np.unique(rows)


def compare(source, target):
    before, after = geometry(source), geometry(target)
    bm = [n for n in before if n['props'][2] == 'Mesh']
    am = [n for n in after if n['props'][2] == 'Mesh']
    if len(bm) != 1 or len(am) != 1: raise ValueError('Expected one assembled mesh per variant')
    b,a = bm[0],am[0]
    bp,ap = data(b,'Vertices'),data(a,'Vertices')
    if not np.array_equal(bp,ap): raise AssertionError('Vertex payload or ordering changed')
    bs = {label(n):n for n in before if n['props'][2] == 'Shape'}
    ass = {label(n):n for n in after if n['props'][2] == 'Shape'}
    if set(bs) != set(ass): raise AssertionError('Shape target list changed')
    shapes = []
    all_shapes_identical=True
    for name in sorted(bs):
        identical=True;delta_max=0.;delta_rms=0.
        for field in ['Indexes','Vertices']:
            if not np.array_equal(data(bs[name],field),data(ass[name],field)):
                identical=False;all_shapes_identical=False
                old=np.zeros_like(bp.reshape((-1,3)));new=np.zeros_like(old)
                old[data(bs[name],'Indexes')]=data(bs[name],'Vertices').reshape((-1,3))
                new[data(ass[name],'Indexes')]=data(ass[name],'Vertices').reshape((-1,3))
                distances=np.linalg.norm(old-new,axis=1)
                delta_max=float(distances.max());delta_rms=float(np.sqrt(np.mean(distances**2)))
                worst=np.argsort(distances)[-8:]
                print('MORPH_PAYLOAD_MISMATCH',json.dumps({'name':name,'sourceSparseCount':len(data(bs[name],'Indexes')),
                      'targetSparseCount':len(data(ass[name],'Indexes')),'maxDeltaDifference':float(distances.max()),
                      'nonzeroDifferences':int(np.sum(distances>1e-8)),
                      'worstVertices':worst.tolist(),'sourceDeltas':old[worst].tolist(),'targetDeltas':new[worst].tolist()}),flush=True)
                # Root authorized a practical 1 micrometre limit after one
                # exact-restoration attempt; record every measured difference.
                if delta_max>1e-6:raise AssertionError('Sparse morph delta exceeds 1 micrometre: '+name+'/'+field)
                break
        shapes.append({'name':name,'indicesSha256':sha(data(bs[name],'Indexes')),
                       'deltaSha256':sha(data(bs[name],'Vertices')),
                       'candidateIndicesSha256':sha(data(ass[name],'Indexes')),
                       'candidateDeltaSha256':sha(data(ass[name],'Vertices')),
                       'payloadByteIdentical':identical,'denseDeltaMaxErrorMeters':delta_max,
                       'denseDeltaRmsErrorMeters':delta_rms,'toleranceMeters':1e-6})
    ends = np.flatnonzero(data(a,'PolygonVertexIndex') < 0)
    sizes = np.diff(np.r_[-1,ends])
    if not np.all(sizes==3): raise AssertionError('Nontriangular exported polygon')
    original_ends = np.flatnonzero(data(b,'PolygonVertexIndex') < 0)
    equivalent = int(np.sum(np.diff(np.r_[-1,original_ends])-2))
    if len(sizes) != equivalent: raise AssertionError('Triangle equivalent count changed')
    u0,u1 = uv_corner_set(b),uv_corner_set(a)
    if not np.array_equal(u0,u1): raise AssertionError('Mapped vertex/material/UV corner set changed')
    baseline_indices = polygon_vertices(b)
    baseline_normals = mapped(child(b,'LayerElementNormal'),'Normals','NormalsIndex',3,baseline_indices)
    vertex_normals = np.zeros((len(bp)//3,3),dtype=np.float64)
    vertex_normals[baseline_indices] = baseline_normals
    baseline_split = np.linalg.norm(baseline_normals-vertex_normals[baseline_indices],axis=1).max()
    if baseline_split > 1e-7: raise AssertionError('Source has split normals; per-vertex baseline comparison is insufficient')
    target_indices = polygon_vertices(a)
    target_normals = mapped(child(a,'LayerElementNormal'),'Normals','NormalsIndex',3,target_indices)
    normal_error = np.linalg.norm(target_normals-vertex_normals[target_indices],axis=1)
    normal_max = float(normal_error.max())
    if normal_max > .0002:
        worst=np.argsort(normal_error)[-12:]
        print('NORMAL_MISMATCH',json.dumps({'max':normal_max,'p99':float(np.quantile(normal_error,.99)),
              'aboveTolerance':int(np.sum(normal_error>.0002)),'sourceZeroNormals':int(np.sum(np.linalg.norm(vertex_normals[target_indices],axis=1)<1e-7)),
              'targetZeroNormals':int(np.sum(np.linalg.norm(target_normals,axis=1)<1e-7)),
              'vertices':target_indices[worst].tolist(),'source':vertex_normals[target_indices[worst]].tolist(),'target':target_normals[worst].tolist()}),flush=True)
        raise AssertionError(f'Mapped normal error {normal_max} exceeds 0.0002 vector length')
    return {'source':str(source),'target':str(target),'passed':True,
            'vertices':len(bp)//3,'triangles':len(sizes),'allPolygonsTriangular':True,
            'pointPayloadSha256':sha(bp),'pointAndMorphPayloadsByteIdentical':all_shapes_identical,
            'shapeTargets':shapes,'mappedUvMaterialCornerSetEqual':True,
            'uniqueVertexUvCorners':len(u0),'uvQuantization':1e-7,
            'mappedNormalMaxVectorError':normal_max,
            'mappedNormalP99VectorError':float(np.quantile(normal_error,.99)),
            'normalTolerance':.0002}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-dir',type=Path,required=True)
    parser.add_argument('--candidate-dir',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--names',nargs='+',default=['Nib_Natural','Nib_GripReplacement','Nib_LegReplacement'])
    args = parser.parse_args()
    results=[]
    for name in args.names:
        result=compare(args.source_dir/(name+'.fbx'),args.candidate_dir/(name+'.fbx'))
        results.append(result)
        print(name,json.dumps({k:v for k,v in result.items() if k!='shapeTargets'}),flush=True)
    args.output.write_text(json.dumps({'passed':True,'variants':results},indent=2)+'\n',newline='\n')
