"""Prepared ear-region guide proposal; never executed or a reviewed source.

Apply only after the adult face and same-geometry alpha comparison. Existing
head guides, outer nap, material names and central visible skin are preserved.
Dimensions/counts are provisional fitting values, not new design canon.
"""
import math, random, sys
from pathlib import Path
from mathutils import Vector
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE.parent/'v6_groom_wip'),str(HERE.parent/'v5_wip')]
from guide_recipe import SurfaceSampler,ear_selector
from nib_groom_v5 import ear_coordinates,EAR_CENTERS,EAR_WIDTHS

COUNTS={'outer_rim':240,'inner_wisps':280}

def ear_frame(point,side):
    along,u=ear_coordinates(point)
    interval=min(4,max(0,int(along*5)));fraction=along*5-interval
    a=Vector(EAR_CENTERS[interval]);b=Vector(EAR_CENTERS[interval+1])
    direction=(b-a).normalized()
    axis=Vector((side*direction.x,0,direction.y))
    across=Vector((side*direction.y,0,-direction.x))
    width=EAR_WIDTHS[interval]*(1-fraction)+EAR_WIDTHS[interval+1]*fraction
    return along,u,axis,across,max(width,.001)

def curved_guide(region,root,normal,source,seed,side):
    rng=random.Random(seed);along,u,axis,across,width=ear_frame(root,side)
    if region=='inner_wisps':
        # Upper rim follows toward the point; lower rim turns partly back toward
        # the root. Both sweep inward in actual ear coordinates. The old single
        # projected diagonal made separated, nearly parallel comb blades.
        inward=-math.copysign(1,u)*across
        axial=(.18+.24*rng.random()) if u<0 else (-.12+.38*rng.random())
        desired=inward*(.70+.22*rng.random())+axis*axial
        length=rng.uniform(.022,.047)
        if along<.26 and abs(u)<.48:
            desired=axis*.82+inward*.25;length=rng.uniform(.028,.042)
        # Preserve central pink membrane: the endpoint's cross-ear excursion
        # stops short of the central fifth where the current width permits it.
        inward_budget=max(.009,(abs(u)-.20)*width)
        projected=max(.15,abs(desired.normalized().dot(across)))
        length=min(length,inward_budget/projected)
        lift=rng.uniform(.005,.012)
    else:
        desired=axis+across*math.copysign(rng.uniform(.05,.20),u)
        length=rng.uniform(.016,.032);lift=rng.uniform(.003,.007)
    tangent=desired-normal*desired.dot(normal)
    if tangent.length<1e-6:raise RuntimeError('Regional ear flow is normal to support')
    tangent.normalize()
    # Smooth, unequal side curl produces a layered lock without a rigid fan.
    curl=normal.cross(tangent).normalized()*rng.uniform(-.004,.004)
    start=root+normal*.00025
    middle=start+tangent*(length*rng.uniform(.43,.57))+normal*lift+curl
    tip=start+tangent*length+normal*rng.uniform(.0004,.0020)-curl*.35
    return {'region':region,'root':list(start),'normal':list(normal),'middle':list(middle),'tip':list(tip),
        'halfWidthMeters':rng.uniform(.0011,.00175),'seed':seed,'sourceHint':list(source),
        'shortNap':False,'regionalProposal':'Actual anatomical-axis inward flow, membrane-bounded tip, unequal side curl'}

def replacement_ear_groups(collection):
    """Only new provisional guide data. Caller must emit/fit/check actual meshes."""
    groups=[];seed=975100
    for side,sign in [('L',1),('R',-1)]:
        ear=next(o for o in collection.objects if o.name.startswith('Fennec cupped ear ') and o.get('bone')=='Ear_'+side)
        for region,count in COUNTS.items():
            strata=[('whole',count,lambda p:True)]
            if region=='inner_wisps':
                strata=[('outer_inward_rim',180,lambda p:abs(ear_coordinates(p)[1])>=.62),
                        ('inner_inward_rim',70,lambda p:.48<=abs(ear_coordinates(p)[1])<.62),
                        ('basal_tufts',30,lambda p:abs(ear_coordinates(p)[1])<.48)]
            roots=[];stratum_reports=[]
            for stratum_index,(label,amount,selector) in enumerate(strata):
                sampler=SurfaceSampler(ear,lambda p,n,s:ear_selector(region,p,n,s) and selector(p))
                spacing=min(.0022,math.sqrt(sampler.total/amount)*.48)
                samples,part=sampler.roots(amount,seed+stratum_index*173,spacing)
                roots.extend(samples);stratum_reports.append({'label':label,**part,'guides':amount})
            audit={'strata':stratum_reports,'areaMetersSquared':sum(p['areaMetersSquared'] for p in stratum_reports)}
            guides=[curved_guide(region,*sample,seed+i,sign) for i,sample in enumerate(roots)]
            audit.update({'status':'Prepared only; no rendered coverage claim','requestedGuides':count,'requiresSameSideRootAttachment':True})
            groups.append({'region':region+'_'+side,'bone':'Ear_'+side,
                'materialRegion':'innerWisps' if region=='inner_wisps' else 'outerEar',
                'guides':guides,'sampling':audit})
            seed+=1000
    return groups
