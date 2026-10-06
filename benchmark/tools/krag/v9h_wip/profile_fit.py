"""Prepared bounded profile correction after actual v9g side-view rejection.

Works on the common continuous source fit for skin, ocular/oral meshes, pivots
and expressions. Removes the old narrow projecting brow/chin peaks first;
coefficients are provisional sculpt values, not an accepted facial design.
"""
import numpy as np


def refine(raw,base_fitted):
    raw=np.asarray(raw,dtype=float);out=np.asarray(base_fitted,dtype=float).copy()
    x,y,z=raw.T;front=np.clip((-y-.005)/.065,0,1)
    g=lambda a,c,w:np.exp(-((a-c)/w)**2)
    # Remove the exact old forward displacement terms that produced the
    # beaked brow and isolated chin wedge in the actual side render.
    mouth=g(x,0,.060)*g(z,.232,.030)*front
    chin=g(x,0,.066)*g(z,.183,.026)*front
    upper=g(x,0,.066)*g(z,.255,.020)*front
    lower=g(x,0,.045)*g(z,.224,.010)*front
    brow=g(abs(x),.036,.021)*g(z,.321+.43*abs(x),.010)*front
    zygoma=g(abs(x),.058,.023)*g(z,.291,.019)*front
    out[:,1]+=.064*mouth+.112*chin+.038*upper+.007*lower
    out[:,1]+=(.058+.003*np.tanh(x/.012))*brow+.030*zygoma
    # Broad connected mandibular volume; the chin remains inside the muzzle
    # depth envelope instead of peaking below a deeply recessed lower lip.
    jaw=np.exp(-(x/.064)**4)*g(z,.199,.046)*front
    muzzle=np.exp(-(x/.043)**4)*g(z,.237,.034)*front
    upper_muzzle=np.exp(-(x/.043)**4)*g(z,.258,.024)*front
    out[:,1]-=.051*jaw+.040*muzzle+.023*upper_muzzle
    # A thicker hood follows the orbital arch. Reducing the forward peak and
    # widening its vertical support prevents a sharp isolated brow shelf.
    hood=g(abs(x),.035,.024)*g(z,.330+.27*abs(x),.019)*front
    out[:,1]-=(.028+.0015*np.tanh(x/.012))*hood
    bridge=g(x,0,.016)*g(z,.320,.023)*front
    out[:,1]-=.009*bridge
    out[:,1]-=.016*g(abs(x),.058,.022)*g(z,.289,.024)*front
    # Bounded cheek plane inset, with the actual oral width informing the
    # nasolabial fold location (the rim ends at |source X|~.02427m).
    t=np.clip((.273-z)/.045,0,1);fold_x=.020+.010*t
    crease=g(abs(x),fold_x,.0034)*g(z,.252,.026)*front
    out[:,1]+=.0065*crease
    mask=.35*g(abs(x),.064,.020)*g(z,.248,.032)*front
    plane=-.122-.24*(z-.24)+.36*(abs(x)-.055)
    out[:,1]+=np.clip(plane-out[:,1],-.022,.022)*mask
    # Distinct vertical glabellar creases shape the heavy paired frown. These
    # are geometric folds above the lid margin, not uniform surface noise.
    for sign in [-1,1]:
        line=sign*(.010+.045*(z-.34))
        out[:,1]+=.0038*g(x,line,.0023)*g(z,.350,.023)*front
    return out


def tusk_specification(fit):
    """Roots on the authored lower-gum centerline; crown through true aperture.

    Source-domain gum formula is identical to krag_head_v9.interior. The tip
    remains provisional until actual closed/open contact and profile review.
    """
    result=[]
    for side in [-1,1]:
        x=side*.0215;gum_y=-.101+.014*(abs(x)/.038)**2
        raw=np.asarray([(x,gum_y,.217),(side*.022,-.139,.234),(side*.020,-.144,.251)])
        result.append({'side':side,'points':fit(raw).tolist(),'radii':[.0095,.0070,.0005],
                       'sourcePoints':raw.tolist(),'root':'Lower provisional gum centerline; Jaw-bound'})
    return result
