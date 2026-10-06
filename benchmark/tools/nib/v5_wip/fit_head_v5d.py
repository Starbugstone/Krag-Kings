"""Bounded, ungenerated v5d shape correction after actual v5c depth review.

The legacy fit remains unchanged for provenance. All distances below are
authoring proposals, not new canonical anatomy. Native/posed review is pending.
"""
import numpy as np
from fit_head import fit_head as legacy_fit, gaussian

def smooth(a,b,value):
    t=np.clip((value-a)/(b-a),0,1)
    return t*t*(3-2*t)

def legacy_face_fit(source):
    fitted=legacy_fit(source).copy();x,y,z=source.T
    front=np.clip((-y-.015)/.05,0,1)
    chin=np.exp(-((z-.184)/.026)**2)*front
    fitted[:,0]*=1-.10*chin;fitted[:,1]+=.004*chin
    nose=np.exp(-(x/.025)**4-((z-.263)/.017)**4)*front
    fitted[:,0]*=1-.13*nose*np.clip((.266-z)/.015,0,1)
    return fitted

def fit_head(source):
    source=np.asarray(source,dtype=np.float64);x,y,z=source.T
    fitted=legacy_fit(source).copy()
    front=np.clip((-y-.005)/.065,0,1)
    # Remove the previous strong central narrowing. The alar loops, pad and
    # nostril topology widen together; this is not a separate nose primitive.
    nose=gaussian(x,0,.030)*gaussian(z,.267,.025)*front
    fitted[:,0]*=(1+.10*nose)/(1-.34*nose)
    fitted[:,0]*=1-.20*nose*np.clip((.268-z)/.017,0,1)
    # Bring upper lip and muzzle shelf toward the existing pad, reducing the
    # tall vertical philtrum seen in the saved profile. Slightly retract the
    # human tip so pad and muzzle read as one short projecting volume.
    muzzle=gaussian(x,0,.055)*gaussian(z,.237,.036)*front
    fitted[:,1]-=.017*muzzle
    fitted[:,1]+=.010*nose
    fitted[:,2]+=.007*muzzle
    chin=gaussian(x,0,.050)*gaussian(z,.188,.026)*front
    fitted[:,2]+=.016*chin
    fitted[:,1]+=.004*chin
    fitted[:,0]*=1-.07*chin
    # Undo the 0.22 secondary vertical compression and add a restrained 0.16
    # opening field. Apply it to the entire ocular assembly, including globes.
    eyes=gaussian(abs(x),.035876,.026)*gaussian(z,.310037,.022)*front
    fitted[:,2]+=(z-.310037)*.38*eyes
    return fitted

def nose_mask(source):
    x,y,z=np.asarray(source).T
    # Broad upper pad, tapered lower edge: preserve the actual alar relief and
    # nostrils, instead of a small grey human tip with a painted dot.
    width=.029-.010*np.clip((.268-z)/.016,0,1)
    pad=np.exp(-(abs(x)/width)**6-((z-.267)/.017)**6)
    return pad*smooth(.132,.150,-y)

def oral_translation():
    # Same representative seam landmark in the old/new continuous fit.
    # Translate teeth, gums, cavity, tongue and their deforming pivots together.
    point=np.asarray([[0.,-.140,.232]])
    return fit_head(point)[0]-legacy_face_fit(point)[0]

def neck_blend(source):
    x,y,z=np.asarray(source).T
    result=(1-smooth(.168,.235,z))*smooth(-.080,-.045,y)
    result[z<=.166002]=1
    return result

def shape_receipt(source):
    old=legacy_face_fit(source);new=fit_head(source);delta=new-old
    x,y,z=np.asarray(source).T
    regions={'muzzle':(abs(x)<.05)&(z>.205)&(z<.275)&(y<-.08),
             'nasalPad':(abs(x)<.032)&(z>.25)&(z<.29)&(y<-.13),
             'orbital':(abs(x)>.01)&(abs(x)<.065)&(z>.29)&(z<.335)&(y<-.08)}
    result={}
    for name,mask in regions.items():
        if not np.any(mask):raise RuntimeError('Missing source shape region '+name)
        result[name]={'vertices':int(mask.sum()),'oldMin':old[mask].min(0).tolist(),
                      'oldMax':old[mask].max(0).tolist(),'proposedMin':new[mask].min(0).tolist(),
                      'proposedMax':new[mask].max(0).tolist(),
                      'maximumDisplacementMeters':float(np.linalg.norm(delta[mask],axis=1).max())}
    return {'status':'Ungenerated shape proposal until saved native/pose review',
            'regions':result,'oralTranslationMeters':oral_translation().tolist(),
            'eyeVerticalField':'Cancel legacy -0.22; add +0.16 about same source eye centers',
            'noseWidthField':'Replace legacy 1-0.34*weight with 1+0.10*weight; taper lower pad by up to20% of its local weight'}
