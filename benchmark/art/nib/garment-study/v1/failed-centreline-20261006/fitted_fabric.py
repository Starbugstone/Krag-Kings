"""Prepared bounded native cloth fitting; no generated or accepted garment.

Simulate only an isolated neutral authoring copy. Bake it to a skinned mesh;
no runtime cloth solver or Blender-only deformation is part of the contract.
"""
import math,json
from pathlib import Path
from collections import defaultdict
import bpy
import numpy as np
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
from cloth_patterns import smooth


def tree(obj):
    obj.data.calc_loop_triangles()
    points=np.asarray([tuple(obj.matrix_world@v.co) for v in obj.data.vertices],dtype=np.float64)
    triangles=np.asarray([t.vertices[:] for t in obj.data.loop_triangles],dtype=np.int32)
    return BVHTree.FromPolygons(points,triangles,all_triangles=True),points,triangles


def collider(obj):
    mesh=bpy.data.meshes.new('TEMP neutral fabric collider '+obj.name)
    mesh.from_pydata([tuple(obj.matrix_world@v.co) for v in obj.data.vertices],[],[p.vertices[:] for p in obj.data.polygons]);mesh.update()
    out=bpy.data.objects.new(mesh.name,mesh);bpy.context.collection.objects.link(out);out.hide_render=True
    out.modifiers.new('Static fitted anatomy collision','COLLISION');out.collision.thickness_outer=.0015;out.collision.cloth_friction=5
    return out


def fit_to_skin(points,support,clearance):
    """Actual nearest skin projection, not ellipse-based shoulder placement."""
    fitted=[];largest=0.
    for value in points:
        p=Vector(value);hit,normal,_,_=support.find_nearest(p)
        if hit is None:raise RuntimeError('No actual anatomical surface for fabric point')
        target=hit+normal*clearance;largest=max(largest,(target-p).length);fitted.append(tuple(target))
    if largest>.035:raise RuntimeError('Undershirt initial fitting exceeds35mm: '+str(largest))
    return np.asarray(fitted),largest


def create(name,pattern,collection,material,uv=None):
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(pattern['points'],[],pattern['faces']);mesh.update();mesh.materials.append(material)
    obj=bpy.data.objects.new(name,mesh);collection.objects.link(obj)
    pin=obj.vertex_groups.new(name='AUTHORING fabric supports')
    for i,value in enumerate(pattern['pins']):
        if value>1e-7:pin.add([i],float(value),'REPLACE')
    layer=mesh.uv_layers.new(name='UVMap')
    if uv is not None:
        for loop,value in zip(layer.data,uv):loop.uv=value
    else:
        for loop in mesh.loops:layer.data[loop.index].uv=pattern['uv'][loop.vertex_index]
    for polygon in mesh.polygons:polygon.use_smooth=True
    return obj,pin


def settle(obj,pin,supports,frames,scarf=False):
    scene=bpy.context.scene;oldframe=scene.frame_current;pin_name=pin.name
    temporary=[collider(support) for support in supports]
    bpy.context.view_layer.objects.active=obj;bpy.ops.object.select_all(action='DESELECT');obj.select_set(True)
    cloth=obj.modifiers.new('Bounded neutral fabric settling','CLOTH');s=cloth.settings
    s.quality=8;s.mass=.14;s.tension_stiffness=25;s.compression_stiffness=25;s.shear_stiffness=14
    s.bending_stiffness=.09 if scarf else .16;s.tension_damping=8;s.compression_damping=8;s.shear_damping=8;s.air_damping=5
    s.vertex_group_mass=pin.name;s.pin_stiffness=1
    c=cloth.collision_settings;c.use_collision=True;c.distance_min=.0018;c.use_self_collision=True;c.self_distance_min=.0018;c.self_friction=4
    cloth.point_cache.frame_start=1;cloth.point_cache.frame_end=frames
    initial=np.asarray([v.co[:] for v in obj.data.vertices]);max_displacement=0.
    try:
        for frame in range(1,frames+1):
            scene.frame_set(frame);bpy.context.view_layer.update()
            if frame%7==0 or frame==frames:
                evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());points=np.asarray([v.co[:] for v in evaluated.data.vertices])
                if not np.isfinite(points).all():raise RuntimeError('Nonfinite cloth solve')
                max_displacement=max(max_displacement,float(np.linalg.norm(points-initial,axis=1).max()))
                if max_displacement>.10:raise RuntimeError('Fabric escaped100mm bounded settling region')
                print('NIB_FABRIC_SOLVE',obj.name,frame,flush=True)
        bpy.context.view_layer.objects.active=obj;bpy.ops.object.modifier_apply(modifier=cloth.name)
    finally:
        for item in temporary:
            mesh=item.data;bpy.data.objects.remove(item,do_unlink=True)
            if mesh.users==0:bpy.data.meshes.remove(mesh)
        scene.frame_set(oldframe)
    obj.vertex_groups.remove(obj.vertex_groups[pin_name])
    return {'frames':frames,'selfCollision':True,'quality':8,'maximumMeasuredDisplacementMeters':max_displacement,
        'colliders':[o.name for o in supports],'collisionClearanceMeters':.0018,'runtimeSimulation':False}


def finish(obj,thickness):
    bpy.context.view_layer.objects.active=obj
    sub=obj.modifiers.new('Smooth fitted fabric','SUBSURF');sub.levels=1;bpy.ops.object.modifier_apply(modifier=sub.name)
    solid=obj.modifiers.new('Actual woven textile thickness','SOLIDIFY');solid.thickness=thickness;solid.offset=0
    bpy.ops.object.modifier_apply(modifier=solid.name)
    for polygon in obj.data.polygons:polygon.use_smooth=True


def bind_to_body(obj,rig,body,rigid=False):
    support,points,triangles=tree(body);bone_names=[g.name for g in body.vertex_groups]
    source_weights=np.zeros((len(points),len(bone_names)))
    for vertex in body.data.vertices:
        for g in vertex.groups:source_weights[vertex.index,g.group]=g.weight
    locations=np.asarray([tuple(obj.matrix_world@v.co) for v in obj.data.vertices])
    query=locations.mean(axis=0,keepdims=True) if rigid else locations
    fields=[];largest=0.
    for p in query:
        hit,_,index,distance=support.find_nearest(Vector(p));largest=max(largest,distance)
        if hit is None:raise RuntimeError('Missing body correspondence for garment')
        ids=triangles[index];a,b,c=points[ids];e0=b-a;e1=c-a;q=np.asarray(hit)-a
        d00=e0@e0;d01=e0@e1;d11=e1@e1;denominator=d00*d11-d01*d01
        if denominator<=1e-18:raise RuntimeError('Degenerate garment weight correspondence')
        v=(d11*(q@e0)-d01*(q@e1))/denominator;w=(d00*(q@e1)-d01*(q@e0))/denominator
        bary=np.maximum([1-v-w,v,w],0);bary/=np.sum(bary)
        fields.append(bary@source_weights[ids])
    fields=np.asarray(fields)
    if rigid:
        bone=int(fields[0].argmax());fields[:]=0;fields[0,bone]=1;fields=np.repeat(fields,len(locations),axis=0)
    obj.vertex_groups.clear();groups=[obj.vertex_groups.new(name=name) for name in bone_names]
    for i,row in enumerate(fields):
        for group,value in zip(groups,row):
            if value>1e-8:group.add([i],float(value),'REPLACE')
    if np.max(abs(fields.sum(axis=1)-1))>2e-6:raise RuntimeError('Garment weights do not normalize')
    world=obj.matrix_world.copy();obj.parent=rig;obj.matrix_world=world
    if not any(m.type=='ARMATURE' for m in obj.modifiers):
        mod=obj.modifiers.new('Portable garment skinning','ARMATURE');mod.object=rig;mod.use_deform_preserve_volume=False
    return {'object':obj.name,'rigid':rigid,'maximumBodySupportDistanceMeters':largest,
        'maximumInfluences':int(np.count_nonzero(fields>1e-8,axis=1).max())}


def scarf_initial_fit(pattern,body,head,shirt):
    """Fit the actual neck envelope before simulation; retain bounded evidence."""
    trees=[tree(obj)[0] for obj in [body,head,shirt]];points=pattern['points'].copy();original_points=points.copy();max_shift=0.;front_max_lift=0.
    for i,value in enumerate(points):
        p=Vector(value);original=p.copy();origin=Vector((0,.008,p.z));direction=p-origin;radius=direction.length;direction.normalize()
        required=radius
        for support in trees:
            hit,_,_,distance=support.ray_cast(origin,direction,.20)
            if hit is not None:required=max(required,distance+.005)
        if required>.15:raise RuntimeError('Scarf initial radial fit escapes Nib neck/shoulder region')
        p=origin+direction*required
        for support in trees:
            hit,normal,_,distance=support.find_nearest(p)
            if hit is not None and distance<.035 and (p-hit).dot(normal)<.0035:p=hit+normal*.0035
        if direction.y<-.65:
            front_max_lift=max(front_max_lift,p.z-original.z)
            if p.z-original.z>.006:
                raise RuntimeError('Front scarf fitting erases authored cowl sag by lifting over6mm; revise the initial pattern')
        max_shift=max(max_shift,(p-original).length);points[i]=p
    if max_shift>.055:raise RuntimeError('Scarf initial contact correction exceeds55mm')
    pattern['points']=points
    front=original_points[:,1]<-.04
    return {'maximumInitialContactAdjustmentMeters':max_shift,'radialEnvelopeMaximumMeters':.15,
        'frontMaximumLiftMeters':front_max_lift,'frontMinimumZBefore':float(original_points[front,2].min()),
        'frontMinimumZAfter':float(points[front,2].min()),'shoulderLiftAppliedToFront':False,
        'status':'Initial actual-skin fitting; final contact and appearance still require native review'}


def strap_displacements(original,new_tree,body_tree):
    """Fit the authored strap centreline; preserve its cross-sectional shape.

    A horizontal radial ray can leave the neck/arm opening and hit an unrelated
    arm surface. Shoulder leather follows the nearest local shoulder support.
    Deltas interpolate through the existing mesh, never flatten both faces onto
    a single collider. The original 35 mm fitting limit is unchanged.
    """
    front=(original[:,1]<-.025)&(original[:,2]>.86)
    if not front.any():raise RuntimeError('Cannot identify the authored strap front')
    side=1 if original[front,0].mean()>0 else -1
    guide=np.asarray([(side*.060,-.073,.880),(side*.073,-.065,.937),
        (side*.082,-.029,.967),(side*.079,.025,.965),(side*.055,.067,.893),
        (side*.017,.074,.816),(-side*.052,.067,.729)],dtype=float)
    shifts=[];receipt=[]
    for i,point in enumerate(guide):
        # The upper leather crosses the exposed shoulder, while front/back
        # lower sections lie on the undershirt. Query the actual local surface.
        upper=float(smooth(.912,.95,point[2]));targets=[]
        for name,support,clearance in [('shirt',new_tree,.005),('body',body_tree,.012)]:
            hit,normal,triangle,distance=support.find_nearest(Vector(point))
            if hit is None:raise RuntimeError('No actual strap centreline support')
            targets.append(np.asarray(hit+normal*clearance))
        target=targets[0]*(1-upper)+targets[1]*upper;delta=target-point
        measured=float(np.linalg.norm(delta))
        receipt.append({'control':i,'original':point.tolist(),'fitted':target.tolist(),
            'displacementMeters':measured,'bodySupportBlend':upper})
        if measured>.035:
            path=Path(__file__).resolve().parents[4]/'benchmark/local/nib-strap-centreline-failure.json'
            path.write_text(json.dumps(receipt,indent=2)+'\n',newline='\n')
            raise RuntimeError('Strap local centreline fit exceeds unchanged35mm gate; '+str(path))
        shifts.append(delta)
    shifts=np.asarray(shifts);changes=[]
    for point in original:
        start=guide[:-1];edge=guide[1:]-start
        t=np.clip(np.sum((point-start)*edge,axis=1)/np.sum(edge*edge,axis=1),0,1)
        distance=np.linalg.norm(point-(start+t[:,None]*edge),axis=1);i=int(distance.argmin())
        # Smooth endpoint interpolation avoids an abrupt displacement slope at
        # each authored section while preserving the original closed leather.
        blend=float(smooth(0,1,t[i]));changes.append(shifts[i]*(1-blend)+shifts[i+1]*blend)
    changes=np.asarray(changes)
    if np.linalg.norm(changes,axis=1).max()>.03500001:raise RuntimeError('Interpolated strap exceeds35mm')
    return changes,receipt


def refit_layer(obj,old_shirt,new_shirt,body,rig,rigid=False):
    old_tree=tree(old_shirt)[0];new_tree=tree(new_shirt)[0];body_tree=tree(body)[0]
    original=np.asarray([tuple(obj.matrix_world@v.co) for v in obj.data.vertices]);changes=np.zeros_like(original)
    support_receipt=None
    if obj.name.startswith('Overalls shoulder strap'):
        changes,support_receipt=strap_displacements(original,new_tree,body_tree)
    for i,p in enumerate(original) if support_receipt is None else []:
        origin=Vector((0,.007,float(p[2])));direction=Vector(p)-origin
        if direction.length<1e-6:continue
        direction.normalize();old,_,_,a=old_tree.ray_cast(origin,direction,.25)
        new,_,_,b=new_tree.ray_cast(origin,direction,.25)
        if new is None:new,_,_,b=body_tree.ray_cast(origin,direction,.25);b=(b+.005) if b is not None else None
        if old is None or new is None:raise RuntimeError('Missing old/new garment support: '+obj.name)
        change=b-a
        if abs(change)>.035:
            nearest={}
            for label,support in [('oldShirt',old_tree),('newShirt',new_tree),('body',body_tree)]:
                q,n,triangle,d=support.find_nearest(Vector(p))
                nearest[label]={'position':list(q) if q else None,'normal':list(n) if n else None,'triangle':triangle,'distanceMeters':d}
            evidence={'object':obj.name,'vertex':i,'point':p.tolist(),'rayOrigin':list(origin),'rayDirection':list(direction),
                'oldRayDistance':a,'newRayDistance':b,'requestedRadialShiftMeters':change,'nearestSurfaces':nearest,
                'status':'Failed unchanged35mm gate; no source saved','repairApplied':False}
            path=Path(__file__).resolve().parents[4]/'benchmark/local/nib-garment-support-failure.json'
            path.write_text(json.dumps(evidence,indent=2)+'\n',newline='\n')
            raise RuntimeError('Layer refit exceeds35mm: '+obj.name+'; diagnostic '+str(path))
        changes[i]=np.asarray(direction)*change
    if rigid:changes[:]=np.mean(changes,axis=0)
    inverse=np.asarray(obj.matrix_world.inverted().to_3x3());local=changes@inverse.T
    arrays=[key.data for key in obj.data.shape_keys.key_blocks] if obj.data.shape_keys else [obj.data.vertices]
    for array in arrays:
        for i,vertex in enumerate(array):vertex.co+=Vector(local[i])
    if obj.data.shape_keys:
        obj.data.vertices.foreach_set('co',np.asarray([v.co[:] for v in obj.data.shape_keys.key_blocks['Basis'].data],dtype=np.float32).ravel())
    obj.data.update();binding=bind_to_body(obj,rig,body,rigid)
    return {'object':obj.name,'maximumShiftMeters':float(np.linalg.norm(changes,axis=1).max()),'binding':binding,
        'supportMode':'actual local centreline' if support_receipt else 'radial torso layers','centreline':support_receipt}
