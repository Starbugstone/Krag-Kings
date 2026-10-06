"""Complete numerical support check on saved actual Nib mesh cache; no Blender launch."""
import sys,json,hashlib,time
from pathlib import Path
import numpy as np
H=Path(__file__).resolve().parent;R=H.parents[3];sys.path.insert(0,str(H));import sewn_undershirt_v2
s=json.loads((R/'benchmark/local/nib-actual-v5-body.json').read_text());p=np.asarray(s['vertices']);tri=np.asarray([(f[0],f[i],f[i+1]) for f in s['polygons'] for i in range(1,len(f)-1)])
dom=np.asarray([sum(w for n,w in r if n.startswith(('Clavicle','UpperArm','LowerArm','ForearmTwist','Hand'))) for r in s['weights']]);tri=tri[np.max(dom[tri],axis=1)<.14];q=p[tri];lo=q.min(1);hi=q.max(1);normal=np.cross(q[:,1]-q[:,0],q[:,2]-q[:,0]);normal/=np.linalg.norm(normal,axis=1)[:,None]
def subnearest(point,ids):
 a,b,c=q[ids,0],q[ids,1],q[ids,2];n=normal[ids];height=np.sum((point-a)*n,1);best=point-height[:,None]*n
 v0=b-a;v1=c-a;v2=best-a;d00=np.sum(v0*v0,1);d01=np.sum(v0*v1,1);d11=np.sum(v1*v1,1);d20=np.sum(v2*v0,1);d21=np.sum(v2*v1,1);den=d00*d11-d01*d01
 v=(d11*d20-d01*d21)/np.maximum(den,1e-30);w=(d00*d21-d01*d20)/np.maximum(den,1e-30);inside=(v>=0)&(w>=0)&(v+w<=1);dist=np.sum((best-point)**2,1);dist[~inside]=np.inf
 for x,y in [(a,b),(b,c),(c,a)]:
  d=y-x;t=np.clip(np.sum((point-x)*d,1)/np.maximum(np.sum(d*d,1),1e-30),0,1);h=x+t[:,None]*d;d2=np.sum((h-point)**2,1);m=d2<dist;best[m]=h[m];dist[m]=d2[m]
 j=int(np.argmin(dist));return best[j],normal[ids[j]],float(dist[j]),int(ids[j])
def nearest(point):
 gap=np.maximum(np.maximum(lo-point,point-hi),0);bound=np.sum(gap*gap,1);ids=np.argpartition(bound,127)[:128];hit,n,d2,i=subnearest(point,ids)
 possible=np.flatnonzero(bound<=d2+1e-15)
 if len(possible)>128:hit,n,d2,i=subnearest(point,possible)
 return hit,n,float(np.sqrt(d2)),i
pat=sewn_undershirt_v2.pattern();pts=pat['points'].copy();rows=[];t=time.time()
for i,(point,d) in enumerate(zip(pts,pat['directions'])):
 hit,n,distance,index=nearest(point);ease=.008+.004*(1-pat['pins'][i]);delta=point-hit;tangent=delta-n*(delta@n);tangent*=min(.25,.004/max(np.linalg.norm(tangent),1e-12));target=hit+n*ease+tangent;rows.append({'vertex':i,'region':pat['regions'][i],'distance':distance,'adjustment':float(np.linalg.norm(target-point)),'alignment':float(n@d),'supportTriangle':index,'normal':n.tolist(),'guide':point.tolist()});pts[i]=target
pts,fairing=sewn_undershirt_v2.relax_projection(pts,pat['faces'],pat['pins'])
faces=np.asarray(pat['faces']);area=np.linalg.norm(np.cross(pts[faces[:,1]]-pts[faces[:,0]],pts[faces[:,2]]-pts[faces[:,0]]),axis=1)
report={'status':'Numerical complete actual Basis correspondence; native generation and cloth solve remain pending','sourceSha256':s['sourceSha256'],'patternSha256':hashlib.sha256(Path(sewn_undershirt_v2.__file__).read_bytes()).hexdigest(),'auditCodeSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'fitCodeSha256':hashlib.sha256((H/'torso_fabric_v2.py').read_bytes()).hexdigest(),'vertices':len(pts),'maximumGuideDistanceMeters':max(v['distance'] for v in rows),'maximumAdjustmentMeters':max(v['adjustment'] for v in rows),'minimumDirectionDot':min(v['alignment'] for v in rows),'minimumFirstCornerDoubleArea':float(area.min()),'zeroCornerAreas':int((area<1e-12).sum()),'bounds':[pts.min(0).tolist(),pts.max(0).tolist()],'surfaceFairing':fairing,'rows':rows,'nativeValidation':False,'artisticAcceptance':False}
report['allPreparedSupportGatesPass']=report['maximumAdjustmentMeters']<=.065 and report['minimumDirectionDot']>=-.1 and report['zeroCornerAreas']==0
np.savez_compressed(R/'benchmark/local/nib-sewn-v2-fit-light.npz',points=pts,faces=faces,normals=np.asarray([r['normal'] for r in rows]))
report['zeroFaceIds']=np.flatnonzero(area<1e-12).tolist()
report['largestGuideRows']=sorted(rows,key=lambda r:-r['distance'])[:5]
normal=np.cross(pts[faces[:,1]]-pts[faces[:,0]],pts[faces[:,2]]-pts[faces[:,0]]);support_n=np.asarray([r['normal'] for r in rows])[faces].mean(1);dots=np.sum(normal*support_n,1)/np.maximum(np.linalg.norm(normal,axis=1)*np.linalg.norm(support_n,axis=1),1e-20)
report['backfacingComparedWithSupport']=int((dots<0).sum());report['minimumSupportNormalDot']=float(dots.min())
report['allPreparedSupportGatesPass'] &= report['backfacingComparedWithSupport']==0
out=R/'benchmark/art/nib/garment-study/sewn-nearest-support-preparation-v2.json';out.write_text(json.dumps(report,indent=2)+'\n',newline='\n');print(json.dumps({k:v for k,v in report.items() if k!='rows'}));print('seconds',time.time()-t)
