"""Broad screened-surface sculpt with actual orbital/oral margin protection.

No semantic face-set boundary truncates the brow or cheek field. Face sets only
identify the interior mouth and orbital graph rings; their neighboring skin is
solved together. This is a new provisional sculpt, not an accepted likeness.
"""
import heapq
import numpy as np


def quintic(value):
    t=np.clip(value,0,1)
    return t*t*t*(10+t*(-15+6*t))


def distances(points,edges,seeds):
    adjacent=[[]for _ in points]
    for a,b in edges:
        length=float(np.linalg.norm(points[a]-points[b]))
        adjacent[int(a)].append((int(b),length));adjacent[int(b)].append((int(a),length))
    result=np.full(len(points),np.inf);queue=[]
    for i in np.flatnonzero(seeds):result[i]=0;heapq.heappush(queue,(0.,int(i)))
    while queue:
        distance,index=heapq.heappop(queue)
        if distance!=result[index]:continue
        for other,length in adjacent[index]:
            candidate=distance+length
            if candidate<result[other]:result[other]=candidate;heapq.heappush(queue,(candidate,other))
    return result


def triangles_of(faces):
    return np.asarray([(f[0],f[i],f[i+1])for f in faces for i in range(1,len(f)-1)],dtype=np.int32)


def refine(raw,points,faces,sets,edges,rings,ocular_contacts=None):
    raw=np.asarray(raw,dtype=np.float64);points=np.asarray(points,dtype=np.float64);n=len(points)
    # Real topological rings are supplied by the audited CC0 orbital tracer.
    # All inner-mouth vertices and the shared lip margins stay fixed.
    fixed=np.zeros(n,dtype=bool)
    for face,tag in zip(faces,sets):
        if tag==7:fixed[list(face)]=True
    for ring in rings.values():fixed[np.asarray(ring,dtype=np.int32)]=True
    if ocular_contacts is not None:fixed[np.asarray(ocular_contacts,dtype=np.int32)]=True
    distance=distances(points,edges,fixed)
    protection=quintic((distance-.002)/.035)
    x,y,z=raw.T;g=lambda v,c,w:np.exp(-((v-c)/w)**2)
    front=quintic((-y-.015)/.105)
    desired=np.zeros((n,3))
    # Volume spans forehead and supraorbital tissue. A modest wide forward/down
    # movement replaces the failed 34 mm thin local visor displacement.
    brow=g(abs(x),.036,.046)*g(z,.341+.10*abs(x),.048)*front
    desired[:,1]-=.0115*brow;desired[:,2]-=.0042*brow
    bridge=g(x,0,.025)*g(z,.338,.051)*front
    desired[:,1]-=.0030*bridge
    # The upper cheek and lower masseter form one broad transition, rather than
    # a local point pushed through the surrounding cheek surface.
    zygoma=g(abs(x),.054,.044)*g(z,.285,.051)*front
    masseter=g(abs(x),.061,.047)*g(z,.238,.045)*front
    desired[:,1]-=.0055*zygoma;desired[:,1]+=.0035*masseter
    mandible=g(x,0,.071)*g(z,.207,.039)*front
    desired[:,1]-=.0060*mandible
    desired[fixed]=0
    tri=triangles_of(faces);t=points[tri]
    cross=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]);twice_area=np.linalg.norm(cross,axis=1)
    valid=twice_area>1e-12
    if not valid.all():tri=tri[valid];t=t[valid];cross=cross[valid];twice_area=twice_area[valid]
    mass=np.bincount(tri.ravel(),np.repeat(twice_area/6,3),minlength=n)
    if np.any(mass<=0):raise RuntimeError('Head surface has isolated or zero-area vertices')
    # Positive cotangent conductance makes the surface solve symmetric and
    # independent of tessellation density. Clamp obtuse negative cotangents;
    # no coordinate-based binary face boundary appears in this operator.
    aa=[];bb=[];ww=[]
    for k in range(3):
        a=(k+1)%3;b=(k+2)%3
        cot=np.einsum('ij,ij->i',t[:,a]-t[:,k],t[:,b]-t[:,k])/twice_area
        aa.append(tri[:,a]);bb.append(tri[:,b]);ww.append(.5*np.maximum(cot,0))
    a=np.concatenate(aa);b=np.concatenate(bb);w=np.concatenate(ww);length_scale=.019
    diagonal=mass+length_scale**2*(np.bincount(a,w,minlength=n)+np.bincount(b,w,minlength=n))
    def neighbors(value):
        return np.column_stack([np.bincount(a,w*value[b,k],minlength=n)+np.bincount(b,w*value[a,k],minlength=n)for k in range(3)])
    def multiply(value):return diagonal[:,None]*value-length_scale**2*neighbors(value)
    rhs=mass[:,None]*desired;solution=desired.copy();residual=rhs-multiply(solution)
    z=residual/diagonal[:,None];direction=z.copy();rz=float(np.sum(residual*z));initial=max(float(np.linalg.norm(rhs)),1e-30)
    for iteration in range(1600):
        relative=float(np.linalg.norm(residual))/initial
        if relative<1e-8:break
        product=multiply(direction);denominator=float(np.sum(direction*product))
        if denominator<=0:raise RuntimeError('Screened sculpt operator is not positive definite')
        alpha=rz/denominator;solution+=alpha*direction;residual-=alpha*product
        z=residual/diagonal[:,None];next_rz=float(np.sum(residual*z));direction=z+(next_rz/rz)*direction;rz=next_rz
    if relative>=1e-8:raise RuntimeError('Broad sculpt surface solve failed convergence')
    delta=solution*protection[:,None];delta[fixed]=0
    magnitude=np.linalg.norm(delta,axis=1)
    if magnitude.max()>.019:raise RuntimeError('Broad sculpt exceeds19 mm bounded mass change')
    a,b=np.asarray(edges).T;edge_length=np.linalg.norm(points[a]-points[b],axis=1)
    edge_gradient=np.linalg.norm(delta[a]-delta[b],axis=1)/np.maximum(edge_length,1e-10)
    after=points+delta;new=after[tri];new_cross=np.cross(new[:,1]-new[:,0],new[:,2]-new[:,0]);new_area=np.linalg.norm(new_cross,axis=1)
    cosine=np.einsum('ij,ij->i',cross,new_cross)/np.maximum(twice_area*new_area,1e-20)
    angles=np.degrees(np.arccos(np.clip(cosine,-1,1)))
    if np.any(cosine<=0)or np.any(new_area<twice_area*.35):raise RuntimeError('Broad sculpt flips or collapses surface triangles')
    if angles.max()>45 or edge_gradient.max()>.65:raise RuntimeError('Broad sculpt transition exceeds bounded normal/gradient change')
    worst=np.argsort(edge_gradient)[-12:][::-1]
    report={'status':'Actual broad surface displacement; profile/likeness and expressions still require renders',
        'surfaceSmoothingLengthMeters':length_scale,'marginDeadBandMeters':.002,'quinticMarginTransitionMeters':.035,
        'fixedOralAndOrbitalVertices':int(fixed.sum()),'maxDisplacementMeters':float(magnitude.max()),
        'screenedSolveIterations':iteration+1,'relativeResidual':relative,
        'displacementGradient':{'p95':float(np.quantile(edge_gradient,.95)),'p99':float(np.quantile(edge_gradient,.99)),'max':float(edge_gradient.max()),
          'worstEdges':[{'vertices':[int(a[i]),int(b[i])],'gradient':float(edge_gradient[i]),'midpoint':((points[a[i]]+points[b[i]])*.5).tolist()}for i in worst]},
        'normalAngleChangeDegrees':{'p95':float(np.quantile(angles,.95)),'p99':float(np.quantile(angles,.99)),'max':float(angles.max())},
        'minimumTriangleAreaRatio':float(np.min(new_area/twice_area)),'flippedTriangles':int(np.sum(cosine<=0)),
        'fixedMarginMaximumDisplacementMeters':float(magnitude[fixed].max()),'ringVertexCounts':{k:len(v)for k,v in rings.items()}}
    return delta,report
