"""Separate, ungenerated muzzle correction after the actual v5d depth audit.

Preserve v5d eye fitting and lower-neck support. Distances are bounded authoring
proposals, not canonical anatomy or a visual-quality claim.
"""
import numpy as np
from fit_head import gaussian
from fit_head_v5d import fit_head as prior_fit, legacy_face_fit, nose_mask, smooth

def fit_head(source):
    source=np.asarray(source,dtype=np.float64)
    x,y,z=source.T
    fitted=prior_fit(source).copy()
    front=np.clip((-y-.015)/.065,0,1)
    # No change in the existing orbital cage or the actual closed neck ring.
    support=front*smooth(.180,.202,z)*(1-smooth(.282,.296,z))
    # v5d's lip leads its nose by 9.51 mm in the evaluated saved mesh. Recess
    # that central shelf while giving the complete alar/pad volume the lead.
    lip=gaussian(x,0,.047)*gaussian(z,.232,.020)*support
    nose=gaussian(x,0,.031)*gaussian(z,.270,.020)*support
    fitted[:,1]+=.011*lip
    fitted[:,1]-=.0075*nose
    # Two overlapping smooth volumes in the existing continuous upper lip,
    # rather than a translated flat muzzle shelf or added detached primitives.
    pads=gaussian(abs(x),.019,.013)*gaussian(z,.252,.014)*support
    fitted[:,1]-=.0045*pads
    philtrum=gaussian(x,0,.007)*gaussian(z,.251,.011)*support
    fitted[:,1]+=.0012*philtrum
    # Restore a rounded lower-lip/chin contour after retracting the lip peak.
    # The old broad underside faced almost straight down (Nz=-.944 at center).
    chin=gaussian(x,0,.033)*gaussian(z,.205,.016)*support
    fitted[:,1]-=.0055*chin
    # Both sides of the closed seam receive the same curved crease field.
    crease=gaussian(abs(x),.031,.018)*gaussian(z,.233,.012)*support
    fitted[:,2]+=.0018*crease
    return fitted

def oral_translation():
    # Existing interiors and Jaw/Tongue/lip pivots start at the repaired v4b
    # baseline. Refit coherently from that same old seam, not from v5d twice.
    point=np.asarray([[0.,-.140,.232]])
    return fit_head(point)[0]-legacy_face_fit(point)[0]

def shape_receipt(source):
    source=np.asarray(source,dtype=np.float64);x,y,z=source.T
    old=prior_fit(source);new=fit_head(source);delta=new-old
    masks={'muzzle':(abs(x)<.05)&(z>.205)&(z<.275)&(y<-.08),
           'nasalPad':(abs(x)<.032)&(z>.25)&(z<.29)&(y<-.13),
           'orbital':(abs(x)>.01)&(abs(x)<.065)&(z>=.296)&(z<.335)&(y<-.08),
           'lowerNeck':z<=.180}
    regions={}
    for name,mask in masks.items():
        if not np.any(mask):raise RuntimeError('Missing correction region '+name)
        regions[name]={'vertices':int(mask.sum()),'priorMin':old[mask].min(0).tolist(),
                       'priorMax':old[mask].max(0).tolist(),'proposedMin':new[mask].min(0).tolist(),
                       'proposedMax':new[mask].max(0).tolist(),
                       'maximumDisplacementMeters':float(np.linalg.norm(delta[mask],axis=1).max())}
    for name in ['orbital','lowerNeck']:
        if regions[name]['maximumDisplacementMeters']!=0:
            raise RuntimeError('v5e changed protected '+name+' fit')
    return {'status':'Ungenerated v5e shape proposal; actual saved and posed review required',
            'regions':regions,'oralTranslationMeters':oral_translation().tolist(),
            'diagnosis':'Actual v5d lip leads nose by 9.51 mm; frontal dark jaw/neck hits are FacialSkin with strongly downward normals',
            'change':'Recess central lip shelf, lead with whole nasal pad, paired continuous upper-muzzle pads and curved crease; retain exact orbital and lower-neck fit',
            'materialChange':False,'newDetachedMuzzleMeshes':False}
