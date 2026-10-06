"""Read-only raw FBX coordinates for later authored-component cleanup."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
from validate_triangulated_payload import geometry,data,child,mapped,polygon_vertices

parser=argparse.ArgumentParser();parser.add_argument('fbx',type=Path);parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args();mesh=next(n for n in geometry(args.fbx) if n['props'][2]=='Mesh')
points=data(mesh,'Vertices').reshape(-1,3);raw=data(mesh,'PolygonVertexIndex')
if not np.all(raw.reshape(-1,3)[:,-1]<0):raise RuntimeError('Expected triangular FBX')
ids=np.where(raw<0,-raw-1,raw).reshape(-1,3);p=points[ids]
cross=np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0]);zero=np.linalg.norm(cross,axis=1)==0
uv=mapped(child(mesh,'LayerElementUV'),'UV','UVIndex',2,ids.reshape(-1)).reshape(-1,3,2)
u=uv[:,1]-uv[:,0];v=uv[:,2]-uv[:,0];uvzero=np.abs(u[:,0]*v[:,1]-u[:,1]*v[:,0])==0
material=data(child(mesh,'LayerElementMaterial'),'Materials')
if len(material)!=len(ids):raise RuntimeError('Expected per-polygon materials')
def regions(mask):
    chosen=np.flatnonzero(mask);groups={}
    for i in chosen:
        center=p[i].mean(0);key=(int(material[i]),*np.round(center,3))
        groups.setdefault(key,[]).append(int(i))
    out=[]
    for group in sorted(groups.values(),key=len,reverse=True):
        block=p[group].reshape(-1,3)
        out.append({'count':len(group),'materialSlot':int(material[group[0]]),'triangleIds':group,
                    'rawLocalMin':block.min(0).tolist(),'rawLocalMax':block.max(0).tolist(),
                    'sampleVertexIds':ids[group[:4]].tolist()})
    return out
report={'status':'Read-only exported triangle localization; authored component identification still requires saved-source correspondence',
        'fbx':str(args.fbx),'sha256':hashlib.sha256(args.fbx.read_bytes()).hexdigest(),
        'coordinateSpace':'FBX mesh local; do not treat as world coordinates without its Model transform',
        'exactZeroAreaTriangles':int(zero.sum()),'exactCollapsedUvTriangles':int(uvzero.sum()),
        'zeroAreaRegions':regions(zero),'largestCollapsedUvRegions':regions(uvzero)[:30]}
args.output.write_text(json.dumps(report,indent=2)+'\n',newline='\n')
print(json.dumps({k:report[k] for k in ['exactZeroAreaTriangles','exactCollapsedUvTriangles']},indent=2))
