"""Prepared coherent lower-jaw/chin study on the actual v9lc face.

This changes the broad mandibular body and angle, not the oral rim, ocular
assembly or repaired neck. Tusk eruption remains a separate visible failure.
Actual neutral/profile and open-mouth review are required before adoption.
"""
import numpy as np
from geodesic_planes import quintic,distances,triangles_of


def refine(raw,points,faces,sets,edges):
    raw=np.asarray(raw,dtype=np.float64);points=np.asarray(points,dtype=np.float64);n=len(points)
    x,y,z=raw.T
    fixed=(z>=.291)|(points[:,2]<=1.704)
    for face,tag in zip(faces,sets):
        if tag==7:fixed[list(face)]=True
    distance=distances(points,edges,fixed)
    protection=quintic((distance-.002)/.022)
    g=lambda v,c,w:np.exp(-((v-c)/w)**2)
    front=quintic((-y-.010)/.100)
    desired=np.zeros((n,3))
    # A wide mental prominence and its underside extend as one volume across
    # the lower jaw. The fourth-power horizontal field has a broad front plane,
    # rather than a narrow Gaussian chin peak that creates a profile beak.
    chin=np.exp(-(x/.058)**4)*g(z,.198,.036)*front
    desired[:,1]-=.0100*chin
    desired[:,2]-=.0030*chin
    # The mandibular angle and body run posteriorly beneath the masseter.
    # Distribute lateral/downward support over an anatomical region, retaining
    # a continuous transition into the chin and unchanged low neck.
    angle=g(abs(x),.056,.032)*g(z,.212,.037)*g(y,-.042,.060)
    desired[:,0]+=np.sign(x)*.0045*angle
    desired[:,2]-=.0040*angle
    # Reduce the inflated lower-cheek front without hollowing the muscle or
    # moving the true commissure. This distinguishes cheek and mandibular edge.
    cheek=g(abs(x),.055,.028)*g(z,.256,.034)*front
    desired[:,1]+=.0035*cheek
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
    a=np.concatenate(aa);b=np.concatenate(bb);w=np.concatenate(ww);length_scale=.016
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
    if magnitude.max()>.016:raise RuntimeError('Broad sculpt exceeds16 mm bounded mandibular change')
    a,b=np.asarray(edges).T;edge_length=np.linalg.norm(points[a]-points[b],axis=1)
    edge_gradient=np.linalg.norm(delta[a]-delta[b],axis=1)/np.maximum(edge_length,1e-10)
    after=points+delta;new=after[tri];new_cross=np.cross(new[:,1]-new[:,0],new[:,2]-new[:,0]);new_area=np.linalg.norm(new_cross,axis=1)
    cosine=np.einsum('ij,ij->i',cross,new_cross)/np.maximum(twice_area*new_area,1e-20)
    angles=np.degrees(np.arccos(np.clip(cosine,-1,1)))
    if np.any(cosine<=0)or np.any(new_area<twice_area*.35):raise RuntimeError('Broad sculpt flips or collapses surface triangles')
    if angles.max()>45 or edge_gradient.max()>.65:raise RuntimeError('Broad sculpt transition exceeds bounded normal/gradient change')
    worst=np.argsort(edge_gradient)[-12:][::-1]
    report={'status':'Actual broad surface displacement; profile/likeness and expressions still require renders',
        'surfaceSmoothingLengthMeters':length_scale,'marginDeadBandMeters':.002,'quinticMarginTransitionMeters':.022,
        'fixedOralAndOrbitalVertices':int(fixed.sum()),'maxDisplacementMeters':float(magnitude.max()),
        'screenedSolveIterations':iteration+1,'relativeResidual':relative,
        'displacementGradient':{'p95':float(np.quantile(edge_gradient,.95)),'p99':float(np.quantile(edge_gradient,.99)),'max':float(edge_gradient.max()),
          'worstEdges':[{'vertices':[int(a[i]),int(b[i])],'gradient':float(edge_gradient[i]),'midpoint':((points[a[i]]+points[b[i]])*.5).tolist()}for i in worst]},
        'normalAngleChangeDegrees':{'p95':float(np.quantile(angles,.95)),'p99':float(np.quantile(angles,.99)),'max':float(angles.max())},
        'minimumTriangleAreaRatio':float(np.min(new_area/twice_area)),'flippedTriangles':int(np.sum(cosine<=0)),
        'fixedMarginMaximumDisplacementMeters':float(magnitude[fixed].max()),'protectedRegions':['Complete oral bag and true lip margins','Upper face/eyes','Lower-neck transition']}
    return delta,report
