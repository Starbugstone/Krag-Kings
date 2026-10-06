"""Reference-constrained broad lip envelope and actual mandibular support.

Prepared and unaccepted. No change to the jaw hinge or ocular surface.
"""
import numpy as np
from profile_and_lip import member,ordered_rim,distances,smooth,extend_residual

class BroadOral:
    target_width=.150
    def __init__(self,points,edges,masks,optical_hold):
        self.points=np.asarray(points,float)
        self.lower=member(masks,24)&member(masks,7)
        self.upper=member(masks,33)&member(masks,7)
        self.rim=ordered_rim(edges,self.lower,self.points)
        self.center=.5*(self.points[self.rim[0],0]+self.points[self.rim[-1],0])
        self.scale=self.target_width/np.ptp(self.points[self.rim,0])
        distance=distances(self.points,edges,self.lower|self.upper)
        self.support=1-smooth((distance-.012)/.048)
        self.support[optical_hold]=0
        # Full support at the actual lip and adjacent roll, smoothly fading
        # through both external cheek/chin and the interior oral bag. The
        # posterior bag is not arbitrarily widened to dictate the dentition.
    def head(self,points):
        p=np.asarray(points,float);q=p.copy()
        if len(p)!=len(self.support):raise RuntimeError('Actual Head correspondence required')
        q[:,0]+=(p[:,0]-self.center)*(self.scale-1)*self.support
        return q


def rim_fraction(order,rest):
    x=rest[order,0]
    center=.5*(x[0]+x[-1]);half=.5*(x[-1]-x[0])
    if half<=0 or np.diff(x).min()<-.0002:raise RuntimeError('Folded or unordered actual lip rim')
    return np.clip(abs(x-center)/half,0,1)


def mandibular_rim_weights(order,rest):
    # Wide central region follows the mandible. Finite derivative at corners
    # replaces the old singular sqrt endpoint. Full range is unchanged.
    return 1-rim_fraction(order,rest)**4


def weight_support(rest,edges,masks,current):
    lower=member(masks,24)&member(masks,7)
    order=ordered_rim(edges,lower,rest)
    desired=mandibular_rim_weights(order,rest)
    values=np.zeros((len(rest),3));values[:,0]=current
    targets=values[order].copy();targets[:,0]=desired
    delta,report=extend_residual(rest,edges,order,targets,values,member(masks,33)|member(masks,11))
    revised=np.clip(current+delta[:,0],0,1)
    if np.max(abs(revised[order]-desired))>1e-8:raise RuntimeError('Actual lower-rim support not met')
    report.update({'method':'True lower-rim quartic mandibular support plus bounded graph-harmonic neighborhood',
                   'lowerRimVertices':len(order),'fixedUpperNoseVertices':int((member(masks,33)|member(masks,11)).sum()),
                   'maxWeightChange':float(abs(revised-current).max()),'artisticAcceptance':False})
    return revised,report


def lower_rim_target(order,rest,posed,rigid_jaw):
    weight=mandibular_rim_weights(order,rest)
    result=rest[order]*(1-weight[:,None])+rigid_jaw[order]*weight[:,None]
    result[0]=posed[order[0]];result[-1]=posed[order[-1]]
    return result
