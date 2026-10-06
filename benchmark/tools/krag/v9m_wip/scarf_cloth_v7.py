"""Isolated v9mb scarf study: a broad asymmetrical sheet, physically settled.

This is prepared source, not a verified cloth result. The v9ka terrace scarf and
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
        top_z=1.804+.029*back-.145*front+.016*math.cos(a+.25)
        base_r=.149+.038*front+.010*abs(math.cos(a))
        drop=.050+.102*front+.018*back+.011*math.sin(a+1.0)
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
            shoulder=max(0.,min(1.,(abs(math.cos(a))-.62)/.28))
            # Distributed support on the upper shoulder edge; no concentrated
            # end-tuck mass pin that gathers most of the strip into a side knot.
            pins.append(max(nape*upper,.62*shoulder*upper))
    for i in range(length-1):
        for j in range(width-1):
            k=i*width+j;faces.append((k,k+1,k+width+1,k+width))
    return np.asarray(vertices),faces,np.asarray(pins)


def collider_copy(source,smooth=False,exterior=False):
    """Exact neutral source surface, with no artificial neck-plane cut.

    Make a geometry-only physics copy: source shape keys/drivers are neither
    copied nor evaluated, and source data is never mutated.
    """
    mesh=source.data;basis=mesh.shape_keys.key_blocks['Basis'].data if mesh.shape_keys else mesh.vertices
    coordinates=[tuple(v.co) for v in basis]
    tags=mesh.attributes.get('.sculpt_face_set');faces=[]
    for polygon in mesh.polygons:
        if exterior and tags and tags.data[polygon.index].value in [7,5,6]:continue
        faces.append(tuple(polygon.vertices))
    data=bpy.data.meshes.new('Temporary cloth source surface '+source.name)
    data.from_pydata(coordinates,[],faces);data.update()
    o=bpy.data.objects.new('Temporary scarf collider '+source.name,data)
    bpy.context.collection.objects.link(o);o.matrix_world=source.matrix_world.copy()
    o.hide_render=True;o.hide_set(False)
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
    cage=o.copy();cage.data=o.data.copy();cage.name='EDITABLE v9mb scarf cloth pattern'
    for key in ['module','rig_bone']:
        if key in cage:del cage[key]
    bpy.data.collections['Authoring control cages'].objects.link(cage)
    cage.hide_render=True;cage.hide_set(True)
    body=c['actual_body']
    head=c['actual_head']
    if body is None or head is None:raise RuntimeError('Actual repaired body/head surfaces required for scarf study')
    colliders=[collider_copy(body),collider_copy(head,exterior=True)]
    # Equipment is a real collision obstacle, but it must not be mistaken for
    # skin when fitting the neck's initial radial envelope below.
    equipment=[obj for obj in bpy.data.objects if obj.type=='MESH' and obj.get('module') in ['Armor','Harness']]
    equipment_colliders=[collider_copy(obj,smooth=False) for obj in equipment]
    # Remove initial local penetration against the actual skin before gravity.
    # This is a bounded outward correction, not a substitute for collision.
    bvhs=[]
    for collider in colliders:
        bvhs.append(BVHTree.FromPolygons([collider.matrix_world@v.co for v in collider.data.vertices],
                                         [tuple(p.vertices) for p in collider.data.polygons]))
    # Fit the initial sheet to the real radial skin envelope rather than
    # trusting an elliptical neck radius across the flaring trapezius/chest.
    # Rays start inside the anatomical axis and hit its first outer surface;
    # this avoids treating a farther upper arm as the scarf support surface.
    # The prior low side rows entered the broad shoulder volume; a horizontal
    # radial ray then found x~0.44m. Keep the gathered sides high and seat them
    # ABOVE the actual torso shoulder surface before fitting radial clearance.
    # Only the torso collider supports this downward ray; the skull must not
    # pull a cloth point onto the crown. Final physical collision still uses both.
    lifted_count=0;max_vertical_fit=0.
    for vertex in o.data.vertices:
        radial=Vector((vertex.co.x,vertex.co.y-.019,0.))
        frontness=max(0.,-radial.y/max(radial.length,1e-9))
        # The shoulder support ray is for the sides/back only. Applying it to
        # the chest-facing sheet flattened its designed vertical width before
        # cloth rest lengths were recorded, destroying the front cowl.
        if frontness>.45:continue
        hit,normal,index,distance=bvhs[0].ray_cast(Vector((vertex.co.x,vertex.co.y,2.20)),Vector((0,0,-1)),.85)
        if hit is not None and 1.40<hit.z<1.88:
            required_z=hit.z+.010
            if required_z>vertex.co.z:
                max_vertical_fit=max(max_vertical_fit,required_z-vertex.co.z)
                vertex.co.z=required_z;lifted_count+=1
    fitted_count=0;max_radial_fit=0.
    for vertex in o.data.vertices:
        origin=Vector((0.,.019,vertex.co.z))
        direction=vertex.co-origin;radius=direction.length
        direction.normalize();required=radius
        for tree in bvhs:
            hit,normal,index,distance=tree.ray_cast(origin,direction,.34)
            if hit is not None:required=max(required,distance+.009)
        if required>.32:
            raise RuntimeError('Scarf radial fit escapes anatomical neck/shoulder bounds: '+str(required))
        if required>radius:
            vertex.co=origin+direction*required
            fitted_count+=1;max_radial_fit=max(max_radial_fit,required-radius)
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
    if max_adjustment>.055:raise RuntimeError('Scarf initial penetration exceeds bounded correction: '+str(max_adjustment))
    # The saved editable pattern records the actual physical-solver start.
    for target,source in zip(cage.data.vertices,o.data.vertices):target.co=source.co.copy()
    bpy.context.view_layer.objects.active=o
    cloth=o.modifiers.new('Gravity settled broad textile','CLOTH');s=cloth.settings
    s.quality=8;s.mass=.19;s.tension_stiffness=22;s.compression_stiffness=22
    s.shear_stiffness=12;s.bending_stiffness=.45;s.tension_damping=8
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
        for collider in colliders+equipment_colliders:
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
        'simulationFrames':54,'quality':8,'selfCollision':True,'bendingStiffness':.45,'shoulderLiftExcludedFrontnessAbove':.45,'pinDomain':'Distributed rear neckline and upper shoulder edge; free lower/front sheet',
        'colliders':'Exact repaired neutral Body, Head exterior, armor and harness geometry; no artificial horizontal neck crop',
        'bodyColliderVertices':len(body.data.vertices),'bodyColliderFaces':len(body.data.polygons),
        'headColliderVertices':len(head.data.vertices),
        'shoulderSurfaceLiftedVertices':lifted_count,'maxShoulderSurfaceLiftMeters':max_vertical_fit,
        'radialEnvelopeFittedVertices':fitted_count,'maxRadialEnvelopeAdjustmentMeters':max_radial_fit,
        'initialPenetrationAdjustedVertices':adjusted,'maxInitialAdjustmentMeters':max_adjustment,
        'settledBoundsMeters':[coords.min(0).tolist(),coords.max(0).tolist()],
        'postSimulationSubdivisions':2,'thicknessMeters':.0024}
    o['cloth_study']=json.dumps(study);c['scarf_cloth_study']=study
    return o
