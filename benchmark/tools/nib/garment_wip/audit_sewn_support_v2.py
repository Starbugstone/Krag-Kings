"""Lightweight ray audit on saved actual Nib Basis cache; no Blender process.

The cache comes from the read-only saved-DNA extractor. This script diagnoses
all pattern correspondences before rerunning any cloth solve. It does not
claim evaluated/native cloth or modifier behavior.
"""
import sys,json,hashlib
from pathlib import Path
import numpy as np
HERE=Path(__file__).parent;ROOT=HERE.parents[3];sys.path.insert(0,str(HERE))
import sewn_undershirt_v2
cache=ROOT/'benchmark/local/nib-actual-v5-body.json';source=json.loads(cache.read_text())
assert source['sourceSha256']=='b82786d632424fd93b798b1a347aab29e568585ee700ce57b0ab435ee76a10da'
p=np.asarray(source['vertices']);triangles=np.asarray([(f[0],f[i],f[i+1]) for f in source['polygons'] for i in range(1,len(f)-1)],dtype=np.int32)
domain=np.asarray([sum(w for n,w in row if n.startswith(('Clavicle','UpperArm','LowerArm','ForearmTwist','Hand'))) for row in source['weights']])
triangles=triangles[np.max(domain[triangles],axis=1)<.14]
q=p[triangles];minimum=q.min(1);maximum=q.max(1);e1=q[:,1]-q[:,0];e2=q[:,2]-q[:,0];normal=np.cross(e1,e2);normal/=np.maximum(np.linalg.norm(normal,axis=1)[:,None],1e-20)
pattern=sewn_undershirt_v2.pattern();failures=[];hits=[]
for i,(point,d) in enumerate(zip(pattern['points'],pattern['directions'])):
 origin=point+d*.18;axis=-d;valid=np.ones(len(triangles),dtype=bool)
 for j in range(3):
  if abs(axis[j])<1e-10:valid&=(minimum[:,j]<=origin[j]+1e-10)&(maximum[:,j]>=origin[j]-1e-10)
 ids=np.flatnonzero(valid)
 h=np.cross(np.broadcast_to(axis,(len(ids),3)),e2[ids]);det=np.sum(e1[ids]*h,1);good=abs(det)>1e-12
 inv=np.zeros_like(det);inv[good]=1/det[good];s=origin-q[ids,0];u=inv*np.sum(s*h,1);cross=np.cross(s,e1[ids]);v=inv*np.sum(axis*cross,1);distance=inv*np.sum(e2[ids]*cross,1)
 good&=(u>=-1e-9)&(v>=-1e-9)&(u+v<=1+1e-9)&(distance>=0)&(distance<=.36)
 candidates=ids[good]
 if len(candidates):
  index=int(candidates[np.argmin(distance[good])]);dot=float(normal[index]@d)
  if dot>=.05:
   hit=origin+axis*float(distance[good].min());hits.append({'vertex':i,'region':pattern['regions'][i],'guide':point.tolist(),'hit':hit.tolist(),'normalDot':dot,'shift':float(np.linalg.norm(hit-point))});continue
 failures.append({'vertex':i,'region':pattern['regions'][i],'guide':point.tolist(),'direction':d.tolist(),'rayCandidates':len(candidates)})
report={'status':'Actual saved Basis cache ray audit; no native garment generation','sourceSha256':source['sourceSha256'],'cacheSha256':hashlib.sha256(cache.read_bytes()).hexdigest(),'patternSha256':hashlib.sha256(Path(sewn_undershirt_v2.__file__).read_bytes()).hexdigest(),'domainInterpretation':'Reconstructed sum of actual arm-chain skin weights; Blender native fitter reads original Nib_ArmDomain attribute','rays':len(pattern['points']),'rayHits':len(hits),'misses':failures,'hits':hits,'nativeValidation':False}
path=ROOT/'benchmark/art/nib/garment-study/sewn-support-audit-v2.json';path.write_text(json.dumps(report,indent=2)+'\n',newline='\n')
from collections import Counter
print(json.dumps({'rays':report['rays'],'hits':len(hits),'misses':len(failures),'missesByRegion':dict(Counter(v['region'] for v in failures)),'missBounds':[np.asarray([v['guide'] for v in failures]).min(0).tolist(),np.asarray([v['guide'] for v in failures]).max(0).tolist()] if failures else None,'firstMisses':failures[:8]}))
# Exact closest-point comparison for every missing directional correspondence.
def nearest(point):
 s=point-q[:,0];height=np.sum(s*normal,1);projected=point-height[:,None]*normal
 v0=e1;v1=e2;v2=projected-q[:,0];d00=np.sum(v0*v0,1);d01=np.sum(v0*v1,1);d11=np.sum(v1*v1,1);d20=np.sum(v2*v0,1);d21=np.sum(v2*v1,1);den=d00*d11-d01*d01
 vb=(d11*d20-d01*d21)/np.maximum(den,1e-30);wc=(d00*d21-d01*d20)/np.maximum(den,1e-30);inside=(vb>=0)&(wc>=0)&(vb+wc<=1)
 best=projected.copy();dist=np.sum((projected-point)**2,1);dist[~inside]=np.inf
 for a,b in [(q[:,0],q[:,1]),(q[:,1],q[:,2]),(q[:,2],q[:,0])]:
  delta=b-a;t=np.clip(np.sum((point-a)*delta,1)/np.maximum(np.sum(delta*delta,1),1e-30),0,1);hit=a+t[:,None]*delta;d2=np.sum((hit-point)**2,1);better=d2<dist;best[better]=hit[better];dist[better]=d2[better]
 index=int(np.argmin(dist));return best[index],normal[index],float(np.sqrt(dist[index])),index
for row in failures:
 point=np.asarray(row['guide']);hit,n,d,index=nearest(point)
 row['closestPoint']=hit.tolist();row['closestNormal']=n.tolist();row['distanceMeters']=d;row['signedNormalGapMeters']=float((point-hit)@n);row['normalVersusRayDirection']=float(n@row['direction']);row['triangle']=index
report['missNearestMaximumMeters']=max(r['distanceMeters'] for r in failures)
report['missNearestMinimumSignedGapMeters']=min(r['signedNormalGapMeters'] for r in failures)
report['rayGuideMaximumOffsetMeters']=max(r['shift'] for r in hits)
path.write_text(json.dumps(report,indent=2)+'\n',newline='\n')
print(json.dumps({'missNearestMaximumMeters':report['missNearestMaximumMeters'],'minimumSigned':report['missNearestMinimumSignedGapMeters'],'worst':sorted(failures,key=lambda r:-r['distanceMeters'])[:8],'maxRayShift':report['rayGuideMaximumOffsetMeters']}))
