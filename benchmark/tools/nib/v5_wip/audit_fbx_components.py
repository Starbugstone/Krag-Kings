"""Lightweight connected-surface cost breakdown of the existing exported mesh."""
import json
import numpy as np
import audit_fbx_geometry as audit

parent=list(range(len(audit.verts)));rank=[0]*len(parent)
def find(i):
    while parent[i]!=i:
        parent[i]=parent[parent[i]];i=parent[i]
    return i
def union(a,b):
    a=find(a);b=find(b)
    if a==b:return
    if rank[a]<rank[b]:a,b=b,a
    parent[b]=a
    if rank[a]==rank[b]:rank[a]+=1

for start,end in zip(audit.starts,audit.ends):
    first=int(audit.ids[start])
    for index in audit.ids[start+1:end+1]:union(first,int(index))
roots=np.array([find(int(audit.ids[i])) for i in audit.starts],dtype=np.int32)
groups,reverse=np.unique(roots,return_inverse=True)
counts=np.bincount(reverse,weights=audit.tris).astype(np.int64)
largest=[]
for group in np.argsort(-counts)[:30]:
    mask=reverse==group;selected=np.flatnonzero(mask)
    vertex_indices=np.unique(np.concatenate([audit.ids[audit.starts[i]:audit.ends[i]+1] for i in selected]))
    co=audit.verts[vertex_indices]
    largest.append({'triangles':int(counts[group]),'vertices':len(vertex_indices),
                    'materials':{m:int(audit.tris[mask&(audit.material==i)].sum()) for i,m in enumerate(audit.mats) if np.any(mask&(audit.material==i))},
                    'meshLocalBounds':{'min':co.min(0).tolist(),'max':co.max(0).tolist()}})
report={'status':'Actual FBX connected-surface audit; no source/output change.',
        'connectedSurfaces':len(groups),'largest':largest}
(audit.OUT.parent/'runtime-fbx-connected-surfaces.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
