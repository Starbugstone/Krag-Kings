"""Cross-sections of actual source surfaces to inspect provisional joint fitting."""
from pathlib import Path
import json,numpy as np
from krag_hand_domains import solve
root=Path(__file__).resolve().parents[3];folder=root/'benchmark/art/krag/anatomy-study'
s=np.load(folder/'GEO-body_male_realistic.npz',allow_pickle=True);v=s['vertices'];polys=s['polygons'];domain,_=solve(v,polys)
edges=set()
for f in polys:
 for a,b in zip(f,np.roll(f,-1)):
  if v[a,0]>.32 and v[b,0]>.32 and max(v[a,2],v[b,2])<.93:edges.add(tuple(sorted((int(a),int(b)))))
def plane(axis,position):
 points=[];fields=[]
 for a,b in edges:
  if (v[a,axis]-position)*(v[b,axis]-position)>=0:continue
  t=(position-v[a,axis])/(v[b,axis]-v[a,axis]);points.append(v[a]*(1-t)+v[b]*t);fields.append(domain[a]*(1-t)+domain[b]*t)
 return np.asarray(points),np.asarray(fields)
report={'status':'Surface intersection measurements only; centers remain a fitting proposal','fingers':{},'thumb':[]}
for k,zs in enumerate([[.805,.765,.729],[.812,.756,.719],[.809,.757,.720],[.813,.778,.744]]):
 rows=[]
 for z in zs:
  p,f=plane(2,z);mask=(f.argmax(1)==k)&(f[:,k]>.015);q=p[mask];w=f[mask,k]**2
  center=np.sum(q*w[:,None],axis=0)/w.sum();rows.append({'z':z,'intersections':len(q),'center':center.tolist(),'bounds':[q.min(0).tolist(),q.max(0).tolist()]})
 report['fingers'][str(k)]=rows
for y in [-.113,-.130,-.150,-.168,-.173]:
 p,f=plane(1,y);mask=(p[:,2]>.800)&(p[:,2]<.875)&(p[:,0]<.395)
 q=p[mask];report['thumb'].append({'y':y,'intersections':len(q),'center':q.mean(0).tolist(),'bounds':[q.min(0).tolist(),q.max(0).tolist()]})
(folder/'hand-joint-cross-sections.json').write_text(json.dumps(report,indent=2)+'\n',newline='\n');print(json.dumps(report,indent=2))
