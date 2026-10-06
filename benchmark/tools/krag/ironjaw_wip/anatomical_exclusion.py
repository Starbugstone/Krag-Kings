"""Prepared anatomical IronJaw partition on retained continuous head topology.

The natural master remains complete. A future fitted mechanical assembly uses
an alternate head surface with the actual mandible and lower oral lining
removed. This is a semantic preparation, not a generated replacement asset.
"""
import heapq
import numpy as np


def _distance(points,edges,seeds,allowed):
    neighbors=[[]for _ in points]
    for a,b in edges:
        if allowed[a]and allowed[b]:
            length=float(np.linalg.norm(points[a]-points[b]));neighbors[a].append((b,length));neighbors[b].append((a,length))
    distance=np.full(len(points),np.inf);queue=[]
    for i in np.flatnonzero(seeds&allowed):distance[i]=0.;queue.append((0.,int(i)))
    heapq.heapify(queue)
    while queue:
        d,i=heapq.heappop(queue)
        if d!=distance[i]:continue
        for j,length in neighbors[i]:
            if d+length<distance[j]:distance[j]=d+length;heapq.heappush(queue,(d+length,int(j)))
    return distance


def partition(points,faces,face_sets):
    points=np.asarray(points,dtype=float);sets=np.asarray(face_sets,dtype=int)
    if len(faces)!=len(sets):raise RuntimeError('Face-set topology mismatch')
    tags=np.zeros(len(points),dtype=np.uint64);edge_faces={}
    for i,(face,tag)in enumerate(zip(faces,sets)):
        if not 0<=tag<64:raise RuntimeError('Unknown unaudited face domain')
        tags[list(face)]|=np.uint64(1)<<np.uint64(tag)
        for a,b in zip(face,np.roll(face,-1)):
            edge_faces.setdefault(tuple(sorted((int(a),int(b)))),[]).append(i)
    member=lambda tag:(tags&(np.uint64(1)<<np.uint64(tag)))!=0
    upper=member(33);lower=member(24);bag=member(7)
    upper_rim=upper&bag;lower_rim=lower&bag;corners=upper_rim&lower_rim
    if corners.sum()!=2 or min(upper_rim.sum(),lower_rim.sum())<10:raise RuntimeError('Actual oral rim semantics absent')
    edges=np.asarray(list(edge_faces),dtype=int)
    du=_distance(points,edges,upper_rim,bag);dl=_distance(points,edges,lower_rim,bag)
    if not np.isfinite(du[bag]).all()or not np.isfinite(dl[bag]).all():raise RuntimeError('Disconnected oral surface')
    # The oral floor belongs to the lower rim in topological distance. This
    # never guesses a raw/world Z cutoff or deletes overlapping visible skin.
    remove=sets==24
    for i,face in enumerate(faces):
        if sets[i]==7:remove[i]=float(np.mean(dl[list(face)]-du[list(face)]))<0
    interface=[]
    for edge,indices in edge_faces.items():
        if any(remove[i]for i in indices)and any(not remove[i]for i in indices):interface.append(edge)
    boundary_vertices=np.unique(np.asarray(interface).ravel())
    preserved_upper=int(np.count_nonzero(remove&(sets==33)))
    if preserved_upper:raise RuntimeError('Upper face/lip accidentally excluded')
    return remove,{'status':'Prepared semantic partition; requires fitted replacement mesh and closed/open clearance review',
        'method':'External mandibular face set24 plus oral floor nearer lower rim along actual set7 edges',
        'removedFaces':int(remove.sum()),'removedExternalMandibleFaces':int(np.count_nonzero(remove&(sets==24))),
        'removedOralFloorFaces':int(np.count_nonzero(remove&(sets==7))),
        'retainedUpperLipNoseFaces':int(np.count_nonzero(np.isin(sets,[33,11])&~remove)),
        'interfaceEdges':[list(e)for e in interface],
        'interfaceSourceBounds':[points[boundary_vertices].min(0).tolist(),points[boundary_vertices].max(0).tolist()],
        'coordinateCutoffUsed':False,'naturalSourceMutated':False,
        'stillRequired':['Generate alternate head while preserving full natural master','Fit hinge bearings to actual Jaw pivot and retained attachment boundary','Replace lower dental/gingival assembly while retaining upper teeth and tongue','Mount selected tusks in mechanical assembly without organic chin overlap','Actual closed/open and side clearance renders plus intersection checks']}
