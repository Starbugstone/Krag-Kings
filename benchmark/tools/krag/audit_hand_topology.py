"""Lightweight source-hand connected-component and bone-fitting diagnostic.
No Blender process, changed source geometry, or pose acceptance is implied.
"""
from pathlib import Path
import json,hashlib,numpy as np
root=Path(__file__).resolve().parents[3]
p=root/'benchmark/art/krag/anatomy-study/GEO-body_male_realistic.npz'
a=np.load(p,allow_pickle=True);v=a['vertices'];faces=a['polygons']
edges=set()
for face in faces:
 for i,j in zip(face,np.roll(face,-1)):edges.add(tuple(sorted((int(i),int(j)))))
adj=[set() for _ in v]
for i,j in edges:adj[i].add(j);adj[j].add(i)
def parts(mask):
 unseen=set(np.flatnonzero(mask));result=[]
 while unseen:
  seed=unseen.pop();part={seed};stack=[seed]
  while stack:
   i=stack.pop();near=adj[i]&unseen;unseen-=near;part|=near;stack.extend(near)
  result.append(sorted(part))
 return sorted(result,key=lambda ids:float(v[ids,1].mean()))
report={'status':'Raw source topology diagnostic; not an accepted Krag hand or posed skin result','sourceSha256':hashlib.sha256(p.read_bytes()).hexdigest(),'slices':[]}
for z in [.87,.85,.83,.82,.81,.80,.79,.78,.77,.76,.75,.74]:
 groups=parts((v[:,0]>.32)&(v[:,2]<z)&(v[:,2]>.68))
 report['slices'].append({'upperZ':z,'components':[{'count':len(g),'indices':[int(i) for i in g],'minimum':v[g].min(0).tolist(),'maximum':v[g].max(0).tolist(),'mean':v[g].mean(0).tolist()} for g in groups]})
out=root/'benchmark/art/krag/anatomy-study/hand-topology-source-diagnostic.json';out.write_text(json.dumps(report,indent=2)+'\n',newline='\n')
for row in report['slices']:
 print(row['upperZ'],[(p['count'],[round(x,4) for x in p['mean']]) for p in row['components']])
