"""Offline saved-geometry attribution; no Blender process or source mutation.

The DNA coordinates/topology are actual. Polygon vertex normals and quad fans
are reconstructed here; a native retry must verify final Blender correspondences.
"""
import argparse,hashlib,heapq,json,os
from pathlib import Path
os.environ['OPENBLAS_NUM_THREADS']='1'
import numpy as np

ROOT=Path(__file__).resolve().parents[4]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def unit(value):return value/max(float(np.linalg.norm(value)),1e-20)

class Surface:
    def __init__(self,paths):
        points=[];normals=[];triangles=[];sources=[]
        for path in paths:
            source=json.loads(path.read_text());transform=source['objectTransform']
            if transform['size']!=[1.,1.,1.] or transform['rot']!=[0.,0.,0.] or transform['parentinv']!=np.eye(4).ravel().tolist():
                raise RuntimeError('Explicit nontrivial saved transform required')
            p=np.asarray(source['vertices'],float)+np.asarray(transform['loc'])
            n=np.zeros_like(p);offset=len(points)
            for polygon,face in enumerate(source['polygons']):
                q=p[face];normal=unit(np.cross(q,np.roll(q,-1,axis=0)).sum(axis=0))
                for i,index in enumerate(face):
                    a=unit(q[i-1]-q[i]);b=unit(q[(i+1)%len(q)]-q[i]);angle=np.arccos(np.clip(float(a@b),-1,1));n[index]+=normal*angle
                for i in range(1,len(face)-1):
                    triangles.append([offset+face[0],offset+face[i],offset+face[i+1]])
                    sources.append({'object':source['meshObject'],'polygon':polygon,'vertices':[face[0],face[i],face[i+1]]})
            n/=np.maximum(np.linalg.norm(n,axis=1)[:,None],1e-20)
            points.extend(p);normals.extend(n)
        self.points=np.asarray(points);self.normals=np.asarray(normals);self.triangles=np.asarray(triangles,int);self.sources=sources
        q=self.points[self.triangles];self.q=q;self.low=q.min(1);self.high=q.max(1);self.center=q.mean(1)
        raw=np.cross(q[:,1]-q[:,0],q[:,2]-q[:,0]);self.geometric=raw/np.maximum(np.linalg.norm(raw,axis=1)[:,None],1e-20)
        self.nodes=[];self.root=self.build(np.arange(len(q)))
    def build(self,ids):
        index=len(self.nodes);lo=self.low[ids].min(0);hi=self.high[ids].max(0)
        self.nodes.append(None)
        if len(ids)<=24:self.nodes[index]=(lo,hi,ids,None)
        else:
            axis=int(np.argmax(hi-lo));ids=ids[np.argsort(self.center[ids,axis])];middle=len(ids)//2
            left=self.build(ids[:middle]);right=self.build(ids[middle:]);self.nodes[index]=(lo,hi,left,right)
        return index
    def nearest(self,point,direction=None):
        best=np.inf;result=None;pending=[(0.,self.root)]
        while pending:
            distance,node=heapq.heappop(pending)
            if distance>=best:continue
            lo,hi,a,b=self.nodes[node]
            if b is not None:
                for child in [a,b]:
                    low,high,_,_=self.nodes[child];delta=np.maximum(np.maximum(low-point,point-high),0);bound=float(delta@delta)
                    if bound<best:heapq.heappush(pending,(bound,child))
                continue
            q=self.q[a];u=q[:,1]-q[:,0];v=q[:,2]-q[:,0];w=point-q[:,0]
            uu=np.einsum('ij,ij->i',u,u);uv=np.einsum('ij,ij->i',u,v);vv=np.einsum('ij,ij->i',v,v)
            uw=np.einsum('ij,ij->i',u,w);vw=np.einsum('ij,ij->i',v,w);denom=uu*vv-uv*uv
            safe=np.where(denom>1e-28,denom,1)
            beta=(vv*uw-uv*vw)/safe;gamma=(uu*vw-uv*uw)/safe
            weights=np.column_stack((1-beta-gamma,beta,gamma));interior=(weights.min(1)>=0)&(denom>1e-28)
            projected=np.einsum('ij,ijk->ik',weights,q);dist=np.sum((projected-point)**2,axis=1);dist[~interior]=np.inf
            for edge in [(0,1),(1,2),(2,0)]:
                start,end=edge;edge_direction=q[:,end]-q[:,start]
                t=np.clip(np.einsum('ij,ij->i',point-q[:,start],edge_direction)/np.maximum(np.einsum('ij,ij->i',edge_direction,edge_direction),1e-28),0,1)
                hit=q[:,start]+edge_direction*t[:,None];d=np.sum((hit-point)**2,axis=1);take=d<dist
                projected[take]=hit[take];dist[take]=d[take];weights[take]=0;weights[take,start]=1-t[take];weights[take,end]=t[take]
            if direction is not None:
                smooth=np.einsum('ij,ijk->ik',weights,self.normals[self.triangles[a]])
                smooth/=np.maximum(np.linalg.norm(smooth,axis=1)[:,None],1e-20)
                admissible=(smooth@direction>=.4)&(self.geometric[a]@direction>0)&(np.einsum('ij,ij->i',smooth,self.geometric[a])>0)
                dist[~admissible]=np.inf
            i=int(np.argmin(dist))
            if dist[i]<best:best=float(dist[i]);result=(projected[i],int(a[i]),weights[i])
        if result is None:raise RuntimeError('No same-side anatomical support exists')
        hit,index,weights=result;vertices=self.triangles[index]
        normal=unit(weights@self.normals[vertices]);q=self.q[index];geometric=unit(np.cross(q[1]-q[0],q[2]-q[0]))
        return hit,normal,geometric,index,float(np.sqrt(best))

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    if args.output.exists():raise RuntimeError('Preserve previous offline preflight')
    paths={side:[ROOT/f'benchmark/local/nib-root-support-{part}-{sign}.json' for part in ['outer','inner']] for side,sign in [('L',1),('R',-1)]}
    surfaces={side:Surface(files) for side,files in paths.items()}
    guide_path=ROOT/'benchmark/art/nib/groom-study/coherent79-v2-runtime-wide-nap/groom-guides.json'
    groups=json.loads(guide_path.read_text())['groups'];records=[]
    for group in groups:
        if not group['bone'].startswith('Ear_'):continue
        surface=surfaces[group['bone'][-1]];failures=[];worst=1.;fitted=[]
        for i,guide in enumerate(group['guides']):
            root=np.asarray(guide['root']);guide_normal=np.asarray(guide['normal'])
            hit,normal,geometric,face,distance=surface.nearest(root)
            tangent=unit(np.asarray(guide['middle'])-root);across=unit(np.cross(tangent,normal));width=guide['halfWidthMeters']*.72
            for sign in [-1,1]:
                point=hit-normal*.0005+across*width*sign
                corner,n,g,index,d=surface.nearest(point);agreement=float(n@g);worst=min(worst,agreement)
                if agreement<=0 or float(n@guide_normal)<.4 or float(g@guide_normal)<=0:
                    failures.append({'guide':i,'cornerSign':sign,'guideRoot':root.tolist(),'query':point.tolist(),
                        'rootSupport':surface.sources[face],'cornerSupport':surface.sources[index],'cornerPoint':corner.tolist(),
                        'cornerDistanceMeters':d,'smoothGeometricDot':agreement,'smoothGuideDot':float(n@guide_normal),'geometricGuideDot':float(g@guide_normal),
                        'guideNormal':guide_normal.tolist(),'smoothNormal':n.tolist(),'geometricNormal':g.tolist()})
                    # Test original guide-facing support without the old
                    # blanket half-millimetre inward bias in the query.
                    query=hit+across*width*sign
                    fitted_point,fn,fg,fi,fd=surface.nearest(query,guide_normal)
                    fitted.append({'guide':i,'cornerSign':sign,'support':surface.sources[fi],
                        'distanceFromOriginalCornerQueryMeters':fd,
                        'distanceFromOldWrongSideProjectionMeters':float(np.linalg.norm(fitted_point-corner)),
                        'smoothGuideDot':float(fn@guide_normal),'geometricGuideDot':float(fg@guide_normal),
                        'smoothGeometricDot':float(fn@fg)})
        records.append({'region':group['region'],'guides':len(group['guides']),'minimumSmoothGeometricDot':worst,'flaggedCorners':len(failures),'failures':failures,
            'orientedSameSideProposals':fitted,'maximumOrientedCornerFitMeters':max((f['distanceFromOriginalCornerQueryMeters'] for f in fitted),default=0.)})
        print(group['region'],len(failures),worst,flush=True)
    report={'status':'Offline saved-mesh attribution; native Blender comparison still required','groups':records,
        'sourceSha256':'09da9c1eb51eabd0402fc1ed52b3d4b07f53a5a74150810796a2b04169d8c88e',
        'guideSha256':sha(guide_path),'inputHashes':{p.name:sha(p) for group in paths.values() for p in group},
        'normalMethod':'Reconstructed angle-weighted polygon vertex normals; explicit quad-fan triangles, not a claim of bit-exact native triangulation',
        'scriptSha256':sha(Path(__file__)),'sharedChanged':False,'artisticAcceptance':False}
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2)+'\n',newline='\n')
    print('NIB_SAVED_ROOT_CORNER_PREFLIGHT_COMPLETE')
if __name__=='__main__':main()
