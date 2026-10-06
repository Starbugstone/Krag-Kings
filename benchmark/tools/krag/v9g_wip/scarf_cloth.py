"""Isolated v9g scarf study: a broad asymmetrical sheet, physically settled.

This is prepared source, not a verified cloth result. The v9f terrace scarf and
its generator remain intact. Body/head colliders come from the actual editable
anatomical cages; the simulation is baked into mesh before rigging/export.
"""
import math
import json
import numpy as np
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def initial_sheet(length=177, width=29):
    """A wrapped sheet with broad diagonal folds and unequal front sag.

    Across-width distance is not a radial staircase. Fold directions cross
    diagonally and broaden/flatten near their ends; free cloth may settle.
    """
    vertices=[];faces=[];pins=[]
    for i in range(length):
        u=i/(length-1);a=math.pi/2-.27+2*math.pi*1.16*u
        front=max(0.,-math.sin(a));back=max(0.,math.sin(a))
        # Both ends tuck behind the armored side. The neckline is low at the
        # front jaw, with shoulder support and a deliberately unequal V sag.
        top_z=1.824+.032*back-.100*front+.014*math.cos(a+.25)
        base_r=.143+.023*front+.010*abs(math.cos(a))
        drop=.158+.020*front+.010*math.sin(a+1.0)
        for j in range(width):
            v=j/(width-1)
            # Broad folds cross the strip rather than maintaining the same
            # lathed cross-section around the whole neck.
            q=v+.090*math.sin(a+.4)*math.sin(math.pi*v)
            f1=.26+.17*math.sin(a+.45)
            f2=.70+.12*math.sin(2*a-1.1)
            fold1=math.exp(-((q-f1)/(.100+.018*math.cos(a)))**2)
            fold2=math.exp(-((q-f2)/(.135+.026*math.sin(a+.4)))**2)
            # A convex roll is followed by a shallow valley; no closed tube.
            valley1=math.exp(-((q-f1-.115)/.095)**2)
            valley2=math.exp(-((q-f2-.140)/.120)**2)
            breadth=.025+.046*front
            r=base_r+breadth*q+.018*fold1+.011*fold2-.007*valley1-.006*valley2
            z=top_z-drop*q-.030*front*math.sin(math.pi*q)
            z+=.014*math.sin(a+2.4*q)*math.sin(math.pi*q)
            # A sideways bias produces a dropped chest V rather than three
            # nested concentric rings. Overlap end is slightly lifted outward.
            angle=a+.105*math.sin(math.pi*q)*math.sin(a-.3)
            end=max(0.,(u-.86)/.14)
            r+=.010*end;z+=.018*end
            p=(r*math.cos(angle),.019+r*math.sin(angle),z)
            vertices.append(p)
            # Only the rear upper edge and one shoulder tuck are attached.
            # This rule uses this mesh's own u/v, never old vertex counts.
            nape=max(0.,min(1.,(math.sin(a)-.35)/.45))
            upper=max(0.,1-v/.17)
            tuck=math.exp(-((u-.965)/.065)**2)*max(0.,1-v/.70)
            pins.append(max(nape*upper,tuck*.86))
    for i in range(length-1):
        for j in range(width-1):
            k=i*width+j;faces.append((k,k+1,k+width+1,k+width))
    return np.asarray(vertices),faces,np.asarray(pins)


def collider_copy(source,head=False):
    """Visible-to-solver duplicate; never mutate the preserved source cage."""
    o=bpy.data.objects.new('Temporary scarf collider '+source.name,source.data.copy())
    bpy.context.collection.objects.link(o);o.matrix_world=source.matrix_world.copy()
    o.hide_render=True;o.hide_set(False)
    if head:
        import krag_face
        for v in o.data.vertices:v.co=Vector(krag_face.H(v.co))
    bpy.context.view_layer.objects.active=o;o.select_set(True)
    sub=o.modifiers.new('Smooth collision cage','SUBSURF');sub.levels=1
    bpy.ops.object.modifier_apply(modifier=sub.name)
    o.modifiers.new('Actual anatomical cloth collision','COLLISION')
    o.collision.thickness_outer=.003;o.collision.cloth_friction=7
    o['temporary_cloth_collider']=True
    return o


def build(c):
    scene=bpy.context.scene;old_frame=scene.frame_current
    vertices,faces,pins=initial_sheet()
    o=c['mesh']('Asymmetrical draped desert scarf',vertices,faces,c['cloth'],'Scarf','Chest')
    # Keep the unrelaxed pattern as editable authoring geometry, not a second
    # visible garment. It stores the own-mesh pin field and construction UVs.
    pin=o.vertex_groups.new(name='Rear neckline and shoulder tuck')
    for i,value in enumerate(pins):
        if value>0:pin.add([i],float(value),'REPLACE')
    cage=o.copy();cage.data=o.data.copy();cage.name='EDITABLE v9g scarf cloth pattern'
    for key in ['module','rig_bone']:
        if key in cage:del cage[key]
    bpy.data.collections['Authoring control cages'].objects.link(cage)
    cage.hide_render=True;cage.hide_set(True)
    body=bpy.data.objects.get('EDITABLE Krag anatomical control cage')
    head=bpy.data.objects.get('EDITABLE Krag continuous facial cage')
    if body is None or head is None:raise RuntimeError('Actual body/head cages required for scarf study')
    colliders=[collider_copy(body),collider_copy(head,head=True)]
    # Remove initial local penetration against the actual skin before gravity.
    # This is a bounded outward correction, not a substitute for collision.
    bvhs=[]
    for collider in colliders:
        bvhs.append(BVHTree.FromPolygons([collider.matrix_world@v.co for v in collider.data.vertices],
                                         [tuple(p.vertices) for p in collider.data.polygons]))
    adjusted=0;max_adjustment=0.
    for vertex in o.data.vertices:
        original=vertex.co.copy()
        for tree in bvhs:
            point,normal,index,distance=tree.find_nearest(vertex.co)
            if point is None:continue
            signed=(vertex.co-point).dot(normal)
            if signed<.006 and distance<.055:vertex.co=point+normal*.006
        d=(vertex.co-original).length
        if d>0:adjusted+=1;max_adjustment=max(max_adjustment,d)
    if max_adjustment>.055:raise RuntimeError('Scarf initial penetration exceeds bounded correction')
    bpy.context.view_layer.objects.active=o
    cloth=o.modifiers.new('Gravity settled broad textile','CLOTH');s=cloth.settings
    s.quality=8;s.mass=.19;s.tension_stiffness=22;s.compression_stiffness=22
    s.shear_stiffness=12;s.bending_stiffness=.12;s.tension_damping=8
    s.compression_damping=8;s.shear_damping=8;s.air_damping=5
    s.vertex_group_mass=pin.name;s.pin_stiffness=1
    cs=cloth.collision_settings;cs.use_collision=True;cs.distance_min=.004
    cs.use_self_collision=True;cs.self_distance_min=.004;cs.self_friction=4
    cloth.point_cache.frame_start=1;cloth.point_cache.frame_end=54
    try:
        for frame in range(1,55):
            scene.frame_set(frame);bpy.context.view_layer.update()
            if frame%9==0:
                evaluated=o.evaluated_get(bpy.context.evaluated_depsgraph_get())
                coords=np.asarray([tuple(v.co) for v in evaluated.data.vertices])
                if not np.isfinite(coords).all() or np.max(np.abs(coords))>3:
                    raise RuntimeError('Scarf solver produced invalid geometry at frame '+str(frame))
                print('KRAG scarf cloth frame',frame,flush=True)
        bpy.context.view_layer.objects.active=o
        bpy.ops.object.modifier_apply(modifier=cloth.name)
    finally:
        for collider in colliders:
            mesh=collider.data;bpy.data.objects.remove(collider,do_unlink=True)
            if mesh.users==0:bpy.data.meshes.remove(mesh)
        scene.frame_set(old_frame)
    coords=np.asarray([tuple(v.co) for v in o.data.vertices])
    if coords[:,2].min()<1.35 or coords[:,2].max()>1.95:
        raise RuntimeError('Settled scarf escaped neck/chest bounds: '+str(coords.min(0))+' / '+str(coords.max(0)))
    # Topology is preserved through the simulation; actual cloth thickness and
    # smooth presentation are added afterwards, not to the collision solve.
    sub=o.modifiers.new('Smooth textile surface','SUBSURF');sub.levels=2
    bpy.context.view_layer.objects.active=o;bpy.ops.object.modifier_apply(modifier=sub.name)
    solid=o.modifiers.new('Woven textile thickness','SOLIDIFY');solid.thickness=.0024;solid.offset=0
    bpy.ops.object.modifier_apply(modifier=solid.name)
    for p in o.data.polygons:p.use_smooth=True
    study={'status':'Actual simulated source study; visual/intersection/pose acceptance pending',
        'simulationFrames':54,'quality':8,'selfCollision':True,'pinDomain':'Own u/v rear neckline and shoulder tuck',
        'colliders':'Copies of actual editable torso and complete proportion-transformed face cages',
        'initialPenetrationAdjustedVertices':adjusted,'maxInitialAdjustmentMeters':max_adjustment,
        'settledBoundsMeters':[coords.min(0).tolist(),coords.max(0).tolist()],
        'postSimulationSubdivisions':2,'thicknessMeters':.0024}
    o['cloth_study']=json.dumps(study);c['scarf_cloth_study']=study
    return o
