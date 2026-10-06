"""Bounded ungenerated face-plane/contact proposal after actual v5f review.

No new canonical measurements are established here. These source-space fields
keep the neck, eye centers, repaired Jaw weights and source topology intact.
Actual neutral/depth/Tongue/Blink review is required before any groom/export.
"""
import heapq
import numpy as np
from mouth_jaw_weights import smooth,distances

def gaussian(value,center,width):return np.exp(-((value-center)/width)**2)

def semantics(count,faces,sets):
    tags=np.zeros(count,dtype=np.uint64)
    for face,tag in zip(faces,sets):tags[np.asarray(face,dtype=int)] |= np.uint64(1)<<np.uint64(tag)
    return {tag:(tags&(np.uint64(1)<<np.uint64(tag)))!=0 for tag in [7,11,24,33]}

def plane_delta(source,basis):
    raw=np.asarray(source,dtype=np.float64);points=np.asarray(basis,dtype=np.float64)
    x,y,z=raw.T;delta=np.zeros_like(points)
    front=smooth(.080,.128,-y)
    # A compact raised nose pad with two upper lobes and a tapered lower tip.
    # It deforms the existing nostril/alar surface, never adds a detached ball.
    pad=np.exp(-(x/.026)**4-((z-.268)/.019)**4)*smooth(.132,.153,-y)
    delta[:,0]-=points[:,0]*.10*pad
    delta[:,1]-=.0038*pad
    delta[:,2]+=(z-.268)*.25*pad
    delta[:,2]+=.0012*gaussian(abs(x),.009,.009)*gaussian(z,.275,.009)*pad
    delta[:,2]-=.0010*gaussian(x,0,.007)*gaussian(z,.258,.008)*pad
    # Broad continuous muzzle pads and a soft central philtrum groove.
    muzzle=gaussian(abs(x),.020,.014)*gaussian(z,.248,.018)*front
    delta[:,1]-=.0020*muzzle
    delta[:,1]+=.0009*gaussian(x,0,.006)*gaussian(z,.252,.012)*front
    # Preserve the round nose-leading profile while narrowing the heavy jowl.
    chin=gaussian(x,0,.052)*gaussian(z,.202,.025)*front
    delta[:,0]-=points[:,0]*.13*chin
    delta[:,2]+=.0018*gaussian(x,0,.029)*gaussian(z,.191,.015)*front
    cheek=gaussian(abs(x),.057,.021)*gaussian(z,.269,.025)*front
    delta[:,1]-=.0018*cheek
    hollow=gaussian(abs(x),.052,.022)*gaussian(z,.239,.020)*front
    delta[:,1]+=.0020*hollow
    # Lift and curve both commissures, with the restrained asymmetry already
    # suggested by sheet02. Mouth contact is solved separately after this.
    corner=gaussian(abs(x),.034,.016)*gaussian(z,.232,.016)*front
    delta[:,2]+=(.0024+.0005*np.sign(x))*corner
    delta[:,1]+=.0010*corner
    # Arched upper orbital fold and a recessed crease below it, both continuous
    # skin relief. Ocular meshes and their pivots are not moved by this pass.
    t=np.clip((abs(x)-.013)/.051,0,1)
    arch=.324+.010*np.sin(np.pi*t)+.003*t
    span=smooth(.009,.017,abs(x))*(1-smooth(.059,.073,abs(x)))
    fold=gaussian(z,arch,.0055)*span*front
    crease=gaussian(z,arch-.0055,.0027)*span*front
    delta[:,1]-=.0028*fold
    delta[:,1]+=.0011*crease
    delta[:,2]+=.0012*fold*(.4+.6*t)
    # Explicitly preserve lower neck and scalp rather than moving the complete
    # head to disguise the face's current proportion/plane problems.
    support=smooth(.178,.193,z)*(1-smooth(.350,.370,z))
    delta*=support[:,None]
    return delta,{'status':'Ungenerated continuous face-plane proposal',
        'maximumDisplacementMeters':float(np.linalg.norm(delta,axis=1).max()),
        'eyeAssemblyMoved':False,'newDetachedFaceMeshes':False,
        'lowerNeckMaximumDeltaMeters':float(np.linalg.norm(delta[z<=.178],axis=1).max()) if np.any(z<=.178) else 0.,
        'features':['projecting tapered nasal pad','paired muzzle pads and philtrum','tapered chin/cheek planes','curved asymmetric commissures','arched upper orbital fold and crease']}

def ordered_rim(mask,edges,corners,source):
    ids=np.flatnonzero(mask);adj={int(i):[] for i in ids}
    for a,b in edges:
        if mask[a] and mask[b]:adj[int(a)].append(int(b));adj[int(b)].append(int(a))
    endpoints=np.flatnonzero(corners)
    if len(endpoints)!=2:raise RuntimeError('Expected two audited mouth commissures')
    start=int(endpoints[np.argmin(source[endpoints,0])]);end=int(endpoints[np.argmax(source[endpoints,0])])
    result=[start];previous=-1
    while result[-1]!=end:
        options=[i for i in adj[result[-1]] if i!=previous]
        if len(options)!=1:raise RuntimeError('Oral rim is not a single ordered path')
        previous=result[-1];result.append(options[0])
        if len(result)>len(ids):raise RuntimeError('Oral rim unexpectedly loops')
    if len(result)!=len(ids):raise RuntimeError('Oral rim contains disconnected vertices')
    return np.asarray(result,dtype=np.int32)

class MouthContact:
    """Separate lip paths share a closed curve; topology remains independent."""
    def __init__(self,source,faces,sets,edges):
        self.source=np.asarray(source,dtype=np.float64);self.edges=np.asarray(edges,dtype=np.int32)
        tags=semantics(len(source),faces,sets);upper=tags[33]&tags[7];lower=tags[24]&tags[7];corners=upper&lower
        self.upper=ordered_rim(upper,edges,corners,source);self.lower=ordered_rim(lower,edges,corners,source)
        self.parameters=[]
        for order in [self.upper,self.lower]:
            length=np.linalg.norm(np.diff(self.source[order],axis=0),axis=1)
            value=np.r_[0,np.cumsum(length)];self.parameters.append(value/value[-1])
        self.rim=upper|lower
        distance=distances(self.source,self.edges,self.rim,np.ones(len(source),dtype=bool))
        self.distance=distance;self.unknown=(distance<.010)&~self.rim
        self.a,self.b=self.edges.T
        length=np.linalg.norm(self.source[self.a]-self.source[self.b],axis=1)
        self.conductance=1/np.maximum(length,1e-10)
        self.diagonal=(np.bincount(self.a,self.conductance,minlength=len(source))+np.bincount(self.b,self.conductance,minlength=len(source)))[self.unknown,None]
    def neighbors(self,values):
        return np.column_stack([np.bincount(self.a,self.conductance*values[self.b,k],minlength=len(self.source))+
            np.bincount(self.b,self.conductance*values[self.a,k],minlength=len(self.source)) for k in range(3)])
    def interpolate(self,values,parameters,at):
        return np.column_stack([np.interp(at,parameters,values[:,k]) for k in range(3)])
    def close(self,points):
        points=np.asarray(points,dtype=np.float64);delta=np.zeros_like(points)
        upper,lower=points[self.upper],points[self.lower];up,low=self.parameters
        # Fit both paths to one piecewise-linear curve on a common parameter
        # grid; the dense topology limits sub-edge approximation error.
        grid=np.linspace(0,1,257)
        common=(self.interpolate(upper,up,grid)+self.interpolate(lower,low,grid))*.5
        delta[self.upper]=self.interpolate(common,grid,up)-upper
        delta[self.lower]=self.interpolate(common,grid,low)-lower
        rhs=self.neighbors(delta)[self.unknown]
        solution=np.zeros_like(rhs);residual=rhs.copy();preconditioned=residual/self.diagonal;direction=preconditioned.copy()
        rz=float(np.sum(residual*preconditioned));initial=max(float(np.linalg.norm(rhs)),1e-30)
        relative=float(np.linalg.norm(residual))/initial
        for iteration in range(2000):
            if relative<1e-9:break
            whole=np.zeros_like(points);whole[self.unknown]=direction
            product=self.diagonal*direction-self.neighbors(whole)[self.unknown]
            denom=float(np.sum(direction*product))
            if denom<=0:raise RuntimeError('Contact interpolation graph is not positive definite')
            alpha=rz/denom;solution+=alpha*direction;residual-=alpha*product
            relative=float(np.linalg.norm(residual))/initial
            next_preconditioned=residual/self.diagonal;next_rz=float(np.sum(residual*next_preconditioned))
            direction=next_preconditioned+(next_rz/rz)*direction;rz=next_rz
        if relative>=1e-9:raise RuntimeError('Contact interpolation did not converge')
        # Smooth the outer edge of the support so contact does not leave a new
        # circular crease at a hard geodesic cutoff.
        fade=1-smooth(.004,.010,self.distance[self.unknown])
        delta[self.unknown]=solution*fade[:,None]
        result=points+delta
        u=self.interpolate(result[self.upper],up,grid);l=self.interpolate(result[self.lower],low,grid)
        residual_gap=np.linalg.norm(u-l,axis=1)
        return result,{'upperRimVertices':len(self.upper),'lowerRimVertices':len(self.lower),
            'rimMaximumAdjustmentMeters':float(np.linalg.norm(delta[self.rim],axis=1).max()),
            'sampledContactMaximumGapMeters':float(residual_gap.max()),
            'sampledContactRmsGapMeters':float(np.sqrt(np.mean(residual_gap**2))),
            'iterations':iteration+1,'relativeLinearResidual':relative,
            'topologyWelded':False,'scope':'Provisional neutral lip-contact fit; actual visibility/pose review mandatory'}
