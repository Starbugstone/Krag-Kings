"""Prepared area-sampled guide field; not integrated into focused v5d.

Run only on a separately opened, neutral reviewed source in an allocated Blender
slot. These functions have only been syntax checked. Root counts and dimensions
remain proposals requiring actual geometry review.
"""
import bisect,math,random,sys
from pathlib import Path
import bpy
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'v5_wip'))
from nib_groom_v5 import ear_coordinates,configure_goggle_envelopes,avoid_goggles

HEAD_REGIONS=[('crown',210),('fringe',120),('temple_L',90),('temple_R',90),('nape',120)]
EAR_REGIONS=[('outer_rim',160),('inner_wisps',100),('outer_nap',160)]

def head_selector(region,p,n,s):
    x,y,z=s
    if region=='crown':return z>.370 and n.z>-.2
    if region=='fringe':return .335<z<=.370 and y<-.035
    if region=='nape':return .240<z<=.370 and y>=-.005
    sign=1 if region.endswith('_L') else -1
    return sign*x>.057 and .290<z<=.370 and y<.030

def ear_selector(region,p,n,s):
    along,u=ear_coordinates(p)
    if not .06<along<.98:return False
    if region=='outer_nap':return n.y>.12
    if n.y>-.12:return False
    if region=='outer_rim':return .70<abs(u)<1.10
    return (.48<abs(u)<.84 and along<.86) or (along<.26 and abs(u)<.48)

class SurfaceSampler:
    """Uniform triangle-area sampling avoids vertex-density root clustering."""
    def __init__(self,obj,selector):
        obj.data.calc_loop_triangles();self.triangles=[];self.cumulative=[];self.total=0.
        world=obj.matrix_world;normals=world.to_3x3().inverted().transposed()
        attr=obj.data.attributes.get('nib_source_position')
        for tri in obj.data.loop_triangles:
            ids=list(tri.vertices);p=[world@obj.data.vertices[i].co for i in ids]
            n=[(normals@obj.data.vertices[i].normal).normalized() for i in ids]
            source=[Vector(attr.data[i].vector) if attr else p[j] for j,i in enumerate(ids)]
            center=sum(p,Vector())/3;normal=sum(n,Vector()).normalized();hint=sum(source,Vector())/3
            if not selector(center,normal,hint):continue
            area=(p[1]-p[0]).cross(p[2]-p[0]).length*.5
            if area<=1e-12:continue
            self.total+=area;self.cumulative.append(self.total);self.triangles.append((p,n,source))
        if not self.triangles:raise RuntimeError('No eligible guide surface on '+obj.name)

    def roots(self,count,seed,spacing):
        rng=random.Random(seed);roots=[];grid={};attempts=0
        while len(roots)<count and attempts<count*100:
            attempts+=1
            p,n,s=self.triangles[bisect.bisect_left(self.cumulative,rng.random()*self.total)]
            a=math.sqrt(rng.random());b=rng.random();weights=(1-a,a*(1-b),a*b)
            point=sum((v*w for v,w in zip(p,weights)),Vector())
            cell=tuple(math.floor(v/spacing) for v in point);too_close=False
            for dx in [-1,0,1]:
                for dy in [-1,0,1]:
                    for dz in [-1,0,1]:
                        for q in grid.get((cell[0]+dx,cell[1]+dy,cell[2]+dz),[]):
                            if (q-point).length<spacing:too_close=True
            if too_close:continue
            normal=sum((v*w for v,w in zip(n,weights)),Vector()).normalized()
            source=sum((v*w for v,w in zip(s,weights)),Vector())
            roots.append((point,normal,source));grid.setdefault(cell,[]).append(point)
        if len(roots)!=count:raise RuntimeError(f'Guide spacing cannot fit proposed count: {len(roots)}/{count}')
        return roots,{'areaMetersSquared':self.total,'triangles':len(self.triangles),'attempts':attempts,'rootSpacingMeters':spacing}

def make_guide(region,root,normal,source,seed,side=1):
    rng=random.Random(seed);short=region=='outer_nap'
    if region=='crown':flow=Vector((-.45,-.65,-.12));length=rng.uniform(.030,.047);lift=.016
    elif region=='fringe':flow=Vector((math.copysign(.65,root.x),-.30,-.18));length=rng.uniform(.024,.038);lift=.012
    elif region.startswith('temple'):flow=Vector((math.copysign(.55,root.x),.48,-.48));length=rng.uniform(.023,.037);lift=.010
    elif region=='nape':flow=Vector((root.x*2,.30,-.90));length=rng.uniform(.025,.043);lift=.010
    elif region=='chin':flow=Vector((root.x*3,-.08,-.95));length=rng.uniform(.008,.015);lift=.002
    elif region=='inner_wisps':
        along,u=ear_coordinates(root);flow=Vector((-side*u*.64,-.06,u*.77))+Vector((side*.13,0,.18))
        length=rng.uniform(.021,.036);lift=.010
    else:
        flow=Vector((side*.65,.06,.76));length=rng.uniform(.007,.012) if short else rng.uniform(.013,.024)
        lift=.002 if short else .007
    # The chin tuft falls away from the underside under gravity; projecting it
    # completely onto a downward-facing surface would make a horizontal comb.
    if region!='chin':flow-=normal*flow.dot(normal)
    if flow.length<1e-5:flow=normal.cross(Vector((1,0,0)))
    if flow.length<1e-5:flow=normal.cross(Vector((0,1,0)))
    flow.normalize();root=root+normal*.00025
    middle=root+flow*(length*.48)+normal*lift
    tip=root+flow*length+normal*(.0005 if short else .002)
    if region in [r[0] for r in HEAD_REGIONS]:middle=avoid_goggles(middle);tip=avoid_goggles(tip)
    return {'region':region,'root':list(root),'normal':list(normal),'middle':list(middle),'tip':list(tip),
            'halfWidthMeters':rng.uniform(.0013,.0023) if short else rng.uniform(.0016,.0026),
            'seed':seed,'sourceHint':list(source),'shortNap':short}

def build_guides(head,collection,nap_alpha_coverage):
    if head.data.attributes.get('nib_source_position') is None:raise RuntimeError('Reviewed fitted-head source coordinates are required')
    configure_goggle_envelopes(collection);groups=[];seed=70100
    for region,count in HEAD_REGIONS:
        sampler=SurfaceSampler(head,lambda p,n,s:head_selector(region,p,n,s))
        roots,audit=sampler.roots(count,seed,.0022)
        guides=[make_guide(region,*sample,seed+i) for i,sample in enumerate(roots)]
        groups.append({'region':region,'bone':'Head','materialRegion':'head','guides':guides,'sampling':audit});seed+=1000
    for side,sign in [('L',1),('R',-1)]:
        ear=next(o for o in collection.objects if o.name.startswith('Fennec cupped ear ') and o.get('bone')=='Ear_'+side)
        for region,count in EAR_REGIONS:
            sampler=SurfaceSampler(ear,lambda p,n,s:ear_selector(region,p,n,s))
            # A fixed 160 short cards leave the broad exterior mostly bare.
            # Report a measured-area density estimate, not assumed coverage.
            target_coverage=1.35 if region=='outer_nap' else None
            if not .05<nap_alpha_coverage<.98:raise RuntimeError('Invalid measured nap-atlas alpha coverage')
            estimated_footprint=2*.0018*.0095*.78*nap_alpha_coverage
            if target_coverage is not None:
                count=max(count,math.ceil(sampler.total*target_coverage/estimated_footprint))
                if count>2400:raise RuntimeError('Outer-ear area exceeds bounded candidate groom budget: '+str(count))
            spacing=min(.0025 if region!='inner_wisps' else .0030,
                        math.sqrt(sampler.total/max(count,1))*.58)
            roots,audit=sampler.roots(count,seed,spacing)
            audit['requestedGuides']=count
            if target_coverage is not None:
                audit['estimatedAlphaFootprintMetersSquared']=estimated_footprint
                audit['targetProjectedCoverage']=target_coverage
                audit['scope']='Guide-density estimate, not measured rendered coverage/overdraw'
            guides=[make_guide(region,*sample,seed+i,side=sign) for i,sample in enumerate(roots)]
            groups.append({'region':region+'_'+side,'bone':'Ear_'+side,
                           'materialRegion':'innerWisps' if region=='inner_wisps' else 'outerEar',
                           'guides':guides,'sampling':audit});seed+=1000
    chin=SurfaceSampler(head,lambda p,n,s:abs(s.x)<.020 and .170<s.z<.208 and s.y<-.100)
    roots,audit=chin.roots(12,seed,.0018)
    groups.append({'region':'chin','bone':'Jaw','materialRegion':'head',
                   'guides':[make_guide('chin',*sample,seed+i) for i,sample in enumerate(roots)],'sampling':audit})
    return groups

def legacy_guides(guides):
    """Reuses the existing verified strand emitter for opaque accents."""
    return [(Vector(g['root']),Vector(g['normal']),Vector(g['middle']),Vector(g['tip']),
             g['halfWidthMeters'],g['seed']) for g in guides]
