"""Half-space surface clipping with exact edge lineage and a welded wrist bridge.

Pure NumPy helper. All per-point fields and per-corner UVs are interpolated with
identical cut parameters. It does not infer skinning or change a source file.
"""
from collections import Counter, defaultdict
import numpy as np


def clip(points, faces, materials, uvs, fields, signed_distance):
    vertices=[]; provenance=[]; index={}; output=[]; output_material=[]; output_uv={k:[] for k in uvs}
    def original(i):
        key=(i,i)
        if key not in index:
            index[key]=len(vertices);vertices.append(points[i]);provenance.append((i,i,0.))
        return index[key]
    def crossing(i,j):
        key=tuple(sorted((i,j)))
        if key not in index:
            a,b=key;t=float(signed_distance[a]/(signed_distance[a]-signed_distance[b]))
            index[key]=len(vertices);vertices.append(points[a]*(1-t)+points[b]*t);provenance.append((a,b,t))
        return index[key]
    for face_id,face in enumerate(faces):
        entries=[]
        for corner,i in enumerate(face):
            j=face[(corner+1)%len(face)];inside=signed_distance[i]>=0;following=signed_distance[j]>=0
            if inside:entries.append((original(i),corner,corner,0.))
            if inside!=following:
                t=float(signed_distance[i]/(signed_distance[i]-signed_distance[j]))
                entries.append((crossing(i,j),corner,(corner+1)%len(face),t))
        if len(entries)<3:continue
        if len({v[0] for v in entries})!=len(entries):raise RuntimeError('Degenerate clipped polygon')
        output.append([v[0] for v in entries]);output_material.append(materials[face_id])
        for name,values in uvs.items():output_uv[name].append([np.asarray(values[face_id][a])*(1-t)+np.asarray(values[face_id][b])*t for _,a,b,t in entries])
    a=np.array([v[0] for v in provenance]);b=np.array([v[1] for v in provenance]);t=np.array([v[2] for v in provenance])
    result_fields={}
    for name,values in fields.items():
        values=np.asarray(values);mix=t.reshape((len(t),)+(1,)*(values.ndim-1));result_fields[name]=values[a]*(1-mix)+values[b]*mix
    return {'points':np.asarray(vertices),'faces':output,'materials':output_material,'uvs':output_uv,'fields':result_fields,'lineage':provenance}


def cut_loop(surface, origin, axis, offset, tolerance=1e-6):
    count=Counter(tuple(sorted((face[i],face[(i+1)%len(face)]))) for face in surface['faces'] for i in range(len(face)))
    distance=(surface['points']-origin)@axis-offset
    edges=[edge for edge,n in count.items() if n==1 and all(abs(distance[v])<tolerance for v in edge)]
    graph=defaultdict(list)
    for a,b in edges:graph[a].append(b);graph[b].append(a)
    if not graph or any(len(v)!=2 for v in graph.values()):raise RuntimeError('Cut is not a single closed manifold ring')
    sequence=[min(graph)];prior=None
    while True:
        choices=[v for v in graph[sequence[-1]] if v!=prior];nxt=choices[0]
        if nxt==sequence[0]:break
        if nxt in sequence:raise RuntimeError('Repeated wrist-ring vertex')
        prior=sequence[-1];sequence.append(nxt)
    if len(sequence)!=len(graph):raise RuntimeError('Cut produced multiple wrist rings')
    return sequence


def connect(upper, lower, upper_ring, lower_ring, origin, across, normal):
    """Join rings through two interpolated rings, preserving original boundaries.

    Ordered contours must be star-shaped about their own centers. Ring samples
    retain full point-field lineage; original surface UVs remain exact.
    """
    count=len(upper['points']);points=np.concatenate([upper['points'],lower['points']]).tolist()
    faces=list(upper['faces'])+[[i+count for i in f] for f in lower['faces']]
    mats=list(upper['materials'])+list(lower['materials'])
    field_names=set(upper['fields'])
    if field_names!=set(lower['fields']):raise RuntimeError('Point-field schemas differ')
    fields={k:np.concatenate([upper['fields'][k],lower['fields'][k]]).tolist() for k in field_names}
    uv_names=set(upper['uvs'])
    if uv_names!=set(lower['uvs']):raise RuntimeError('UV-layer schemas differ')
    uvs={k:list(upper['uvs'][k])+list(lower['uvs'][k]) for k in uv_names}
    def polar(ids):
        coords=np.array([points[i] for i in ids]);center=coords.mean(0);q=coords-center
        angles=np.arctan2(q@normal,q@across)%(2*np.pi)
        # Topology order, not an angle sort that could hide a folded contour.
        delta=np.angle(np.exp(1j*(np.roll(angles,-1)-angles)))
        if np.sum(delta)<0:ids=ids[::-1];angles=angles[::-1];delta=np.angle(np.exp(1j*(np.roll(angles,-1)-angles)))
        if np.any(delta<=0):raise RuntimeError('Non-star-shaped wrist boundary needs explicit repair')
        start=int(np.argmin(angles));return ids[start:]+ids[:start],np.roll(angles,-start)
    top,at=polar(list(upper_ring));bottom,ab=polar([v+count for v in lower_ring]);period=2*np.pi
    def sample(theta):
        extended=np.r_[ab[-1]-period,ab,ab[0]+period];ids=[bottom[-1]]+bottom+[bottom[0]]
        j=int(np.searchsorted(extended,theta)-1);t=float((theta-extended[j])/(extended[j+1]-extended[j]));return ids[j],ids[j+1],t
    rings=[top]
    for fraction in [1/3,2/3]:
        new=[]
        for old,theta in zip(top,at):
            a,b,t=sample(theta);target=np.asarray(points[a])*(1-t)+np.asarray(points[b])*t
            new.append(len(points));points.append((np.asarray(points[old])*(1-fraction)+target*fraction).tolist())
            for key in field_names:
                value=(np.asarray(fields[key][a])*(1-t)+np.asarray(fields[key][b])*t)*fraction+np.asarray(fields[key][old])*(1-fraction)
                fields[key].append(value.tolist())
        rings.append(new)
    def add(face):
        faces.append(face);mats.append(0)
        for name in uv_names:uvs[name].append([[.5,.5] for _ in face])
    for r0,r1 in zip(rings,rings[1:]):
        for i in range(len(top)):add([r0[i],r0[(i+1)%len(top)],r1[(i+1)%len(top)],r1[i]])
    # Unequal loop counts: advance one contour vertex at a time. Every edge is
    # shared once; geometric validation follows after native normal rebuilding.
    a_ring=rings[-1];i=j=0
    while i<len(a_ring) or j<len(bottom):
        next_a=at[(i+1)%len(at)]+(period if i+1>=len(at) else 0) if i<len(a_ring) else float('inf')
        next_b=ab[(j+1)%len(ab)]+(period if j+1>=len(ab) else 0) if j<len(bottom) else float('inf')
        a0=a_ring[i%len(a_ring)];b0=bottom[j%len(bottom)]
        if next_a<=next_b:
            add([a0,a_ring[(i+1)%len(a_ring)],b0]);i+=1
        else:
            add([a0,bottom[(j+1)%len(bottom)],b0]);j+=1
    return {'points':np.asarray(points),'faces':faces,'materials':mats,'uvs':uvs,'fields':{k:np.asarray(v) for k,v in fields.items()},
            'join':{'upperRingVertices':len(top),'lowerRingVertices':len(bottom),'intermediateRings':2,'weldedSharedIndices':True}}
