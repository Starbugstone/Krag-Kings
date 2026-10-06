"""Nib read-only FBX audit, adapted from the Krag agent's geometry auditor."""
import json, struct, zlib
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[4]
PATH=ROOT/'benchmark/shared/characters/nib/Nib_Natural.fbx'
OUT=ROOT/'benchmark/art/nib/v5-study/runtime-geometry-audit-v4b.json'

with PATH.open('rb') as stream:
    header=stream.read(27);assert header.startswith(b'Kaydara FBX Binary')
    version=struct.unpack_from('<I',header,23)[0];size=25 if version>=7500 else 13;fmt='<QQQB' if version>=7500 else '<IIIB'
    def prop():
        kind=stream.read(1)
        scalar={b'Y':('<h',2),b'C':('<?',1),b'I':('<i',4),b'F':('<f',4),b'D':('<d',8),b'L':('<q',8)}
        if kind in scalar:
            f,n=scalar[kind];return struct.unpack(f,stream.read(n))[0]
        if kind in (b'S',b'R'):
            n=struct.unpack('<I',stream.read(4))[0];data=stream.read(n);return data.decode(errors='replace') if kind==b'S' else {'bytes':n}
        n,encoding,length=struct.unpack('<III',stream.read(12));offset=stream.tell();stream.seek(length,1)
        return {'array':kind.decode(),'count':n,'encoding':encoding,'bytes':length,'offset':offset}
    def node(allowed=None):
        raw=stream.read(size)
        if len(raw)!=size:return None
        end,count,_,length=struct.unpack(fmt,raw)
        if not end:return None
        name=stream.read(length).decode()
        if allowed is not None and name not in allowed:stream.seek(end);return None
        properties=[prop() for _ in range(count)];children=[]
        child_filter={'Geometry','Material','Model','Deformer'} if name=='Objects' else None
        while stream.tell()<end-size:
            child=node(child_filter)
            if child is not None:children.append(child)
        stream.seek(end);return {'name':name,'properties':properties,'children':children}
    roots=[]
    while True:
        at=stream.tell();item=node({'Objects','Connections'})
        if item:roots.append(item)
        elif stream.tell()==at+size:break

objects=next(n['children'] for n in roots if n['name']=='Objects')
edges=[n['properties'] for n in next(n['children'] for n in roots if n['name']=='Connections') if n['name']=='C']
by_id={n['properties'][0]:n for n in objects if n['properties']}
def label(n):return n['properties'][1].split('\x00',1)[0]
def child(n,name):return next(c for c in n['children'] if c['name']==name)
def array(meta):
    with PATH.open('rb') as stream:stream.seek(meta['offset']);raw=stream.read(meta['bytes'])
    if meta['encoding']:raw=zlib.decompress(raw)
    return np.frombuffer(raw,dtype={'d':'<f8','f':'<f4','i':'<i4','l':'<i8','b':'u1','c':'i1'}[meta['array']])

report={'fbx':str(PATH),'fbxVersion':version,'status':'Read-only geometry audit; source and shared exports unchanged','meshes':[],'shapeTargets':[]}
for obj in objects:
    if obj['name']!='Geometry':continue
    if obj['properties'][2]=='Shape':
        index=child(obj,'Indexes')['properties'][0];v=child(obj,'Vertices')['properties'][0]
        report['shapeTargets'].append({'name':label(obj),'sparseAffectedVertices':index['count'],'deltaComponents':v['count'],'compressedDeltaBytes':v['bytes']})
        continue
    if obj['properties'][2]!='Mesh':continue
    verts=array(child(obj,'Vertices')['properties'][0]).reshape(-1,3)
    ids=array(child(obj,'PolygonVertexIndex')['properties'][0]).copy();ends=np.flatnonzero(ids<0);ids[ends]=-ids[ends]-1
    starts=np.r_[0,ends[:-1]+1];tris=ends-starts-1
    material=array(child(child(obj,'LayerElementMaterial'),'Materials')['properties'][0])
    model=next(e[2] for e in edges if e[1]==obj['properties'][0] and by_id.get(e[2],{}).get('name')=='Model')
    mats=[label(by_id[e[1]]) for e in edges if e[2]==model and by_id.get(e[1],{}).get('name')=='Material']
    centre=np.empty((len(ends),3))
    for axis in range(3):centre[:,axis]=np.add.reduceat(verts[ids,axis],starts)/(ends-starts+1)
    regions={'Head above 1.025m':centre[:,2]>1.025,'Neck and torso':(centre[:,2]>=.59)&(centre[:,2]<=1.025)&(np.abs(centre[:,0])<.13),
             'Arms and hands':(np.abs(centre[:,0])>=.13)&(centre[:,2]>=.5),'Legs and clothing below waist':centre[:,2]<.59}
    item={'name':label(obj),'vertices':len(verts),'polygons':len(ends),'triangles':int(tris.sum()),'meshLocalBoundsNotWorldBounds':{'min':verts.min(axis=0).tolist(),'max':verts.max(axis=0).tolist()},
          'trianglesByMaterial':{m:int(tris[material==i].sum()) for i,m in enumerate(mats)},
          'trianglesByOverlappingMeshLocalRegion':{k:int(tris[mask].sum()) for k,mask in regions.items()},
          'fullMeshMorphPositionBufferMB':len(verts)*25*3*4/1024**2,'fullMeshMorphPositionAndNormalAndTangentMB':len(verts)*25*9*4/1024**2}
    report['meshes'].append(item)
OUT.write_text(json.dumps(report,indent=2));print(json.dumps(report['meshes'],indent=2))
