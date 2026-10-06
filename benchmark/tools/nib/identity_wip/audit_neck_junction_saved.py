"""Read-only actual saved cage neck attribution; no native scene or mutation."""
import argparse,collections,hashlib,json,os
from pathlib import Path
os.environ['OPENBLAS_NUM_THREADS']='1'
import numpy as np
ROOT=Path(__file__).resolve().parents[4]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def load(path):
    j=json.loads(path.read_text());t=j['objectTransform']
    if t['size']!=[1.,1.,1.] or t['rot']!=[0.,0.,0.] or t['parentinv']!=np.eye(4).ravel().tolist():
        raise RuntimeError('Explicit nontrivial saved object transform required')
    return j,np.asarray(j['vertices'],float)+np.asarray(t['loc'])

def boundaries(j,p):
    edges=collections.Counter()
    for f in j['polygons']:
        for a,b in zip(f,f[1:]+f[:1]):edges[tuple(sorted((a,b)))]+=1
    adj=collections.defaultdict(set)
    for (a,b),count in edges.items():
        if count==1:adj[a].add(b);adj[b].add(a)
    remaining=set(adj);groups=[]
    while remaining:
        stack=[next(iter(remaining))];component=set()
        while stack:
            a=stack.pop()
            if a in component:continue
            component.add(a);stack.extend(adj[a]-component)
        remaining-=component;ids=np.asarray(sorted(component),int);q=p[ids]
        groups.append({'indices':ids.tolist(),'count':len(ids),'minimumMeters':q.min(0).tolist(),
                       'maximumMeters':q.max(0).tolist(),'meanMeters':q.mean(0).tolist(),
                       'edgeDegrees':dict(collections.Counter(len(adj[i]) for i in ids))})
    return sorted(groups,key=lambda g:g['maximumMeters'][2],reverse=True)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    if args.output.exists():raise RuntimeError('Preserve previous saved junction attribution')
    paths={part:ROOT/f'benchmark/local/nib-adult-neck-{part}.json' for part in ['body','head']}
    body,bp=load(paths['body']);head,hp=load(paths['head'])
    expected='37c0d919e4844cb98339e03fd4e31f5cc04a5b52172561b0aeb65cfab0296db4'
    if any(j['sourceSha256']!=expected for j in [body,head]):raise RuntimeError('Pinned actual coherent source mismatch')
    loops=boundaries(body,bp);headloops=boundaries(head,hp);ids=np.asarray(loops[0]['indices'])
    triangles=[]
    for face in head['polygons']:
        triangles.extend([[face[0],face[i],face[i+1]] for i in range(1,len(face)-1)])
    q=hp[np.asarray(triangles)];lo=q[:,:,2].min(1);hi=q[:,:,2].max(1)
    center=np.asarray(loops[0]['meanMeters']);records=[]
    for i in ids:
        point=bp[i];origin=center.copy();origin[2]=point[2]
        direction=point-origin;radius=np.linalg.norm(direction);direction/=radius
        tri=q[(lo<=point[2])&(hi>=point[2])]
        e1=tri[:,1]-tri[:,0];e2=tri[:,2]-tri[:,0]
        h=np.cross(np.broadcast_to(direction,e2.shape),e2);a=np.einsum('ij,ij->i',e1,h)
        valid=abs(a)>1e-14;inverse=np.divide(1,a,out=np.zeros_like(a),where=valid)
        s=origin-tri[:,0];u=inverse*np.einsum('ij,ij->i',s,h);cross=np.cross(s,e1)
        v=inverse*(cross@direction);distance=inverse*np.einsum('ij,ij->i',e2,cross)
        hit=valid&(u>=-1e-8)&(v>=-1e-8)&(u+v<=1+1e-8)&(distance>1e-7)
        ordered=np.sort(distance[hit]);unique=[]
        for d in ordered:
            if not unique or abs(d-unique[-1])>1e-6:unique.append(float(d))
        record={'bodyVertex':int(i),'worldPointMeters':point.tolist(),'positiveHeadIntersectionsMeters':unique,
                'bodyRadiusMeters':float(radius),'bodyNeckWeight':dict(body['weights'][i]).get('Neck',0.)}
        if len(unique)==1:record['bodyMinusHeadRadiusMeters']=float(radius-unique[0])
        records.append(record)
    coherent=[r['bodyMinusHeadRadiusMeters'] for r in records if 'bodyMinusHeadRadiusMeters' in r]
    lower=np.nonzero(hp[:,2]<1.050)[0];headweights={bone:np.asarray([dict(head['weights'][i]).get(bone,0.) for i in lower]) for bone in ['Neck','Head','Jaw']}
    r={'status':'Actual saved geometry boundary/radial attribution; no evaluated pose or source mutation',
       'sourceSha256':expected,'inputHashes':{k:sha(p) for k,p in paths.items()},'codeSha256':sha(Path(__file__)),
       'bodyObject':body['meshObject'],'headObject':head['meshObject'],'bodyBoundaryLoops':loops,'headBoundaryLoops':headloops,
       'upperBodyLoopHeightSpanMeters':float(np.ptp(bp[ids,2])),
       'upperBodyLoopNeckWeightRange':[min(r['bodyNeckWeight'] for r in records),max(r['bodyNeckWeight'] for r in records)],
       'headLowerNeckWorldZRangeMeters':[float(hp[lower,2].min()),float(hp[lower,2].max())],
       'headLowerNeckWeightRange':{k:[float(v.min()),float(v.max())] for k,v in headweights.items()},
       'radialHeadSurface':{'method':'Double-sided rays from actual Body neck center at each boundary height against Head quad-fan triangles; no native triangulation equivalence claim',
         'singleExitRays':len(coherent),'totalRays':len(records),
         'bodyOutsideHeadBeyondPoint5mm':sum(d>.0005 for d in coherent),
         'signedBodyMinusHeadRadiusRangeMeters':[min(coherent),max(coherent)] if coherent else None,'samples':records},
       'attribution':'Body is open and its source whole-face height crop leaves an irregular upper ring. Head is closed. Native posed ownership/continuity views remain necessary.',
       'nextRepair':'Author a clean actual Head/Body junction with matched surface and Neck weights; do not hide the open sawtooth with scarf; preserve upper face/bind/actions and apply matching neck geometry to restoration partition',
       'sharedChanged':False,'artisticAcceptance':False}
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(r,indent=2)+'\n',newline='\n')
    print(json.dumps({k:r[k] for k in ['upperBodyLoopHeightSpanMeters','upperBodyLoopNeckWeightRange','headLowerNeckWeightRange']}))
    print('Radial',len(coherent),len(records),min(coherent),max(coherent),sum(d>.0005 for d in coherent))
if __name__=='__main__':main()
