"""Provisional hidden organic anatomy fit; pure arrays, no Blender or file writes.

Lower-body source landmarks were measured from the retained CC0 cage. Foot and
hip anatomy is a review proposal; the concepts show these regions clothed.
Existing runtime ankle-control markers are retained for the first pose study.
"""
import numpy as np
from anatomy_warp_study import warp as upper_warp

SOURCE_ANCHORS={
 'hip':(.100,-.012,.780),
 'knee':(.137,.020,.435),
 'ankleShaft':(.171,.057,.135),
 'forefoot':(.239,-.145,.020),
}
TARGET_ANCHORS={
 'hip':(.167,.019,1.018),
 'knee':(.188,-.016,.570),
 'ankleControl':(.190,.026,.240),
 'forefoot':(.190,-.205,.065),
}

def smooth(value):
    value=np.clip(value,0,1)
    return value*value*(3-2*value)


def fit(points):
    p=np.asarray(points,dtype=float)
    upper=upper_warp(p)
    sign=np.where(p[:,0]<0,-1.,1.)
    x=np.abs(p[:,0]);y=p[:,1];z=p[:,2]
    # Keep the connected source pelvis/legs/toes. A monotone height map retains
    # the plantar surface and raises the ankle shaft inside the existing boots.
    height=np.interp(z,[-.00554783,.020,.070,.100,.135,.270,.435,.780,.950,1.020],
                       [.005,.030,.085,.145,.240,.385,.570,1.018,1.073,1.164])
    source_x=np.interp(z,[.0,.135,.435,.780,.950],[.171,.171,.137,.100,.103])
    source_y=np.interp(z,[.0,.135,.435,.780,.950],[.057,.057,.020,-.012,-.010])
    target_x=np.interp(z,[.0,.135,.435,.780,.950],[.190,.190,.188,.167,.181])
    target_y=np.interp(z,[.0,.135,.435,.780,.950],[.026,.026,-.016,.019,.018])
    thickness=np.interp(z,[.0,.135,.270,.435,.630,.780,.950],[1.60,1.58,1.72,1.73,1.95,1.93,1.75])
    dx=x-source_x;dy=y-source_y
    # The library feet point outward. Turn the complete foot surface into the
    # existing forward-facing boot footprint while leaving the calf axis intact.
    foot=smooth((.165-z)/.065)
    theta=-.326*foot
    local_x=dx*np.cos(theta)-dy*np.sin(theta)
    local_y=dx*np.sin(theta)+dy*np.cos(theta)
    foot_length_scale=np.interp(z,[0,.10,.17],[1.27,1.40,1.72])
    leg_x=target_x+local_x*thickness
    leg_y=target_y+local_y*(foot_length_scale*foot+thickness*(1-foot))
    # The shared groin stays on the midline, instead of reflecting a fitted
    # positive-leg point through the opposite thigh.
    leg_amount=smooth(x/.075)*smooth((.970-z)/.200)
    pelvis_x=x*np.interp(z,[.780,.950,1.020],[1.68,1.75,1.855])
    pelvis_y=.018+(y+.010)*np.interp(z,[.780,.950,1.020],[1.65,1.73,1.81])
    lower=np.column_stack(((pelvis_x*(1-leg_amount)+leg_x*leg_amount)*sign,
                           pelvis_y*(1-leg_amount)+leg_y*leg_amount,height))
    amount=smooth((1.020-z)/.160)
    # Relaxed hands occupy the same height band as the hips in the source cage.
    # Retain their established anatomical fit rather than treating them as legs.
    arm=(x>.240)&(z>.650)
    amount[arm]=0
    return upper*(1-amount[:,None])+lower*amount[:,None]


def lower_weights(point):
    """Normalized smooth pelvic, knee, ankle and forefoot fields in rig metres."""
    def s(a,b,t):return float(smooth((t-a)/(b-a)))
    x,y,z=point
    side='L' if x>=0 else 'R'
    left=s(-.065,.065,x)
    hip=s(.930,1.110,z)
    thigh=s(.505,.635,z)
    shin=s(.190,.290,z)
    toe=(1-s(-.185,-.130,y))*(1-s(.090,.170,z))
    leg={f'Thigh_{side}':thigh,
         f'Shin_{side}':(1-thigh)*shin,
         f'Foot_{side}':(1-thigh)*(1-shin)*(1-toe),
         f'Toe_{side}':(1-thigh)*(1-shin)*toe}
    # Smoothly share medial upper-thigh/groin skin between both hips.
    if z>.82:
        value=leg.pop(f'Thigh_{side}')
        leg['Thigh_L']=value*left;leg['Thigh_R']=value*(1-left)
    result={name:value*(1-hip) for name,value in leg.items()}
    result['Pelvis']=hip
    result={name:value for name,value in result.items() if value>1e-8}
    total=sum(result.values())
    return [(name,value/total) for name,value in result.items()]
