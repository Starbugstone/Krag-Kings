# Adapted locally from tools/nib/v5_wip/mouth_jaw_weights.py at SHA256
# 32e162941906005c49e32803739a4f38086b947e99ce3fa982620789a91845fb.
# Preserves that frozen source. Krag follow-up adds a broader commissure
# transition and explicit anatomical oral-floor/roof anchors.
# v9ka uses a true half-ellipse over the complete corner-to-centre arc;
# the old sine-power profile held lateral lip tissue too high.
"""Topology-aware Jaw field for the audited CC0-derived Nib head.

Uses the retained source face sets: 33 upper lip/cheek, 24 lower lip/jaw,
7 oral bag, 11 nose. Distances travel along actual mesh edges, never across
the closed lips by a nearest-position shortcut. Provisional repair recipe;
actual saved source and expression render verification remain mandatory.
"""
import heapq
import numpy as np

def smooth(a,b,x):
    t=np.clip((x-a)/(b-a),0,1)
    return t*t*(3-2*t)

def distances(points,edges,seeds,allowed):
    adjacency=[[] for _ in points]
    lengths=np.linalg.norm(points[edges[:,0]]-points[edges[:,1]],axis=1)
    for (a,b),length in zip(edges,lengths):
        if allowed[a] and allowed[b]:
            adjacency[a].append((int(b),float(length)))
            adjacency[b].append((int(a),float(length)))
    result=np.full(len(points),np.inf);queue=[]
    for index in np.flatnonzero(seeds&allowed):
        result[index]=0.;queue.append((0.,int(index)))
    heapq.heapify(queue)
    while queue:
        value,index=heapq.heappop(queue)
        if value!=result[index]:continue
        for other,length in adjacency[index]:
            candidate=value+length
            if candidate<result[other]:
                result[other]=candidate;heapq.heappush(queue,(candidate,other))
    return result

def calculate(source,faces,face_sets,edges,neck,corner_fade=.020):
    source=np.asarray(source,dtype=np.float64);edges=np.asarray(edges,dtype=np.int32)
    tags=np.zeros(len(source),dtype=np.uint64)
    for face,tag in zip(faces,face_sets):
        if not 0<=int(tag)<64:raise RuntimeError('Unexpected unaudited facial set')
        tags[np.asarray(face,dtype=int)] |= np.uint64(1)<<np.uint64(tag)
    member=lambda tag:(tags&(np.uint64(1)<<np.uint64(tag)))!=0
    lower=member(24);upper=member(33);bag=member(7);nose=member(11)
    if min(lower.sum(),upper.sum(),bag.sum(),nose.sum())<100:
        raise RuntimeError('Missing audited upper/lower lip, oral or nose domains')
    lower_rim=lower&bag
    upper_rim=upper&bag
    corners=lower_rim&upper_rim
    if lower_rim.sum()<20 or upper_rim.sum()<20 or corners.sum()<2:
        raise RuntimeError('Audited independent upper/lower oral rims are absent')
    # All fixed upper surfaces stay on the cranium. The commissure follows the
    # existing MouthCorner expression controls; mandibular opening fades into
    # it along the lower rim instead of crossing the upper-lip skin.
    corner_distance=distances(source,edges,corners,lower_rim)
    if not np.isfinite(corner_distance[lower_rim]).all():
        raise RuntimeError('Lower oral rim is not connected to both corners')
    # A half-ellipse displacement over the full real lower-rim arc yields a
    # rounded opening. The former fixed-distance plateau made a trapezoid.
    radius=float(np.max(corner_distance[lower_rim]))
    if radius<=.015:raise RuntimeError('Unexpectedly short retained lower lip arc')
    progress=np.clip(corner_distance/radius,0,1)
    rim_weight=np.sqrt(np.maximum(0,1-(1-progress)**2))
    # Lower-jaw surfaces away from cranial/neck boundaries are mandibular.
    # The boundary blend width is measured along source topology. Inner mouth
    # vertices are solved between their actual separate upper/lower rims.
    lower_boundary=lower&~bag&((tags&~(np.uint64(1)<<np.uint64(24)))!=0)
    boundary_distance=distances(source,edges,lower_boundary,lower)
    lower_anchor=lower&~bag&~upper&(boundary_distance>=.009)
    mouth_z=float(np.median(source[lower_rim,2]))
    oral_floor=bag&~lower_rim&~upper_rim&(source[:,2]<mouth_z-.008)
    oral_roof=bag&~lower_rim&~upper_rim&(source[:,2]>mouth_z+.008)
    fixed_zero=~(lower|bag)|upper|nose|lower_boundary|oral_roof
    fixed_one=(lower_anchor|oral_floor)&~fixed_zero
    known=fixed_zero|fixed_one|lower_rim
    value=np.zeros(len(source));value[fixed_one]=1
    value[lower_rim]=rim_weight[lower_rim]
    value[fixed_zero]=0
    unknown=~known
    lengths=np.linalg.norm(source[edges[:,0]]-source[edges[:,1]],axis=1)
    if np.any(lengths<1e-10):raise RuntimeError('Zero-length edge in Jaw graph')
    # Symmetric inverse-length averaging is a scalar harmonic interpolation;
    # it preserves boundaries while avoiding piecewise x/y/z branch jumps.
    conductance=1/lengths
    a,b=edges.T
    denominator=np.bincount(a,conductance,minlength=len(source))+np.bincount(b,conductance,minlength=len(source))
    if np.any(denominator[unknown]<=0):raise RuntimeError('Disconnected Jaw solve vertex')
    def neighbors(values):
        return np.bincount(a,conductance*values[b],minlength=len(source))+np.bincount(b,conductance*values[a],minlength=len(source))
    diagonal=denominator[unknown]
    rhs=neighbors(value)[unknown]
    def multiply(values):
        whole=np.zeros(len(source));whole[unknown]=values
        return diagonal*values-neighbors(whole)[unknown]
    # Diagonally preconditioned conjugate gradients avoids the very slow
    # low-frequency convergence of Jacobi on the dense subdivided oral bag.
    solution=np.zeros(int(unknown.sum()));residual=rhs.copy()
    preconditioned=residual/diagonal;direction=preconditioned.copy()
    rz=float(np.dot(residual,preconditioned));initial=max(float(np.linalg.norm(rhs)),1e-30)
    relative=float(np.linalg.norm(residual))/initial
    for iteration in range(3000):
        if relative<1e-9:break
        product=multiply(direction);denom=float(np.dot(direction,product))
        if denom<=0:raise RuntimeError('Jaw harmonic graph is not positive definite')
        alpha=rz/denom;solution+=alpha*direction;residual-=alpha*product
        relative=float(np.linalg.norm(residual))/initial
        next_preconditioned=residual/diagonal
        next_rz=float(np.dot(residual,next_preconditioned))
        direction=next_preconditioned+(next_rz/rz)*direction;rz=next_rz
    if relative>=1e-9:raise RuntimeError('Jaw harmonic solve did not converge')
    value[unknown]=solution
    if value.min()<-1e-6 or value.max()>1+1e-6:raise RuntimeError('Harmonic Jaw field violates boundary maximum principle')
    result=np.clip(value,0,1)*(1-np.clip(neck,0,1))
    if np.any(result[upper|nose]>1e-12):raise RuntimeError('Jaw still pulls upper lip or nose')
    if not np.isfinite(result).all():raise RuntimeError('Invalid repaired Jaw weights')
    return result,{'method':'Audited semantic domains and edge-geodesic anchors with harmonic inner-mouth/lower-jaw interpolation',
        'sourceFaceSets':{'upperLipCheek':33,'lowerLipJaw':24,'oralBag':7,'nose':11},
        'upperLipVertices':int(upper.sum()),'lowerLipRimVertices':int(lower_rim.sum()),
        'upperLipRimVertices':int(upper_rim.sum()),'cornerVertices':int(corners.sum()),
        'lowerJawAnchorVertices':int(fixed_one.sum()),'unknownSolvedVertices':int(unknown.sum()),
        'iterations':iteration+1,'relativeLinearResidual':relative,
        'upperLipMaximumJawWeight':float(result[upper].max()),'noseMaximumJawWeight':float(result[nose].max()),
        'lowerRimJawWeightRange':[float(result[lower_rim].min()),float(result[lower_rim].max())],
        'lowerRimCornerToCenterSourceMeters':radius,'lowerRimProfile':'sqrt(1 - (1-geodesicFraction)^2)','lowerJawBoundarySourceMeters':.009,
        'oralFloorAnchorVertices':int(oral_floor.sum()),'oralRoofAnchorVertices':int(oral_roof.sum()),'sourceMouthHeight':mouth_z,
        'provisional':True,'requiresActualPoseReview':True}
