"""Prepared source-topology shoulder field shared by fitting and skinning.

Face sets 20/21 identify the original upper arms/deltoids;11/12 the forearms.
The smooth transition is measured along their actual interface with thorax,
not a global X/Z band that accidentally pins the medial biceps to the chest.
All widths are provisional technical support distances, not design canon.
"""
import heapq
import numpy as np
from forearm_twist import smooth
from anatomical_body_fit import SOURCE_SEGMENTS,TARGET_SEGMENTS,rotation_between

ARM_FACE_SETS=frozenset([11,12,20,21])
THORAX_SUPPORT=.025
ARM_SUPPORT=.055

def solve(points,faces,face_sets):
    p=np.asarray(points,float);face_sets=np.asarray(face_sets,int)
    if len(faces)!=len(face_sets):raise RuntimeError('Face-set topology mismatch')
    incident=[set() for _ in p];edges=set()
    for f,region in zip(faces,face_sets):
        f=list(map(int,f));is_arm=int(region) in ARM_FACE_SETS
        for i in f:incident[i].add(is_arm)
        for a,b in zip(f,f[1:]+f[:1]):edges.add(tuple(sorted((a,b))))
    seam=np.asarray([len(s)==2 for s in incident]);arm=np.asarray([True in s for s in incident]);adj=[[] for _ in p]
    for a,b in edges:
        length=float(np.linalg.norm(p[a]-p[b]));adj[a].append((b,length));adj[b].append((a,length))
    if not seam.any():raise RuntimeError('Actual thorax/upper-arm interface is absent')
    distance=np.full(len(p),np.inf);distance[seam]=0.;heap=[(0.,int(i)) for i in np.flatnonzero(seam)]
    heapq.heapify(heap)
    while heap:
        d,i=heapq.heappop(heap)
        if d!=distance[i]:continue
        for j,length in adj[i]:
            proposal=d+length
            if proposal<distance[j]:distance[j]=proposal;heapq.heappush(heap,(proposal,j))
    if not np.isfinite(distance).all():raise RuntimeError('Disconnected anatomical crop')
    signed=np.where(arm,distance,-distance);field=smooth(-THORAX_SUPPORT,ARM_SUPPORT,signed)
    if np.any(field[~arm & (distance>=THORAX_SUPPORT)]!=0) or np.any(field[arm & (distance>=ARM_SUPPORT)]!=1):raise RuntimeError('Semantic interior anchors moved')
    return field,{'interfaceVertices':int(seam.sum()),'armSurfaceVertices':int(arm.sum()),'thoraxSurfaceVertices':int((~arm).sum()),'transitionVertices':int(((field>0)&(field<1)).sum()),'supportSourceMeters':{'thorax':THORAX_SUPPORT,'arm':ARM_SUPPORT},'semanticArmFaceSets':sorted(ARM_FACE_SETS),'fieldRange':[float(field.min()),float(field.max())],'status':'Prepared coherent fit/skin field; actual native posed proof still required'}

def warp(points,domain):
    raw=np.asarray(points,float);p=raw.copy();sign=np.where(p[:,0]>=0,1.,-1.);p[:,0]=abs(p[:,0]);domain=np.asarray(domain,float)
    if domain.shape!=(len(p),) or np.min(domain)<0 or np.max(domain)>1:raise RuntimeError('Invalid semantic fitting field')
    z=[.90,.945,1.05,1.15,1.25,1.353,1.40,1.46];body=p.copy()
    body[:,2]=np.interp(p[:,2],z,[.635,.663,.731,.807,.882,.938,.990,1.048])
    body[:,0]*=np.interp(p[:,2],z,[.56,.56,.59,.64,.70,.73,.72,.65])
    body[:,1]=.008+(p[:,1]+.010)*np.interp(p[:,2],z,[.58,.59,.59,.60,.62,.62,.59,.56])
    candidates=[];distances=[]
    for index,(source,target) in enumerate(zip(SOURCE_SEGMENTS,TARGET_SEGMENTS)):
        a,b=source;ta,tb=target;axis=b-a;t=(p-a)@axis/(axis@axis);projected=a+t[:,None]*axis;closest=a+np.clip(t,0,1)[:,None]*axis
        distances.append(np.linalg.norm(p-closest,axis=1));radial=(p-projected)@rotation_between(axis,tb-ta).T
        candidates.append(ta+t[:,None]*(tb-ta)+radial*(.69 if index==0 else .64))
    weights=1/np.maximum(np.stack(distances,1),.018)**4;weights/=weights.sum(1)[:,None];arms=np.sum(np.stack(candidates,1)*weights[:,:,None],1)
    fitted=body*(1-domain[:,None])+arms*domain[:,None];fitted[:,0]*=sign
    return fitted
