from pathlib import Path
import json, math
import numpy as np
root=Path('D:/Dev/Krag-Kings/benchmark/local')
r=json.loads((root/'nib-semantic-body-wrap-support.json').read_text());p=np.array(r['vertices']);tris=np.array([(poly[0],poly[i],poly[i+1]) for poly in r['polygons'] for i in range(1,len(poly)-1)])
A=p[tris[:,0]];E=p[tris[:,1]]-A;F=p[tris[:,2]]-A
norm=np.cross(E,F);norm/=np.linalg.norm(norm,axis=1)[:,None]

def hit(origin,direction,ids):
 a=A[ids];e=E[ids];f=F[ids]
 h=np.cross(direction,f);det=np.einsum('ij,ij->i',e,h);ok=np.abs(det)>1e-10
 inv=np.divide(1.,det,out=np.zeros_like(det),where=ok);s=origin-a
 u=inv*np.einsum('ij,ij->i',s,h);q=np.cross(s,e);v=inv*(q@direction);distance=inv*np.einsum('ij,ij->i',f,q)
 good=ok&(u>=-1e-6)&(v>=-1e-6)&(u+v<=1+1e-6)&(distance>=0)&(distance<=.24)
 if not good.any():return None
 at=int(np.argmin(np.where(good,distance,1e9)));index=int(ids[at]);pt=origin+direction*distance[at]
 return pt,norm[index],index,np.array([1-u[at]-v[at],u[at],v[at]])

report={'sourceSha256':r['sourceSha256'],'meshTransform':r['objectTransform'],'sides':{},'nativeBlenderRun':False}
for side,sign in [('L',1),('R',-1)]:
 elbow=np.array(r['bones']['LowerArm_'+side]['head']);wrist=np.array(r['bones']['Hand_'+side]['head']);axis=wrist-elbow;length=np.linalg.norm(axis);axis/=length
 lateral=np.array([sign,0.,0.]);lateral-=axis*lateral.dot(axis);lateral/=np.linalg.norm(lateral);front=np.cross(axis,lateral)
 allowed={'LowerArm_'+side,'ForearmTwist_'+side,'Hand_'+side}
 influence=np.array([sum(w for name,w in row if name in allowed) for row in r['weights']]);center=p[tris].mean(1);t=(center-elbow)@axis/length;radial=np.linalg.norm(center-elbow-t[:,None]*(wrist-elbow),axis=1)
 ids=np.flatnonzero((influence[tris].mean(1)>.92)&(t>.15)&(t<1.05)&(radial<.06))
 whole_first=None;misses=[];firstfail=None;minnormal=1.;maxradius=0.;minweight=1.;rays=0
 for j in range(401):
  s=j/400;theta=math.tau*5*s+sign*.6;outward=lateral*math.cos(theta)+front*math.sin(theta);ct=.40+.51*s;width=.0225*(1+.07*math.sin(theta*.43+1.1))
  for i in range(13):
   u=i/12;edge=.00038*math.sin(theta*3.1+.7)*(abs(2*u-1)**6);tt=ct+((u-.5)*width+edge)/length;center=elbow+(wrist-elbow)*tt;origin=center+outward*.10
   if whole_first is None:
    full=hit(origin,-outward,np.arange(len(tris)))
    if full is not None and (full[1].dot(outward)<.25 or np.linalg.norm(full[0]-center)>.048):
     pt,n,ind,bary=full;whole_first={'row':j,'column':i,'point':pt.tolist(),'normalDot':float(n.dot(outward)),'radius':float(np.linalg.norm(pt-center)),'forearmWeight':float(bary@influence[tris[ind]]),'origin':origin.tolist()}
   h=hit(origin,-outward,ids);rays+=1
   if h is None:
    misses.append([j,i]);continue
   pt,n,index,bary=h;nd=float(n.dot(outward));radius=float(np.linalg.norm(pt-center));weight=float(bary@influence[tris[index]])
   minnormal=min(minnormal,nd);maxradius=max(maxradius,radius);minweight=min(minweight,weight)
   if firstfail is None and (nd<.25 or radius>.048 or weight<.97):firstfail={'row':j,'column':i,'point':pt.tolist(),'normalDot':nd,'radius':radius,'weight':weight}
 report['sides'][side]={'triangles':len(ids),'rays':rays,'misses':misses,'minimumNormalDot':minnormal,'maxRadius':maxradius,'minimumForearmWeight':minweight,'firstRemainingFailure':firstfail,'firstWholeBodyFailure':whole_first}
(root/'nib-wrap-support-preflight.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
