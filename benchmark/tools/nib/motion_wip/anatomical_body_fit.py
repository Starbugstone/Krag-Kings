"""Provisional continuous Nib torso/arm fit on the licensed CC0 body cage.

This changes construction, not fixed joint positions. It deliberately excludes
the human head/hands/legs. Fitting dimensions require actual reference review.
"""
import numpy as np
from forearm_twist import smooth,twist_weights

SOURCE_SEGMENTS=np.asarray([[(.176,.018,1.353),(.279,0,1.119)],
                            [(.279,0,1.119),(.373,-.051,.910)]])
TARGET_SEGMENTS=np.asarray([[ (.128,.005,.938),(.189,-.003,.769)],
                            [(.189,-.003,.769),(.218,-.031,.614)]])


def rotation_between(a,b):
    a=a/np.linalg.norm(a);b=b/np.linalg.norm(b);v=np.cross(a,b);c=float(a@b)
    if c<-.999:raise RuntimeError('Unexpected reversed anatomical segment')
    k=np.asarray([[0,-v[2],v[1]],[v[2],0,-v[0]],[-v[1],v[0],0]])
    return np.eye(3)+k+k@k/(1+c)


def crop(points,polygons):
    """Covered waist and wrists end inside existing garment/hand coverage."""
    raw=np.asarray(points,dtype=np.float64)
    keep=(raw[:,2]<1.460)&((raw[:,2]>.945)|((abs(raw[:,0])>.240)&(raw[:,2]>.920)))
    faces=[list(map(int,face)) for face in polygons if all(keep[int(i)] for i in face)]
    used=np.asarray(sorted({i for face in faces for i in face}),dtype=np.int32)
    lookup={old:i for i,old in enumerate(used)}
    return used,[[lookup[i] for i in face] for face in faces]


def warp(points):
    raw=np.asarray(points,dtype=np.float64);p=raw.copy();sign=np.where(p[:,0]>=0,1.,-1.);p[:,0]=abs(p[:,0])
    z=[.90,.945,1.05,1.15,1.25,1.353,1.40,1.46]
    body=p.copy()
    body[:,2]=np.interp(p[:,2],z,[.635,.663,.731,.807,.882,.938,.990,1.048])
    body[:,0]*=np.interp(p[:,2],z,[.56,.56,.59,.64,.70,.73,.72,.65])
    body[:,1]=.008+(p[:,1]+.010)*np.interp(p[:,2],z,[.58,.59,.59,.60,.62,.62,.59,.56])
    candidates=[];distances=[]
    for index,(source,target) in enumerate(zip(SOURCE_SEGMENTS,TARGET_SEGMENTS)):
        a,b=source;ta,tb=target;axis=b-a;t=(p-a)@axis/(axis@axis)
        projected=a+t[:,None]*axis;closest=a+np.clip(t,0,1)[:,None]*axis
        distances.append(np.linalg.norm(p-closest,axis=1))
        radial=(p-projected)@rotation_between(axis,tb-ta).T
        # Lean exposed anatomy; fixed Nib joints remain the fitting anchors.
        scale=.69 if index==0 else .64
        candidates.append(ta+t[:,None]*(tb-ta)+radial*scale)
    weights=1/np.maximum(np.stack(distances,axis=1),.018)**4
    weights/=weights.sum(axis=1)[:,None]
    arms=np.sum(np.stack(candidates,axis=1)*weights[:,:,None],axis=1)
    threshold=.120+.035*np.clip((p[:,2]-1.20)/.16,0,1)
    blend=smooth(threshold,threshold+.09,p[:,0])
    result=body*(1-blend[:,None])+arms*blend[:,None];result[:,0]*=sign
    if not np.isfinite(result).all():raise RuntimeError('Nonfinite anatomical fit')
    return result


def weights(points,arm_domain,bones):
    """Source-topology shoulder domain and chain-relative elbow/twist field."""
    p=np.asarray(points,dtype=np.float64);domain=np.clip(arm_domain,0,1)
    result={name:np.zeros(len(p)) for name in ['Spine','Chest','Neck']+
            [prefix+'_'+side for side in ['L','R'] for prefix in ['Clavicle','UpperArm','LowerArm','ForearmTwist','Hand']]}
    chest=smooth(.76,.89,p[:,2]);neck=smooth(.965,1.035,p[:,2])*(1-smooth(.045,.090,abs(p[:,0])))
    result['Spine']=(1-domain)*(1-neck)*(1-chest)
    result['Chest']=(1-domain)*(1-neck)*chest
    result['Neck']=(1-domain)*neck
    for side,sign in [('L',1),('R',-1)]:
        shoulder,elbow=np.asarray(bones['UpperArm_'+side]);_,wrist=np.asarray(bones['LowerArm_'+side])
        # Signed bisector coordinate prevents elbow support from depending on
        # scene Z; support remains continuous through the flexion crease.
        bisector=(wrist-shoulder);bisector/=np.linalg.norm(bisector)
        distal=smooth(-.018,.026,(p-elbow)@bisector)
        upper_axis=elbow-shoulder;upper_axis/=np.linalg.norm(upper_axis)
        collar=(1-smooth(-.012,.050,(p-shoulder)@upper_axis))*.55
        fraction=domain*(p[:,0]*sign>=0)
        result['Clavicle_'+side]=fraction*(1-distal)*collar
        result['UpperArm_'+side]=fraction*(1-distal)*(1-collar)
        twist=twist_weights(p,elbow,wrist)
        for i,name in enumerate(['LowerArm_','ForearmTwist_','Hand_']):
            result[name+side]=fraction*distal*twist[:,i]
    array=np.stack(list(result.values()),axis=1)
    if array.min()<-1e-12 or np.max(abs(array.sum(axis=1)-1))>1e-7:
        raise RuntimeError('Anatomical weights are not normalized')
    if np.max(np.count_nonzero(array>1e-7,axis=1))>8:raise RuntimeError('Too many skin influences')
    return result
