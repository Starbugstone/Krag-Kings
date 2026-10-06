"""Prepared post-v9f sculpt study; intentionally not imported by frozen recipe.

Refines the same continuous face topology. This must be evaluated on all head,
ocular, oral and facial-control points through the common fit, never on skin
alone. Coefficients are provisional reference-refinement values, not canon.
Actual v9f neutral/profile/expression review must precede enabling this study.
"""
import numpy as np

def refine(raw,base_fitted):
    raw=np.asarray(raw,dtype=float);result=np.asarray(base_fitted,dtype=float).copy()
    x,y,z=raw.T;front=np.clip((-y-.035)/.06,0,1)
    g=lambda a,c,w:np.exp(-((a-c)/w)**2)
    # More substantial paired brow pads and a connecting bony nasal bridge.
    # The central bridge is narrow; no single horizontal shelf spans both eyes.
    paired=np.exp(-((np.abs(x)-.034)/.021)**4)*g(z,.333+.25*np.abs(x),.011)
    paired*=np.clip((np.abs(x)-.009)/.012,0,1)
    bridge=g(x,0,.019)*g(z,.299,.024)
    result[:,1]-=(.010*paired+.014*bridge)*front
    # A broad projecting muzzle is divided from flatter lateral cheek planes
    # by an actual fold, rather than a more prominent lip-shaped cushion.
    t=np.clip((.272-z)/.040,0,1);fold_x=.026+.018*t
    extent=g(z,.251,.025)
    crease=g(np.abs(x),fold_x,.0040)*extent
    muzzle=g(np.abs(x),fold_x-.008,.0090)*extent
    cheek=g(np.abs(x),.064,.017)*g(z,.246,.031)
    result[:,1]+=(.0080*crease-.0130*muzzle+.0040*cheek)*front
    # Wide lower jaw remains one connected volume. Reduce the isolated lower
    # lip's projection while bringing the broad mandibular/chin plane forward.
    chin=np.exp(-(x/.060)**4)*g(z,.183,.025)
    lower_lip=g(x,0,.045)*g(z,.224,.010)
    result[:,1]+=(.006*lower_lip-.024*chin)*front
    return result

def tusk_specification(fit):
    """Proposed visible ivory height restored toward the original front sheet.

    The old .034m pre-transform tusk is mostly hidden below the upper lip; this
    returns a longer curved tooth rather than enlarging a disconnected cone.
    Actual closed/open-mouth contact still needs review.
    """
    specs=[]
    for side in [-1,1]:
        anchor=fit([(side*.036,-.122,.228)])[0]
        path=[anchor,anchor+np.asarray((side*.001,-.018,.029)),anchor+np.asarray((-side*.004,-.022,.058))]
        specs.append({'side':side,'points':np.asarray(path).tolist(),'radii':[.0105,.006,.0005]})
    return specs
