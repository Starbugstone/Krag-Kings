"""Separate, provisional regular-Krag weapon study; never edits shared assets.

Reference: the regular Krag's practical long firearm in concept sheet 10.
This is an exterior art prop, with no functional internal mechanism. The saved
grip dimensions come from the actual v9f hand fit. New silhouette and unseen
surfaces require rendered review before any character transplant/export.
"""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
import bmesh
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[3]
ARGS = argparse.ArgumentParser()
ARGS.add_argument('--output', type=Path, required=True)
ARGS.add_argument('--render', action='store_true')
args = ARGS.parse_args(sys.argv[sys.argv.index('--') + 1:])
OUT = args.output
OUT.mkdir(parents=True, exist_ok=True)
if (OUT / 'Krag_Regular_Weapon_Study_v2.blend').exists():
    raise RuntimeError('Existing source preserved; use a fresh study directory')
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1
scene.render.engine = 'CYCLES'
scene.cycles.samples = 40
scene.cycles.use_denoising = True
scene.render.threads_mode = 'FIXED'
scene.render.threads = 4
scene.render.resolution_x = 1400
scene.render.resolution_y = 1000
scene.render.resolution_percentage = 100
scene.view_settings.view_transform = 'AgX'
parts = []


def material(name, color, metal, rough, painted=False):
    m=bpy.data.materials.new(name);m.use_nodes=True
    n,links=m.node_tree.nodes,m.node_tree.links
    bs=n.get('Principled BSDF');bs.inputs['Metallic'].default_value=metal
    tc=n.new('ShaderNodeTexCoord')
    def noise(scale,detail=3):
        node=n.new('ShaderNodeTexNoise');node.inputs['Scale'].default_value=scale;node.inputs['Detail'].default_value=detail
        links.new(tc.outputs['Object'],node.inputs['Vector']);return node
    broad=noise(22,4);fine=noise(850,3);chips=noise(145,4)
    palette=n.new('ShaderNodeValToRGB')
    palette.color_ramp.elements[0].color=(*[c*.48 for c in color],1)
    palette.color_ramp.elements[1].color=(*[min(1,c*1.18) for c in color],1)
    links.new(broad.outputs['Fac'],palette.inputs[0]);links.new(palette.outputs[0],bs.inputs['Base Color'])
    roughness=n.new('ShaderNodeMapRange');roughness.inputs['From Min'].default_value=.15;roughness.inputs['From Max'].default_value=.85
    roughness.inputs['To Min'].default_value=max(.05,rough-.14);roughness.inputs['To Max'].default_value=min(1,rough+.15)
    links.new(fine.outputs['Fac'],roughness.inputs['Value']);links.new(roughness.outputs['Result'],bs.inputs['Roughness'])
    bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.32;bump.inputs['Distance'].default_value=.00011
    links.new(fine.outputs['Fac'],bump.inputs['Height']);links.new(bump.outputs['Normal'],bs.inputs['Normal'])
    if painted:
        mask=n.new('ShaderNodeValToRGB');mask.color_ramp.elements[0].position=.59;mask.color_ramp.elements[1].position=.64
        links.new(chips.outputs['Fac'],mask.inputs[0])
        mix=n.new('ShaderNodeMixRGB');mix.inputs[2].default_value=(.13,.078,.034,1)
        links.new(mask.outputs[0],mix.inputs[0]);links.new(palette.outputs[0],mix.inputs[1]);links.new(mix.outputs[0],bs.inputs['Base Color'])
        metallic=n.new('ShaderNodeMapRange');metallic.inputs['To Min'].default_value=.07;metallic.inputs['To Max'].default_value=.82
        links.new(mask.outputs[0],metallic.inputs['Value']);links.new(metallic.outputs['Result'],bs.inputs['Metallic'])
        chipped=n.new('ShaderNodeBump');chipped.inputs['Strength'].default_value=.3;chipped.inputs['Distance'].default_value=.00017
        links.new(mask.outputs[0],chipped.inputs['Height']);links.new(bump.outputs['Normal'],chipped.inputs['Normal']);links.new(chipped.outputs['Normal'],bs.inputs['Normal'])
    return m


steel = material('Weapon_BlackenedSteel', (.065, .072, .070), .82, .43)
edge = material('Weapon_WornSteelEdges', (.15, .16, .145), .85, .43)
brass = material('Weapon_AgedBrass', (.22, .125, .039), .77, .47)
teal = material('Weapon_WeatheredTeal', (.025, .10, .092), .65, .62, True)
copper = material('Weapon_DarkCopper', (.24, .075, .025), .8, .4)
leather = material('Weapon_GripLeather', (.060, .031, .014), 0, .78)
recess = material('Weapon_Recess', (.005, .006, .005), .25, .83)
canvas = material('Weapon_GripBinding', (.21, .155, .095), 0, .9)


def finish(o, name, mat):
    o.name = name
    o.data.materials.append(mat)
    o['module'] = 'Weapon_R_Study'
    parts.append(o)
    return o


def box(name, p, size, mat, bevel=.002):
    bpy.ops.mesh.primitive_cube_add(size=1, location=p)
    o = bpy.context.object
    o.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        mod = o.modifiers.new('Machined edge radius', 'BEVEL')
        mod.width, mod.segments = bevel, 3
        bpy.ops.object.modifier_apply(modifier=mod.name)
    return finish(o, name, mat)


def cylinder(name, a, b, radius, mat, vertices=48):
    a, b = Vector(a), Vector(b)
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius,
                                      depth=(b-a).length, location=(a+b)/2)
    o = bpy.context.object
    o.rotation_euler = (b-a).to_track_quat('Z', 'Y').to_euler()
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    mod=o.modifiers.new('Turned edge radius','BEVEL');mod.width=.0005;mod.segments=2
    bpy.context.view_layer.objects.active=o
    bpy.ops.object.modifier_apply(modifier=mod.name)
    return finish(o, name, mat)


def shell(name, start, end, outer, inner, mat, vents=False, center_z=.132):
    # A genuinely open, thick-walled exterior shroud. Boundaries around every
    # decorative cutout are closed; a painted black cap is not used as a bore.
    count = 96
    ys = [start, end] if not vents else [start, start+(end-start)*.14,
        start+(end-start)*.43, start+(end-start)*.56,
        start+(end-start)*.86, end]
    vertices, faces = [], []
    for y in ys:
        for radius in [outer, inner]:
            for j in range(count):
                a = j*math.tau/count
                vertices.append((math.cos(a)*radius, y, center_z+math.sin(a)*radius))
    def v(row, layer, j): return row*count*2+layer*count+j%count
    def solid(row, j):
        if row < 0 or row >= len(ys)-1: return False
        return not (vents and row in (1, 3) and j%12 in range(3, 9))
    for row in range(len(ys)-1):
        for j in range(count):
            if not solid(row, j): continue
            a,b,c,d = v(row,0,j),v(row,0,j+1),v(row+1,0,j+1),v(row+1,0,j)
            e,f,g,h = v(row,1,j),v(row,1,j+1),v(row+1,1,j+1),v(row+1,1,j)
            faces += [(a,b,c,d),(h,g,f,e)]
            if not solid(row-1,j): faces.append((a,e,f,b))
            if not solid(row+1,j): faces.append((d,c,g,h))
            if not solid(row,j-1): faces.append((a,d,h,e))
            if not solid(row,j+1): faces.append((b,f,g,c))
    me=bpy.data.meshes.new(name)
    me.from_pydata(vertices, [], faces)
    me.update()
    bm=bmesh.new();bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-7)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    if any(not e.is_manifold for e in bm.edges):
        raise AssertionError('Open/invalid shell boundary: '+name)
    bm.to_mesh(me);bm.free()
    o=bpy.data.objects.new(name,me);scene.collection.objects.link(o)
    return finish(o,name,mat)


def tube(name, points, radius, mat):
    curve=bpy.data.curves.new(name,'CURVE')
    curve.dimensions='3D';curve.resolution_u=6
    curve.bevel_depth=radius;curve.bevel_resolution=2
    curve.use_fill_caps=True
    spline=curve.splines.new('BEZIER');spline.bezier_points.add(len(points)-1)
    for bp,p in zip(spline.bezier_points,points):
        bp.co=p;bp.handle_left_type=bp.handle_right_type='AUTO'
    o=bpy.data.objects.new(name,curve);scene.collection.objects.link(o)
    bpy.context.view_layer.objects.active=o;o.select_set(True)
    for selected in bpy.context.selected_objects:
        if selected!=o:selected.select_set(False)
    bpy.ops.object.convert(target='MESH')
    return finish(bpy.context.object,name,mat)


def bolt(side,y,z,r=.004):
    # Surface-only hardware; its cross recess is an art detail.
    x=side*.086
    cylinder('Retaining bolt', (x-side*.003,y,z),(x+side*.0015,y,z),r,brass,16)
    box('Bolt recess', (x+side*.002,y,z),(.0008,r*1.1,r*.24),recess,.0001)


# Grip core uses the actual v9f dimensions, centered on GripMount. Raised
# bindings are a new detail and need an equipped contact/intersection review.
handle_length=.18641426310500822
box('Fitted grip core',(0,0,0),(.0648,.04224,handle_length),leather,.008)
for z in [-.065,-.041,-.017,.007,.031,.055]:
    tube('Worn grip binding',[(-.032,-.019,z),(-.034,0,z+.003),
         (-.031,.018,z+.006),(.031,.018,z+.006),(.034,0,z+.003),(.032,-.019,z)],.0018,canvas)
box('Grip heel cap',(0,0,-handle_length/2+.005),(.071,.048,.015),brass,.004)
receiver=box('Receiver',(0,-.045,.132),(.142,.252,.128),steel,.012)
# Recessed layered housing ends break the broad plain cuboid silhouette.
box('Rear housing inset',(0,.085,.132),(.110,.032,.096),recess,.008)
box('Rear fitted cap',(0,.099,.132),(.120,.016,.106),steel,.010)
box('Stepped upper housing',(0,-.028,.199),(.106,.172,.025),teal,.007)
box('Lower housing rib',(0,-.082,.067),(.106,.150,.018),steel,.004)
for side in (-1,1):
    box('Panel gasket',(side*.073,-.048,.135),(.009,.194,.092),recess,.005)
    box('Layered side armor',(side*.078,-.048,.135),(.008,.185,.083),teal,.004)
    box('Panel upper brass edge',(side*.083,-.048,.175),(.006,.189,.007),brass,.001)
    for yy in [-.125,.039]:box('Panel upright edge',(side*.083,yy,.137),(.006,.007,.077),brass,.001)
    box('Inset panel recess',(side*.083,-.045,.139),(.004,.078,.048),recess,.003)
    box('Inset small fitted cover',(side*.086,-.045,.139),(.005,.068,.038),steel,.003)
    for yy in [-.071,-.019]:
        for zz in [.125,.153]:
            cylinder('Cover rivet',(side*.087,yy,zz),(side*.091,yy,zz),.0022,brass,16)
    for yy in [-.094,-.085,-.076]:
        box('Receiver vent recess',(side*.084,yy,.147),(.003,.003,.032),recess,.0005)
    box('Panel lower edge',(side*.079,-.048,.096),(.005,.19,.009),brass,.001)
    for y in [-.121,-.061,.016,.038]:
        for z in [.106,.165]:bolt(side,y,z)
    box('Receiver seam',(side*.078,-.141,.134),(.003,.007,.080),recess,.0005)
    # Unequal external bracing and a compact side fitting keep the regular
    # firearm distinct from the boss's enormous drum/pressure-rig design.
    cylinder('External brace',(side*.064,-.17,.094),(side*.052,-.34,.099),.006,edge,20)
    cylinder('Brace clamp',(side*.059,-.225,.094),(side*.059,-.242,.094),.009,brass,20)
shell('Recessed barrel',-.16,-.561,.032,.024,steel)
shroud=shell('Perforated heat shroud',-.205,-.498,.047,.041,steel)
cutters=[]
for yy in [-.263,-.317,-.403,-.451]:
    for a in [0,math.pi/2]:
        direction=Vector((math.cos(a),0,math.sin(a)))
        center=Vector((0,yy,.132))
        cutter=cylinder('Temporary vent cutter',center-direction*.075,center+direction*.075,.013,recess,24)
        cutters.append(cutter)
# One bounded boolean on the hollow shell retains real round openings.
bpy.ops.object.select_all(action='DESELECT')
for o in cutters:o.select_set(True);parts.remove(o)
bpy.context.view_layer.objects.active=cutters[0];bpy.ops.object.join();cutters_object=bpy.context.object
bpy.context.view_layer.objects.active=shroud
modifier=shroud.modifiers.new('Round cooling perforations','BOOLEAN');modifier.operation='DIFFERENCE';modifier.solver='EXACT';modifier.object=cutters_object
bpy.ops.object.modifier_apply(modifier=modifier.name)
bpy.data.objects.remove(cutters_object,do_unlink=True)
for y,width in [(-.215,.017),(-.358,.011),(-.49,.016)]:
    shell('Riveted shroud band',y,y-width,.049,.047,brass)
    for j in range(8):
        a=j*math.tau/8
        p=Vector((math.cos(a)*.051,y-width/2,.132+math.sin(a)*.051))
        d=Vector((math.cos(a),0,math.sin(a)))
        cylinder('Band pin',p-d*.003,p+d*.001,.003,edge,12)
shell('Muzzle rim',-.538,-.567,.038,.024,steel)
shell('Muzzle worn lip',-.563,-.569,.039,.024,edge)
for j in range(6):
    a=j*math.tau/6
    xx,zz=math.cos(a)*.034,.132+math.sin(a)*.034
    cylinder('Muzzle-face pin',(xx,-.567,zz),(xx,-.570,zz),.002,brass,12)
shell('Muzzle sleeve',-.509,-.540,.039,.032,steel)
shell('Forward brass collar',-.506,-.517,.041,.038,brass)
# A shallow dark interior closes well behind the visible cylindrical cavity.
cylinder('Dark rear of visible bore',(0,-.163,.132),(0,-.164,.132),.024,recess)
box('Rear sight pedestal',(0,.033,.205),(.045,.037,.022),steel,.003)
for x in [-.017,.017]:box('Rear sight ear',(x,.027,.222),(.008,.026,.022),brass,.002)
box('Front sight pedestal',(0,-.489,.185),(.029,.030,.016),steel,.002)
box('Front sight blade',(0,-.488,.201),(.007,.012,.020),brass,.001)
box('Top rib',(0,-.046,.218),(.023,.114,.011),steel,.002)
for y in [-.091,-.068,-.045,-.022]:box('Top rib relief',(0,y,.225),(.025,.004,.004),recess,.0005)
tube('Compact copper return',[(.079,.03,.14),(.094,.022,.135),(.095,-.013,.092),
     (.089,-.079,.088),(.078,-.103,.105)],.005,copper)
for y,z in [(.025,.14),(-.10,.105)]:
    cylinder('Copper fitting',(.073,y,z),(.09,y,z),.009,brass,12)

# Canonical authoring axes: -Y forward, +Z above the grip. The eventual
# transplant must derive the rigid basis from the source mount's row/aim axes.
for name,point in [('GripMount',(0,0,0)),('WeaponMuzzle',(0,-.567,.132)),
                   ('WeaponAim',(0,-.667,.132))]:
    e=bpy.data.objects.new(name,None);scene.collection.objects.link(e)
    e.location=point;e.empty_display_size=.025

# Smooth round surfaces while keeping planar breaks and small bevels explicit.
for o in parts:
    bpy.context.view_layer.objects.active=o
    bm=bmesh.new();bm.from_mesh(o.data)
    for face in bm.faces:face.smooth=True
    for edge_bm in bm.edges:
        edge_bm.smooth=edge_bm.is_manifold and edge_bm.calc_face_angle(0)<math.radians(40)
    bm.to_mesh(o.data);bm.free();o.data.update()
    weighted=o.modifiers.new('Area-weighted hard-surface normals','WEIGHTED_NORMAL')
    weighted.keep_sharp=True;weighted.weight=50
    bpy.ops.object.modifier_apply(modifier=weighted.name)
# Pack the editable mesh parts with explicit UVs; these are source UVs only.
for o in parts:
    bpy.ops.object.select_all(action='DESELECT');o.select_set(True)
    bpy.context.view_layer.objects.active=o
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if not o.data.uv_layers:o.data.uv_layers.new(name='UVMap')
    o.data.uv_layers.active.name='UVMap'
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=1.1519,island_margin=.012)
    bpy.ops.object.mode_set(mode='OBJECT')

world=bpy.data.worlds.new('Neutral workshop');scene.world=world;world.use_nodes=True
world.node_tree.nodes['Background'].inputs[0].default_value=(.17,.19,.21,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.35
def aim(o,target):o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
for name,p,energy,size in [('Key',(1,-1.2,1.7),140,1.2),('Fill',(-1,-.3,.8),50,1),('Rim',(.2,.8,1.3),100,.8)]:
    d=bpy.data.lights.new(name,'AREA');d.energy=energy;d.shape='DISK';d.size=size
    o=bpy.data.objects.new(name,d);scene.collection.objects.link(o);o.location=p;aim(o,(0,-.20,.09))
camera_data=bpy.data.cameras.new('ReviewCamera');camera=bpy.data.objects.new('ReviewCamera',camera_data)
scene.collection.objects.link(camera);scene.camera=camera;camera_data.type='ORTHO'
camera.location=(.9,-1.25,.64);aim(camera,(0,-.23,.08));camera_data.ortho_scale=.86
scene.render.image_settings.file_format='PNG'
source=OUT/'Krag_Regular_Weapon_Study_v2.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(source))
triangles=sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in parts)
report={'status':'Provisional isolated exterior study; not equipped, exported or artistically accepted',
        'reference':'krag-kings-design/concept-art/10-clan-boss-and-krag-comparison.png, regular Krag',
        'referenceSha256':hashlib.sha256((ROOT/'krag-kings-design/concept-art/10-clan-boss-and-krag-comparison.png').read_bytes()).hexdigest(),
        'recipeSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'source':str(source),'sourceSha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'meshObjects':len(parts),'triangles':triangles,'gripLengthMeters':handle_length,
        'gripCrossSectionMeters':[.0648,.04224],'forward':'-Y','up':'Z',
        'gripBindingAddedBeyondCore':True,'equippedHandContactVerified':False,
        'sharedAssetsChanged':False,'rendered':False,'views':[]}
if args.render:
    for name,p,target,scale in [('ThreeQuarter',(.9,-1.25,.64),(0,-.23,.08),.86),
        ('Side',(1.4,-.19,.26),(0,-.22,.085),.85),
        ('Muzzle',(.38,-1,.35),(0,-.39,.13),.45)]:
        camera.location=p;aim(camera,target);camera_data.ortho_scale=scale
        path=OUT/('Krag_Weapon_'+name+'.png');scene.render.filepath=str(path)
        bpy.ops.render.render(write_still=True)
        report['views'].append({'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    report['rendered']=True
(OUT/'study.json').write_text(json.dumps(report,indent=2)+'\n')
print('KRAG_WEAPON_STUDY_COMPLETE '+str(source),flush=True)
