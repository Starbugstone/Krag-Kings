"""Ungenerated concept-region fur layers on the actual saved head/ear skin."""
import math, random, sys
from pathlib import Path
from importlib.util import spec_from_file_location, module_from_spec
from mathutils import Vector
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'v5_wip'))
from nib_groom_v5 import ear_coordinates, EAR_CENTERS, EAR_WIDTHS, avoid_goggles, configure_goggle_envelopes
spec=spec_from_file_location('nib_surface_prior_guides',HERE.parent/'v6_groom_wip/guide_recipe.py')
prior=module_from_spec(spec);spec.loader.exec_module(prior)
SurfaceSampler=prior.SurfaceSampler

HEAD_COUNTS={'undercoat':420,'crown':320,'fringe':170,'temple_L':150,'temple_R':150,'nape':240}


def head_selector(region,p,n,s):
    if region=='undercoat':
        return any(prior.head_selector(r,p,n,s) for r in HEAD_COUNTS if r!='undercoat')
    return prior.head_selector(region,p,n,s)


def ear_frame(p,side):
    t,u=ear_coordinates(p);i=min(4,max(0,int(t*5)));f=t*5-i
    direction=(Vector(EAR_CENTERS[i+1])-Vector(EAR_CENTERS[i])).normalized()
    axis=Vector((side*direction.x,0,direction.y));across=Vector((side*direction.y,0,-direction.x))
    return t,u,axis,across,EAR_WIDTHS[i]*(1-f)+EAR_WIDTHS[i+1]*f


def make(region,root,normal,source,seed,side=1):
    rng=random.Random(seed);ear=region.startswith('ear_');under=region in ['undercoat','ear_undercoat','ear_exterior']
    if ear:
        along,u,axis,across,width=ear_frame(root,side)
        inward=-math.copysign(1,u)*across
        if region=='ear_exterior':
            direction=axis+across*rng.uniform(-.18,.18);length=rng.uniform(.009,.019);lift=rng.uniform(.001,.0028)
        elif region=='ear_undercoat':
            direction=axis*.50+inward*.70;length=rng.uniform(.012,.025);lift=rng.uniform(.0015,.004)
        else:
            direction=inward*.82+axis*(.34 if u<0 else -.22)+Vector((0,0,-.08))
            length=rng.uniform(.030,.057);lift=rng.uniform(.006,.014)
            # The lower basal fringe follows upward before turning inward.
            if along<.26:direction=axis*.78+inward*.43;length=rng.uniform(.033,.051)
            if along>.28:
                budget=max(.012,(abs(u)-.09)*width)
                length=min(length,budget/max(.25,abs(direction.normalized().dot(across))))
        half=rng.uniform(.0030,.0048) if region=='ear_locks' else rng.uniform(.0028,.0044)
    else:
        side=1 if root.x>=0 else -1
        if region=='crown':direction=Vector((-.32+root.x*4,-.58,.08));length=rng.uniform(.029,.052);lift=rng.uniform(.010,.020)
        elif region=='fringe':direction=Vector((side*.70,-.18,-.42));length=rng.uniform(.027,.043);lift=rng.uniform(.006,.011)
        elif region.startswith('temple'):direction=Vector((side*.38,.21,-.78));length=rng.uniform(.034,.057);lift=rng.uniform(.006,.013)
        elif region=='nape':direction=Vector((root.x*2,.25,-.96));length=rng.uniform(.032,.058);lift=rng.uniform(.006,.012)
        else:direction=Vector((side*.22,-.12,-.65 if source.z<.35 else .12));length=rng.uniform(.009,.018);lift=rng.uniform(.001,.003)
        half=rng.uniform(.0032,.0048) if not under else rng.uniform(.0034,.0052)
    direction-=normal*direction.dot(normal)
    if direction.length<1e-5:direction=normal.cross(Vector((1,0,0)))
    direction.normalize();lateral=normal.cross(direction).normalized();curl=lateral*rng.uniform(-.005,.005)
    start=root+normal*.00015
    middle=start+direction*length*rng.uniform(.38,.58)+normal*lift+curl
    tip=start+direction*length+normal*rng.uniform(.0005,.003)-curl*rng.uniform(.2,.6)
    if not ear:middle=avoid_goggles(middle);tip=avoid_goggles(tip)
    return {'region':region,'root':list(start),'normal':list(normal),'middle':list(middle),'tip':list(tip),
            'halfWidthMeters':half,'seed':seed,'sourceHint':list(source),'undercoat':under,
            'tile':12+seed%4 if under else seed%12,'rollRadians':rng.uniform(-.40,.40),
            'widthEndFraction':rng.uniform(.60,.82)}


def build(head,collection):
    configure_goggle_envelopes(collection);groups=[];seed=1150200
    for region,count in HEAD_COUNTS.items():
        def select(p,n,s):
            if not head_selector(region,p,n,s):return False
            if region in ['fringe','undercoat'] and abs(s.x)<.018 and s.z<.353:return False
            return (avoid_goggles(p)-p).length<.00005
        sampler=SurfaceSampler(head,select);spacing=min(.0015,math.sqrt(sampler.total/count)*.36)
        roots,audit=sampler.roots(count,seed,spacing)
        groups.append({'region':region,'bone':'Head','materialRegion':'head','guides':[make(region,*v,seed+i)for i,v in enumerate(roots)],'sampling':audit})
        seed+=3000
    for side,sign in [('L',1),('R',-1)]:
        ear=next(o for o in collection.objects if o.name.startswith('Fennec cupped ear ')and o.get('bone')=='Ear_'+side)
        for region in ['ear_exterior','ear_undercoat','ear_locks']:
            def select(p,n,s):
                t,u=ear_coordinates(p)
                if not .045<t<.982:return False
                if region=='ear_exterior':return n.y>.12
                if n.y>-.15:return False
                if region=='ear_undercoat':return abs(u)>.53 or t<.24
                return (.60<abs(u)<.96 and t<.90)or(t<.25 and abs(u)<.55)
            sampler=SurfaceSampler(ear,select)
            if region=='ear_exterior':count=min(2200,max(600,math.ceil(sampler.total/.000039)))
            elif region=='ear_undercoat':count=min(1300,max(480,math.ceil(sampler.total/.000047)))
            else:count=340
            spacing=min(.0018,math.sqrt(sampler.total/count)*.38)
            roots,audit=sampler.roots(count,seed,spacing)
            groups.append({'region':region+'_'+side,'bone':'Ear_'+side,'materialRegion':'innerWisps'if region=='ear_locks'else'outerEar',
                           'guides':[make(region,*v,seed+i,side=sign)for i,v in enumerate(roots)],'sampling':audit})
            seed+=5000
    return groups
