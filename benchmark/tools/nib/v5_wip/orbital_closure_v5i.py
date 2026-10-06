"""Provisional loop/globe closure, evaluated numerically before native use.

Uses the actual fitted opaque eye surface and the audited continuous orbital
topology. No source-space Gaussian, binary nasal cutoff, or global horizontal
closure line defines the shape. This remains a proposal until posed review.
"""
import numpy as np

def front_surface_y(points_xz,vertices,triangles):
    """Frontal ray intersection with the actual opaque ocular triangles."""
    t=np.asarray(vertices,dtype=np.float64)[triangles]
    a=t[:,0][:,[0,2]];b=t[:,1][:,[0,2]]-a;c=t[:,2][:,[0,2]]-a
    determinant=b[:,0]*c[:,1]-b[:,1]*c[:,0]
    valid=abs(determinant)>1e-14;denominator=np.where(valid,determinant,1.)
    result=[]
    for p in np.asarray(points_xz):
        q=p-a;u=(q[:,0]*c[:,1]-q[:,1]*c[:,0])/denominator
        v=(b[:,0]*q[:,1]-b[:,1]*q[:,0])/denominator
        inside=valid&(u>=-1e-8)&(v>=-1e-8)&(u+v<=1+1e-8)
        y=t[:,0,1]+u*(t[:,1,1]-t[:,0,1])+v*(t[:,2,1]-t[:,0,1])
        result.append(float(y[inside].min()) if inside.any() else np.nan)
    return np.asarray(result)

def split_arcs(order,points):
    order=np.asarray(order,dtype=np.int32)
    # Rotate the closed topological ring to the minimum-X canthus. Both
    # traversals end at the same maximum-X canthus and remain separate paths.
    order=np.roll(order,-int(np.argmin(points[order,0])))
    end=int(np.argmax(points[order,0]))
    a=order[:end+1];b=np.r_[order[0],order[:end-1:-1]]
    if a[-1]!=b[-1] or a[0]!=b[0]:raise RuntimeError('Orbital paths do not share both canthi')
    upper,lower=(a,b) if points[a,2].mean()>points[b,2].mean() else (b,a)
    for arc in [upper,lower]:
        if np.any(np.diff(points[arc,0])<=0):raise RuntimeError('Candidate lid arc is not monotonic in X')
    return upper,lower

class OrbitalDomain:
    """Vector harmonic interpolation between an anatomical rim and anchors."""
    def __init__(self,source,faces,sets,edges,outer,ring):
        self.count=len(source);self.ring=np.asarray(ring,dtype=np.int32)
        orbital=np.zeros(self.count,dtype=bool);orbital[np.unique(faces[sets==outer])]=True
        other=np.zeros(self.count,dtype=bool);other[np.unique(faces[sets!=outer])]=True
        self.unknown=orbital&~other;self.unknown[self.ring]=False
        self.anchors=~self.unknown;self.anchors[self.ring]=False
        self.a,self.b=edges.T
        length=np.linalg.norm(source[self.a]-source[self.b],axis=1)
        if np.any(length<1e-10):raise RuntimeError('Degenerate orbital graph edge')
        self.conductance=1/length
        self.diagonal=(np.bincount(self.a,self.conductance,minlength=self.count)+np.bincount(self.b,self.conductance,minlength=self.count))[self.unknown,None]
    def neighbors(self,value):
        return np.column_stack([np.bincount(self.a,self.conductance*value[self.b,k],minlength=self.count)+
            np.bincount(self.b,self.conductance*value[self.a,k],minlength=self.count) for k in range(3)])
    def solve(self,rim_delta):
        delta=np.zeros((self.count,3));delta[self.ring]=rim_delta
        rhs=self.neighbors(delta)[self.unknown]
        solution=np.zeros_like(rhs);residual=rhs.copy();z=residual/self.diagonal;direction=z.copy()
        rz=float(np.sum(residual*z));initial=max(float(np.linalg.norm(rhs)),1e-30)
        relative=float(np.linalg.norm(residual))/initial
        for iteration in range(2000):
            if relative<1e-9:break
            vector=np.zeros_like(delta);vector[self.unknown]=direction
            product=self.diagonal*direction-self.neighbors(vector)[self.unknown]
            denominator=float(np.sum(direction*product))
            if denominator<=0:raise RuntimeError('Orbital graph is not positive definite')
            alpha=rz/denominator;solution+=alpha*direction;residual-=alpha*product
            relative=float(np.linalg.norm(residual))/initial
            z=residual/self.diagonal;next_rz=float(np.sum(residual*z))
            direction=z+(next_rz/rz)*direction;rz=next_rz
        if relative>=1e-9:raise RuntimeError('Orbital interpolation did not converge')
        delta[self.unknown]=solution
        if np.max(abs(delta[self.anchors]))!=0:raise RuntimeError('Closure moved its orbital anchors')
        return delta,{'iterations':iteration+1,'relativeResidual':relative,
            'movingRimVertices':len(self.ring),'interpolatedVertices':int(self.unknown.sum()),
            'anchorMaximumDeltaMeters':0.}
    def preserve_local_rotation(self,points,delta,iterations=12):
        """Provisional ARAP relaxation with the exact same ring/anchor targets.

        Scalar harmonic displacement can fold the thin canthus transition.
        This tests local surface rotation preservation, without changing the
        target seam, expanding the anatomical support, or moving the nose.
        It is accepted only by subsequent geometry and actual pose checks.
        """
        moving=self.unknown.copy();moving[self.ring]=True
        selected=moving[self.a]|moving[self.b]
        a=self.a[selected];b=self.b[selected];w=self.conductance[selected]
        rest=points[a]-points[b];result=delta.copy()
        fixed=np.zeros_like(delta);fixed[self.ring]=delta[self.ring]
        fixed_rhs=self.neighbors(fixed)[self.unknown]
        active=np.flatnonzero(moving)
        def incidence(value):
            return np.column_stack([np.bincount(a,w*value[:,k],minlength=self.count)-np.bincount(b,w*value[:,k],minlength=self.count) for k in range(3)])
        residuals=[]
        for outer_iteration in range(iterations):
            q=points+result;deformed=q[a]-q[b]
            covariance=np.zeros((self.count,3,3))
            for j in range(3):
                for k in range(3):
                    value=w*deformed[:,j]*rest[:,k]
                    covariance[:,j,k]=np.bincount(a,value,minlength=self.count)+np.bincount(b,value,minlength=self.count)
            u,_,vt=np.linalg.svd(covariance[active])
            correction=np.ones((len(active),3));correction[:,-1]=np.linalg.det(u@vt)
            rotation=np.broadcast_to(np.eye(3),(self.count,3,3)).copy()
            rotation[active]=(u*correction[:,None,:])@vt
            transformed=np.einsum('nij,nj->ni',.5*(rotation[a]+rotation[b]),rest)
            rhs=fixed_rhs+incidence(transformed-rest)[self.unknown]
            solution=result[self.unknown].copy()
            def multiply(value):
                v=np.zeros_like(delta);v[self.unknown]=value
                return self.diagonal*value-self.neighbors(v)[self.unknown]
            residual=rhs-multiply(solution);z=residual/self.diagonal;direction=z.copy()
            rz=float(np.sum(residual*z));initial=max(float(np.linalg.norm(rhs)),1e-30)
            relative=float(np.linalg.norm(residual))/initial
            for iteration in range(1200):
                if relative<1e-8:break
                product=multiply(direction);denominator=float(np.sum(direction*product))
                if denominator<=0:raise RuntimeError('Orbital ARAP graph is not positive definite')
                alpha=rz/denominator;solution+=alpha*direction;residual-=alpha*product
                relative=float(np.linalg.norm(residual))/initial
                z=residual/self.diagonal;next_rz=float(np.sum(residual*z))
                direction=z+(next_rz/rz)*direction;rz=next_rz
            if relative>=1e-8:raise RuntimeError('Orbital ARAP solve did not converge')
            change=float(np.linalg.norm(result[self.unknown]-solution,axis=1).max())
            result[self.unknown]=solution;residuals.append({'iteration':outer_iteration+1,'maximumChangeMeters':change,'linearResidual':relative})
        if not np.array_equal(result[self.ring],delta[self.ring]) or np.max(abs(result[self.anchors]))!=0:
            raise RuntimeError('Local rotation fit moved its fixed seam/anchors')
        return result,{'status':'Numerical rotation-preserving proposal, not accepted geometry','iterations':residuals,'fixedSeamAndAnchorsPreserved':True}

def eye_surface(cache,side):
    a=cache['sclera_'+side];b=cache['iris_'+side]
    return np.vstack((a,b)),np.vstack((cache['scleraTriangles_'+side],cache['irisTriangles_'+side]+len(a)))

def propose(cache,topology,rotation_preservation=False):
    basis=np.asarray(cache['basis'],dtype=np.float64);source=cache['source']
    faces=cache['faces'].astype(np.int32);sets=cache['faceSets'];edges=cache['edges']
    neutral=basis.copy();report={'status':'Numerical loop/globe closure proposal; not generated or accepted',
        'ocularClearanceMeters':.00020,'eyes':{}}
    domains={};surfaces={};arcs={}
    for side,outer in [('R',9),('L',10)]:
        ring=np.asarray(topology['eyes'][side]['candidateRingVertexIds'],dtype=np.int32)
        upper,lower=split_arcs(ring,basis);arcs[side]=(upper,lower)
        domain=OrbitalDomain(source,faces,sets,edges,outer,ring);domains[side]=domain
        vertices,triangles=eye_surface(cache,side);surfaces[side]=(vertices,triangles)
        shell=front_surface_y(basis[ring][:,[0,2]],vertices,triangles)
        valid=np.isfinite(shell);rim=np.zeros((len(ring),3))
        rim[valid,1]=np.minimum(0,shell[valid]-.00020-basis[ring[valid],1])
        correction,metric=domain.solve(rim);neutral+=correction
        report['eyes'][side]={'ring':ring.tolist(),'upperArc':upper.tolist(),'lowerArc':lower.tolist(),
            'neutralClearance':metric,'maximumNeutralAdjustmentMeters':float(np.linalg.norm(correction,axis=1).max()),
            'priorRingPointsBehindOpaqueShell':int(np.sum(basis[ring[valid],1]>shell[valid]))}
    shapes={}
    for side in ['L','R']:
        domain=domains[side];ring=domain.ring;upper,lower=arcs[side]
        vertices,triangles=surfaces[side]
        x=neutral[ring,0]
        up=np.column_stack([np.interp(x,neutral[upper,0],neutral[upper,k]) for k in range(3)])
        low=np.column_stack([np.interp(x,neutral[lower,0],neutral[lower,k]) for k in range(3)])
        # Upper lids cover most of the aperture; the lower lid rises less.
        # The shared seam retains the actual canthus heights and curvature.
        seam=.25*up+.75*low;seam[:,0]=x
        seam[:,1]=np.minimum(up[:,1],low[:,1])
        shell=front_surface_y(seam[:,[0,2]],vertices,triangles);valid=np.isfinite(shell)
        seam[valid,1]=np.minimum(seam[valid,1],shell[valid]-.00020)
        rim=seam-neutral[ring]
        # A linear morph follows a chord. Bound the final forward position by
        # all sampled intermediate shell crossings, not only the closed pose.
        for fraction in np.linspace(.05,.95,19):
            sample=neutral[ring]+rim*fraction
            shell=front_surface_y(sample[:,[0,2]],vertices,triangles);valid=np.isfinite(shell)
            required=(shell[valid]-.00020-neutral[ring[valid],1])/fraction
            rim[valid,1]=np.minimum(rim[valid,1],required)
        delta,metric=domain.solve(rim)
        if rotation_preservation:
            delta,rotation_metric=domain.preserve_local_rotation(neutral,delta)
            report['eyes'][side]['localRotationFit']=rotation_metric
        shapes['Blink_'+side]=delta
        # The partial eye squeeze stays in the same anatomical domain rather
        # than drawing a wide Gaussian crease through the nasal bridge.
        squeeze=rim.copy();upper_mask=np.isin(ring,upper)
        squeeze[upper_mask]*=.18;squeeze[~upper_mask]*=.65
        squint,squint_metric=domain.solve(squeeze);shapes['Squint_'+side]=squint
        report['eyes'][side]['blinkSolve']=metric
        report['eyes'][side]['squintSolve']=squint_metric
        report['eyes'][side]['maximumBlinkDeltaMeters']=float(np.linalg.norm(delta,axis=1).max())
        report['eyes'][side]['maximumSquintDeltaMeters']=float(np.linalg.norm(squint,axis=1).max())
    return neutral,shapes,report
