"""Quantify source triangle/normal defects without loading an engine or Blender.
Read-only, one mesh at a time; source-space units are reported without guessing scale.
"""
import argparse,hashlib,json,os,struct,zlib
from pathlib import Path
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
import numpy as np


def read_meshes(path):
    meshes=[]
    with Path(path).open('rb') as f:
        header=f.read(27)
        if not header.startswith(b'Kaydara FBX Binary'):raise ValueError('Binary FBX required')
        version=struct.unpack_from('<I',header,23)[0]
        fmt,size=('<QQQB',25) if version>=7500 else ('<IIIB',13)
        scalar={b'Y':'<h',b'C':'<?',b'I':'<i',b'F':'<f',b'D':'<d',b'L':'<q'}
        dtype={b'd':'<f8',b'f':'<f4',b'i':'<i4',b'l':'<i8',b'b':'u1',b'c':'u1'}
        def prop():
            kind=f.read(1)
            if kind in scalar:
                form=scalar[kind];return struct.unpack(form,f.read(struct.calcsize(form)))[0]
            if kind in (b'S',b'R'):
                count=struct.unpack('<I',f.read(4))[0];data=f.read(count)
                return data.decode('utf-8','replace') if kind==b'S' else data
            if kind in dtype:
                count,encoding,length=struct.unpack('<III',f.read(12));data=f.read(length)
                if encoding:data=zlib.decompress(data)
                values=np.frombuffer(data,dtype=dtype[kind])
                if len(values)!=count:raise ValueError('Array count mismatch')
                return values
            raise ValueError(kind)
        def node(parent='',active=None):
            raw=f.read(size)
            if len(raw)<size:return
            end,count,_,length=struct.unpack(fmt,raw)
            if not end:return
            name=f.read(length).decode()
            if (not parent and name!='Objects') or (parent=='Objects' and name!='Geometry'):
                f.seek(end);return
            props=[prop() for _ in range(count)]
            if name=='Geometry':
                if len(props)<3 or props[2]!='Mesh':f.seek(end);return
                active={'name':props[1].split('\0')[0],'arrays':{}};meshes.append(active)
            if active is not None and props and isinstance(props[0],np.ndarray) and name in ('Vertices','PolygonVertexIndex','Normals','UV','UVIndex','Materials'):
                active['arrays'][name]=props[0]
            while f.tell()<end-size:node(name,active)
            f.seek(end)
        while f.tell()<Path(path).stat().st_size-size:
            old=f.tell();node()
            if f.tell()==old+size:break
    return meshes


def audit(path):
    results=[]
    for mesh in read_meshes(path):
        arrays=mesh['arrays'];vertices=arrays['Vertices'].reshape(-1,3);indices=arrays['PolygonVertexIndex']
        if len(indices)%3 or not np.all(indices[2::3]<0) or np.any(indices.reshape(-1,3)[:,:2]<0):raise ValueError('All-triangle FBX required')
        indices=np.where(indices<0,-indices-1,indices).reshape(-1,3)
        if np.min(indices)<0 or np.max(indices)>=len(vertices):raise ValueError('Triangle vertex index out of range')
        p=vertices[indices];cross=np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0]);double_area=np.sqrt(np.einsum('ij,ij->i',cross,cross));del p,cross
        diagonal=float(np.linalg.norm(np.max(vertices,axis=0)-np.min(vertices,axis=0)));epsilon=diagonal*diagonal*1e-12
        exact=double_area==0;near=double_area<=epsilon
        item={'name':mesh['name'],'vertices':len(vertices),'triangles':len(indices),'finiteVertexComponents':bool(np.all(np.isfinite(vertices))),'boundsDiagonalFileUnits':diagonal,'exactZeroAreaTriangles':int(np.sum(exact)),'nearZeroAreaTriangles':int(np.sum(near)),'relativeDoubleAreaThreshold':1e-12,'minimumNonzeroDoubleAreaFileUnitsSquared':float(np.min(double_area[double_area>0])) if np.any(double_area>0) else None}
        if 'Materials' in arrays:
            mats=arrays['Materials']
            if len(mats)==len(indices):
                ids,counts=np.unique(mats[near],return_counts=True);item['nearZeroTrianglesByMaterialSlot']={int(i):int(c) for i,c in zip(ids,counts)}
        if 'Normals' in arrays:
            normals=arrays['Normals'].reshape(-1,3);norm=np.sqrt(np.einsum('ij,ij->i',normals,normals))
            item['authoredNormals']={'count':len(normals),'finite':bool(np.all(np.isfinite(normals))),'zeroLengthCount':int(np.sum(norm<=1e-12)),'nonunitOutsideOnePercent':int(np.sum(np.abs(norm-1)>.01)),'minimumLength':float(np.min(norm)),'maximumLength':float(np.max(norm))}
        if 'UV' in arrays and 'UVIndex' in arrays and len(arrays['UVIndex'])==len(indices)*3:
            uv=arrays['UV'].reshape(-1,2)[arrays['UVIndex'].reshape(-1,3)];a=uv[:,1]-uv[:,0];b=uv[:,2]-uv[:,0];det=np.abs(a[:,0]*b[:,1]-a[:,1]*b[:,0])
            item['uvTriangles']={'exactZeroArea':int(np.sum(det==0)),'nearZeroDoubleArea1eMinus12':int(np.sum(det<=1e-12)),'finite':bool(np.all(np.isfinite(uv)))}
        results.append(item)
    return {'file':str(path),'sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest(),'scope':'Neutral source geometry and authored normals only; does not diagnose importer tangents or morphed-pose degeneracy','meshes':results}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('files',nargs='+',type=Path);parser.add_argument('--output',required=True,type=Path);args=parser.parse_args()
    args.output.write_text(json.dumps([audit(p) for p in args.files],indent=2)+'\n')
