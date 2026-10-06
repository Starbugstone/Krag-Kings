"""Read-only orbital-loop study from a hash-verified actual saved-head cache.

This measures topology and identifies candidate tight rings. A minimum-radius
ring is not assumed to be the visible lid margin: fitted eye-surface contact
and actual posed review are required before it becomes an animation anchor.
No Blender process, mesh modification or shape repair occurs here.
"""
import argparse
from collections import Counter,deque
import hashlib,json
from pathlib import Path
import numpy as np

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def membership(vertex_count,faces,sets,tag):
    result=np.zeros(vertex_count,dtype=bool)
    result[np.unique(faces[sets==tag])]=True
    return result

def ring_order(ids,edges):
    ids=set(map(int,ids));adj={i:[] for i in ids}
    for a,b in edges:
        if a in ids and b in ids:adj[int(a)].append(int(b));adj[int(b)].append(int(a))
    degrees=Counter(len(v) for v in adj.values())
    if set(degrees)!={2}:return None,{str(k):v for k,v in degrees.items()}
    first=min(ids);order=[first];previous=None;current=first
    while True:
        candidates=[i for i in adj[current] if i!=previous]
        nxt=min(candidates) if previous is None else candidates[0]
        if nxt==first:break
        if nxt in order:return None,{'unexpectedSubcycle':True}
        order.append(nxt);previous,current=current,nxt
    return (order if len(order)==len(ids) else None),{str(k):v for k,v in degrees.items()}

def analyze(points,basis,faces,sets,edges):
    result={}
    for side,inner,outer,cx in [('R',5,9,-.0358764),('L',6,10,.0358764)]:
        inside=membership(len(points),faces,sets,inner)
        outside=membership(len(points),faces,sets,outer)
        boundary=inside&outside;seed=np.flatnonzero(boundary)
        graph=[[] for _ in points]
        for a,b in edges:
            if outside[a] and outside[b]:graph[int(a)].append(int(b));graph[int(b)].append(int(a))
        distance=np.full(len(points),-1,dtype=np.int32);distance[seed]=0;queue=deque(seed)
        while queue:
            a=queue.popleft()
            for b in graph[a]:
                if distance[b]<0:distance[b]=distance[a]+1;queue.append(b)
        layers=[]
        for layer in range(int(distance.max())+1):
            ids=np.flatnonzero(distance==layer);p=points[ids];q=basis[ids]
            radii=np.hypot(p[:,0]-cx,p[:,2]-.3100375)
            order,degrees=ring_order(ids,edges)
            layers.append({'stepsFromTaggedCavityBoundary':layer,'vertices':len(ids),
                'sourceMeanY':float(p[:,1].mean()),'sourceMeanProjectedRadius':float(radii.mean()),
                'sourceMinimumProjectedRadius':float(radii.min()),
                'sourceXWidth':float(np.ptp(p[:,0])),'sourceZHeight':float(np.ptp(p[:,2])),
                'fittedBoundsMin':q.min(axis=0).tolist(),'fittedBoundsMax':q.max(axis=0).tolist(),
                'singleClosedCycle':order is not None,'withinLayerEdgeDegrees':degrees})
        eligible=[item for item in layers if item['singleClosedCycle']]
        if not eligible:raise RuntimeError('No closed orbital ring identified: '+side)
        tight=min(eligible,key=lambda item:item['sourceMeanProjectedRadius'])
        ids=np.flatnonzero(distance==tight['stepsFromTaggedCavityBoundary'])
        order,_=ring_order(ids,edges)
        result[side]={'sourceTags':{'cavity':inner,'surroundingOrbitalSurface':outer},
            'boundaryVertices':len(seed),'layers':layers,'candidateTightClosedRing':tight,
            'candidateRingVertexIds':order,'candidateIsNotYetVerifiedLidMargin':True}
    return result

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--cache',type=Path,required=True)
    parser.add_argument('--audit',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    audit=json.loads(args.audit.read_text())
    if sha(args.cache)!=audit['cacheSha256']:raise RuntimeError('Actual source cache hash mismatch')
    cache=np.load(args.cache,allow_pickle=True)
    report={'status':'Actual cached topology measurements; closure design remains provisional and ungenerated',
        'cacheSha256':sha(args.cache),'auditSha256':sha(args.audit),'codeSha256':sha(Path(__file__)),
        'sources':audit['sources'],'changedSource':False,'artisticAcceptance':False,
        'coordinates':'Source attribute in original head local metres; fitted Basis remains in Nib head object space, before its world transform',
        'eyes':analyze(cache['source'],cache['basis'],cache['faces'].astype(np.int32),cache['face_sets'],cache['edges']),
        'nextEvidence':['Inspect actual fitted sclera/iris surfaces in the same head coordinate frame.',
            'Verify the candidate loop against the true visible lid margin; face-set boundary alone lies too far inside the cavity.',
            'Use upper/lower arc correspondence and globe clearance with fixed orbital anchors, preserving the nose and Jaw repair.',
            'Check partial and full closure for inverted faces, collisions, seam continuity and nasal displacement before actual neutral/Tongue/Blink renders.']}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n',newline='\n')
    print('NIB_ORBITAL_TOPOLOGY_STUDY_COMPLETE')

if __name__=='__main__':main()
