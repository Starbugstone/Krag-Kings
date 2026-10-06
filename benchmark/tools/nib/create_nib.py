"""Krag Kings Nib: editable layered character source and animated interchange exports.

Original geometry authored for this project from the supplied Nib and bionics sheets.
Run with Blender 5.2 --background --python this_file.py. No external assets required.
"""
import bpy, math, random, json, os, sys, shutil, hashlib
import numpy as np
from pathlib import Path
from mathutils import Vector, Matrix

ROOT=Path(__file__).resolve().parents[3]
ART=ROOT/'benchmark/art/nib'; OUT=ROOT/'benchmark/shared/characters/nib'
sys.path.insert(0,str(Path(__file__).resolve().parent))
from nib_face import build_face, build_deformation_contract, FACE_BONES, add_shapes
from nib_animation import build_animation
from nib_anatomy import build_continuous_anatomy, anatomical_weights
HEAD_DROP=-.032
CINEMATIC='--cinematic' in sys.argv
FUR_MULTIPLIER=3 if CINEMATIC else 1
TEX=OUT/'textures'; ART.mkdir(parents=True,exist_ok=True); TEX.mkdir(parents=True,exist_ok=True)
random.seed(721)
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
for datablocks in (bpy.data.materials,bpy.data.images,bpy.data.actions):
    for item in list(datablocks): datablocks.remove(item)
scene=bpy.context.scene; scene.unit_settings.system='METRIC'; scene.unit_settings.scale_length=1
scene.render.engine='CYCLES'; scene.cycles.samples=20; scene.render.threads_mode='FIXED';scene.render.threads=4
COL=bpy.data.collections.new('Nib_Authored_Components'); scene.collection.children.link(COL)
OBJECTS=[]; FINGER_CHAINS={}; VARIANT_PARTS={'natural':[],'grip':[],'leg':[]}

def material(name,base,kind='leather',metal=0.0,rough=.65):
    """Tileable base/normal/roughness/metalness data shared by Blender and engines."""
    size=2048 if name=='Nib_Skin' else 1024; yy,xx=np.mgrid[0:size,0:size].astype(np.float32)/size
    rng=np.random.default_rng(sum(ord(c) for c in name))
    noise=np.zeros((size,size),np.float32)
    # Periodic interpolated random fields avoid the rejected diagonal woodgrain.
    for count,amp in [(4,.42),(8,.24),(16,.15),(32,.09),(64,.055),(128,.025)]:
        grid=rng.uniform(-1,1,(count,count));gx=xx*count;gy=yy*count
        ix=gx.astype(np.int32);iy=gy.astype(np.int32);tx=gx-ix;ty=gy-iy
        tx=tx*tx*(3-2*tx);ty=ty*ty*(3-2*ty)
        field=(grid[iy%count,ix%count]*(1-tx)+grid[iy%count,(ix+1)%count]*tx)*(1-ty)+(grid[(iy+1)%count,ix%count]*(1-tx)+grid[(iy+1)%count,(ix+1)%count]*tx)*ty
        noise+=field*amp
    micro=rng.random((size,size)).astype(np.float32)
    v=noise
    if kind=='skin':
        freckles=np.maximum(0,np.sin(xx*149+np.sin(yy*53))*np.sin(yy*127+np.sin(xx*23))-.60)
        mottling=np.clip((noise-.015)*5,0,1)
        shade=1+v*.35-freckles*.35-mottling*.24+(micro-.5)*.07; height=v*.007+micro*.0015
    elif kind=='cloth':
        weave=np.sin(xx*math.tau*240)*np.sin(yy*math.tau*240)
        shade=1+v*.30+weave*.06+(micro-.5)*.06; height=v*.02+weave*.013
    elif kind=='metal':
        chip=(v>.16).astype(np.float32)
        scratches=np.power(np.maximum(0,np.sin(xx*math.tau*131+np.sin(yy*math.tau*3))),36)*.10
        shade=1+v*.55-scratches; height=v*.02+scratches*.02
    elif kind=='hair':
        shade=1+v*.28+np.sin(xx*math.tau*150)*.12; height=np.sin(xx*math.tau*150)*.008
    else:
        cracks=np.power(np.abs(np.sin(xx*math.tau*37+np.sin(yy*math.tau*9))*np.sin(yy*math.tau*31+np.sin(xx*math.tau*5))),18)
        shade=1+v*1.6-cracks*.26+(micro-.5)*.16; height=v*.045-cracks*.024+micro*.014
        dust=np.maximum(0, v+.05)**1.5
        shade+=dust*1.5
    rgb=np.clip(np.array(base)[None,None,:]*shade[:,:,None],0,1)
    if kind=='metal' and 'Teal' in name:
        chip=(v>.13)[:,:,None]
        rgb=np.where(chip,np.array([.19,.105,.053])[None,None,:]*(1+v[:,:,None]),rgb)
    grad_y,grad_x=np.gradient(height)
    nn=np.dstack((-grad_x*22,-grad_y*22,np.ones((size,size))))
    nn/=np.linalg.norm(nn,axis=2)[:,:,None]; nn=nn*.5+.5
    maps={'BaseColor':rgb,'Normal':nn,'Roughness':np.repeat(np.clip(rough+v*.18,0,1)[:,:,None],3,axis=2),'Metallic':np.ones((size,size,3))*metal}
    images={}
    for suffix,arr in maps.items():
        rgba=np.concatenate((arr,np.ones((size,size,1))),axis=2).astype(np.float32)
        im=bpy.data.images.new(name+'_'+suffix,width=size,height=size,alpha=False)
        im.colorspace_settings.name='sRGB' if suffix=='BaseColor' else 'Non-Color'
        im.pixels.foreach_set(rgba.reshape(-1)); im.filepath_raw=str(TEX/(name+'_'+suffix+'.png')); im.file_format='PNG'; im.save()
        texture_path=im.filepath_raw;bpy.data.images.remove(im)
        im=bpy.data.images.load(texture_path,check_existing=True)
        im.colorspace_settings.name='sRGB' if suffix=='BaseColor' else 'Non-Color'
        images[suffix]=im
    mat=bpy.data.materials.new(name); mat.use_nodes=True
    bs=mat.node_tree.nodes.get('Principled BSDF'); bs.inputs['Base Color'].default_value=(*base,1); bs.inputs['Metallic'].default_value=metal; bs.inputs['Roughness'].default_value=rough
    for suffix,socket in [('BaseColor','Base Color'),('Roughness','Roughness'),('Metallic','Metallic')]:
        n=mat.node_tree.nodes.new('ShaderNodeTexImage'); n.image=images[suffix]; mat.node_tree.links.new(n.outputs['Color'],bs.inputs[socket])
    n=mat.node_tree.nodes.new('ShaderNodeTexImage'); n.image=images['Normal']; norm=mat.node_tree.nodes.new('ShaderNodeNormalMap'); norm.inputs['Strength'].default_value=.5; mat.node_tree.links.new(n.outputs['Color'],norm.inputs['Color']); mat.node_tree.links.new(norm.outputs['Normal'],bs.inputs['Normal'])
    if kind=='skin': bs.inputs['Subsurface Weight'].default_value=.10; bs.inputs['Subsurface Radius'].default_value=(1,.48,.2)
    mat.diffuse_color=(*base,1); return mat

print('NIB_STAGE textures',flush=True)
SKIN=material('Nib_Skin',(.59,.39,.23),'skin',rough=.72)
MUZZLE=material('Nib_Muzzle',(.69,.52,.34),'skin',rough=.67)
INNER=material('Nib_EarInner',(.24,.105,.052),'skin',rough=.84)
LEATHER=material('Nib_Leather',(.13,.082,.045),'leather',rough=.83)
WORKWEAR=material('Nib_Workwear',(.13,.10,.073),'cloth',rough=.88)
if (ART/'Nib_Workwear_BaseColor_v1.png').exists():
    destination=TEX/'Nib_Workwear_BaseColor.png'
    # Bake the authored canvas's material tint into the common albedo, so both
    # engines receive exactly the same darker charcoal-brown workwear color.
    original=bpy.data.images.load(str(ART/'Nib_Workwear_BaseColor_v1.png'),check_existing=False)
    pixels=np.empty(original.size[0]*original.size[1]*4,dtype=np.float32);original.pixels.foreach_get(pixels)
    pixels.reshape((-1,4))[:,:3]*=.42
    baked=bpy.data.images.new('Nib workwear tint bake',width=original.size[0],height=original.size[1],alpha=False)
    baked.colorspace_settings.name='sRGB';baked.pixels.foreach_set(pixels);baked.filepath_raw=str(destination);baked.file_format='PNG';baked.save()
    bpy.data.images.remove(baked);bpy.data.images.remove(original)
    image=bpy.data.images.load(str(destination),check_existing=False)
    for node in WORKWEAR.node_tree.nodes:
        if node.type=='TEX_IMAGE' and node.image and 'BaseColor' in node.image.name:node.image=image
CLOTH=material('Nib_Cloth',(.35,.267,.175),'cloth',rough=.91)
HAIR=material('Nib_Hair',(.43,.34,.22),'hair',rough=.86)
BRASS=material('Nib_Brass',(.23,.13,.050),'metal',metal=.78,rough=.47)
STEEL=material('Nib_Steel',(.16,.18,.17),'metal',metal=.88,rough=.35)
TEAL=material('Nib_Teal',(.075,.29,.28),'metal',metal=.68,rough=.44)
EYE=material('Nib_Eye',(.53,.29,.065),'skin',rough=.18)
DARK=material('Nib_Dark',(.025,.018,.012),'leather',rough=.53)
GLASS=material('Nib_Lens',(.025,.095,.10),'metal',metal=.25,rough=.10)
STITCH=material('Nib_Stitch',(.45,.32,.17),'cloth',rough=.8)

def own(obj,mat,bone='Head',variant='all'):
    for c in list(obj.users_collection): c.objects.unlink(obj)
    COL.objects.link(obj)
    if mat: obj.data.materials.append(mat)
    obj['bone']=bone; obj['variant']=variant
    OBJECTS.append(obj)
    if variant!='all': VARIANT_PARTS.setdefault(variant,[]).append(obj)
    return obj

def shade(o):
    if o.type=='MESH':
        for p in o.data.polygons:p.use_smooth=True
    return o

def apply(o,mod):
    bpy.context.view_layer.objects.active=o
    bpy.ops.object.modifier_apply(modifier=mod.name)

def uv(o):
    if o.type!='MESH': return
    bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
    if not o.data.uv_layers: o.data.uv_layers.new(name='UVMap')
    o.data.uv_layers.active.name='UVMap'
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(68),island_margin=.016);bpy.ops.object.mode_set(mode='OBJECT')

def ell(name,loc,scale,mat,bone='Head',variant='all',seg=40,rings=24):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg,ring_count=rings,location=loc)
    o=bpy.context.object;o.name=name;o.scale=scale;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    return shade(own(o,mat,bone,variant))

def box(name,loc,scale,mat,bone='Pelvis',bevel=.006,variant='all',rot=None):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.name=name;o.scale=scale
    if rot:o.rotation_euler=rot
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    own(o,mat,bone,variant)
    if bevel:
        m=o.modifiers.new('Soft manufactured edges','BEVEL')
        # Keep a real planar band on thin patches/pockets. A bevel clamped at
        # half-thickness produced collapsed triangles after float FBX export.
        m.width=min(bevel,min(abs(float(v)) for v in scale)*.45);m.segments=3;apply(o,m)
    shade(o);return o

def soft_pouch(name,center,size,mat,bone='Pelvis'):
    cx,cy,cz=center;sx,sy,sz=size;vs=[];fs=[];rows=15;sides=40
    for row in range(rows):
        t=row/(rows-1);bulge=.82+.18*math.sin(t*math.pi);z=cz+(t-.5)*sz
        for k in range(sides):
            a=k/sides*math.tau;c=math.cos(a);s=math.sin(a)
            x=cx+sx*.5*math.copysign(abs(c)**.48,c)*bulge
            y=cy+sy*.5*math.copysign(abs(s)**.48,s)*(.68+.32*math.sin(t*math.pi))
            y+=.0013*math.sin(t*17+a*3)*math.sin(t*math.pi)
            vs.append((x,y,z+.0012*math.sin(a*4+t*5)*math.sin(t*math.pi)))
    for row in range(rows-1):
        for k in range(sides):
            a=row*sides+k;b=row*sides+(k+1)%sides;fs.append((a,b,b+sides,a+sides))
    fs.extend([tuple(reversed(range(sides))),tuple((rows-1)*sides+k for k in range(sides))])
    me=bpy.data.meshes.new(name);me.from_pydata(vs,[],fs);me.update();obj=bpy.data.objects.new(name,me);COL.objects.link(obj);own(obj,mat,bone);shade(obj);uv(obj)
    sub=obj.modifiers.new('Soft sewn construction','SUBSURF');sub.levels=1;apply(obj,sub)
    return obj

def tube(name,points,radii,mat,bone='Head',variant='all',sides=12,res=2):
    """Tapered swept surface, UV along length; supports authored muscle/cloth profiles."""
    ps=[Vector(p) for p in points]; verts=[];faces=[]
    for i,p in enumerate(ps):
        tangent=(ps[min(i+1,len(ps)-1)]-ps[max(0,i-1)]).normalized()
        a=tangent.cross(Vector((0,1,0))).normalized()
        if a.length<.1:a=tangent.cross(Vector((1,0,0))).normalized()
        b=tangent.cross(a).normalized(); r=radii[i] if isinstance(radii,list) else radii
        if isinstance(r,(int,float)):rx=ry=r
        else:rx,ry=r
        for j in range(sides):
            angle=j/sides*math.tau
            v=p+a*(math.cos(angle)*rx)+b*(math.sin(angle)*ry); verts.append(tuple(v))
    for i in range(len(ps)-1):
        for j in range(sides):faces.append((i*sides+j,i*sides+(j+1)%sides,(i+1)*sides+(j+1)%sides,(i+1)*sides+j))
    faces.append(tuple(range(sides-1,-1,-1))); faces.append(tuple((len(ps)-1)*sides+j for j in range(sides)))
    me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update()
    # Analytic longitudinal UVs avoid thousands of context-dependent unwrap calls,
    # and keep woven cloth/hair direction aligned with the actual authored form.
    layer=me.uv_layers.new(name='UVMap')
    for polygon in me.polygons:
        seam=any(me.loops[k].vertex_index%sides==sides-1 for k in polygon.loop_indices)
        for k in polygon.loop_indices:
            vi=me.loops[k].vertex_index;u=(vi%sides)/sides
            if polygon.index>=(len(ps)-1)*sides:
                # Cap loops need a disk, not one constant longitudinal V.
                angle=(vi%sides)/sides*math.tau
                layer.data[k].uv=(.5+.48*math.cos(angle),.5+.48*math.sin(angle))
                continue
            if seam and vi%sides==0:u=1
            layer.data[k].uv=(u,(vi//sides)/max(1,len(ps)-1))
    o=bpy.data.objects.new(name,me);COL.objects.link(o);own(o,mat,bone,variant)
    if res:
        sub=o.modifiers.new('Shaped surface smoothing','SUBSURF');sub.levels=res;apply(o,sub)
    return shade(o)

def line(name,pts,radius,mat,bone='Head',variant='all'):
    return tube(name,pts,[radius]*len(pts),mat,bone,variant,sides=6,res=1)

def torus(name,loc,major,minor,mat,bone='Head',rot=(math.pi/2,0,0),variant='all'):
    bpy.ops.mesh.primitive_torus_add(major_segments=40,minor_segments=10,location=loc,major_radius=major,minor_radius=minor,rotation=rot)
    o=bpy.context.object;o.name=name;return shade(own(o,mat,bone,variant))

def cylinder(name,a,b,r,mat,bone='Head',variant='all',vertices=24):
    aa=Vector(a);bb=Vector(b);d=bb-aa
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=r,depth=d.length,location=(aa+bb)/2)
    o=bpy.context.object;o.name=name;o.rotation_mode='QUATERNION';o.rotation_quaternion=d.to_track_quat('Z','Y');own(o,mat,bone,variant)
    bevel=o.modifiers.new('Edge glints','BEVEL');bevel.width=min(.002,r*.18);bevel.segments=2;apply(o,bevel);shade(o);return o

def rivet(loc,bone='Pelvis',mat=BRASS,r=.0026,variant='all'):
    return ell('Set rivet',loc,(r,r*.55,r),mat,bone,variant,seg=12,rings=8)

print('NIB_STAGE anatomy',flush=True)
# Torso, underlying adult neck and unified sculpted face.
tube('Sleeveless dust undershirt',[(0,.014,.58),(0,.007,.63),(0,0,.73),(0,.004,.84),(0,.007,.93),(0,.007,.97)],[(.083,.058),(.093,.064),(.082,.060),(.103,.075),(.137,.071),(.092,.044)],CLOTH,'Torso',sides=40,res=2)
tube('Adult neck',[(0,.008,.93),(0,.006,.99),(0,.012,1.055),(0,.004,1.105)],[(.045,.037),(.031,.032),(.031,.033),(.05,.04)],SKIN,'Neck',sides=32,res=1)

facial_data=build_face(globals())
print('NIB_STAGE ears',flush=True)
# Exactly two large sculpted concave fennec ears. Front and back are a closed loft.
def ear(side):
    # Closed cupped anatomy, not ellipsoidal leaf plus an intersecting membrane.
    centers=[(.066,0,1.210),(.114,.006,1.250),(.170,.015,1.289),(.220,.026,1.333),(.269,.038,1.379),(.309,.05,1.417)]
    widths=[.009,.056,.069,.060,.036,.0004]
    rows=28;cols=19;verts=[];faces=[]
    def position(t,u,front=True):
        f=t*5;a=min(int(f),4);q=f-a
        c=Vector(centers[a]).lerp(Vector(centers[a+1]),q);w=widths[a]*(1-q)+widths[a+1]*q
        # Thick raised rim with the centre recessed into the bowl.
        x=side*(c.x+w*u*.64);z=c.z-w*u*.77
        y=c.y-.018+.020*(1-u*u)+(0 if front else .006)
        return (x,y,z)
    for back in [False,True]:
        for i in range(rows):
            t=i/(rows-1)
            for j in range(cols):verts.append(position(t,-1+2*j/(cols-1),not back))
    n=rows*cols
    for i in range(rows-1):
        for j in range(cols-1):
            a=i*cols+j;quad=(a,a+1,a+cols+1,a+cols)
            faces.append(quad if side==1 else tuple(reversed(quad)))
            faces.append(tuple(reversed(tuple(v+n for v in quad))) if side==1 else tuple(v+n for v in quad))
    perimeter=list(range(cols))+[i*cols+cols-1 for i in range(1,rows)]+list(range((rows-1)*cols+cols-2,(rows-1)*cols-1,-1))+[i*cols for i in range(rows-2,0,-1)]
    for i,a in enumerate(perimeter):
        b=perimeter[(i+1)%len(perimeter)];faces.append((a,b,b+n,a+n))
    me=bpy.data.meshes.new('Ear closed cupped anatomy');me.from_pydata(verts,[],faces);me.update();o=bpy.data.objects.new('Fennec cupped ear '+str(side),me);COL.objects.link(o);own(o,SKIN,'Ear_L' if side==1 else 'Ear_R');sub=o.modifiers.new('Smooth auricle','SUBSURF');sub.levels=1;apply(o,sub);uv(o);shade(o)
    vs=[];fs=[]
    for i in range(rows):
        t=.05+i/(rows-1)*.89
        for j in range(cols):
            u=(-1+2*j/(cols-1))*.87;p=Vector(position(t,u));p.y-=.0012;vs.append(tuple(p))
    for i in range(rows-1):
        for j in range(cols-1):
            a=i*cols+j;quad=(a,a+1,a+cols+1,a+cols);fs.append(quad if side==1 else tuple(reversed(quad)))
    me=bpy.data.meshes.new('Fitted ear velvet');me.from_pydata(vs,[],fs);me.update();oo=bpy.data.objects.new('Ear inner velvet '+str(side),me);COL.objects.link(oo);own(oo,INNER,'Ear_L' if side==1 else 'Ear_R');uv(oo);shade(oo)
    for edge in [-1,1]:
        points=[position(.03+i/31*.94,edge*.93) for i in range(32)]
        radii=[.0015+.003*math.sin(i/31*math.pi)**.5 for i in range(32)]
        tube('Rounded auricle cartilage rim',points,radii,SKIN,'Ear_L' if side==1 else 'Ear_R',sides=10,res=1)
    fold=[Vector(position(.04+t*.36,.12+.35*t)) for t in [0,.25,.5,.75,1]]
    for point in fold:point.y-=.007
    tube('Auricle basal cartilage fold',[tuple(p) for p in fold],[.006,.006,.005,.003,.0008],SKIN,'Ear_L' if side==1 else 'Ear_R',sides=10,res=1)
    for k in range(330):
        t=random.uniform(.04,.95);u=random.choice([-1,1])*random.uniform(.69,1.0);p=Vector(position(t,u));p.y-=.0015
        tip=p+Vector((side*random.uniform(.003,.010),-.003,random.uniform(.003,.013)))
        tube('Fine auricle fur',[tuple(p),tuple(p.lerp(tip,.6)+Vector((0,-.001,0))),tuple(tip)],[.00065,.00035,.00003],HAIR,'Ear_L' if side==1 else 'Ear_R',sides=3,res=0)
for s in [-1,1]:ear(s)

print('NIB_STAGE hair',flush=True)
# Dense fine strands follow curved clump guides rather than separate solid spikes.
def fur_mesh(name,guides,bone='Head',mat=None,variant='all'):
    vs=[];fs=[];uvs=[]
    for root,mid,tip,radius in guides:
        root=Vector(root);mid=Vector(mid);tip=Vector(tip);base=len(vs);rings=8 if CINEMATIC else 5;sides=4 if CINEMATIC else 3
        for j in range(rings):
            t=j/(rings-1);point=(1-t)**2*root+2*(1-t)*t*mid+t*t*tip
            tangent=(2*(1-t)*(mid-root)+2*t*(tip-mid)).normalized()
            axis=tangent.cross(Vector((0,1,0)))
            if axis.length<.01:axis=tangent.cross(Vector((1,0,0)))
            axis.normalize();other=tangent.cross(axis).normalized();r=radius*(1-t)**.7+.000008
            for k in range(sides):
                a=k/sides*math.tau;vs.append(tuple(point+r*(axis*math.cos(a)+other*math.sin(a))));uvs.append((k/sides,t))
        for j in range(rings-1):
            for k in range(sides):
                a=base+j*sides+k;b=base+j*sides+(k+1)%sides;fs.append((a,b,b+sides,a+sides))
    me=bpy.data.meshes.new(name);me.from_pydata(vs,[],fs);me.update();o=bpy.data.objects.new(name,me);COL.objects.link(o);own(o,mat or HAIR,bone,variant);shade(o);o['fur_strands']=len(guides)
    layer=me.uv_layers.new(name='UVMap')
    for loop in me.loops:layer.data[loop.index].uv=uvs[loop.vertex_index]
    return o
hair_guides=[]
for k in range(420):
    angle=random.uniform(0,math.tau);elev=random.uniform(.18,1)
    p=Vector((math.cos(angle)*.078*math.sqrt(1-elev*elev),.013+math.sin(angle)*.063*math.sqrt(1-elev*elev),1.164+elev*.101))
    if p.y<-.006 and p.z<1.210:continue
    flow=Vector((p.x*.22,math.sin(angle)*.020,-.022-random.random()*.013))
    if p.y<-.006:flow=Vector((-.014-random.random()*.016,-.014,-.015-random.random()*.009))
    mid=p+flow*.46+Vector((random.uniform(-.004,.004),-.004,.016));tip=p+flow
    for strand in range(13*FUR_MULTIPLIER):
        offset=Vector((random.uniform(-.0025,.0025),random.uniform(-.002,.002),random.uniform(-.0025,.0025)))
        hair_guides.append((p+offset,mid+offset*.8,tip+offset*.5+Vector((random.uniform(-.003,.003),0,random.uniform(-.004,.004))),random.uniform(.00015,.00032)))
for sign in [-1,1]:
    for k in range(280*FUR_MULTIPLIER):
        p=Vector((sign*random.uniform(.069,.085),random.uniform(-.030,.008),random.uniform(1.155,1.197)))
        tip=p+Vector((sign*random.uniform(.009,.017),random.uniform(-.006,.008),-random.uniform(.008,.018)))
        hair_guides.append((p,p.lerp(tip,.50)+Vector((sign*.004,-.003,.008)),tip,random.uniform(.00014,.00030)))
fur_mesh('Swept fine head and cheek coat',hair_guides)
for sign,side in [(1,'L'),(-1,'R')]:
    guides=[]
    for k in range(1150*FUR_MULTIPLIER):
        t=random.uniform(.13,.75);u=random.choice([-1,1])*random.uniform(.50,.91)
        x=.066+.243*t;z=1.210+.207*t;w=.068*math.sin(t*math.pi)**.7
        root=Vector((sign*(x+w*u*.64),.05*t-.019+.018*(1-u*u),z-w*u*.77))
        tip=root+Vector((-sign*u*random.uniform(.008,.026),-.006,random.uniform(-.003,.014)))
        guides.append((root,root.lerp(tip,.55)+Vector((0,-.004,.006)),tip,random.uniform(.00012,.00027)))
    fur_mesh('Soft inner auricle hair '+side,guides,'Ear_'+side)

# Goggles: leather band, brass annuli, glass, hinges, buckles, bridges, bolts.
band=[]
for i in range(49):
    a=i/48*math.tau;band.append((math.sin(a)*.089,.007-math.cos(a)*.065,1.213+math.cos(a)*.008))
tube('Goggle leather head strap',band,[(.009,.004)]*len(band),LEATHER,sides=8,res=1)
for s in [-1,1]:
    loc=(s*.040,-.061,1.228);r=torus('Brass goggle rim',loc,.026,.0045,BRASS)
    r.rotation_euler[2]=s*.14
    lens=ell('Teal glass goggle lens',(s*.040,-.064,1.228),(.022,.0035,.022),GLASS)
    torus('Goggle leather gasket',(s*.040,-.056,1.228),.026,.006,LEATHER)
    for a in [0,math.pi/2,math.pi,math.pi*1.5]:rivet((s*.040+math.cos(a)*.026,-.066,1.228+math.sin(a)*.026),'Head',STEEL,r=.0018)
    box('Goggle side hinge',(s*.075,-.038,1.221),(.014,.016,.009),BRASS,'Head',.002)
line('Goggle bridge',[(-.013,-.068,1.227),(0,-.075,1.235),(.013,-.068,1.227)],.003,BRASS)

# Broad desert scarf hangs around the neck and settles onto shoulders/chest.
verts=[];faces=[];N=96;M=22
for j in range(M):
    t=j/(M-1)
    for i in range(N):
        a=i/N*math.tau;front=max(0,-math.sin(a));back=max(0,math.sin(a))
        radx=.035+t*.099;rady=.045+t*.053
        sag=front**1.5*(.011+t*.045)
        fold=.005*math.sin(t*math.pi*5+.7*math.sin(a*2))*(.3+.7*front)
        z=1.012-t*.060-sag+fold+.005*math.sin(a*3+t*4)
        verts.append((radx*math.cos(a),.005+rady*math.sin(a),z))
for j in range(M-1):
    for i in range(N):faces.append((j*N+i,j*N+(i+1)%N,(j+1)*N+(i+1)%N,(j+1)*N+i))
me=bpy.data.meshes.new('Soft hanging scarf');me.from_pydata(verts,[],faces);me.update();o=bpy.data.objects.new('Draped desert scarf',me);COL.objects.link(o);own(o,CLOTH,'Chest');sol=o.modifiers.new('Fabric thickness','SOLIDIFY');sol.thickness=.0025;apply(o,sol);sub=o.modifiers.new('Relaxed folds','SUBSURF');sub.levels=1;apply(o,sub);shade(o);uv(o)
print('NIB_STAGE clothing',flush=True)
# Overalls bib, front pockets, worked leather shoulder straps and crossed back.
# Fitted hanging bib surface with its own fold field, thickness and stitched edge.
verts=[];faces=[]
for i in range(17):
    t=i/16;z=.682+t*.212;w=.082-.023*t+.003*math.sin(t*math.pi)
    for j in range(15):
        u=-1+2*j/14;verts.append((u*w,-.066-.014*math.sin(t*math.pi*.70)+.023*u*u+.004*math.sin(t*17+u*2)*math.sin(math.pi*t),z+.002*math.sin(u*9+t*3)))
for i in range(16):
    for j in range(14):
        a=i*15+j;faces.append((a,a+1,a+16,a+15))
me=bpy.data.meshes.new('Shaped fabric bib');me.from_pydata(verts,[],faces);me.update();o=bpy.data.objects.new('Overalls draped bib',me);COL.objects.link(o);own(o,WORKWEAR,'Torso');sol=o.modifiers.new('Heavy fabric thickness','SOLIDIFY');sol.thickness=.002;apply(o,sol);sub=o.modifiers.new('Sewn folds','SUBSURF');sub.levels=1;apply(o,sub);shade(o);uv(o)
soft_pouch('Bib sewn chest pocket',(0,-.081,.812),(.094,.013,.070),WORKWEAR,'Chest')
box('Bib pocket flap',(0,-.087,.845),(.100,.007,.023),WORKWEAR,'Chest',.003)
for s in [-1,1]:
    pts=[(s*.060,-.073,.880),(s*.073,-.065,.937),(s*.082,-.029,.967),(s*.079,.025,.965),(s*.055,.067,.893),(s*.017,.074,.816),(-s*.052,.067,.729)]
    tube('Overalls shoulder strap',pts,[(.010,.004)]*len(pts),LEATHER,'Torso',sides=8,res=1)
    box('Strap adjustment buckle',(s*.062,-.079,.894),(.025,.006,.027),BRASS,'Chest',.002)
    box('Buckle hollow insert',(s*.062,-.083,.894),(.016,.003,.018),LEATHER,'Chest',.001)
    rivet((s*.061,-.081,.873),'Chest',BRASS,.005)
    line('Bib stitched outer seam',[(s*.069,-.077,.876),(s*.069,-.078,.83),(s*.061,-.078,.743)],.0010,STITCH,'Torso')
    for z in np.linspace(.755,.855,18):
        line('Bib hand stitching',[(s*.051,-.086,z),(s*.047,-.086,z+.003)],.00065,STITCH,'Chest')

# Trouser pelvis and shaped legs with compression folds, rolled cuffs, piping, patches.
tube('Overalls pelvis',[(0,.012,.57),(0,.006,.61),(0,.005,.676),(0,.004,.713)],[(.086,.056),(.100,.064),(.092,.063),(.084,.057)],WORKWEAR,'Pelvis',sides=40,res=2)
for s,label in [(1,'L'),(-1,'R')]:
    x=s*.066
    pts=[];rs=[]
    for j in range(37):
        t=j/36;z=.604-t*.400;xx=x+s*(.008*math.sin(t*math.pi))
        rx=.055-t*.018+.010*math.sin(t*math.pi*13)**3
        ry=.057-t*.020+.007*math.cos(t*math.pi*17)
        pts.append((xx,.009+.009*math.sin(t*7),z));rs.append((rx,ry))
    tube('Shaped overalls trouser '+label,pts,rs,WORKWEAR,'Leg_'+label,sides=32,res=1)
    for side in [-1,1]:
        seam=[(s*.069+side*(.054-t*.018),.013,.596-t*.376) for t in np.linspace(0,1,18)]
        line('Trouser raised seam '+label,seam,.0016,STITCH,'Leg_'+label)
    box('Knee patched panel '+label,(s*.074,-.038,.339),(.068,.011,.096),WORKWEAR,'Shin_'+label,.008)
    for z in np.linspace(.299,.377,14):
        for ss in [-1,1]:line('Knee visible stitch',[(s*.074+ss*.028,-.045,z),(s*.074+ss*.028,-.045,z+.003)],.0007,STITCH,'Shin_'+label)
    soft_pouch('Cargo sewn pocket '+label,(s*.112,-.006,.481),(.024,.063,.092),WORKWEAR,'Thigh_'+label)
    box('Cargo pocket flap '+label,(s*.127,-.007,.525),(.012,.070,.027),CLOTH,'Thigh_'+label,.005)
    # rolled cuffs with actual rucked surface
    for j in range(3):
        p=[]
        for k in range(33):
            a=k/32*math.tau;p.append((s*.073+math.cos(a)*(.044-j*.001),.006+math.sin(a)*(.043-j*.001),.215+j*.009+.005*math.sin(a*3+j)))
        tube('Rolled trouser cuff '+label,p,[(.007,.006)]*len(p),CLOTH,'Shin_'+label,sides=8,res=1)
    variant='natural' if label=='R' else 'all'
    # Natural right lower leg has separate visibility for restorative variant.
    tube('Natural lower leg '+label,[(s*.073,.008,.210),(s*.075,.008,.168),(s*.075,.006,.124),(s*.075,.001,.088)],[(.027,.030),(.023,.022),(.016,.018),(.018,.019)],SKIN,'Shin_'+label,variant,sides=24,res=2)
    for j in range(6):
        p=[]
        for k in range(25):
            a=k/24*math.tau;p.append((s*.075+math.cos(a)*(.018+j*.0006),.004+math.sin(a)*(.020+j*.0007),.117+j*.009+.0015*math.sin(a*2)))
        tube('Ankle fabric bindings '+label,p,.0033,CLOTH,'Shin_'+label,variant,sides=6,res=1)
    ell('Worn ankle boot '+label,(s*.075,-.008,.062),(.032,.045,.058),LEATHER,'Foot_'+label,variant)
    box('Formed leather toe '+label,(s*.075,-.043,.038),(.072,.095,.049),LEATHER,'Foot_'+label,.017,variant)
    box('Heavy sewn outsole '+label,(s*.075,-.028,.014),(.078,.139,.021),DARK,'Foot_'+label,.009,variant)
    # Welt rim and tread, wraps and metal buckle.
    for j in range(9):
        box('Boot tread '+label,(s*.075,-.084+j*.014,.005),(.077,.007,.009),LEATHER,'Foot_'+label,.001,variant)
    for z in [.065,.09]:
        torus('Boot strap '+label,(s*.075,-.002,z),.030,.0035,CLOTH,'Foot_'+label,rot=(0,0,0),variant=variant)
        box('Boot teal buckle '+label,(s*.077,-.037,z),(.024,.008,.014),TEAL,'Foot_'+label,.002,variant)
    for j in range(4):
        yy=-.044+j*.01;zz=.062+j*.006
        line('Crossed boot lace '+label,[(s*.075-.019,yy,zz),(s*.075+.017,yy+.009,zz+.007)],.0015,CLOTH,'Foot_'+label,variant)
        line('Crossed boot lace '+label,[(s*.075+.019,yy,zz),(s*.075-.017,yy+.009,zz+.007)],.0015,CLOTH,'Foot_'+label,variant)

# Adult slender muscled arms, five articulated-looking fingers, fingerless gloves.
for s,label in [(1,'L'),(-1,'R')]:
    shoulder=Vector((s*.128,.005,.938));elbow=Vector((s*.189,-.003,.769));wrist=Vector((s*.218,-.031,.614))
    pts=[shoulder,shoulder.lerp(elbow,.19),shoulder.lerp(elbow,.43),shoulder.lerp(elbow,.70),elbow,elbow.lerp(wrist,.20),elbow.lerp(wrist,.50),elbow.lerp(wrist,.80),wrist]
    radii=[(.034,.035),(.041,.040),(.033,.034),(.028,.031),(.021,.023),(.028,.028),(.024,.023),(.017,.018),(.015,.016)]
    # The organic arm is one uninterrupted skinned surface, including the elbow.
    pts.insert(0,Vector((s*.094,.007,.950)));radii.insert(0,(.037,.035))
    v='natural' if label=='L' else 'all'
    tube('Continuous organic arm '+label,[tuple(p) for p in pts],radii,SKIN,'Arm_'+label,v,sides=32,res=1)
    if label=='L':
        tube('Retained upper arm for replacement',[tuple(p) for p in pts[:6]],radii[:6],SKIN,'UpperArm_L','grip',sides=32,res=1)
    for j in range(10):
        t=.40+j*.05;c=elbow.lerp(wrist,t);r=.036-t*.018
        pts2=[]
        for k in range(25):
            a=k/24*math.tau;pts2.append(tuple(c+Vector((math.cos(a)*r,math.sin(a)*r, .0015*math.sin(a*3)))))
        tube('Forearm desert wrap '+label,pts2,.0032,CLOTH,'LowerArm_'+label,v,sides=6,res=1)
    palm=Vector((s*.227,-.043,.582))
    ell('Leather glove palm '+label,tuple(palm),(.023,.017,.032),LEATHER,'Hand_'+label,v)
    box('Glove wrist strap '+label,(s*.220,-.045,.616),(.032,.029,.012),LEATHER,'Hand_'+label,.004,v)
    for j in range(4):
        fx=palm.x+(j-1.5)*.012; zz=.563-(.008 if j in [0,3] else 0)
        fp=[(fx,-.046,zz+.01),(fx+s*.004,-.049,zz-.011),(fx+s*.003,-.060,zz-.028),(fx,-.070,zz-.032)]
        if label=='R':
            fp=[(fx,-.043,.575),(fx,-.062,.567),(fx,-.066,.581),(fx,-.050,.592)]
        finger=['Index','Middle','Ring','Little'][j]
        FINGER_CHAINS[finger+'_'+label]=[Vector(p) for p in fp]
        tube('Finger '+label+' '+str(j),fp,[.0052,.005,.004,.0028],SKIN,'Finger_'+finger+'_'+label,v,sides=10,res=2)
        tube('Fingerless glove '+label+' '+str(j),fp[:2],[.0063,.0058],LEATHER,finger+'1_'+label,v,sides=10,res=1)
        ell('Fingernail '+label,tuple(Vector(fp[-1])+Vector((0,-.0015,.001))),(.0023,.001,.0035),MUZZLE,finger+'3_'+label,v,seg=12,rings=8)
        rivet((fx,-.062,.587),'Hand_'+label,BRASS,.002,v)
    thumb=[(palm.x-s*.021,-.042,.594),(palm.x-s*.034,-.055,.581),(palm.x-s*.037,-.066,.565)]
    if label=='R':thumb=[(-.207,-.039,.595),(-.204,-.059,.599),(-.219,-.067,.596)]
    FINGER_CHAINS['Thumb_'+label]=[Vector(p) for p in thumb]
    tube('Thumb '+label,thumb,[.007,.006,.0035],SKIN,'Finger_Thumb_'+label,v,sides=12,res=2)
    tube('Thumb glove '+label,thumb[:2],[.009,.0075],LEATHER,'Thumb1_'+label,v,sides=12,res=1)

# Layered belt with teal enamel repair plates, work pouches and wrench silhouettes.
p=[]
for i in range(49):
    a=i/48*math.tau;p.append((math.cos(a)*.102,.006+math.sin(a)*.071,.663+.003*math.sin(a*3)))
tube('Utility belt leather',p,[(.012,.005)]*len(p),LEATHER,'Pelvis',sides=8,res=1)
box('Belt main buckle',(0,-.071,.665),(.045,.014,.031),BRASS,'Pelvis',.003)
box('Belt buckle inset',(0,-.080,.665),(.032,.005,.018),DARK,'Pelvis',.001)
for s in [-1,1]:
    box('Belt teal plate',(s*.051,-.063,.663),(.029,.013,.030),TEAL,'Pelvis',.003,rot=(0,0,-s*.25))
    for z in [.653,.675]:rivet((s*.052,-.072,z),'Pelvis',STEEL,.002)
    soft_pouch('Shaped tool pouch',(s*.102,-.003,.615),(.040,.058,.083),LEATHER,'Pelvis')
    box('Tool pouch closing flap',(s*.104,-.026,.647),(.044,.012,.034),CLOTH,'Pelvis',.004)
    rivet((s*.104,-.034,.637),'Pelvis',BRASS,.003)
    box('Rear patch pocket',(s*.050,.069,.591),(.064,.012,.067),LEATHER,'Pelvis',.007)
    line('Rear pocket seam',[(s*.05-.026,.077,.618),(s*.05-.026,.078,.568),(s*.05,.080,.562),(s*.05+.026,.078,.568),(s*.05+.026,.077,.618)],.001,STITCH,'Pelvis')
    line('Hanging tool handle',[(s*.089,-.061,.62),(s*.100,-.069,.555),(s*.105,-.075,.518)],.006,STEEL,'Pelvis')
    torus('Wrench open ring',(s*.105,-.075,.513),.012,.0045,BRASS,'Pelvis')
    for j in range(4):rivet((s*.096,.075,.62-j*.008),'Pelvis',BRASS,.002)

# Light restorative forearm: same reach/grip and mass envelope, no upgrade/claw.
elbow=Vector((.189,-.003,.769)); wrist=Vector((.218,-.031,.614))
cylinder('Replacement radius piston',elbow+Vector((-.012,0,-.015)),wrist+Vector((-.009,0,.018)),.005,STEEL,'LowerArm_L','grip')
cylinder('Replacement ulna piston',elbow+Vector((.012,0,-.015)),wrist+Vector((.009,0,.018)),.005,BRASS,'LowerArm_L','grip')
cylinder('Restorative elbow spindle',(.170,-.003,.761),(.206,-.003,.761),.019,STEEL,'LowerArm_L','grip')
tube('Small fitted teal forearm shell',[(.194,-.004,.736),(.201,-.009,.706),(.209,-.021,.661)],[(.022,.018),(.021,.017),(.014,.013)],TEAL,'LowerArm_L','grip',sides=20,res=1)
for s in [-1,1]:line('Restorative flexible cable',[(.189+s*.020,.012,.748),(.196+s*.023,.014,.711),(.212+s*.014,.002,.655)],.0027,DARK,'LowerArm_L','grip')
torus('Fitted prosthetic cuff',(.188,-.003,.770),.023,.005,LEATHER,'LowerArm_L',rot=(0,.15,0),variant='grip')
box('Replacement palm',(.227,-.043,.582),(.039,.027,.054),STEEL,'Hand_L',.009,'grip')
box('Teal knuckle service plate',(.227,-.059,.588),(.033,.005,.030),TEAL,'Hand_L',.002,'grip')
for j in range(4):
    fx=.227+(j-1.5)*.012;zz=.563-(.008 if j in [0,3] else 0)
    fp=[(fx,-.046,zz+.01),(fx+.004,-.049,zz-.011),(fx+.003,-.060,zz-.028),(fx,-.070,zz-.032)]
    for k in range(3):
        cylinder('Articulated replacement finger',fp[k],fp[k+1],.0042,STEEL,['Index','Middle','Ring','Little'][j]+str(k+1)+'_L','grip',vertices=12)
        ell('Replacement finger hinge',fp[k],(.0049,.005,.0049),BRASS,['Index','Middle','Ring','Little'][j]+str(k+1)+'_L','grip',seg=12,rings=8)
    rivet((fx,-.062,.587),'Hand_L',BRASS,.002,'grip')
for a,b in zip([(.206,-.042,.594),(.193,-.055,.581)],[ (.193,-.055,.581),(.190,-.066,.565)]):cylinder('Restorative thumb',a,b,.005,STEEL,'Hand_L','grip',vertices=12)

# Light restorative lower right leg, regular stride and boot envelope.
cylinder('Replacement lower leg rod',(-.075,.008,.208),(-.075,.004,.070),.010,STEEL,'Shin_R','leg')
tube('Restorative shin shield',[(-.075,-.003,.202),(-.075,-.009,.17),(-.075,-.010,.104)],[(.024,.017),(.023,.016),(.016,.011)],TEAL,'Shin_R','leg',sides=20,res=1)
for x in [-.09,-.06]:cylinder('Slim shin guide',(x,.016,.196),(x,.014,.087),.004,BRASS,'Shin_R','leg')
cylinder('Restorative ankle pivot',(-.098,.001,.071),(-.052,.001,.071),.013,STEEL,'Foot_R','leg')
ell('Regular prosthetic foot',(-.075,-.034,.035),(.033,.064,.024),STEEL,'Foot_R','leg')
box('Restorative foot sole',(-.075,-.026,.012),(.073,.133,.020),DARK,'Foot_R',.008,'leg')
for yy in [-.075,-.045,-.010]:box('Foot articulated plate',(-.075,yy,.049),(.061,.023,.008),TEAL,'Foot_R',.004,'leg')
for z in [.178,.196]:torus('Replacement leg cloth cuff',(-.075,.007,z),.025,.004,CLOTH,'Shin_R',rot=(0,0,0),variant='leg')

# Rifle exists as a compact workmanlike benchmark prop on the right hand.
box('Compact salvage carbine receiver',(-.235,-.076,.589),(.037,.082,.038),TEAL,'Hand_R',.005)
cylinder('Carbine barrel',(-.235,-.10,.602),(-.235,-.221,.602),.009,STEEL,'Hand_R')
cylinder('Carbine muzzle',(-.235,-.205,.602),(-.235,-.233,.602),.012,STEEL,'Hand_R')
box('Carbine wood stock',(-.235,.006,.596),(.032,.083,.031),LEATHER,'Hand_R',.004)
box('Carbine lower grip',(-.235,-.078,.562),(.023,.025,.053),LEATHER,'Hand_R',.004)
box('Carbine magazine',(-.235,-.109,.566),(.025,.031,.045),STEEL,'Hand_R',.003)

# In the relaxed pose the carbine hangs muzzle-down; the aiming arm raises it forward.
weapon_grip=Vector((-.235,-.078,.562));weapon_pivot=Vector((-.227,-.043,.582));weapon_turn=Matrix.Rotation(math.pi/2,4,'X')
for obj in OBJECTS:
    if 'carbine' in obj.name.lower():
        obj.matrix_world=Matrix.Translation(weapon_pivot)@weapon_turn@Matrix.Translation(-weapon_grip)@obj.matrix_world

print('NIB_STAGE united anatomy',flush=True)
build_continuous_anatomy(globals())
# Sparse fine fuzz preserves visible concept skin; denser cinematic source uses
# the same coverage and silhouette without a fur-covered body redesign.
for surface in [o for o in list(OBJECTS) if o.get('bone') in ['BodyAnatomy','FaceSurface']]:
    facial=surface.get('bone')=='FaceSurface';candidates=[]
    for vertex in surface.data.vertices:
        point=surface.matrix_world@vertex.co;normal=(surface.matrix_world.to_3x3()@vertex.normal).normalized()
        if facial:
            if point.y<.01 and 1.077<point.z<1.200 and normal.y<-.15:candidates.append((point,normal))
        elif abs(point.x)>.125 or point.z>.965:candidates.append((point,normal))
    guides=[]
    for strand in range((1100 if facial else 2300)*FUR_MULTIPLIER):
        point,normal=random.choice(candidates);root=point+normal*.00008
        length=random.uniform(.0007,.0015) if facial else random.uniform(.001,.0025)
        tip=root+normal*length+Vector((0,0,-length*.30));mid=root.lerp(tip,.5)+normal*length*.10
        guides.append((root,mid,tip,random.uniform(.000025,.000055)))
    fuzz=fur_mesh('Fine skin fuzz '+surface.get('variant','all'),guides,surface['bone'],HAIR,surface.get('variant','all'))
    if facial:add_shapes(fuzz)
print('NIB_STAGE rig',flush=True)
# Shorter exposed neck matches the reference proportions.
for obj in OBJECTS:
    tag=obj.get('bone','')
    if tag in FACE_BONES or tag in ['Head','FaceSurface'] or tag.startswith('Ear_'):
        obj.location.z+=HEAD_DROP

# Rig, weighting, clips. Every component is editable in source, standalone variants export.
armdata=bpy.data.armatures.new('Nib_Rig');rig=bpy.data.objects.new('Nib_Rig',armdata);scene.collection.objects.link(rig)
bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
BONES={}
def bone(name,head,tail,parent=None):
    if name in FACE_BONES or name=='Head' or name.startswith('Ear_'):
        head=Vector(head)+Vector((0,0,HEAD_DROP));tail=Vector(tail)+Vector((0,0,HEAD_DROP))
    b=armdata.edit_bones.new(name);b.head=head;b.tail=tail
    if parent:b.parent=armdata.edit_bones[parent]
    b.align_roll(Vector((0,-1,0)));BONES[name]=(Vector(head),Vector(tail));return b
bone('Root',(0,0,0),(0,0,.12));bone('Pelvis',(0,0,.59),(0,0,.70),'Root');bone('Spine',(0,0,.70),(0,0,.85),'Pelvis');bone('Chest',(0,0,.85),(0,0,.965),'Spine');bone('Neck',(0,0,.965),(0,0,1.055+HEAD_DROP),'Chest');bone('Head',(0,0,1.055),(0,0,1.235),'Neck')
for name,(start,end,parent) in FACE_BONES.items():bone(name,start,end,parent)
for s,label in [(1,'L'),(-1,'R')]:
    bone('Clavicle_'+label,(0,0,.94),(s*.128,.005,.938),'Chest')
    bone('UpperArm_'+label,(s*.128,.005,.938),(s*.189,-.003,.769),'Clavicle_'+label)
    bone('LowerArm_'+label,(s*.189,-.003,.769),(s*.218,-.031,.614),'UpperArm_'+label)
    bone('Hand_'+label,(s*.218,-.031,.614),(s*.227,-.052,.56),'LowerArm_'+label)
    bone('Thigh_'+label,(s*.066,.009,.594),(s*.073,.015,.35),'Pelvis')
    bone('Shin_'+label,(s*.073,.015,.35),(s*.075,.004,.10),'Thigh_'+label)
    bone('Foot_'+label,(s*.075,.004,.10),(s*.075,-.065,.035),'Shin_'+label)
    bone('Toe_'+label,(s*.075,-.065,.035),(s*.075,-.093,.031),'Foot_'+label)
    bone('Ear_'+label,(s*.066,0,1.208),(s*.232,.03,1.38),'FaceRoot')
for key,points in FINGER_CHAINS.items():
    finger,side=key.split('_')
    for j in range(len(points)-1):
        bone(finger+str(j+1)+'_'+side,points[j],points[j+1],'Hand_'+side if j==0 else finger+str(j)+'_'+side)
bone('Weapon',(-.227,-.043,.582),(-.227,-.083,.427),'Hand_R')
bone('WeaponMuzzle',(-.227,-.083,.427),(-.227,-.083,.387),'Weapon')
bone('WeaponAim',(-.227,-.083,.387),(-.227,-.083,.367),'WeaponMuzzle')
bpy.ops.object.mode_set(mode='OBJECT');rig.select_set(False);rig.show_in_front=True

def weights(o):
    tag=o['bone'];groups={}
    if tag=='BodyAnatomy':names=['Neck','Chest','Spine','UpperArm_L','LowerArm_L','UpperArm_R','LowerArm_R']
    elif tag=='FaceSurface':names=['Head','Jaw']
    elif tag.startswith('Finger_'):
        key=tag[len('Finger_'):];finger,side=key.split('_');chain=FINGER_CHAINS[key];names=[finger+str(j+1)+'_'+side for j in range(len(chain)-1)]
    elif tag=='Torso':names=['Pelvis','Spine','Chest']
    elif tag.startswith('Leg_'):names=['Thigh_'+tag[-1],'Shin_'+tag[-1],'Pelvis']
    elif tag.startswith('UpperArm_'):names=[tag,'LowerArm_'+tag[-1],'Chest']
    elif tag.startswith('Arm_'):names=['UpperArm_'+tag[-1],'LowerArm_'+tag[-1],'Chest']
    else:names=[tag]
    for n in names:groups[n]=o.vertex_groups.new(name=n)
    for v in o.data.vertices:
        p=o.matrix_world@v.co
        if tag=='BodyAnatomy':ww=anatomical_weights(p,BONES)
        elif tag=='FaceSurface':
            z=p.z-HEAD_DROP;front=max(0,min(1,(-p.y+.010)/.050));jaw=max(0,min(1,(1.122-z)/.035))*front
            if abs(p.x)<.045 and p.y<-.055 and 1.101<z<1.117:
                line=1.1105+.0015*(p.x/.036)**3
                jaw=max(0,min(1,(line+.0006-z)/.0012))
            ww={'Head':1-jaw,'Jaw':jaw}
        elif tag.startswith('Finger_'):
            distances=[]
            for i in range(len(chain)-1):
                delta=chain[i+1]-chain[i];t=max(0,min(1,(p-chain[i]).dot(delta)/delta.length_squared));distances.append(((p-chain[i].lerp(chain[i+1],t)).length,i,t))
            _,i,t=min(distances)
            blend=max(0,min(1,(t-.60)/.40)) if i<len(names)-1 else 0
            ww={names[i]:1-blend}
            if blend:ww[names[i+1]]=blend
        elif tag=='Torso':
            if p.z<.75:t=max(0,min(1,(p.z-.64)/.12));ww={'Pelvis':1-t,'Spine':t}
            else:t=max(0,min(1,(p.z-.79)/.12));ww={'Spine':1-t,'Chest':t}
        elif tag.startswith('Leg_'):
            t=max(0,min(1,(.395-p.z)/.085));waist=max(0,min(1,(p.z-.565)/.070));ww={names[0]:(1-t)*(1-waist),names[1]:t*(1-waist),'Pelvis':waist}
        elif tag.startswith('UpperArm_') or tag.startswith('Arm_'):
            t=max(0,min(1,(.800-p.z)/.045));a,b=BONES[names[0]];along=(p-a).dot((b-a).normalized());shoulder=max(0,min(1,(.025-along)/.050));ww={names[0]:(1-t)*(1-shoulder),names[1]:t*(1-shoulder),'Chest':shoulder}
        else:ww={names[0]:1}
        for n,w in ww.items():
            if w>0:groups[n].add([v.index],w,'REPLACE')
    mod=o.modifiers.new('Nib deformation','ARMATURE');mod.object=rig;o.parent=rig

for o in OBJECTS:
    if o.type=='MESH':
        if not o.data.uv_layers:uv(o)
        o.data.uv_layers.active.name='UVMap';weights(o)

scene.render.fps=30
def reset_pose():
    for pb in rig.pose.bones:pb.rotation_mode='XYZ';pb.rotation_euler=(0,0,0);pb.location=(0,0,0);pb.scale=(1,1,1)
def setrot(name,x=0,y=0,z=0):rig.pose.bones[name].rotation_euler=tuple(math.radians(v) for v in (x,y,z))
def keyall(frame):
    for pb in rig.pose.bones:
        pb.keyframe_insert('rotation_euler',frame=frame);pb.keyframe_insert('location',frame=frame)

ACTIONS, DEFORMATION, LOCOMOTION=build_animation(globals())
scene['source_version']='v4 closed facial fit / united shoulder anatomy review candidate'
scene['deformation_contract']=json.dumps(DEFORMATION)
scene['locomotion_contract']=json.dumps(LOCOMOTION)

# Source always opens on organic Nib, variants and components preserved in one file.
def visible_for(o,variant):
    tag=o.get('variant','all')
    if tag=='all':return True
    if tag=='organic':return variant!='grip'
    if tag=='natural':
        name=o.name
        isleftarm=(' L' in name or '.L' in name) and any(w in name for w in ['forearm','Elbow','wrap','glove','Finger','Thumb','Fingernail','Set rivet'])
        # Region is reliable from bone contract, not natural-language object names.
        region=o.get('bone','')
        if variant=='grip' and (region in ['Arm_L','LowerArm_L','Hand_L'] or (region.endswith('_L') and any(region.startswith(n) for n in ['Finger_','Index','Middle','Ring','Little','Thumb']))):return False
        if variant=='leg' and region in ['Shin_R','Foot_R']:return False
        return True
    return tag==variant

for o in OBJECTS:o.hide_render=not visible_for(o,'natural');o.hide_set(o.hide_render)
scene['asset_status']='Authored benchmark candidate; visual likeness requires user review. Not a certified production master.'
scene['reference']='krag-kings-design/concept-art/02-nib-character-sheet.png; 05-jetpack-bionics-sheet.png'
scene['bionic_rule']='Nib variants have one functional lightweight replacement; no upgrade bonus or heavy augmentation.'

# A neutral studio setup records actual mesh evidence. Renderer kept separate from exports.
def aim(o,p):o.rotation_euler=(Vector(p)-o.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(location=(2.3,-4.5,1.90));camera=bpy.context.object;camera.name='Nib_Review_Camera';camera.data.type='ORTHO';camera.data.ortho_scale=1.78;aim(camera,(0,0,.75));scene.camera=camera
def light(name,loc,power,size,color):
    bpy.ops.object.light_add(type='AREA',location=loc);o=bpy.context.object;o.name=name;o.data.energy=power;o.data.shape='DISK';o.data.size=size;o.data.color=color;aim(o,(0,0,.8))
light('Warm key',(-2,-3,4),450,3.0,(1,.87,.70));light('Soft fill',(3,-2,2),260,2.5,(.74,.86,1));light('Rim',(0,2,3),600,2,(1,.90,.74))
bpy.ops.mesh.primitive_plane_add(size=200);floor=bpy.context.object;floor.name='Review sandy floor';floor.data.materials.append(CLOTH)
scene.world.color=(.23,.23,.23);scene.render.resolution_x=1400;scene.render.resolution_y=1600;scene.render.resolution_percentage=100
scene.view_settings.view_transform='AgX';scene.render.image_settings.file_format='PNG'
# Explicit texture paths are relative after saving for portable source.
blend_path=ART/('Nib_Cinematic.blend' if CINEMATIC else 'Nib_Master.blend');bpy.ops.wm.save_as_mainfile(filepath=str(blend_path),compress=True)
for im in bpy.data.images:
    if im.filepath:im.filepath=bpy.path.relpath(im.filepath,start=str(ART))
bpy.ops.wm.save_as_mainfile(filepath=str(blend_path),compress=True)

report={'sourceVersion':scene['source_version'],'sourceSha256':hashlib.sha256(blend_path.read_bytes()).hexdigest(),'codeSha256':{name:hashlib.sha256((Path(__file__).parent/name).read_bytes()).hexdigest() for name in ['create_nib.py','nib_face.py','nib_animation.py','nib_anatomy.py']},'boneCount':len(rig.data.bones),'bones':[b.name for b in rig.data.bones],'nativeCompressed':True,'furRepresentation':'Skinned opaque geometric strands; no simulation','furStrands':sum(int(o.get('fur_strands',0)) for o in OBJECTS),'furTriangles':sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in OBJECTS if o.get('fur_strands')),'cinematic':CINEMATIC,'componentCount':len(OBJECTS),'verticesAllComponents':sum(len(o.data.vertices) for o in OBJECTS if o.type=='MESH'),'trianglesAllComponents':sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in OBJECTS if o.type=='MESH'),'shapeNames':sorted({k.name for o in OBJECTS if o.type=='MESH' and o.data.shape_keys for k in o.data.shape_keys.key_blocks if k.name!='Basis'}),'clips':{a.name:{'startFrame':int(a.frame_range[0]),'endFrame':int(a.frame_range[1]),'durationSeconds':(a.frame_range[1]-a.frame_range[0])/scene.render.fps} for a in ACTIONS},'status':'Unaccepted review candidate; no AAA likeness claim'}
(ART/('cinematic-source-report.json' if CINEMATIC else 'source-report.json')).write_text(json.dumps(report,indent=2))
print('NIB_SOURCE_GENERATED_EXPORT_AND_REVIEW_SEPARATELY '+json.dumps(report),flush=True)
