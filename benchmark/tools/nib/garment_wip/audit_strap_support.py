"""Read-only closest-triangle study from actual saved anatomy coordinates."""
import argparse,hashlib,json,os
from pathlib import Path
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
import numpy as np
p=argparse.ArgumentParser();p.add_argument('--cache',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();d=json.loads(a.cache.read_text());points=np.asarray(d['vertices'],float)
tris=np.asarray([(f[0],f[i],f[i+1]) for f in d['polygons'] for i in range(1,len(f)-1)],int);xyz=points[tris];base=xyz[:,0];u=xyz[:,1]-base;v=xyz[:,2]-base
normal=np.cross(u,v);norm=np.linalg.norm(normal,axis=1);valid=norm>1e-12;normal/=np.maximum(norm[:,None],1e-30)
def nearest(q):
 diff=q-base;d00=np.einsum('ij,ij->i',u,u);d01=np.einsum('ij,ij->i',u,v);d11=np.einsum('ij,ij->i',v,v);den=d00*d11-d01*d01
 du=np.einsum('ij,ij->i',diff,u);dv=np.einsum('ij,ij->i',diff,v)
 b=(d11*du-d01*dv)/np.maximum(den,1e-30);c=(d00*dv-d01*du)/np.maximum(den,1e-30)
 inside=valid&(b>=0)&(c>=0)&(b+c<=1);candidate=base+b[:,None]*u+c[:,None]*v;distance=np.linalg.norm(candidate-q,axis=1);distance[~inside]=np.inf
 best=int(distance.argmin());hit=candidate[best];best_distance=float(distance[best]);tri=best
 for j,k in [(0,1),(1,2),(2,0)]:
  edge=xyz[:,k]-xyz[:,j];t=np.clip(np.einsum('ij,ij->i',q-xyz[:,j],edge)/np.maximum(np.einsum('ij,ij->i',edge,edge),1e-30),0,1)
  candidate=xyz[:,j]+t[:,None]*edge;dist=np.linalg.norm(candidate-q,axis=1);dist[~valid]=np.inf;i=int(dist.argmin())
  if dist[i]<best_distance:best_distance=float(dist[i]);hit=candidate[i];tri=i
 return hit,normal[tri],tri,best_distance
original=np.asarray([(-.060,-.073,.880),(-.073,-.065,.937),(-.082,-.029,.967),(-.079,.025,.965),(-.055,.067,.893),(-.017,.074,.816),(.052,.067,.729)])
rows=[]
for i,q in enumerate(original):
 hit,n,tri,distance=nearest(q);rows.append({'control':i,'oldPoint':q.tolist(),'actualClosestSkinPoint':hit.tolist(),'outwardTriangleNormal':n.tolist(),'triangle':tri,'distanceMeters':distance,'signedNormalDistanceMeters':float((q-hit)@n),'supportPlus12mm':(hit+n*.012).tolist()})
r={'status':'Read-only actual native Basis closest-triangle measurements; no source authoring or visual acceptance','source':d['source'],'sourceSha256':d['sourceSha256'],'cacheSha256':hashlib.sha256(a.cache.read_bytes()).hexdigest(),'meshObject':d['meshObject'],'objectTransform':d['objectTransform'],'controls':rows,'interpretation':'Old leather route is provisional obsolete geometry; actual skin support informs a fresh fitted strap. No gate or anatomical point is moved.'}
a.output.write_text(json.dumps(r,indent=2)+'\n',newline='\n');print(json.dumps(rows))
