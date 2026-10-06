from pathlib import Path
import sys,json,hashlib
import numpy as np
ROOT=Path(r"D:\Dev\Krag-Kings")
sys.path.insert(0,str(ROOT/'benchmark/tools/nib/v5_wip'))
from validate_triangulated_payload import geometry,data,polygon_vertices
source=ROOT/'benchmark/art/nib/groom-study/native-filtered-target-v1/triangulated/Nib_Natural.fbx'
mesh=next(g for g in geometry(source) if g['props'][2]=='Mesh')
p=data(mesh,'Vertices').reshape(-1,3)
idx=polygon_vertices(mesh).reshape(-1,3)
q=np.fromfile(ROOT/'benchmark/local/unity-strand-hair-pilot/character-import-v2/mesh-0-source-positions.bin',dtype='<f4').reshape(-1,3)
j=np.fromfile(ROOT/'benchmark/local/unity-strand-hair-pilot/character-import-v2/mesh-0-indices.bin',dtype='<i4').reshape(-1,3)
area=np.linalg.norm(np.cross(p[idx[:,1]]-p[idx[:,0]],p[idx[:,2]]-p[idx[:,0]]),axis=1)*.5
area2=np.linalg.norm(np.cross(q[j[:,1]]-q[j[:,0]],q[j[:,2]]-q[j[:,0]]),axis=1)*.5
print(json.dumps({'sourceVertices':len(p),'sourceTriangles':len(idx),'sourceBounds':[p.min(0).tolist(),p.max(0).tolist()],'importVertices':len(q),'importTriangles':len(j),'importBounds':[q.min(0).tolist(),q.max(0).tolist()],'sourceZeroArea':int(sum(area==0)),'sourceTinyArea':{str(t):int(sum(area<=t)) for t in [1e-20,1e-18,1e-16,1e-14,1e-12]},'importZeroArea':int(sum(area2==0))},indent=2))

from scipy.spatial import cKDTree
manifest=json.loads((source.parent/'manifest.json').read_text())
world=manifest['variants'][0]['sourceRestBoundsMeters']
offset=np.asarray(world['min'])-p.min(0)
if np.max(np.abs(p.max(0)+offset-np.asarray(world['max'])))>2e-7:raise RuntimeError('Mesh-local bounds do not match authored world bounds by translation')
canonical=p+offset
unique,source_id=np.unique(canonical,axis=0,return_inverse=True)
distance,import_id=cKDTree(unique).query(q,workers=1)
if distance.max()>2e-6:raise RuntimeError('Imported vertex movement exceeds2micrometres '+str(distance.max()))
def keys(indices,ids):
 x=np.sort(ids[indices],axis=1).astype('<i8')
 return np.ascontiguousarray(x).view(np.dtype((np.void,24))).ravel()
source_keys=keys(idx,source_id);import_keys=keys(j,import_id)
a,ac=np.unique(source_keys,return_counts=True);b,bc=np.unique(import_keys,return_counts=True)
from collections import Counter
expected=Counter({x.tobytes():int(n) for x,n in zip(a,ac)});actual=Counter({x.tobytes():int(n) for x,n in zip(b,bc)})
removed=expected-actual;added=actual-expected
removed_source=np.array([i for i,key in enumerate(source_keys) if key.tobytes() in removed])
result={'sourceSha256':hashlib.sha256(source.read_bytes()).hexdigest(),'authoredWorldOffsetFromRawFbx':offset.tolist(),'maximumImportedVertexErrorMeters':float(distance.max()),'sourceTriangles':len(idx),'importedTriangles':len(j),'removedTriangleMultiplicity':sum(removed.values()),'addedTriangleMultiplicity':sum(added.values()),'removedSourceCandidateIndices':removed_source.tolist(),'removedMaximumAreaM2':float(area[removed_source].max()) if len(removed_source) else 0,'removedNonzeroAreaCandidateCount':int(sum(area[removed_source]>0)),'matchedNondegenerateTriangleMultiset':sum(added.values())==0 and sum(removed.values())==126 and not np.any(area[removed_source]>0)}
(ROOT/'benchmark/local/unity-strand-hair-pilot/character-import-v2/topology-attribution.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
