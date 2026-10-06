"""Read-only CC0 animation-head topology study; never touches pinned exports.

Run with Blender's bundled plain Python (NumPy/OpenImageIO), not Blender.
These are diagnostic projections of actual reference topology, not final art.
"""
import json, math
from pathlib import Path
import numpy as np
import OpenImageIO as oiio

ROOT=Path(__file__).resolve().parents[4]
SOURCE=ROOT/'benchmark/art/krag/anatomy-study'
OUT=ROOT/'benchmark/art/nib/v5-study'
OUT.mkdir(parents=True,exist_ok=True)

def load_reference():
    data=np.load(SOURCE/'GEO-head_animation_realistic.npz',allow_pickle=True)
    verts=data['vertices'].astype(float)
    faces=[list(map(int,p)) for p in data['polygons']]
    return verts,faces

def boundaries(verts,faces):
    edges={}
    for p in faces:
        for a,b in zip(p,p[1:]+p[:1]):
            edge=tuple(sorted((a,b)));edges[edge]=edges.get(edge,0)+1
    adjacency={}
    for (a,b),n in edges.items():
        if n==1:adjacency.setdefault(a,[]).append(b);adjacency.setdefault(b,[]).append(a)
    groups=[];seen=set()
    for start in adjacency:
        if start in seen:continue
        found=[];todo=[start]
        while todo:
            i=todo.pop()
            if i in seen:continue
            seen.add(i);found.append(i);todo.extend(adjacency[i])
        co=verts[found]
        groups.append({'indices':found,'count':len(found),'min':co.min(0).tolist(),'max':co.max(0).tolist(),'mean':co.mean(0).tolist()})
    return groups

def render(verts,faces,path,angle=0,marked=None):
    W,H=900,1200;ca,sa=math.cos(angle),math.sin(angle)
    co=np.column_stack((verts[:,0]*ca+verts[:,1]*sa,verts[:,2],-verts[:,0]*sa+verts[:,1]*ca))
    lo=co[:,:2].min(0);hi=co[:,:2].max(0);factor=min((W-100)/(hi[0]-lo[0]),(H-100)/(hi[1]-lo[1]))
    xy=(co[:,:2]-(lo+hi)/2)*factor;xy[:,0]+=W/2;xy[:,1]=H/2-xy[:,1]
    pixels=np.full((H,W,3),.88,dtype=np.float32);depth=np.full((H,W),np.inf)
    normals=np.zeros_like(co)
    for face in faces:
        n=np.cross(co[face[1]]-co[face[0]],co[face[2]]-co[face[0]])
        for i in face:normals[i]+=n
    normals/=-np.maximum(np.linalg.norm(normals,axis=1)[:,None],1e-10)
    light=np.array([-.3,.45,-1]);light/=np.linalg.norm(light)
    tones=.24+.62*np.maximum(0,normals@light)
    for face in faces:
        for j in range(1,len(face)-1):
            ids=[face[0],face[j],face[j+1]];a,b,c=xy[ids]
            x0,x1=max(0,int(min(a[0],b[0],c[0]))),min(W-1,int(max(a[0],b[0],c[0]))+1)
            y0,y1=max(0,int(min(a[1],b[1],c[1]))),min(H-1,int(max(a[1],b[1],c[1]))+1)
            if x1<=x0 or y1<=y0:continue
            xx,yy=np.meshgrid(np.arange(x0,x1)+.5,np.arange(y0,y1)+.5)
            den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
            if abs(den)<1e-12:continue
            u=((b[1]-c[1])*(xx-c[0])+(c[0]-b[0])*(yy-c[1]))/den
            v=((c[1]-a[1])*(xx-c[0])+(a[0]-c[0])*(yy-c[1]))/den;w=1-u-v
            zz=u*co[ids[0],2]+v*co[ids[1],2]+w*co[ids[2],2]
            mask=(u>=0)&(v>=0)&(w>=0)&(zz<depth[y0:y1,x0:x1]);depth[y0:y1,x0:x1][mask]=zz[mask]
            intensity=u*tones[ids[0]]+v*tones[ids[1]]+w*tones[ids[2]]
            pixels[y0:y1,x0:x1][mask]=intensity[mask,None]*np.array([.90,.73,.57])
    if marked:
        colors=[(1,.1,.1),(.1,.7,1),(.2,1,.2),(1,.1,1)]
        for n,g in enumerate(marked):
            for i in g['indices']:
                x,y=map(int,xy[i]);z=co[i,2]
                if 3<=x<W-3 and 3<=y<H-3 and z<depth[y,x]+.003:pixels[y-2:y+3,x-2:x+3]=colors[n%4]
    output=oiio.ImageOutput.create(str(path));output.open(str(path),oiio.ImageSpec(W,H,3,oiio.UINT8));output.write_image((np.clip(pixels,0,1)*255).astype(np.uint8));output.close()

if __name__=='__main__':
    verts,faces=load_reference();groups=boundaries(verts,faces)
    (OUT/'head-landmarks.json').write_text(json.dumps({'status':'CC0 reference topology; not adopted into Nib yet','vertices':verts.tolist(),'faces':faces,'boundaryGroups':groups},indent=2))
    for label,angle in [('Front',0),('Side',math.pi/2),('Perspective',.55)]:render(verts,faces,OUT/('Reference_Head_'+label+'.png'),angle,groups)
    print(json.dumps({'vertices':len(verts),'faces':len(faces),'boundaries':groups},indent=2))
