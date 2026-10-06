"""Prepared attachment of new groom to the reviewed rooted ear rig.

Retain the same geometric Head/Ear/EarTip field as the actual ear study, so
cards and opaque fibers cannot revert the auricle to rigid single-bone acting.
"""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'motion_wip'))
from ear_motion import weights as ear_weights


def bind(obj,rig):
    tag=obj.get('bone','')
    if tag not in ['Ear_L','Ear_R']:return None
    names=['Head',tag,'EarTip_'+tag[-1]]
    if any(name not in rig.data.bones for name in names):
        raise RuntimeError('New ear groom requires reviewed Head/Ear/EarTip skeleton')
    old={group.index:group.name for group in obj.vertex_groups}
    if any(old[g.group]!=tag or abs(g.weight-1)>1e-7 for v in obj.data.vertices for g in v.groups):
        raise RuntimeError('Unexpected initial ear groom binding: '+obj.name)
    transform=rig.matrix_world.inverted()@obj.matrix_world
    points=np.asarray([tuple(transform@v.co) for v in obj.data.vertices],dtype=np.float64)
    field=ear_weights(points)
    obj.vertex_groups.clear();groups=[obj.vertex_groups.new(name=name) for name in names]
    for i,row in enumerate(field):
        for group,value in zip(groups,row):
            if value>1e-8:group.add([i],float(value),'REPLACE')
    obj['ear_groom_binding']='Continuous Head/base/distal cartilage field; same authored source as ear-motion study'
    return {'component':obj.name,'bones':names,'maximumInfluences':int(np.count_nonzero(field>1e-8,axis=1).max()),
        'meanHeadBaseTipWeight':field.mean(axis=0).tolist(),
        'actualTwitchPoseReviewRequired':True}
