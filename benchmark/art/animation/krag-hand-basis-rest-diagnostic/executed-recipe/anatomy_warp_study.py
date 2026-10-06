"""Unintegrated anatomical cage study using the official CC0 reference topology.

Landmarks are provisional measured fitting values, not approved new anatomy.
V8 authoring code imports this fitting map; no v8 production binary has been
generated or reviewed yet. Pinned v7 assets do not use this topology.
"""
import numpy as np

SOURCE_SEGMENTS=[
    ((.176,.018,1.353),(.279,.000,1.119)),
    ((.279,.000,1.119),(.373,-.051,.910)),
    ((.373,-.051,.910),(.410,-.105,.797)),
]
TARGET_SEGMENTS=[
    ((.348,.012,1.613),(.509,.008,1.300)),
    ((.509,.008,1.300),(.599,-.019,1.043)),
    ((.599,-.019,1.043),(.620,-.042,.918)),
]

def rotation_between(a,b):
    a=a/np.linalg.norm(a);b=b/np.linalg.norm(b);v=np.cross(a,b);c=float(np.dot(a,b))
    matrix=np.array([[0,-v[2],v[1]],[v[2],0,-v[0]],[-v[1],v[0],0]])
    return np.eye(3)+matrix+matrix@matrix/(1+c)

def warp(vertices):
    points=np.asarray(vertices,dtype=float);side=np.where(points[:,0]>=0,1.,-1.);p=points.copy();p[:,0]=np.abs(p[:,0])
    source_z=[.86,.95,1.05,1.15,1.25,1.34,1.40,1.46]
    body=p.copy();body[:,2]=np.interp(p[:,2],source_z,[.94,1.073,1.20,1.32,1.47,1.62,1.74,1.85])
    body[:,0]*=np.interp(p[:,2],source_z,[1.5,1.75,1.90,2.12,2.14,1.94,1.98,1.9])
    body[:,1]=.018+(p[:,1]+.010)*np.interp(p[:,2],source_z,[1.65,1.73,1.85,1.95,1.90,1.80,1.90,1.95])
    candidates=[];distances=[]
    for i,(source,target) in enumerate(zip(SOURCE_SEGMENTS,TARGET_SEGMENTS)):
        a,b=np.array(source);ta,tb=np.array(target);axis=b-a;t=np.einsum('ij,j->i',p-a,axis)/np.dot(axis,axis)
        # Extrapolate longitudinally past the hand target so the digit lengths remain coherent.
        clipped=np.clip(t,0,1);anchor=a+clipped[:,None]*axis
        distances.append(np.linalg.norm(p-anchor,axis=1))
        radial=p-(a+t[:,None]*axis);rotation=rotation_between(axis,tb-ta)
        thickness=[2.55,2.35,2.60][i]
        radial_target=(radial@rotation.T)*thickness
        # Hand thickness and finger-row width are independent. Uniform radial
        # enlargement made the relaxed human finger spread fan unnaturally wide.
        if i==2:radial_target[:,1]*=.74
        candidates.append(ta+t[:,None]*(tb-ta)+radial_target)
    distance=np.stack(distances,axis=1);weights=1/np.maximum(distance,.015)**6;weights/=weights.sum(axis=1)[:,None]
    arm=np.sum(np.stack(candidates,axis=1)*weights[:,:,None],axis=1)
    # Broader Krag palms/digits retain the narrow attachment at the wrist.
    hand=np.clip((.930-p[:,2])/.050,0,1);hand=hand*hand*(3-2*hand)
    wrist=np.array(TARGET_SEGMENTS[2][0]);arm=wrist+(arm-wrist)*(1+.27*hand[:,None])
    cutoff=.145+.035*np.clip((p[:,2]-1.20)/.15,0,1)
    influence=np.clip((p[:,0]-cutoff)/.065,0,1);influence=influence*influence*(3-2*influence)
    result=body*(1-influence[:,None])+arm*influence[:,None];result[:,0]*=side
    return result
