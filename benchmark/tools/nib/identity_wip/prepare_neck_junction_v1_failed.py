"""Offline bounded collar fit to an actual Head neck cross-section.

No Blender/source mutation. Upper face coordinates are not changed; new body
positions require native topology, posed seam and visible-skin review.
"""
import argparse,collections,hashlib,json,os
from pathlib import Path
os.environ['OPENBLAS_NUM_THREADS']='1'
import numpy as np
from audit_neck_junction_saved import load,boundaries,ROOT
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def smooth(x):
    x=np.clip(x,0,1);return x*x*(3-2*x)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output-dir',type=Path,required=True);args=parser.parse_args()
    if args.output_dir.exists():raise RuntimeError('Preserve previous neck preflight')
    files={part:ROOT/f'benchmark/local/nib-adult-neck-{part}.json' for part in ['body','head']}
    body,bp=load(files['body']);head,hp=load(files['head']);source=np.asarray(head['attributes']['nib_source_position']['values'])
    expected='37c0d919e4844cb98339e03fd4e31f5cc04a5b52172561b0aeb65cfab0296db4'
    if any(j['sourceSha256']!=expected for j in [body,head]):raise RuntimeError('Wrong saved source')
    loops=boundaries(body,bp);ring=np.asarray(loops[0]['indices'],int);height=1.035
    # Only actual original neck, never the mandibular surface at a similar Z.
    segments=[];supports=[]
    for polygon,f in enumerate(head['polygons']):
        if max(source[f,2])>.185:continue
        for i in range(1,len(f)-1):
            tri=[f[0],f[i],f[i+1]];q=hp[tri];points=[]
            if q[:,2].min()>height or q[:,2].max()<height:continue
            for a,b in [(0,1),(1,2),(2,0)]:
                za=q[a,2]-height;zb=q[b,2]-height
                if za*zb<0:
                    t=-za/(zb-za);points.append(q[a]+t*(q[b]-q[a]))
            if len(points)==2 and np.linalg.norm(points[0]-points[1])>1e-9:
                segments.append(points);supports.append(tri)
    seg=np.asarray(segments)
    if len(seg)<32:raise RuntimeError('Missing actual neck contour')
    # Prove one closed contour; quantization only identifies existing segment
    # endpoint equivalence, not a smoothing or coordinate repair.
    keys=lambda p:tuple(np.round(p/.000001).astype(np.int64))
    adj=collections.defaultdict(set)
    for a,b in seg:
        ka,kb=keys(a),keys(b);adj[ka].add(kb);adj[kb].add(ka)
    if any(len(v)!=2 for v in adj.values()):raise RuntimeError('Head neck cross-section is not a simple closed loop')
    remaining=set(adj);components=0
    while remaining:
        components+=1;seen=set();stack=[next(iter(remaining))]
        while stack:
            a=stack.pop()
            if a in seen:continue
            seen.add(a);stack.extend(adj[a]-seen)
        remaining-=seen
    if components!=1:raise RuntimeError('Multiple Head-neck contour components')
    center=seg.reshape(-1,3).mean(0);bodycenter=bp[ring].mean(0)
    target=bp.copy();radius_errors=[]
    def cross(a,b):return a[...,0]*b[...,1]-a[...,1]*b[...,0]
    for index in ring:
        direction=bp[index,:2]-bodycenter[:2];direction/=np.linalg.norm(direction)
        a=seg[:,0,:2];edge=seg[:,1,:2]-a;denom=cross(np.broadcast_to(direction,edge.shape),edge)
        safe=abs(denom)>1e-12;distance=np.divide(cross(a-center[:2],edge),denom,out=np.zeros(len(seg)),where=safe)
        t=np.divide(cross(a-center[:2],np.broadcast_to(direction,edge.shape)),denom,out=np.zeros(len(seg)),where=safe)
        valid=safe&(distance>0)&(t>=-1e-8)&(t<=1+1e-8)
        distances=np.sort(distance[valid]);unique=[]
        for value in distances:
            if not unique or abs(value-unique[-1])>1e-6:unique.append(float(value))
        if len(unique)!=1:raise RuntimeError('Head contour not star-shaped from actual center '+str((int(index),unique)))
        target[index,:2]=center[:2]+direction*(unique[0]-.0002);target[index,2]=height
        radius_errors.append(unique[0])
    edges=set()
    for f in body['polygons']:
        edges.update(tuple(sorted((a,b))) for a,b in zip(f,f[1:]+f[:1]))
    edges=np.asarray(sorted(edges),int);length=np.linalg.norm(bp[edges[:,0]]-bp[edges[:,1]],axis=1)
    # Dirichlet upper ring; anchors below the lower neck remain exact.
    active=bp[:,2]>.995;fixed=~active;fixed[ring]=True
    delta=np.zeros_like(bp);delta[ring]=target[ring]-bp[ring];rhs=delta.copy()
    a,b=edges.T;weight=1/np.maximum(length,.0001);degree=np.bincount(a,weight,minlength=len(bp))+np.bincount(b,weight,minlength=len(bp))
    converged=False
    for iteration in range(20000):
        sums=np.zeros_like(bp)
        for k in range(3):sums[:,k]=np.bincount(a,weight*delta[b,k],minlength=len(bp))+np.bincount(b,weight*delta[a,k],minlength=len(bp))
        new=sums/np.maximum(degree[:,None],1e-20);new[fixed]=rhs[fixed]
        residual=float(np.linalg.norm(new-delta,axis=1).max());delta=new
        if residual<1e-9:converged=True;break
    if not converged:raise RuntimeError('Bounded collar field did not converge')
    target=bp+delta
    tris=np.asarray([[f[0],f[i],f[i+1]] for f in body['polygons'] for i in range(1,len(f)-1)],int)
    def surface(p):
        q=p[tris];n=np.cross(q[:,1]-q[:,0],q[:,2]-q[:,0]);area=np.linalg.norm(n,axis=1)
        return n,area
    n0,ar0=surface(bp);n1,ar1=surface(target);dot=np.sum(n0*n1,axis=1)/np.maximum(ar0*ar1,1e-25)
    changed=np.linalg.norm(delta,axis=1)>1e-8
    # Only original neck topology is eligible for matched interface controls.
    neck=source[:,2]<.185
    influence=smooth((hp[:,2]-1.026)/.005)*(1-smooth((hp[:,2]-1.039)/.011))*neck
    support=np.unique(np.asarray(supports).ravel());influence[support]=1.
    report={'status':'Offline actual-cross-section neck proposal; no saved native source or pose proof','sourceSha256':expected,
      'codeSha256':sha(Path(__file__)),'inputHashes':{k:sha(p) for k,p in files.items()},'junctionHeightMeters':height,
      'contourSegments':len(seg),'contourComponents':components,'contourCenterMeters':center.tolist(),
      'bodyUpperRingVertices':len(ring),'bodyChangedVertices':int(changed.sum()),'bodyMaximumMoveMeters':float(np.linalg.norm(delta,axis=1).max()),
      'bodyMinimumNeckZChanged':float(bp[changed,2].min()),'fieldIterations':iteration+1,'fieldResidualMeters':residual,
      'introducedDegenerateTriangles':int(np.sum((ar0>1e-16)&(ar1<=1e-16))),
      'changedTrianglesRotatedOver90':int(np.sum((dot<0)&changed[tris].any(1))),
      'minimumAreaRatio':float((ar1/np.maximum(ar0,1e-25)).min()),'headGeometryChanged':False,
      'headInterfaceWeightChangedVertices':int((influence>0).sum()),'headInterfaceSupportVertices':len(support),
      'headInterfaceWeightRule':'Neck-only on actual interface support, smooth fade within original neck below sourceZ0.185; no nasal/oral/ocular weight change',
      'hardStructuralFailure':bool(np.any((ar0>1e-16)&(ar1<=1e-16)) or np.any(dot<0)),
      'sharedChanged':False,'artisticAcceptance':False,'pending':['Native exact cached-source correspondence','Matched restorative Body and attached fine fuzz changes','Native LBS neck/head extreme and actual bare-junction source renders','Scarf construction remains an independent visible failure']}
    args.output_dir.mkdir(parents=True);cache=args.output_dir/'proposal.npz'
    np.savez_compressed(cache,expectedBody=bp.astype(np.float32),expectedHeadLocal=np.asarray(head['vertices'],np.float32),bodyDelta=delta.astype(np.float32),bodyTarget=target.astype(np.float32),bodyRing=ring,headNeckWeightInfluence=influence.astype(np.float32),headSupportVertices=support)
    report['proposalSha256']=sha(cache);(args.output_dir/'proposal.json').write_text(json.dumps(report,indent=2)+'\n',newline='\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
