from pathlib import Path
import sys,hashlib,json,numpy as np
import OpenImageIO as oiio
r=Path(r'D:\Dev\Krag-Kings\benchmark');sys.path.insert(0,str(r/'tools/krag'))
from anatomy_warp_study import warp
source=r/'art/krag/anatomy-study/GEO-body_male_realistic.npz';d=np.load(source,allow_pickle=True);v=d['vertices'];mask=(v[:,0]>.315)&(v[:,2]<.95)&(v[:,2]>.70);faces=[list(map(int,f)) for f in d['polygons'] if all(mask[int(i)] for i in f)];used=sorted({i for f in faces for i in f});lookup={i:j for j,i in enumerate(used)};faces=[[lookup[i] for i in f] for f in faces];v=v[used];out=r/'art/animation/krag-hand-basis-rest-diagnostic/cage-comparison';out.mkdir(exist_ok=True)
W=600;H=760
for name,points in [('OriginalBody',v),('AdaptedBody',warp(v))]:
 for view,outward in [('Palm',np.array([-1.,0,0])),('Back',np.array([1.,0,0])),('Edge',np.array([0.,-1,0]))]:
  up=np.array([0.,0,1]);right=np.cross(up,outward);camera=np.array([right,up,-outward]);co=points@camera.T;lo=co[:,:2].min(0);hi=co[:,:2].max(0);fac=min((W-60)/(hi[0]-lo[0]),(H-60)/(hi[1]-lo[1]));xy=(co[:,:2]-(lo+hi)/2)*fac;xy[:,0]+=W/2;xy[:,1]=H/2-xy[:,1];normal=np.zeros_like(points)
  for f in faces:
   n=np.cross(points[f[1]]-points[f[0]],points[f[2]]-points[f[0]])
   for i in f:normal[i]+=n
  normal/=np.maximum(np.linalg.norm(normal,axis=1)[:,None],1e-10);light=outward+.4*up-.3*right;light/=np.linalg.norm(light);tone=.22+.63*np.maximum(0,normal@light);pix=np.full((H,W,3),.16,np.float32);depth=np.full((H,W),np.inf)
  for f in faces:
   for j in range(1,len(f)-1):
    ids=[f[0],f[j],f[j+1]];a,b,c=xy[ids];x0,x1=max(0,int(min(a[0],b[0],c[0]))),min(W,int(max(a[0],b[0],c[0]))+1);y0,y1=max(0,int(min(a[1],b[1],c[1]))),min(H,int(max(a[1],b[1],c[1]))+1)
    if x1<=x0 or y1<=y0:continue
    xx,yy=np.meshgrid(np.arange(x0,x1)+.5,np.arange(y0,y1)+.5);den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
    if abs(den)<1e-10:continue
    u=((b[1]-c[1])*(xx-c[0])+(c[0]-b[0])*(yy-c[1]))/den;q=((c[1]-a[1])*(xx-c[0])+(a[0]-c[0])*(yy-c[1]))/den;w=1-u-q;z=u*co[ids[0],2]+q*co[ids[1],2]+w*co[ids[2],2];m=(u>=0)&(q>=0)&(w>=0)&(z<depth[y0:y1,x0:x1]);depth[y0:y1,x0:x1][m]=z[m];intensity=u*tone[ids[0]]+q*tone[ids[1]]+w*tone[ids[2]];pix[y0:y1,x0:x1][m]=intensity[m,None]
  path=out/(name+'_'+view+'.png');o=oiio.ImageOutput.create(str(path));o.open(str(path),oiio.ImageSpec(W,H,3,oiio.UINT8));o.write_image((np.clip(pix,0,1)*255).astype(np.uint8));o.close()
(out/'source.json').write_text(json.dumps({'status':'Actual source-cage diagnostic projections, not Blender/engine renders or proposed final meshes','sourceSha256':hashlib.sha256(source.read_bytes()).hexdigest(),'recipeSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'vertices':len(v),'faces':len(faces),'sharedChanged':False},indent=2)+'\n')
print('Actual original/adapted source cage projections complete')
