"""Measured whole-head proportion proposal, separate from the v9e sculpt.

The concept's manually measured head/outer-shoulder ratio is about .239,
versus about .306 in the matched v9c view. This preserves facial relationships
by applying one 0.77 scale to the complete assembly, anchored near the chin.
Only the lower neck blends back to the unchanged body. Actual views required.
"""
import numpy as np

SCALE=.77
ANCHOR=np.asarray((0.,.014,1.770))

def transform(points):
    p=np.asarray(points,dtype=float)
    t=np.clip((p[...,2]-1.670)/.105,0,1)
    t=t*t*(3-2*t)
    return p+(SCALE-1)*(p-ANCHOR)*t[...,None]

def point(p):
    return tuple(transform(np.asarray(p)))

def specification():
    return {'status':'Provisional measured whole-head correction; actual neutral/expression review required',
        'scale':SCALE,'anchorMeters':ANCHOR.tolist(),'lowerNeckBlendZ':[1.670,1.775],
        'expectedCrownMeters':point((0,0,2.107))[2],
        'referenceMeasurements':'benchmark/art/krag/anatomy-study/front-proportion-landmarks-v9c.json',
        'appliesTo':['skull/face','eyes','oral meshes and tusks','facial/jaw/eye rest pivots','neck transition'],
        'separateFromSculpt':True}
