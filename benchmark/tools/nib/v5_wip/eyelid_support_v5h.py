"""Continuous support proposal for the isolated post-v5g Blink repair.

The nasal domain is an anchor, not a discontinuous vertex switch. Distance
travels along the retained surface graph so neighboring cheek/lid vertices
approach zero continuously. Actual closure and extremes still require review.
"""
import numpy as np
from mouth_jaw_weights import distances,smooth
from face_planes_v5g import semantics

def calculate(source,faces,sets,edges,width=.004):
    points=np.asarray(source,dtype=np.float64)
    edges=np.asarray(edges,dtype=np.int32)
    nasal=semantics(len(points),faces,sets)[11]
    if nasal.sum()<100:raise RuntimeError('Missing audited nasal anchor domain')
    if not .002<=width<=.008:raise RuntimeError('Unbounded provisional Blink transition')
    distance=distances(points,edges,nasal,np.ones(len(points),dtype=bool))
    lateral=smooth(0,width,distance)
    brow=1-smooth(.322,.336,points[:,2])
    result=lateral*brow
    if not np.isfinite(result).all() or result.min()<0 or result.max()>1:
        raise RuntimeError('Nonfinite or out-of-range eyelid support')
    if result[nasal].max()!=0:raise RuntimeError('Nasal anchor is not fixed')
    boundary=nasal[edges[:,0]]!=nasal[edges[:,1]]
    length=np.linalg.norm(points[edges[:,0]]-points[edges[:,1]],axis=1)
    jump=abs(result[edges[:,0]]-result[edges[:,1]])
    return result,{'status':'Continuous support proposal; native pose/closure review required',
        'method':'Cubic smoothstep of edge-geodesic distance outside nasal face-set11; retained smooth upper-brow fade',
        'transitionSourceMeters':width,'nasalAnchorVertices':int(nasal.sum()),
        'partiallySupportedVertices':int(((result>0)&(result<1)).sum()),
        'boundaryMaximumSupportJump':float(jump[boundary].max()),
        'boundaryMaximumSupportSlopePerSourceMeter':float((jump[boundary]/np.maximum(length[boundary],1e-12)).max()),
        'allFinite':True,'range':[float(result.min()),float(result.max())],
        'nasalMaximumSupport':0.,'changesJawWeights':False,'changesNeutralBasis':False}
