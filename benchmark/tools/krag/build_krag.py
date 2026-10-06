"""Editable Krag sculpt, modular mechanisms, weighted rig and reusable motion clips.
Run Blender 5.2 --background --python <this script>. All units metres, front -Y.
Original concept sheets 01 and 07 are visual authority. Authored geometry with
provenance-recorded CC0 skin material inputs; pending source pass is unaccepted.
"""
import bpy, math, random, json, os, sys, time
from mathutils import Vector, Matrix
from pathlib import Path
from math import sin, cos, pi
sys.path.insert(0,str(Path(__file__).resolve().parent))
import krag_face, krag_locomotion, krag_cloth, krag_anatomy, krag_armor, krag_full_leg, krag_harness, krag_head_v9
random.seed(483)
ROOT=Path(__file__).resolve().parents[3]
ART=ROOT/'benchmark/art/krag'
def path_argument(name,default):return Path(sys.argv[sys.argv.index(name)+1]) if name in sys.argv else default
OUT=path_argument('--output-dir',ROOT/'benchmark/shared/characters/krag');TEX=OUT/'textures'
MASTER_PATH=path_argument('--master-path',ART/'Krag_Master.blend')
for p in [ART,OUT,TEX,ART/'renders']: p.mkdir(parents=True,exist_ok=True)
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
for x in list(bpy.data.materials): bpy.data.materials.remove(x)
scene=bpy.context.scene; scene.unit_settings.system='METRIC'; scene.unit_settings.scale_length=1
parts=[]; groups={}; materials={}
def log(x): print('KRAG:',x,flush=True)
def hand_rest(p,side):
    s=1 if side=='L' else -1;q=Vector(p);pivot=Vector((s*.599,-.019,1.043));u=max(0,min(1,(1.11-q.z)/.105));u=u*u*(3-2*u);a=-s*pi/2*u
    d=q-pivot;return pivot+Vector((d.x*cos(a)-d.y*sin(a),d.x*sin(a)+d.y*cos(a),d.z))
def mark(o,group,bone=None):
    o['module']=group
    if bone:o['rig_bone']=bone
    parts.append(o); groups.setdefault(group,[]).append(o)
    return o

def mat(name,color,metal=0,rough=.6,kind='plain'):
    m=bpy.data.materials.new(name); m.use_nodes=True; n=m.node_tree.nodes;l=m.node_tree.links;n.clear()
    out=n.new('ShaderNodeOutputMaterial'); bs=n.new('ShaderNodeBsdfPrincipled');l.new(bs.outputs['BSDF'],out.inputs['Surface']);bs.inputs['Metallic'].default_value=metal;bs.inputs['Roughness'].default_value=rough
    tex=n.new('ShaderNodeTexCoord');noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value={'skin':80,'cloth':650,'leather':95,'paint':42,'metal':120}.get(kind,45);noise.inputs['Detail'].default_value=4;l.new(tex.outputs['Object'],noise.inputs['Vector'])
    ramp=n.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].position=.23;ramp.color_ramp.elements[1].position=.78
    ramp.color_ramp.elements[0].color=tuple(c*(.80 if kind=='cloth' else .48) for c in color)+(1,);ramp.color_ramp.elements[1].color=tuple(min(1,c*(1.07 if kind=='cloth' else 1.2)) for c in color)+(1,);l.new(noise.outputs['Fac'],ramp.inputs[0])
    bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.35;bump.inputs['Distance'].default_value=.0012 if kind in ('metal','paint') else (.00035 if kind=='cloth' else .0018);l.new(noise.outputs['Fac'],bump.inputs['Height']);l.new(bump.outputs['Normal'],bs.inputs['Normal'])
    if kind=='skin':
        pore=n.new('ShaderNodeTexNoise');pore.inputs['Scale'].default_value=370;pore.inputs['Detail'].default_value=3;l.new(tex.outputs['Object'],pore.inputs['Vector']);fine=n.new('ShaderNodeBump');fine.inputs['Strength'].default_value=.30;fine.inputs['Distance'].default_value=.0008;l.new(pore.outputs['Fac'],fine.inputs['Height']);l.new(fine.outputs['Normal'],bump.inputs['Normal'])
        vor=n.new('ShaderNodeTexVoronoi');vor.feature='DISTANCE_TO_EDGE';vor.inputs['Scale'].default_value=24;warp=n.new('ShaderNodeTexNoise');warp.inputs['Scale'].default_value=7;warp.inputs['Detail'].default_value=2;l.new(tex.outputs['Object'],warp.inputs['Vector']);mul=n.new('ShaderNodeVectorMath');mul.operation='SCALE';mul.inputs['Scale'].default_value=.054;l.new(warp.outputs['Color'],mul.inputs[0]);add=n.new('ShaderNodeVectorMath');add.operation='ADD';l.new(tex.outputs['Object'],add.inputs[0]);l.new(mul.outputs[0],add.inputs[1]);l.new(add.outputs[0],vor.inputs['Vector'])
        cr=n.new('ShaderNodeValToRGB');cr.color_ramp.elements[0].position=.008;cr.color_ramp.elements[0].color=(.12,.075,.036,1);cr.color_ramp.elements[1].position=.050;cr.color_ramp.elements[1].color=(1,1,1,1);l.new(vor.outputs['Distance'],cr.inputs[0])
        mix=n.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=.43;l.new(ramp.outputs['Color'],mix.inputs[1]);l.new(cr.outputs['Color'],mix.inputs[2]);l.new(mix.outputs[0],bs.inputs['Base Color'])
        b2=n.new('ShaderNodeBump');b2.inputs['Strength'].default_value=.55;b2.inputs['Distance'].default_value=.0035;l.new(vor.outputs['Distance'],b2.inputs['Height']);l.new(bump.outputs['Normal'],b2.inputs['Normal']);l.new(b2.outputs[0],bs.inputs['Normal']);bs.inputs['Subsurface Weight'].default_value=.035
    elif kind=='cloth':
        soil=n.new('ShaderNodeTexNoise');soil.inputs['Scale'].default_value=9;soil.inputs['Detail'].default_value=3;soil.inputs['Roughness'].default_value=.7;l.new(tex.outputs['Object'],soil.inputs['Vector'])
        wear=n.new('ShaderNodeValToRGB');wear.color_ramp.elements[0].position=.27;wear.color_ramp.elements[0].color=(.38,.28,.19,1);wear.color_ramp.elements[1].position=.73;wear.color_ramp.elements[1].color=(1,1,1,1);l.new(soil.outputs['Fac'],wear.inputs[0])
        aged=n.new('ShaderNodeMixRGB');aged.blend_type='MULTIPLY';aged.inputs[0].default_value=.55;l.new(ramp.outputs[0],aged.inputs[1]);l.new(wear.outputs[0],aged.inputs[2]);l.new(aged.outputs[0],bs.inputs['Base Color'])
    elif kind=='paint':
        rust=n.new('ShaderNodeValToRGB');rust.color_ramp.elements[0].position=.37;rust.color_ramp.elements[0].color=(.18,.082,.025,1);rust.color_ramp.elements[1].position=.43;rust.color_ramp.elements[1].color=(*color,1);l.new(noise.outputs[0],rust.inputs[0]);l.new(rust.outputs[0],bs.inputs['Base Color'])
    else:l.new(ramp.outputs[0],bs.inputs['Base Color'])
    materials[name]=m;return m
skin=mat('Krag_SandstoneSkin',(.31,.163,.068),0,.73,'skin');cloth=mat('Krag_DesertCanvas',(.28,.205,.13),0,.9,'cloth');leather=mat('Krag_OiledLeather',(.085,.044,.017),0,.67,'leather');paint=mat('Krag_WeatheredTeal',(.046,.104,.101),.72,.58,'paint');steel=mat('Krag_BlackenedSteel',(.074,.075,.070),.82,.51,'metal');brass=mat('Krag_AgedBrass',(.31,.166,.047),.72,.49,'metal');bone=mat('Krag_Ivory',(.52,.405,.25),0,.39);dark=mat('Krag_Recess',(.023,.012,.006),0,.8);iris=mat('Krag_Amber',(.68,.27,.014),.1,.25);eye=mat('Krag_EyeWhite',(.045,.024,.011),0,.24);copper=mat('Krag_CopperHose',(.39,.13,.055),.65,.35,'metal')

# The generic material recipe's 1.8mm bump is inappropriate on centimetre-size
# optical surfaces. Preserve the fitted curvature; iris pigment relief, if
# enabled, is authored separately in true ocular coordinates at 18 micrometres.
for ocular,roughness in [(eye,.16),(iris,.20)]:
    optical_bs=next(node for node in ocular.node_tree.nodes if node.type=='BSDF_PRINCIPLED')
    for link in list(optical_bs.inputs['Normal'].links):ocular.node_tree.links.remove(link)
    optical_bs.inputs['Metallic'].default_value=0
    optical_bs.inputs['Roughness'].default_value=roughness
    ocular['surface_representation']='Smooth opaque curved optical shell; generic millimetre noise bump removed'


# CC0 scanned fracture microstructure replaces uniform procedural cells on sandstone skin.
# Original source files, authors, URLs and hashes are retained under reference-materials.
scan_root=ART/'reference-materials/mud_cracked_dry_03'
if (scan_root/'mud_cracked_dry_03_diff_2k.jpg').exists():
    n=skin.node_tree.nodes;l=skin.node_tree.links;n.clear();out=n.new('ShaderNodeOutputMaterial');bs=n.new('ShaderNodeBsdfPrincipled');l.new(bs.outputs[0],out.inputs[0]);bs.inputs['Subsurface Weight'].default_value=.028
    tc=n.new('ShaderNodeTexCoord')
    maps={}
    for ch in ['diff','disp','rough']:
        im=bpy.data.images.load(str(scan_root/('mud_cracked_dry_03_'+ch+'_2k.jpg')),check_existing=True);im.colorspace_settings.name='sRGB' if ch=='diff' else 'Non-Color';node=n.new('ShaderNodeTexImage');node.image=im;node.projection='BOX';node.projection_blend=.24;node.extension='REPEAT';mapping=n.get('Skin physical scale')
        if mapping is None:
            mapping=n.new('ShaderNodeVectorMath');mapping.name='Skin physical scale';mapping.operation='SCALE';mapping.inputs['Scale'].default_value=2.1;l.new(tc.outputs['Object'],mapping.inputs[0])
        l.new(mapping.outputs[0],node.inputs['Vector']);maps[ch]=node
    tint=n.new('ShaderNodeMixRGB');tint.blend_type='MULTIPLY';tint.inputs[0].default_value=1;tint.inputs[2].default_value=(.55,.36,.19,1);l.new(maps['diff'].outputs['Color'],tint.inputs[1]);l.new(tint.outputs[0],bs.inputs['Base Color'])
    fine=n.new('ShaderNodeTexNoise');fine.inputs['Scale'].default_value=430;fine.inputs['Detail'].default_value=3;l.new(tc.outputs['Object'],fine.inputs['Vector']);pores=n.new('ShaderNodeBump');pores.inputs['Strength'].default_value=.25;pores.inputs['Distance'].default_value=.0007;l.new(fine.outputs['Fac'],pores.inputs['Height'])
    relief=n.new('ShaderNodeBump');relief.inputs['Strength'].default_value=.62;relief.inputs['Distance'].default_value=.0018;l.new(maps['disp'].outputs['Color'],relief.inputs['Height']);l.new(pores.outputs[0],relief.inputs['Normal']);l.new(relief.outputs[0],bs.inputs['Normal'])
    rough=n.new('ShaderNodeMath');rough.operation='MULTIPLY_ADD';rough.inputs[1].default_value=.35;rough.inputs[2].default_value=.53;l.new(maps['rough'].outputs['Color'],rough.inputs[0]);l.new(rough.outputs[0],bs.inputs['Roughness'])

face_skin=skin.copy();face_skin.name='Krag_FacialSkin';materials[face_skin.name]=face_skin
if face_skin.node_tree.nodes.get('Skin physical scale'):face_skin.node_tree.nodes['Skin physical scale'].inputs['Scale'].default_value=4.6
for node in face_skin.node_tree.nodes:
    if node.type=='BUMP':node.inputs['Distance'].default_value*=.45
# Central facial skin carries pores and shaped expression folds. Broken large
# plates remain on the outer skull, rather than covering lips and eyelids.
face_nodes=face_skin.node_tree.nodes;face_links=face_skin.node_tree.links
face_bs=next(node for node in face_nodes if node.type=='BSDF_PRINCIPLED')
face_color_source=face_bs.inputs['Base Color'].links[0].from_socket
quiet=face_nodes.new('ShaderNodeMixRGB');quiet.name='Quieter central facial skin';quiet.blend_type='MIX';quiet.inputs[0].default_value=.76;quiet.inputs[2].default_value=(.185,.111,.054,1)
face_links.new(face_color_source,quiet.inputs[1]);face_links.new(quiet.outputs[0],face_bs.inputs['Base Color'])
region=face_nodes.new('ShaderNodeAttribute');region.attribute_name='Krag_SkinRegion'
regional_color=face_nodes.new('ShaderNodeMixRGB');regional_color.name='Continuous facial skin regions'
face_links.new(region.outputs['Fac'],regional_color.inputs[0]);face_links.new(quiet.outputs[0],regional_color.inputs[1]);face_links.new(face_color_source,regional_color.inputs[2]);face_links.new(regional_color.outputs[0],face_bs.inputs['Base Color'])
for node in face_nodes:
    if node.type=='BUMP' and node.inputs['Distance'].default_value>.0004:node.inputs['Distance'].default_value*=.35

def finish(o,name,ma,group,bn=None,smooth=True):
    if ma==skin and group in ['Head','Face','Eyelids_L','Eyelids_R']:ma=face_skin
    if group=='Face' and name in ['Eye globe','Amber iris','Pupil','Eye glint']:bn='Eye_'+('L' if o.location.x>0 else 'R')
    if group=='Face' and name=='Lower ivory tusk':bn='Jaw'
    o.name=name;o.data.materials.append(ma)
    if smooth and o.type=='MESH':
        for p in o.data.polygons:p.use_smooth=True
    return mark(o,group,bn)
def mesh(name,verts,faces,ma,group,bn=None):
    d=bpy.data.meshes.new(name);d.from_pydata(verts,[],faces);d.update();o=bpy.data.objects.new(name,d);bpy.context.collection.objects.link(o);return finish(o,name,ma,group,bn)
def uvball(name,p,s,ma=skin,group='Body',bn=None,seg=32,rings=20):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg,ring_count=rings,location=p);o=bpy.context.object;o.scale=s;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);return finish(o,name,ma,group,bn)
def box(name,p,s,ma,group,bn=None,bevel=.015):
    bpy.ops.mesh.primitive_cube_add(size=1,location=p);o=bpy.context.object;o.scale=s;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);finish(o,name,ma,group,bn)
    if bevel:
        mod=o.modifiers.new('Rounded worked edges','BEVEL');mod.width=bevel;mod.segments=3;mod.affect='EDGES';bpy.context.view_layer.objects.active=o;bpy.ops.object.modifier_apply(modifier=mod.name)
    return o
def tube(name,points,radii,ma,group,bn=None,n=12,cap=True):
    vs=[];fs=[]
    for i,p in enumerate(points):
        p=Vector(p);a=Vector(points[min(i+1,len(points)-1)])-Vector(points[max(i-1,0)]);a.normalize();u=a.cross(Vector((0,1,0)))
        if u.length<.1:u=a.cross(Vector((1,0,0)))
        u.normalize();v=a.cross(u).normalized();r=radii[i] if hasattr(radii,'__len__') else radii
        for j in range(n):vs.append(p+r*(cos(2*pi*j/n)*u+sin(2*pi*j/n)*v))
    for i in range(len(points)-1):
        for j in range(n):a=i*n+j;b=i*n+(j+1)%n;fs.append((a,b,b+n,a+n))
    if cap:fs.extend([tuple(reversed(range(n))),tuple((len(points)-1)*n+j for j in range(n))])
    return mesh(name,vs,fs,ma,group,bn)
def cyl(name,a,b,r,ma,group,bn=None,n=24):return tube(name,[a,b],[r,r],ma,group,bn,n)
def torus(name,p,major,minor,ma,group,bn=None,rot=(pi/2,0,0)):
    bpy.ops.mesh.primitive_torus_add(major_segments=40,minor_segments=10,location=p,major_radius=major,minor_radius=minor,rotation=rot);return finish(bpy.context.object,name,ma,group,bn)
def loft(name,rings,ma,group,bn=None,n=48,fold=0):
    vs=[];fs=[]
    if fold and len(rings)>5:
        expanded=[]
        for a,b in zip(rings[:-1],rings[1:]):
            for k in range(4):expanded.append(tuple(a[j]+(b[j]-a[j])*k/4 for j in range(5)))
        rings=expanded+[rings[-1]]
    for i,(z,x,y,rx,ry) in enumerate(rings):
        for j in range(n):
            t=2*pi*j/n;f=1+fold*(.5*sin(7*t+z*21)+.3*sin(13*t-z*11));wr=fold*.10*(sin(z*115+2*sin(t*3))+.5*sin(z*190-t*3))*math.exp(-((z-.39)/.20)**2);vs.append((x+(rx*f+wr)*cos(t),y+(ry*f+wr)*sin(t),z+.002*fold*sin(t*9+i)))
    for i in range(len(rings)-1):
        for j in range(n):a=i*n+j;b=i*n+(j+1)%n;fs.append((a,b,b+n,a+n))
    fs.extend([tuple(reversed(range(n))),tuple((len(rings)-1)*n+j for j in range(n))]);return mesh(name,vs,fs,ma,group,bn)
def join_sculpt(objs,name,voxel=.006,iterations=3):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:o.select_set(True)
    bpy.context.view_layer.objects.active=objs[0];bpy.ops.object.join();o=objs[0];o.name=name
    re=o.modifiers.new('Unified anatomical sculpt','REMESH');re.mode='VOXEL';re.voxel_size=voxel;bpy.ops.object.modifier_apply(modifier=re.name)
    sm=o.modifiers.new('Anatomical surface blend','SMOOTH');sm.factor=.72;sm.iterations=iterations;bpy.ops.object.modifier_apply(modifier=sm.name)
    for p in o.data.polygons:p.use_smooth=True
    return o

def ribbon(name,points,width,ma,group,bn=None,thick=.009):
    verts=[]
    for i,p in enumerate(points):
        t=Vector(points[min(i+1,len(points)-1)])-Vector(points[max(0,i-1)]);w=Vector((t.z,0,-t.x)).normalized()*width*.5;verts.extend([Vector(p)-w,Vector(p)+w])
    o=mesh(name,verts,[(2*i,2*i+1,2*i+3,2*i+2) for i in range(len(points)-1)],ma,group,bn);sol=o.modifiers.new('Material thickness','SOLIDIFY');sol.thickness=thick;bpy.context.view_layer.objects.active=o;bpy.ops.object.modifier_apply(modifier=sol.name);bev=o.modifiers.new('Soft cut edges','BEVEL');bev.width=.003;bev.segments=2;bpy.ops.object.modifier_apply(modifier=bev.name);return o

log('Continuous Krag anatomical cage adaptation')
anatomical_source=krag_anatomy.build(globals())
if '--continuous-head' in sys.argv:
    head=krag_head_v9.build(globals())
else:
    # Head is a single unified sculpt; amber eyes are deliberately deep below the brow.
    headparts=[]
    def hp(name,p,s):o=uvball(name,p,s,skin,'Head','Head');headparts.append(o);return o
    hp('Cranium',(0,.009,1.932),(.166,.141,.175));hp('Frontal bone',(0,-.083,2.007),(.150,.085,.090));hp('Occiput',(0,.077,1.93),(.133,.099,.15));hp('Broad jaw',(0,-.040,1.811),(.149,.126,.103));hp('Chin',(0,-.162,1.801),(.119,.061,.068));hp('Muzzle',(0,-.139,1.870),(.125,.070,.054));hp('Nose bridge',(0,-.131,1.96),(.043,.052,.068));hp('Nose',(0,-.191,1.925),(.047,.042,.035))
    for s in [-1,1]:
        hp('Zygomatic arch',(s*.094,-.117,1.914),(.057,.042,.062));hp('Temple',(s*.121,-.011,1.968),(.045,.102,.083));b=hp('Heavy angular brow',(s*.071,-.145,1.986),(.076,.049,.028));b.rotation_euler.y=s*-.40
        hp('Nasal wing',(s*.035,-.185,1.917),(.026,.038,.022));hp('Masseter',(s*.108,-.030,1.84),(.044,.091,.086));hp('Ear cartilage',(s*.155,.012,1.949),(.031,.021,.052));hp('Lower orbital tissue',(s*.070,-.144,1.946),(.042,.032,.024))
    head=join_sculpt(headparts,'Head_Sculpt',.0018,6);head['rig_bone']='Head'
    # Ear concha, lips, nostrils, folded creases, ivory lower tusks.
    for s in [-1,1]:
        uvball('Ear concha',(s*.163,-.006,1.947),(.013,.009,.029),dark,'Face','Head')
        torus('Ear helix',(s*.161,-.007,1.949),.022,.006,skin,'Face','Head').scale=(.62,1,1.45)
        uvball('Eye globe',(s*.071,-.165,1.964),(.022,.020,.016),eye,'Face','Head',seg=48,rings=32)
        uvball('Amber iris',(s*.071,-.1852,1.964),(.0078,.0017,.0078),iris,'Face','Head',seg=40,rings=24)
        uvball('Pupil',(s*.071,-.187,1.964),(.0028,.0008,.0030),dark,'Face','Head',seg=32,rings=20)
        eye_bone='Eye_'+('L' if s>0 else 'R')
        torus('Iris limbal edge',(s*.071,-.1864,1.964),.0078,.00045,dark,'Face',eye_bone)
        for ray in range(28):
            a=2*pi*ray/28;radius=.0068+.0007*sin(ray*2.8);r0=.0034+.0005*cos(ray*1.8)
            tube('Fine iris stria',[(s*.071+r0*cos(a),-.1867,1.964+r0*sin(a)),(s*.071+radius*cos(a+.025),-.1862,1.964+radius*sin(a+.025))],[.00009,.00015],brass if ray%4 else dark,'Face',eye_bone,5)
        uvball('Eye glint',(s*.068,-.188,1.967),(.00075,.0004,.00075),bone,'Face','Head',seg=12,rings=8)
        tube('Lower ivory tusk',[(s*.078,-.195,1.838),(s*.079,-.212,1.855),(s*.075,-.212,1.873)],[.009,.005,.0005],bone,'Face','Head',16)
        tube('Nose to jaw fold',[(s*.047,-.190,1.907),(s*.073,-.189,1.889),(s*.098,-.161,1.863)],[.003,.0035,.0015],skin,'Face','Head',8)
    # Mouth line depressed between broad lips.
    tube('Lower lip',[(-.080,-.183,1.819),(-.049,-.199,1.830),(0,-.207,1.833),(.049,-.199,1.830),(.080,-.183,1.819)],[.004,.007,.009,.007,.004],skin,'Face','Head',16)
    # Merge lip/ear/fold skin into the same deforming facial surface before cutting cavities.
    facial_skin_parts=[bpy.data.objects['Head_Sculpt']]+[o for o in bpy.data.objects if o.type=='MESH' and o.get('module')=='Face' and len(o.data.materials)>0 and o.data.materials[0]==face_skin]
    head=join_sculpt(facial_skin_parts,'Head_Sculpt',.0018,4);head['module']='Head';head['rig_bone']='Head'
    krag_face.geometry(globals())
# Partition the connected anatomical surface at the modular bionic boundaries.
log('Continuous torso-arm surface and anatomical partition')
skin_groups={'Body','BioArm_L','BioArm_R','BioForearm_L','BioForearm_R'}
unified=anatomical_source
bpy.context.view_layer.objects.active=unified;bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
unified.data.update();src=unified.data
source_arm_domain=None
source_hand_domains=None
if '--anatomical-domain' in sys.argv:
    import krag_skin_domains
    source_arm_domain=krag_skin_domains.read(src)
if '--topological-hands' in sys.argv:
    import krag_hand_domains
    source_hand_domains=krag_hand_domains.read(src)
bins={g:[] for g in skin_groups}
for poly in src.polygons:
    co=poly.center
    if abs(co.x)<.325:group='Body'
    else:
        side='L' if co.x>0 else 'R';sgn=1 if co.x>0 else -1
        elbow=Vector((sgn*.509,.008,1.30));axis=Vector((sgn*.09,-.02,-.257)).normalized()
        group=('BioForearm_' if (co-elbow).dot(axis)>0 else 'BioArm_')+side
    if not(group=='Body' and max(src.vertices[i].co.z for i in poly.vertices)<1.071):bins[group].append(poly)
for group,polys in bins.items():
    used=sorted(set(i for poly in polys for i in poly.vertices));index={v:i for i,v in enumerate(used)}
    dat=bpy.data.meshes.new(group+' continuous surface');dat.from_pydata([src.vertices[i].co for i in used],[],[tuple(index[i] for i in poly.vertices) for poly in polys]);dat.update()
    if source_arm_domain is not None:krag_skin_domains.attach(dat,source_arm_domain[used])
    if source_hand_domains is not None:krag_hand_domains.attach(dat,source_hand_domains[used])
    for ma in src.materials:dat.materials.append(ma)
    for a,b in zip(dat.polygons,polys):a.material_index=b.material_index;a.use_smooth=True
    try:dat.normals_split_custom_set_from_vertices([tuple(src.vertices[i].normal) for i in used])
    except Exception as e:log('Custom normal fallback '+str(e))
    o=bpy.data.objects.new(group,dat);bpy.context.collection.objects.link(o);mark(o,group)
bpy.data.objects.remove(unified,do_unlink=True)
log('Clothing, boots, harness and plate armor')
# Trousers as coherent folded surface; no modern upper-body clothing.
loft('Trouser seat',[(.885,0,.02,.083,.127),(.945,0,.02,.195,.169),(1.015,0,.02,.261,.190),(1.065,0,.02,.25,.185),(1.10,0,.02,.247,.175)],cloth,'Garments','Pelvis',fold=.025)
for s,side in [(-1,'R'),(1,'L')]:
    rings=[]
    for z,rx,ry,y in [(.25,.086,.084,0),(.28,.117,.105,.006),(.32,.113,.107,.007),(.36,.132,.115,.015),(.40,.113,.109,.018),(.45,.128,.111,.018),(.50,.132,.123,.020),(.55,.139,.122,-.005),(.60,.126,.123,-.020),(.66,.133,.130,-.025),(.73,.148,.144,-.009),(.82,.156,.152,.005),(.93,.157,.160,.018),(1.025,.130,.157,.018),(1.075,.100,.148,.018),(1.11,.080,.143,.018)]:rings.append((z,s*(.17+(1-z)*.03),y,rx,ry))
    loft('Trousers_upper_'+side,[r for r in rings if r[0]>=.55],cloth,'TrouserLeg_'+side,n=64,fold=.018)
    loft('Trousers_lower_'+side,[r for r in rings if r[0]<=.60],cloth,'BioLowerLeg_'+side,n=64,fold=.018)
    # Curved knee reinforcement follows the actual cloth surface; no buried flat centre.
    def knee_y(dx,zz):
        profile=[(.48,.019,.127,.118),(.55,-.005,.139,.122),(.60,-.020,.126,.123),(.67,-.024,.135,.132)]
        for aa,bb in zip(profile[:-1],profile[1:]):
            if aa[0]<=zz<=bb[0]:
                u=(zz-aa[0])/(bb[0]-aa[0]);yy=aa[1]+(bb[1]-aa[1])*u;rx=aa[2]+(bb[2]-aa[2])*u;ry=aa[3]+(bb[3]-aa[3])*u;return yy-ry*math.sqrt(max(.01,1-(dx/rx)**2))-.009
        return -.15
    patch_vertices=[];patch_faces=[]
    for iz in range(25):
        zz=.486+.176*iz/24
        for ix in range(21):
            dx=-.093+.186*ix/20;patch_vertices.append((s*.191+dx,knee_y(dx,zz),zz))
    for iz in range(24):
        for ix in range(20):k=iz*21+ix;patch_faces.append((k,k+1,k+22,k+21))
    patch=mesh('Contoured leather knee reinforcement',patch_vertices,patch_faces,leather,'TrouserLeg_'+side);solid=patch.modifiers.new('Knee leather thickness','SOLIDIFY');solid.thickness=.003;bpy.context.view_layer.objects.active=patch;bpy.ops.object.modifier_apply(modifier=solid.name)
    for dx in [-.083,.083]:
        for k in range(9):
            zz=.496+k*.018;tube('Knee saddle stitch',[(s*.191+dx,knee_y(dx,zz)-.002,zz),(s*.191+dx,knee_y(dx,zz+.007)-.002,zz+.007)],[.0012,.0012],cloth,'TrouserLeg_'+side,n=6)
    # Heavy stitched outside seam follows the volume of the trousers.
    for j in range(20):
        zz=.32+j*.034;xx=s*(.17+(1-zz)*.03+.114+(zz-.32)*.055)
        tube('Trouser side seam',[(xx,.018,zz),(xx,.018,zz+.021)],[.002,.002],leather,'BioLowerLeg_'+side if zz<.55 else 'TrouserLeg_'+side,'Shin_'+side if zz<.55 else 'Thigh_'+side,6)
    # Outside cargo pockets, flap and straps.
    pouch=box('Thigh cargo pocket',(s*.29,-.010,.827),(.091,.149,.196),leather,'TrouserLeg_'+side,bevel=.022)
    box('Cargo flap',(s*.302,-.045,.900),(.088,.155,.048),cloth,'TrouserLeg_'+side,bevel=.011)
    box('Cargo keeper',(s*.338,-.050,.850),(.014,.019,.086),leather,'TrouserLeg_'+side,bevel=.004)
    # Organic boot volume with broad rounded toe and ankle column.
    bootparts=[uvball('Boot toe',(s*.19,-.085,.099),(.116,.168,.087),leather,'Boot_'+side,'Foot_'+side),uvball('Boot heel',(s*.19,.049,.119),(.102,.096,.106),leather,'Boot_'+side,'Foot_'+side),loft('Boot shaft',[(.08,s*.19,.01,.105,.12),(.15,s*.19,.019,.099,.100),(.22,s*.19,.028,.102,.087),(.29,s*.19,.026,.109,.085)],leather,'Boot_'+side,'Foot_'+side,n=48,fold=.035)]
    boot=join_sculpt(bootparts,'Boot_'+side,.004);boot['rig_bone']='Foot_'+side
    sole=box('Layered boot sole',(s*.19,-.055,.034),(.224,.321,.041),steel,'Boot_'+side,'Foot_'+side,bevel=.035)
    vs=[];fs=[];rows=[(-.255,.079,.114),(-.240,.106,.145),(-.218,.116,.173),(-.190,.118,.182),(-.165,.117,.184)]
    for yy,rr,top in rows:
        for k in range(21):
            a=pi*k/20;vs.append((s*.19+rr*cos(a),yy,.052+(top-.052)*(max(0,sin(a))**.62)))
    for j in range(len(rows)-1):
        for k in range(20):a=j*21+k;fs.append((a,a+21,a+22,a+1))
    toe=mesh('Formed steel toe cover',vs,fs,steel,'Boot_'+side,'Foot_'+side);sol=toe.modifiers.new('Toe sheet thickness','SOLIDIFY');sol.thickness=.005;bpy.context.view_layer.objects.active=toe;bpy.ops.object.modifier_apply(modifier=sol.name)
    face_vertices=[];face_polys=[]
    for row in range(9):
        u=row/8
        for j in range(25):
            x=-.079+.158*j/24;top=.052+(.114-.052)*max(0,1-(x/.079)**2)**.40;face_vertices.append((s*.19+x,-.257+.008*(x/.079)**2,.047+(top-.047)*u))
    for row in range(8):
        for j in range(24):k=row*25+j;face_polys.append((k,k+1,k+26,k+25))
    toe_front=mesh('Closed formed front toe cap',face_vertices,face_polys,steel,'Boot_'+side,'Foot_'+side);thickness=toe_front.modifiers.new('Toe cap face thickness','SOLIDIFY');thickness.thickness=.004;bpy.context.view_layer.objects.active=toe_front;bpy.ops.object.modifier_apply(modifier=thickness.name)
    tube('Toe cover rolled rim',[(s*.19+rows[-1][1]*cos(pi*k/20),rows[-1][0],.052+(rows[-1][2]-.052)*max(0,sin(pi*k/20))**.62) for k in range(21)],.004,brass,'Boot_'+side,'Foot_'+side,8)
    for j in range(6):box('Sole traction lug',(s*.19,-.198+j*.056,.013),(.216,.021,.016),dark,'Boot_'+side,'Foot_'+side,bevel=.004)
    for z,y in [(.19,-.077),(.24,-.060),(.29,-.055)]:
        ribbon('Boot wrap strap',[(s*.19-.09,y+.06,z),(s*.19-.073,y-.018,z+.004),(s*.19,y-.031,z),(s*.19+.083,y-.018,z-.006),(s*.19+.100,y+.04,z)],.036,leather,'Boot_'+side,'Foot_'+side)
        box('Boot brass buckle',(s*.19+.045,y-.038,z),(.047,.011,.038),brass,'Boot_'+side,'Foot_'+side,bevel=.004)
        box('Buckle recess',(s*.19+.045,y-.045,z),(.028,.006,.021),dark,'Boot_'+side,'Foot_'+side,bevel=.002)
    for k in range(4):
        y=-.151+k*.021;z=.183+k*.010
        tube('Boot lace',[(s*.19-.059,y,z),(s*.19+.055,y+.021,z+.015)],[.004,.004],cloth,'Boot_'+side,'Foot_'+side,8)
        tube('Boot lace',[(s*.19+.059,y,z),(s*.19-.055,y+.021,z+.015)],[.004,.004],cloth,'Boot_'+side,'Foot_'+side,8)
# Belt with external seam and irregularly placed brass studs.
loft('Waist belt',[(1.027,0,.015,.272,.20),(1.047,0,.015,.275,.202),(1.103,0,.015,.265,.193),(1.112,0,.015,.261,.19)],leather,'Belt','Pelvis',n=96)
for a in range(0,360,24):
    t=a*pi/180;uvball('Belt stud',(.276*cos(t),.015+.203*sin(t),1.083),(.009,.009,.009),brass,'Belt','Pelvis',seg=12,rings=8)
torus('Circular clan buckle',(0,-.199,1.073),.048,.010,brass,'Belt','Pelvis');uvball('Buckle steel hub',(0,-.205,1.073),(.026,.012,.026),steel,'Belt','Pelvis')
for x in [-.208,.203]:
    box('Belt utility pouch',(x,-.139,1.062),(.077,.064,.105),leather,'Belt','Pelvis',bevel=.009);box('Pouch flap',(x,-.178,1.095),(.075,.011,.034),leather,'Belt','Pelvis',bevel=.005);uvball('Pouch clasp',(x,-.187,1.086),(.008,.003,.009),brass,'Belt','Pelvis',seg=12,rings=8)
# Harness surface is fitted to the actual continuous anatomy.
krag_harness.build(globals())
# Scarf follows the reference's thick looped fabric construction.
if '--broad-scarf' in sys.argv:
    import krag_scarf_v3
    krag_scarf_v3.build(globals())
else:krag_cloth.wrapped(globals())
# Hanging front sash, hem with cut irregularity.
vs=[];fs=[]
for i in range(22):
    t=i/21;z=1.054-.39*t
    for j in range(9):
        u=j/8;vs.append((.115+(u-.5)*(.13-.025*t)+.022*sin(t*5),-.210-.023*sin(u*pi*4+t*3)+.065*t,z+(.014*sin(j*9) if i==21 else 0)))
for i in range(21):
    for j in range(8):a=i*9+j;fs.append((a,a+1,a+10,a+9))
o=mesh('Frayed clan waist sash',vs,fs,cloth,'Belt','Pelvis');so=o.modifiers.new('Woven thickness','SOLIDIFY');so.thickness=.004;bpy.context.view_layer.objects.active=o;bpy.ops.object.modifier_apply(modifier=so.name)
for j in range(17):
    x=.062+j*.006;z=.665+.015*sin(j*2.5);tube('Frayed sash thread',[(x,-.153,z),(x+.002*sin(j),-.151,z-.013-random.random()*.024)],[.0011,.0007],cloth,'Belt','Pelvis',5)
# Rounded layered cap with fitted retaining straps, rolled overlaps and rivets.
krag_armor.build(globals())
log('Crusher arm, iron jaw and piston leg')
# Full left replacement. Visible open mechanics and narrow structural members contrast huge claw.
G='BionicArm_L_Crusher'
uvball('Shoulder rotary housing',(.392,.013,1.594),(.108,.113,.122),steel,G,'UpperArm_L')
torus('Shoulder brass bearing',(.427,-.091,1.604),.068,.012,brass,G,'UpperArm_L')
cyl('Upper arm load beam',(.420,.026,1.563),(.505,.026,1.321),.066,steel,G,'UpperArm_L')
for dx,dy in [(-.060,-.041),(.058,-.037),(.010,.070)]:
    a=(.438+dx,.015+dy,1.555);b=(.503+dx,.015+dy,1.33);cyl('Upper hydraulic barrel',a,b,.026,brass,G,'UpperArm_L');cyl('Piston shaft',(a[0],a[1],a[2]-.01),(b[0],b[1],b[2]-.045),.014,steel,G,'UpperArm_L')
for y in [-.081,.090]:
    cyl('Elbow axle',(.515,y,1.303),(.515,y+(-.028 if y<0 else .028),1.303),.087,steel,G,'LowerArm_L');torus('Elbow retaining ring',(.515,y,1.303),.064,.010,brass,G,'LowerArm_L')
# Upper-arm protective plates over the working hydraulic bundle.
for xx,yy in [(.465,-.073),(.449,.086)]:
    o=box('Crusher upper-arm armored casing',(xx,yy,1.43),(.118,.023,.156),paint,G,'UpperArm_L',bevel=.019);o.rotation_euler.y=.32
    for dx in [-.046,.046]:
        for dz in [-.056,.056]:uvball('Upper casing bolt',(xx+dx,yy+(-.017 if yy<0 else .017),1.43+dz),(.008,.006,.008),brass,G,'UpperArm_L',seg=12,rings=8)
# Forearm central barrel with cut armor plates, dual cylinders and ribbed hoses.
cyl('Crusher forearm chassis',(.531,.007,1.278),(.633,.007,.995),.086,steel,G,'LowerArm_L')
for x,y in [(.498,-.067),(.583,.072)]:
    cyl('Forearm power cylinder',(x,y,1.261),(x+.082,y,1.059),.033,brass,G,'LowerArm_L');cyl('Forearm bright piston',(x+.050,y,1.13),(x+.100,y,.983),.015,steel,G,'LowerArm_L')
for z in [1.245,1.031]:
    torus('Arm barrel steel band',(.531+(1.278-z)*.36,.007,z),.094,.010,steel,G,'LowerArm_L',rot=(0,.34,0))
# Shaped front shield, wide teal panel with irregular beveled edge.
o=box('Forearm salvaged teal shield',(.587,-.082,1.144),(.160,.035,.192),paint,G,'LowerArm_L',bevel=.031);o.rotation_euler.y=.34
for dx in [-.067,.062]:
    for dz in [-.071,.069]:uvball('Shield perimeter bolt',(.587+dx,-.105,1.144+dz),(.009,.006,.009),brass,G,'LowerArm_L',seg=12,rings=8)
for k in range(2):
    pts=[]
    for j in range(22):
        t=j/21;pts.append((.465+.105*t-.035*sin(pi*t),-.072-k*.025-.018*sin(pi*t),1.516-.414*t))
    tube('Flexible copper pressure line',pts,.012 if k==0 else .008,copper if k==0 else dark,G,'UpperArm_L',12)
    for j in range(1,21,2):uvball('Hose clamp',pts[j],(.014,.014,.009),steel,G,'UpperArm_L',seg=12,rings=8)
# Readable pressure dial on outer forearm.
cyl('Pressure gauge case',(.643,-.086,1.250),(.643,-.121,1.250),.057,brass,G,'LowerArm_L')
cyl('Pressure gauge ivory face',(.643,-.124,1.250),(.643,-.127,1.250),.048,bone,G,'LowerArm_L')
for j in range(11):
    a=-.8+4.5*j/10;p=(.643+.040*sin(a),-.129,1.250+.040*cos(a));q=(.643+.033*sin(a),-.130,1.250+.033*cos(a));tube('Gauge dial tick',[p,q],.0016,steel,G,'LowerArm_L',6)
tube('Pressure dial needle',[(.643,-.132,1.250),(.665,-.132,1.278)],[.0025,.001],dark,G,'LowerArm_L',8)
# Huge open articulated three-jaw crusher, individual joints and visible gear collar.
uvball('Crusher knuckle casing',(.652,.004,.978),(.128,.103,.110),steel,G,'Hand_L')
for a in [0,pi*.5,pi,pi*1.5]:
    uvball('Crusher collar bolt',(.652+.107*cos(a),-.087,.978+.078*sin(a)),(.013,.009,.013),brass,G,'Hand_L',seg=12,rings=8)
for j,dx in enumerate([-.106,0,.106]):
    yy=-.063 if j!=1 else .072
    x=.652+dx;tipx=.652+dx*.38;pts=[(x,yy,.962),(x+dx*.65,yy-.014,.854),(x+dx*.75,yy-.045,.763),(tipx,yy-.092,.713)]
    radii=[.051,.058,.048,.012];o=tube('Crusher articulated jaw '+str(j),pts,radii,steel,G,'Claw_'+str(j),8)
    for k in [0,1]:
        p=pts[k];cyl('Claw hinge pin',(p[0],p[1]-.055,p[2]),(p[0],p[1]+.039,p[2]),.026,brass,G,'Claw_'+str(j));torus('Claw hinge retaining ring',(p[0],p[1]-.058,p[2]),.019,.004,steel,G,'Claw_'+str(j))
    mid=Vector(pts[1]);box('Claw replaceable armor shoe',(mid.x,mid.y-.045,mid.z),(.070,.016,.097),paint,G,'Claw_'+str(j),bevel=.009)
    for k in range(3):
        t=(k+.5)/3;a=Vector(pts[1]).lerp(Vector(pts[2]),t);toward=Vector((.652-a.x,0,-.015)).normalized()*.021;tip=a+toward
        tube('Crusher serrated tooth',[a,tip],[.012,.001],brass,G,'Claw_'+str(j),6)
# Iron jaw attaches anatomically at cheek bearings and chin, no face-covering helmet.
G='BionicJaw_Iron'
o=box('Iron chin forged shield',(0,-.171,1.787),(.209,.067,.083),steel,G,'Jaw',bevel=.020)
for s in [-1,1]:
    cyl('Jaw cheek hinge',(s*.137,-.085,1.855),(s*.137,-.113,1.855),.041,brass,G,'Head');torus('Jaw hinge ring',(s*.137,-.119,1.855),.031,.005,steel,G,'Head')
    tube('Jaw side support',[(s*.134,-.110,1.850),(s*.118,-.171,1.810),(s*.092,-.201,1.790)],[.019,.014,.012],steel,G,'Jaw',12)
    for z in [1.776,1.810]:uvball('Jaw rivet',(s*.079,-.207,z),(.007,.005,.007),brass,G,'Jaw',seg=12,rings=8)
for j in range(7):
    x=(j-3)*.022;box('Iron jaw tooth',(x,-.197,1.839),(.017,.025,.029),bone,G,'Jaw',bevel=.004)
# Reinforced right shin prosthesis, full modeled foot, natural trouser leg can remain above knee.
G='BionicLeg_R_Piston';x=-.19
uvball('Piston knee joint',(x,.002,.578),(.096,.095,.085),steel,G,'Shin_R')
for dx in [-.053,.053]:
    cyl('Leg hydraulic cylinder',(x+dx,.01,.54),(x+dx,.017,.30),.028,brass,G,'Shin_R');cyl('Leg polished piston',(x+dx,.018,.35),(x+dx,.022,.16),.016,steel,G,'Shin_R')
o=box('Piston shin shield',(x,-.076,.403),(.126,.03,.190),paint,G,'Shin_R',bevel=.020)
for dx in [-.048,.048]:
    for z in [.337,.472]:uvball('Shin plate rivet',(x+dx,-.096,z),(.008,.006,.008),brass,G,'Shin_R',seg=12,rings=8)
uvball('Mechanical ankle',(x,.021,.174),(.063,.067,.069),steel,G,'Foot_R');box('Mechanical armored foot',(x,-.078,.075),(.195,.283,.105),steel,G,'Foot_R',bevel=.023)
box('Mechanical foot teal upper',(x,-.062,.130),(.175,.204,.025),paint,G,'Foot_R',bevel=.010)
for j in range(4):box('Piston foot front claw',(x-.074+j*.049,-.207,.054),(.036,.065,.055),brass,G,'Foot_R',bevel=.007)
krag_full_leg.geometry(globals())
# Optical replacement stays small, an optional module.
G='BionicEye_L';uvball('Optical prosthetic rim',(.069,-.174,1.971),(.041,.030,.034),steel,G,'Head');torus('Optical retaining brass ring',(.069,-.203,1.971),.023,.005,brass,G,'Head');uvball('Optical amber lens',(.069,-.206,1.971),(.018,.004,.017),iris,G,'Head')
# Compatible right one-handed scrap firearm, visible in every runtime variant.
G='Weapon_R';bn='Hand_R'
o=box('Scrap hand cannon receiver',(-.628,-.159,.997),(.114,.173,.10),steel,G,bn,bevel=.011)
cyl('Hand cannon thick barrel',(-.628,-.188,1.014),(-.628,-.415,1.014),.044,steel,G,bn)
cyl('Hand cannon bore',(-.628,-.415,1.014),(-.628,-.419,1.014),.028,dark,G,bn)
box('Hand cannon wooden grip',(-.628,-.089,.935),(.090,.066,.117),leather,G,bn,bevel=.008)
box('Hand cannon teal side plate',(-.689,-.142,.994),(.012,.117,.063),paint,G,bn,bevel=.004)
# Hand cannon rests muzzle-down; raising the arm rotates it to horizontal aim.
pivot=Vector((-.628,-.089,.935));grip_rotation=Matrix.Rotation(pi/2,4,'X')
for o in list(bpy.data.objects):
    if o.type=='MESH' and o.get('module')=='Weapon_R':
        o.matrix_world=Matrix.Translation(pivot+Vector((0,0,-.038)))@grip_rotation@Matrix.Translation(-pivot)@o.matrix_world
for o in list(bpy.data.objects):
    if o.type=='MESH' and o.get('module')=='Weapon_R':
        pivot=Vector((-.599,-.019,1.043));rotation=Matrix.Rotation(pi/2,4,'Z');o.matrix_world=Matrix.Translation(pivot)@rotation@Matrix.Translation(-pivot)@o.matrix_world
# Seat the rest grip against the adapted anatomical palm; marker bones below use
# the same rigid offset. Actual closed-finger contact still needs posed review.
WEAPON_REST_SHIFT=Vector((-.060,-.029,.010))
for o in list(bpy.data.objects):
    if o.type=='MESH' and o.get('module')=='Weapon_R':o.matrix_world=Matrix.Translation(WEAPON_REST_SHIFT)@o.matrix_world
grip_spec=None
if '--anatomical-grip' in sys.argv:
    import krag_grip_v2
    grip_spec=krag_grip_v2.mount(globals())
# Blend upper trouser cloth into one tailored surface; accessories remain separate.
trouser_parts=[o for o in bpy.data.objects if o.type=='MESH' and (o.name=='Trouser seat' or o.name.startswith('Trousers_upper_'))]
trousers=join_sculpt(trouser_parts,'Tailored trouser base',.0032,3);trousers['module']='Garments'
bpy.context.view_layer.objects.active=trousers;bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
for v in trousers.data.vertices:
    x,y,z=v.co
    if .58<z<1.07:
        # A few broad unequal compression folds, radiating from hip/crotch and knee.
        side=1 if x>0 else -1;front=max(0,min(1,(-y+.025)/.09));xx=abs(x)
        folds=[(.951,-.29,.010,.018),(.864,.22,-.007,.022),(.714,-.19,.006,.019)] if side>0 else [(.925,.24,.009,.024),(.823,-.31,-.008,.018),(.672,.16,.006,.023)]
        delta=0
        for zz,slope,amp,width in folds:
            distance=z-zz-slope*(xx-.18);across=math.exp(-((xx-.18)/.16)**4)
            delta+=amp*(math.exp(-(distance/width)**2)-.48*math.exp(-((distance-width*1.6)/(width*1.5))**2))*across
        v.co.y-=delta*front
krag_full_leg.split_natural_thigh(globals(),trousers)
# Reference-proportion head: compact adult cranium, broad bulldog jaw, fixed crown.
for o in list(bpy.data.objects):
    if o.type=='MESH' and (o.get('module') in {'Head','Face','BionicJaw_Iron','BionicEye_L','MouthInterior','Eyelids_L','Eyelids_R'} or o.get('krag_head_control_cage')):
        head_transform=o.matrix_world.copy();inv=head_transform.inverted()
        for v in o.data.vertices:
            q=head_transform@v.co;v.co=inv@Vector(krag_face.H(q))
# Consolidate modules while preserving bone membership per vertex.
log('Module consolidation and UV unwrapping')
# Mark rigid weights before joining. Skin forearms and cloth will be reweighted later.
for o in list(bpy.data.objects):
    if o.type!='MESH' or 'module' not in o:continue
    if o.data.uv_layers: o.data.uv_layers.active.name='UVMap'
    bn=o.get('rig_bone')
    if bn:
        vg=o.vertex_groups.get(bn) or o.vertex_groups.new(name=bn);vg.add(list(range(len(o.data.vertices))),1,'REPLACE')
modules={}
for g in list(groups):
    obs=[o for o in bpy.data.objects if o.type=='MESH' and o.get('module')==g]
    if not obs:continue
    bpy.ops.object.select_all(action='DESELECT')
    for o in obs:o.select_set(True)
    bpy.context.view_layer.objects.active=obs[0]
    if len(obs)>1:bpy.ops.object.join()
    o=obs[0];o.name=g;o['module']=g;modules[g]=o
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=1.1519,island_margin=.02);bpy.ops.object.mode_set(mode='OBJECT')
    o.data.uv_layers.active.name='UVMap'
log('Skeletal rig')
bpy.ops.object.select_all(action='DESELECT');ad=bpy.data.armatures.new('Krag_Skeleton');rig=bpy.data.objects.new('Krag_Rig',ad);bpy.context.collection.objects.link(rig);bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
bones={}
def bn(n,h,t,par=None):
    b=ad.edit_bones.new(n);b.head=h;b.tail=t
    if par:b.parent=ad.edit_bones[par]
    bones[n]=(Vector(h),Vector(t));return b
head_base=(0,.014,1.84);head_tail=(0,.014,2.105)
if '--reference-head-scale' in sys.argv:
    import krag_proportions_v9f
    head_base=krag_proportions_v9f.point(head_base);head_tail=krag_proportions_v9f.point(head_tail)
bn('Root',(0,0,0),(0,0,.18));bn('Pelvis',(0,.015,1.015),(0,.015,1.175),'Root');bn('Spine',(0,.015,1.175),(0,.015,1.39),'Pelvis');bn('Chest',(0,.015,1.39),(0,.02,1.64),'Spine');bn('Neck',(0,.02,1.64),head_base,'Chest');bn('Head',head_base,head_tail,'Neck');bn('Jaw',krag_face.H(globals().get('continuous_head_landmarks',{}).get('JawPivot',(0,-.040,1.845))),krag_face.H(globals().get('continuous_head_landmarks',{}).get('JawTail',(0,-.170,1.790))),'Head')
for s,side in [(-1,'R'),(1,'L')]:
    bn('Clavicle_'+side,(s*.055,.02,1.636),(s*.348,.012,1.613),'Chest');bn('UpperArm_'+side,(s*.348,.012,1.613),(s*.509,.008,1.300),'Clavicle_'+side);bn('LowerArm_'+side,(s*.509,.008,1.300),(s*.599,-.019,1.043),'UpperArm_'+side);bn('Hand_'+side,(s*.599,-.019,1.043),(s*.620,-.042,.927),'LowerArm_'+side)
    bn('Thigh_'+side,(s*.167,.019,1.018),(s*.188,-.016,.570),'Pelvis');bn('Shin_'+side,(s*.188,-.016,.570),(s*.19,.026,.240),'Thigh_'+side);bn('Foot_'+side,(s*.19,.026,.240),(s*.19,-.149,.082),'Shin_'+side);bn('Toe_'+side,(s*.19,-.149,.082),(s*.19,-.230,.067),'Foot_'+side)
for s,side in [(-1,'R'),(1,'L')]:
    landmarks=krag_anatomy.hand_landmarks(side)
    for j in range(4):
        a,b,c=landmarks['Finger_'+str(j)]
        joint=bn('Finger1_'+str(j)+'_'+side,a,b,'Hand_'+side);joint.align_roll(Vector((s,0,0)))
        joint=bn('Finger2_'+str(j)+'_'+side,b,c,'Finger1_'+str(j)+'_'+side);joint.align_roll(Vector((s,0,0)))
    a,b,c=landmarks['Thumb']
    joint=bn('Thumb1_'+side,a,b,'Hand_'+side);joint.align_roll(Vector((s,0,0)))
    joint=bn('Thumb2_'+side,b,c,'Thumb1_'+side);joint.align_roll(Vector((s,0,0)))
for j,dx in enumerate([-.106,0,.106]):bn('Claw_'+str(j),(.652+dx,-.063 if j!=1 else .072,.962),(.652+dx*.65,-.070 if j!=1 else .065,.82),'Hand_L')
weapon_muzzle=Vector(grip_spec['muzzle']) if grip_spec else Vector((-.450,-.048,.567))+WEAPON_REST_SHIFT
weapon_aim=Vector(grip_spec['aim']) if grip_spec else Vector((-.450,-.048,.467))+WEAPON_REST_SHIFT
bn('WeaponMuzzle',weapon_muzzle,weapon_muzzle+Vector((0,0,-.025)),'Hand_R').use_deform=False
bn('WeaponAim',weapon_aim,weapon_aim+Vector((0,0,-.025)),'Hand_R').use_deform=False
krag_face.bones(bn,globals().get('continuous_head_landmarks')); ad.edit_bones['Jaw'].parent=ad.edit_bones['FaceRoot']
bpy.ops.object.mode_set(mode='OBJECT');rig.show_in_front=True
# Art-directed deformation skinning via nearest anatomical segment weights.
def distseg(p,a,b):
    t=max(0,min(1,(p-a).dot(b-a)/(b-a).length_squared));return (p-(a+(b-a)*t)).length
for g,o in modules.items():
    if g in ['Body','BioArm_L','BioArm_R','BioForearm_L','BioForearm_R']:allowed=['Pelvis','Spine','Chest','Neck']+[a+'_'+side for side in ['L','R'] for a in ['Clavicle','UpperArm','LowerArm','Hand']]
    elif g=='Garments' or g.startswith('TrouserLeg_') or g.startswith('BioLowerLeg_') or g=='NaturalThigh_R':allowed=['Pelvis','Thigh_L','Thigh_R','Shin_L','Shin_R']
    else:allowed=[]
    if allowed:
        o.vertex_groups.clear()
        extra=[n for n in bones if n.startswith('Finger') or n.startswith('Thumb')] if g in ['Body','BioArm_L','BioArm_R','BioForearm_L','BioForearm_R'] else []
        vgs={n:o.vertex_groups.new(name=n) for n in allowed+extra}
        domain=krag_skin_domains.read(o.data) if extra and '--anatomical-domain' in sys.argv else None
        hand_domains=krag_hand_domains.read(o.data) if extra and '--topological-hands' in sys.argv else None
        for v in o.data.vertices:
            candidates=allowed
            if extra and abs(v.co.x)>.48 and v.co.z<1.05:
                side='L' if v.co.x>0 else 'R';candidates=['Hand_'+side,'LowerArm_'+side]+[n for n in extra if n.endswith('_'+side)]
            weighted=krag_anatomy.anatomical_weights(v.co,bones,None if domain is None else domain[v.index],None if hand_domains is None else hand_domains[v.index]) if extra else krag_anatomy.smooth_segment_weights(v.co,bones,candidates)
            # Contract supports up to eight influences. Only very small far-chain
            # tails can reach this cap; actual counts and deformation are reviewed.
            weighted=sorted(weighted,key=lambda item:item[1],reverse=True)[:8]
            total=sum(w for n,w in weighted)
            for n,w in weighted:vgs[n].add([v.index],w/total,'REPLACE')
    elif not o.vertex_groups:
        vg=o.vertex_groups.new(name='Pelvis');vg.add(list(range(len(o.data.vertices))),1,'REPLACE')
    o.parent=rig;mod=o.modifiers.new('Krag weighted deformation','ARMATURE');mod.object=rig
log('Facial soft tissue keys and anatomical corrective shapes')
krag_face.face_weights(modules)
for o in modules.values():
    for mod in o.modifiers:
        if mod.type=='ARMATURE':mod.show_viewport=False
# Animation authored on local bone channels; frame-based poses express distinct physical actions.
scene.render.fps=30
for pb in rig.pose.bones:pb.rotation_mode='XYZ'
def reset():
    for p in rig.pose.bones:p.rotation_euler=(0,0,0);p.location=(0,0,0)
def rot(n,x=0,y=0,z=0):rig.pose.bones[n].rotation_euler=(x,y,z)
def key(frame):
    for p in rig.pose.bones:
        p.keyframe_insert(data_path='rotation_euler',frame=frame,group=p.name);p.keyframe_insert(data_path='location',frame=frame,group=p.name)
rig.animation_data_create()
locomotion_metrics=[];grip_metrics=[]
for name,frames in [('Idle',61),('Walk',37),('Run',19),('Melee',37),('Shoot',31),('Hit',28)]:
    action=bpy.data.actions.new(name);action.use_fake_user=True;rig.animation_data.action=action
    previous_grip_rotations={}
    for f in range(1,frames+1):
        scene.frame_set(f);reset();t=(f-1)/(frames-1);wave=sin(t*2*pi)
        for j in range(4):
            rot('Finger1_'+str(j)+'_R',-.68,0,(j-1.5)*.018);rot('Finger2_'+str(j)+'_R',-.78)
            curl=.80 if name=='Melee' else .11+j*.018
            rot('Finger1_'+str(j)+'_L',-curl,0,(j-1.5)*.035);rot('Finger2_'+str(j)+'_L',-curl*.8)
        rot('Thumb1_R',-.18,0,.34);rot('Thumb2_R',-.14);rot('Thumb1_L',-.06,0,-.08)
        if name=='Idle':
            rot('Chest',.018*wave,0,.012*cos(t*2*pi));rot('Head',-.009*wave,.010*wave,.009*wave);rot('UpperArm_L',0,.013*wave,.03);rot('UpperArm_R',0,-.013*wave,-.03);rig.pose.bones['Pelvis'].location.y=.006*wave
        elif name in ('Walk','Run'):
            locomotion_metrics.extend(dict(clip=name,frame=f,**m) for m in krag_locomotion.pose(rig,name,t))
        elif name=='Melee':
            # Windup then heavy left downward crusher and recoil.
            wind=sin(min(t/.42,1)*pi/2);strike=max(0,min((t-.42)/.19,1));recover=max(0,(t-.70)/.30);a=(wind-1.25*strike)*(1-recover)
            rot('Chest',-.18*a,0,-.23*a);rot('UpperArm_L',-1.28*a,-.08,.10);rot('LowerArm_L',-.58*max(0,a));rot('Head',.10*a,0,.12*a);rot('Thigh_L',-.10*a);rot('UpperArm_R',-.25*a,0,-.08)
            for j in range(3):rot('Claw_'+str(j),0,(j-1)*.21*strike*(1-recover),0)
        elif name=='Shoot':
            aim=min(t/.22,1)*(1-max(0,(t-.78)/.22));kick=max(0,1-abs(t-.40)/.065)+.70*max(0,1-abs(t-.58)/.055)
            rot('Chest',-.05*kick,0,-.12*aim);rot('Head',0,0,.09*aim);rot('UpperArm_L',-.14*aim,0,.06)
            if '--aim-solver' in sys.argv:
                import krag_weapon_pose
                result=krag_weapon_pose.pose(rig,aim,kick)
                if aim>.999 and result['dotIntendedDirection']<.9999:raise ValueError('Krag muzzle aim solver failed')
                if result['wristErrorMeters']>1e-5:raise ValueError('Krag aiming wrist missed target')
            else:
                rot('UpperArm_R',-1.20*aim-.16*kick,0,-.08*aim);rot('LowerArm_R',-.31*aim-.12*kick);rot('Hand_R',.04*kick)
        else:
            hit=sin(min(t/.24,1)*pi/2)*math.exp(-max(0,t-.24)*4);rot('Chest',-.30*hit,0,-.14*hit);rot('Head',-.23*hit,.08*hit,.14*hit);rot('Spine',-.11*hit);rot('UpperArm_L',-.21*hit,0,.18*hit);rot('UpperArm_R',-.13*hit,0,-.16*hit);rot('Thigh_L',.14*hit);rot('Shin_L',.22*hit)
        krag_face.action_expression(rig,name,t)
        if grip_spec:
            grip_metrics.append({'clip':name,'frame':f,**krag_grip_v2.pose(rig,grip_spec,left_fist=name=='Melee')})
            for pb in rig.pose.bones:
                if not pb.name.startswith(('Finger','Thumb')):continue
                if pb.name in previous_grip_rotations:pb.rotation_euler.make_compatible(previous_grip_rotations[pb.name])
                previous_grip_rotations[pb.name]=pb.rotation_euler.copy()
        key(f)
    action['facial_performance']='Authored FaceRoot subtree tracks accompany this body animation; serious fearless Krag direction.'
    action['clip_name']=name;action['loop']=name in ('Idle','Walk','Run');action['root_motion']=False
reset();krag_face.performance(rig)
for o in modules.values():
    for mod in o.modifiers:
        if mod.type=='ARMATURE':mod.show_viewport=True
log('Building portable facial and pose corrective targets')
deformation=krag_face.add_morphs(modules,rig)
(OUT/'facial-rig.json').write_text(json.dumps(deformation,indent=2),newline='\n')
reset();rig.animation_data.action=bpy.data.actions['Idle'];scene.frame_set(1)
(ART/('locomotion-target-verification.json' if MASTER_PATH.name=='Krag_Master.blend' else MASTER_PATH.stem+'-locomotion-target-verification.json')).write_text(json.dumps({'status':'Analytic skeleton targets only; actual rendered sole contact pending','samples':locomotion_metrics,'maxAnkleErrorMeters':max(m['errorMeters'] for m in locomotion_metrics)},indent=2),newline='\n')
# Record the real hierarchy's firing direction, without assuming Blender bone
# roll or local Euler axes. Source animation review must also verify the grip.
weapon_samples=[]
rig.animation_data.action=bpy.data.actions['Shoot']
for frame in [13,18,19]:
    scene.frame_set(frame);bpy.context.view_layer.update()
    muzzle=rig.matrix_world@rig.pose.bones['WeaponMuzzle'].head
    aim=rig.matrix_world@rig.pose.bones['WeaponAim'].head
    forward=(aim-muzzle).normalized()
    weapon_samples.append({'frame':frame,'muzzleMeters':list(muzzle),'forward':list(forward),
                           'dotCharacterForward':forward.dot(Vector((0,-1,0)))})
    if grip_spec:weapon_samples[-1].update(krag_grip_v2.verify_visible_muzzle(rig,modules['Weapon_R']))
(ART/(MASTER_PATH.stem+'-weapon-pose-verification.json')).write_text(json.dumps({
    'status':'Actual source bone transforms; rendered weapon grip/aim quality remains unverified',
    'samples':weapon_samples},indent=2),newline='\n')
rig.animation_data.action=bpy.data.actions['Idle'];scene.frame_set(1)
# Variant visibility source contract and export list.
variants={
'Krag_Natural': {'off':['BionicArm_L_Crusher','BionicJaw_Iron','BionicLeg_R_Piston','BionicEye_L','Weapon_R']},
'Krag_Crusher': {'off':['BioArm_L','BioForearm_L','HandDetails_L','BionicLeg_R_Piston','BionicEye_L','Weapon_R']},
'Krag_IronJaw': {'off':['BionicArm_L_Crusher','BionicLeg_R_Piston','Weapon_R']},
'Krag_Piston': {'off':['BionicArm_L_Crusher','BionicJaw_Iron','BionicEye_L','Boot_R','BioLowerLeg_R','Weapon_R']}}
for variant in variants.values():variant['off'].append('BionicThigh_R_Full')
variants['Krag_FullLeg']={'off':['BionicArm_L_Crusher','BionicJaw_Iron','BionicEye_L','Boot_R','BioLowerLeg_R','NaturalThigh_R','TrouserLeg_R','Weapon_R']}

def variant(name):
    off=variants[name]['off']
    for g,o in modules.items():o.hide_render=g in off;o.hide_set(g in off)
variant('Krag_Natural')
# Source studio is separate from FBX selection.
log('Save source and render WIP')
world=bpy.data.worlds.new('Warm studio') if not scene.world else scene.world;scene.world=world;world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.28,.31,.34,1);world.node_tree.nodes['Background'].inputs[1].default_value=.45
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.017));floor=bpy.context.object;floor.name='Studio ground';fm=mat('Studio_Sand',(.39,.31,.22),0,.88,'cloth');floor.data.materials.append(fm)
def area(name,p,power,color,size):
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.color=color;data.shape='DISK';data.size=size;o=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(o);o.location=p;o.rotation_euler=(Vector((0,0,1.2))-o.location).to_track_quat('-Z','Y').to_euler()
area('Warm key',(-3,-4,5),500,(1,.84,.66),3.0);area('Cool fill',(3,-1,3),280,(.66,.80,1),2.5);area('Warm rim',(1,3,4),600,(1,.83,.57),2.0)
camd=bpy.data.cameras.new('Review camera');cam=bpy.data.objects.new('Review camera',camd);bpy.context.collection.objects.link(cam);scene.camera=cam;camd.type='ORTHO';camd.ortho_scale=2.5
scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.use_denoising=True;scene.cycles.device='CPU';scene.render.resolution_x=900;scene.render.resolution_y=900;scene.render.resolution_percentage=100;scene.view_settings.view_transform='AgX'
cam.location=(3,-6,2.8);cam.rotation_euler=(Vector((0,0,1.08))-cam.location).to_track_quat('-Z','Y').to_euler()
# Embed the exact authoring sources so later external script edits cannot obscure provenance.
for source_script in ['build_krag.py','krag_face.py','krag_locomotion.py','krag_cloth.py','krag_anatomy.py','anatomy_warp_study.py','krag_armor.py','krag_full_leg.py','krag_harness.py','krag_head_v9.py','krag_iris_material.py','krag_weapon_pose.py','krag_skin_domains.py','krag_grip_v2.py','krag_hand_domains.py','krag_proportions_v9f.py','krag_scarf_v3.py']:
    content=(Path(__file__).parent/source_script).read_text();text_block=bpy.data.texts.get(source_script) or bpy.data.texts.new(source_script);text_block.clear();text_block.write(content)
bpy.ops.wm.save_as_mainfile(filepath=str(MASTER_PATH),compress=True);bpy.ops.file.make_paths_relative();bpy.ops.wm.save_as_mainfile(filepath=str(MASTER_PATH),compress=True)
scene.render.filepath=str(ART/'renders/Krag_Natural_Perspective.png')
if '--skip-render' not in sys.argv:bpy.ops.render.render(write_still=True)
log('Source saved; render '+('skipped' if '--skip-render' in sys.argv else 'finished'))
# Manifest kept local to this asset; shared root manifest belongs to integration lead.
data={'height_m':2.107,'forward':'-Y','up':'Z','ankles_m':{'Foot_L':[.19,.026,.24],'Foot_R':[-.19,.026,.24]},'ground_z':0,'bones':list(bones),'clips':['Idle','Walk','Run','Melee','Shoot','Hit','FacePerformance'],'deformation':deformation,'locomotionCycles':krag_locomotion.manifest(),'variants':variants,'modules':list(modules),'source':str(MASTER_PATH.relative_to(ROOT)).replace('\\','/'),'materials':list(materials),'triangles':sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in modules.values())}
if globals().get('continuous_head_landmarks'):data['facialFitLandmarksMeters']={name:list(krag_face.H(point)) for name,point in continuous_head_landmarks.items()}
if globals().get('continuous_head_eye_audit'):data['sourceEyeTransformVerification']=continuous_head_eye_audit
if globals().get('anatomical_domain_statistics'):data['anatomicalDomainStudy']=anatomical_domain_statistics
if globals().get('hand_domain_statistics'):data['handDomainStudy']=hand_domain_statistics
if '--reference-head-scale' in sys.argv:
    data['headProportionStudy']=krag_proportions_v9f.specification()
    data['height_m']=krag_proportions_v9f.specification()['expectedCrownMeters']
if grip_spec:
    data['gripMountStudy']=grip_spec
    (ART/(MASTER_PATH.stem+'-grip-target-verification.json')).write_text(json.dumps({'status':'Actual skeletal endpoint checks only; no posed skin/contact acceptance','spec':grip_spec,'samples':grip_metrics},indent=2),newline='\n')
(OUT/'krag_asset_contract.json').write_text(json.dumps(data,indent=2),newline='\n')
log('COMPLETE source creation; use export_krag.py for PBR texture baking and FBX.')
