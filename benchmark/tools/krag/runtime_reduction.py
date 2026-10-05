"""Derived mesh reduction with pinned boundaries and barycentric morph transfer.

The dense source object is never edited. Seam/material-boundary vertices receive
zero collapse weight, which Blender's decimator treats as ineligible edges.
See Blender bmesh_decimate_collapse.cc, bm_decim_build_edge_cost_single.
https://raw.githubusercontent.com/blender/blender/main/source/blender/bmesh/tools/bmesh_decimate_collapse.cc
"""
import math
import bpy, bmesh
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree


def coordinates(points):
    data=np.empty(len(points)*3,dtype=np.float32)
    points.foreach_get('co',data)
    return data.reshape(-1,3)


def triangles(mesh):
    mesh.calc_loop_triangles()
    data=np.empty(len(mesh.loop_triangles)*3,dtype=np.int32)
    mesh.loop_triangles.foreach_get('vertices',data)
    return data.reshape(-1,3)


def statistics(values):
    a=np.asarray(values,dtype=float)
    return {'samples':len(a),'rmsMeters':float(np.sqrt(np.mean(a*a))),
            'p95Meters':float(np.percentile(a,95)),
            'p99Meters':float(np.percentile(a,99)),'maxMeters':float(a.max())}


def correspondence(tree,verts,tris,points):
    """Closest base triangle and clamped barycentric weights for every point."""
    indices=np.empty(len(points),dtype=np.int32)
    nearest=np.empty((len(points),3),dtype=np.float32)
    distance=np.empty(len(points),dtype=np.float32)
    for i,point in enumerate(points):
        co,normal,index,dist=tree.find_nearest(Vector(point))
        if index is None:raise RuntimeError('No surface correspondence for vertex '+str(i))
        indices[i]=index;nearest[i]=co;distance[i]=dist
    ids=tris[indices]
    # Thin triangles suffer catastrophic Gram-determinant cancellation in
    # float32. Keep barycentric arithmetic double-precision, even though mesh
    # storage and the returned portable fields remain float32.
    a,b,c=(verts[ids[:,axis]].astype(np.float64) for axis in range(3))
    u=b-a;v=c-a;w=nearest.astype(np.float64)-a
    d00=np.einsum('ij,ij->i',u,u);d01=np.einsum('ij,ij->i',u,v);d11=np.einsum('ij,ij->i',v,v)
    d20=np.einsum('ij,ij->i',w,u);d21=np.einsum('ij,ij->i',w,v)
    denominator=d00*d11-d01*d01
    safe=np.where(np.abs(denominator)>1e-20,denominator,1)
    wb=(d11*d20-d01*d21)/safe;wc=(d00*d21-d01*d20)/safe
    weights=np.column_stack((1-wb-wc,wb,wc))
    weights=np.maximum(weights,0);weights/=np.maximum(weights.sum(axis=1)[:,None],1e-10)
    return ids,weights.astype(np.float32),distance


def pinned_vertices(mesh,bone_indices=None):
    bm=bmesh.new();bm.from_mesh(mesh);bm.verts.ensure_lookup_table();bm.edges.ensure_lookup_table()
    uv=bm.loops.layers.uv.active;pinned=set();skin_pinned=set();causes={'boundaryEdges':0,'uvSeamEdges':0,'materialEdges':0,'skinTransitionEdges':0}
    skin=[{g.group:g.weight for g in vertex.groups if bone_indices is not None and g.group in bone_indices and g.weight>1e-6} for vertex in mesh.vertices]
    for edge in bm.edges:
        loops=list(edge.link_loops);reason=None
        if len(loops)!=2:reason='boundaryEdges'
        elif loops[0].face.material_index!=loops[1].face.material_index:reason='materialEdges'
        elif uv:
            pairs=[]
            for loop in loops:
                pairs.append({loop.vert.index:loop[uv].uv.copy(),loop.link_loop_next.vert.index:loop.link_loop_next[uv].uv.copy()})
            if any((pairs[0][v.index]-pairs[1][v.index]).length>1e-6 for v in edge.verts):reason='uvSeamEdges'
        if reason is None and bone_indices:
            wa,wb=(skin[v.index] for v in edge.verts)
            if wa and wb and (set(wa)!=set(wb) or max(wa,key=wa.get)!=max(wb,key=wb.get) or max(abs(wa.get(k,0)-wb.get(k,0)) for k in set(wa)|set(wb))>.10):reason='skinTransitionEdges'
        if reason:
            causes[reason]+=1;pinned.update(v.index for v in edge.verts)
            if reason=='skinTransitionEdges':skin_pinned.update(v.index for v in edge.verts)
    # Keep the original triangles in a two-ring neighborhood of discontinuous skin fields.
    # Pinning only edge endpoints still lets adjacent collapses retriangulate across them.
    for _ in range(2):
        skin_pinned.update(other.index for index in list(skin_pinned) for edge in bm.verts[index].link_edges for other in edge.verts)
    pinned.update(skin_pinned);causes['skinProtectedBandVertices']=len(skin_pinned)
    bm.free();return sorted(pinned),causes


def transfer_skin_weights(source,result,rig,ids,barycentric):
    """Transfer the source skin field at each new vertex, rather than trusting collapse interpolation."""
    names=[group.name for group in source.vertex_groups if group.name in rig.data.bones]
    column={source.vertex_groups[name].index:i for i,name in enumerate(names)}
    source_weights=np.zeros((len(source.data.vertices),len(names)),dtype=np.float32)
    for vertex in source.data.vertices:
        for group in vertex.groups:
            if group.group in column:source_weights[vertex.index,column[group.group]]=group.weight
    target=np.einsum('ijk,ij->ik',source_weights[ids],barycentric)
    target[target<1e-6]=0;totals=target.sum(axis=1)
    if np.min(totals)<1e-7:raise RuntimeError('Barycentric skin transfer produced an unweighted vertex')
    target/=totals[:,None]
    result.vertex_groups.clear()
    for i,name in enumerate(names):
        group=result.vertex_groups.new(name=name)
        for index in np.flatnonzero(target[:,i]>0):group.add([int(index)],float(target[index,i]),'REPLACE')
    return {'method':'Barycentric interpolation of original source triangle bone weights','maxPositiveInfluences':int(np.max(np.sum(target>1e-6,axis=1))),'maxNormalizationCorrection':float(np.max(np.abs(totals-1)))}


def check_pinned_seams(source,result,source_vertices,low_vertices,pinned):
    """Verify protected coordinates and their UV corner values survived reduction."""
    if not pinned:return {'samples':0,'maxPositionErrorMeters':0,'uvCornerValuesPreserved':True}
    tree=KDTree(len(low_vertices))
    for i,v in enumerate(low_vertices):tree.insert(Vector(v),i)
    tree.balance();maximum=0
    for index in pinned:maximum=max(maximum,tree.find(Vector(source_vertices[index]))[2])
    if maximum>2e-7:raise RuntimeError(f'{source.name}: protected boundary moved by {maximum}m')
    key=lambda co:tuple(round(float(x),6) for x in co)
    protected={key(source_vertices[i]) for i in pinned};expected={};actual={}
    for obj,vertices,destination in [(source,source_vertices,expected),(result,low_vertices,actual)]:
        uv=obj.data.uv_layers.active
        for loop in obj.data.loops:
            position=key(vertices[loop.vertex_index])
            if position in protected:destination.setdefault(position,set()).add(tuple(round(float(x),6) for x in uv.data[loop.index].uv))
    missing=sum(len(values-actual.get(position,set())) for position,values in expected.items())
    if missing:raise RuntimeError(f'{source.name}: {missing} protected UV corner values changed')
    return {'samples':len(pinned),'maxPositionErrorMeters':maximum,'uvCornerValuesPreserved':True}


def validate_weights(obj,rig):
    bone_groups={g.index for g in obj.vertex_groups if g.name in rig.data.bones}
    totals=[];missing=[];max_influences=0
    for vertex in obj.data.vertices:
        weights=[g.weight for g in vertex.groups if g.group in bone_groups]
        if any(not math.isfinite(w) or w<0 for w in weights):raise RuntimeError(f'{obj.name}: negative/nonfinite individual skin weight at {vertex.index}')
        max_influences=max(max_influences,sum(w>1e-6 for w in weights));total=sum(weights)
        if not math.isfinite(total) or total<1e-7:missing.append(vertex.index)
        totals.append(total)
    if missing:raise RuntimeError(f'{obj.name}: unweighted/nonfinite vertices: {missing[:12]}')
    error=max(abs(x-1) for x in totals)
    if error>1e-4:raise RuntimeError(f'{obj.name}: weight sum differs from one by {error}')
    if max_influences>8:raise RuntimeError(f'{obj.name}: {max_influences} positive skin influences exceed the shared eight-influence import contract')
    return {'maxSumError':error,'unweightedVertices':0,'maxPositiveBoneInfluences':max_influences,'negativeOrNonfiniteWeights':0}


def attach_portable_drivers(obj,rig,deformation):
    for entry in deformation['drivers']:
        key=obj.data.shape_keys.key_blocks.get(entry['morph'])
        if not key:continue
        curve=key.driver_add('value');driver=curve.driver;driver.type='SCRIPTED'
        for axis in 'xyz':
            variable=driver.variables.new();variable.name=axis;variable.type='TRANSFORMS'
            target=variable.targets[0];target.id=rig;target.bone_target=entry['bone'];target.transform_space='LOCAL_SPACE'
            target.transform_type=('ROT_' if entry['channel']=='rotationMagnitudeDegrees' else 'LOC_')+axis.upper()
        metric=('2*acos(min(1,abs(cos(x/2)*cos(y/2)*cos(z/2)+sin(x/2)*sin(y/2)*sin(z/2))))*57.2957795131'
                if entry['channel']=='rotationMagnitudeDegrees' else 'sqrt(x*x+y*y+z*z)')
        driver.expression=f'min({entry.get("maxWeight",1)},max(0,(({metric})-{entry["start"]})/{entry["end"]-entry["start"]}))'


def reduce_object(source,rig,target_triangles,deformation,surface_limit=.0025,morph_limit=.0015):
    """Return a new object and actual approximation report; caller owns replacement."""
    basis=np.array(source.matrix_world.to_3x3(),dtype=float)
    if not np.allclose(basis.T@basis,np.eye(3),atol=1e-6):raise RuntimeError(source.name+': unapplied scale makes local surface distances differ from metres')
    source_vertices=coordinates(source.data.shape_keys.key_blocks['Basis'].data if source.data.shape_keys else source.data.vertices)
    source_triangles=triangles(source.data);before=len(source_triangles)
    entry={'module':source.get('module',source.name),'sourceVertices':len(source_vertices),'sourceTriangles':before,'requestedTriangles':target_triangles}
    if before<=target_triangles:
        entry.update({'reduced':False,'runtimeVertices':len(source_vertices),'runtimeTriangles':before,'weights':validate_weights(source,rig)})
        return source,entry
    source_tree=BVHTree.FromPolygons(source_vertices.tolist(),source_triangles.tolist(),all_triangles=True)
    bpy.ops.object.select_all(action='DESELECT')
    result=source.copy();result.data=source.data.copy();bpy.context.collection.objects.link(result)
    result.hide_set(False);result.hide_render=False;result.select_set(True);bpy.context.view_layer.objects.active=result
    if result.data.shape_keys:result.shape_key_clear()
    result.data.vertices.foreach_set('co',source_vertices.ravel())
    for mod in list(result.modifiers):result.modifiers.remove(mod)
    pinned,causes=pinned_vertices(result.data,{g.index for g in result.vertex_groups if g.name in rig.data.bones})
    protect=result.vertex_groups.new(name='__RuntimeReductionEligible')
    protect.add(list(range(len(result.data.vertices))),1,'REPLACE')
    if pinned:protect.add(pinned,0,'REPLACE')
    mod=result.modifiers.new('Derived silhouette-aware reduction','DECIMATE');mod.decimate_type='COLLAPSE'
    protect_name=protect.name
    mod.ratio=target_triangles/before;mod.use_collapse_triangulate=True;mod.vertex_group=protect_name;mod.vertex_group_factor=1
    bpy.ops.object.modifier_apply(modifier=mod.name)
    # Applying a modifier can recreate the deform-group RNA collection.
    remaining_group=result.vertex_groups.get(protect_name)
    if remaining_group:result.vertex_groups.remove(remaining_group)
    result.data.update();low_vertices=coordinates(result.data.vertices);low_triangles=triangles(result.data)
    if not np.isfinite(low_vertices).all():raise RuntimeError('Nonfinite reduced coordinates: '+source.name)
    ids,weights,distance=correspondence(source_tree,source_vertices,source_triangles,low_vertices)
    skin_transfer=transfer_skin_weights(source,result,rig,ids,weights)
    low_tree=BVHTree.FromPolygons(low_vertices.tolist(),low_triangles.tolist(),all_triangles=True)
    sample_ids=np.unique(np.linspace(0,len(source_vertices)-1,min(16000,len(source_vertices)),dtype=np.int32))
    reverse_ids,reverse_weights,reverse_distance=correspondence(low_tree,low_vertices,low_triangles,source_vertices[sample_ids])
    surface={'runtimeVerticesToSource':statistics(distance),'sampledSourceVerticesToRuntime':statistics(reverse_distance)}
    entry.update({'reduced':True,'runtimeVertices':len(low_vertices),'runtimeTriangles':len(low_triangles),
                  'pinnedVertexCount':len(pinned),'pinnedReasons':causes,'surfaceError':surface,'morphs':{}})
    entry['skinWeightTransfer']=skin_transfer
    entry['protectedSeamValidation']=check_pinned_seams(source,result,source_vertices,low_vertices,pinned)
    if max(surface[k]['maxMeters'] for k in surface)>surface_limit:
        raise RuntimeError(f'{source.name}: surface error exceeds {surface_limit}m; measured {surface}')
    result.shape_key_add(name='Basis',from_mix=False)
    for shape in list(source.data.shape_keys.key_blocks)[1:] if source.data.shape_keys else []:
        delta=coordinates(shape.data)-source_vertices
        low_delta=np.einsum('ijk,ij->ik',delta[ids],weights)
        key=result.shape_key_add(name=shape.name,from_mix=False);key.slider_min=shape.slider_min;key.slider_max=shape.slider_max
        key.data.foreach_set('co',(low_vertices+low_delta).ravel())
        reverse_delta=np.einsum('ijk,ij->ik',low_delta[reverse_ids],reverse_weights)
        morph_error=np.linalg.norm(reverse_delta-delta[sample_ids],axis=1)
        metrics=statistics(morph_error);metrics['maxDisplacementMeters']=float(np.linalg.norm(low_delta,axis=1).max())
        entry['morphs'][shape.name]=metrics
        if metrics['maxMeters']>morph_limit:raise RuntimeError(f'{source.name}/{shape.name}: morph delta error {metrics["maxMeters"]}m exceeds {morph_limit}m')
    attach_portable_drivers(result,rig,deformation)
    armature=result.modifiers.new('Krag weighted deformation','ARMATURE');armature.object=rig
    entry['weights']=validate_weights(result,rig)
    uv=result.data.uv_layers.active
    if not uv or uv.name!='UVMap':raise RuntimeError('UVMap missing after reduction: '+source.name)
    values=np.empty(len(uv.data)*2,dtype=np.float32);uv.data.foreach_get('uv',values)
    if not np.isfinite(values).all():raise RuntimeError('Nonfinite UVs after reduction: '+source.name)
    entry['uv']={'layer':uv.name,'finite':True,'seamVerticesPinned':True}
    result['runtime_reduction_source_triangles']=before;result['runtime_reduction_triangles']=len(low_triangles)
    return result,entry
