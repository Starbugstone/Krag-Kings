"""Deterministically halve strand segments without dropping guides or tips.

Retains every authored strand, cross-section, root and tip. Copies skin weights,
UV coordinates and every shape exactly at retained vertices. A geometric chord
error is measured at omitted rings for Basis and all shapes before acceptance.
"""
import bpy
import numpy as np

def co_array(points):
    result=np.empty(len(points)*3,dtype=np.float32);points.foreach_get('co',result)
    return result.reshape(-1,3)

def reduce_fur(source,rig,deformation,attach_drivers,max_chord_error=.0008):
    count=int(source.get('fur_strands',0));old_rings=5;sides=3
    initial_rings=[0,4] if source.name.startswith('Fine skin fuzz') else [0,2,4]
    if count<=0 or len(source.data.vertices)!=count*old_rings*sides:
        raise RuntimeError('Unexpected batch strand topology: '+source.name)
    keys=list(source.data.shape_keys.key_blocks) if source.data.shape_keys else []
    basis=co_array(keys[0].data if keys else source.data.vertices)
    matrix=np.asarray(source.matrix_world,dtype=float)[:3,:3]
    kept=[set(initial_rings) for _ in range(count)]
    # Preserve extra rings only where measured curvature requires them. The
    # first trial found a 2.736 mm chord on a few head strands; do not relax the
    # 2.5 mm limit or force those guides into the same segmentation budget.
    for shape in keys or [None]:
        co=co_array(shape.data) if shape else basis
        rings=co.reshape((count,old_rings,sides,3))
        for strand in range(count):
            while True:
                failing=[]
                for r in range(old_rings):
                    if r in kept[strand]:continue
                    a=max(k for k in kept[strand] if k<r);b=min(k for k in kept[strand] if k>r);t=(r-a)/(b-a)
                    delta=(rings[strand,r]-(rings[strand,a]*(1-t)+rings[strand,b]*t))@matrix.T
                    if np.linalg.norm(delta,axis=-1).max()>max_chord_error:failing.append(r)
                if not failing:break
                kept[strand].update(failing)
    indices=np.array([s*old_rings*sides+r*sides+k for s in range(count) for r in sorted(kept[s]) for k in range(sides)],dtype=np.int32)
    metrics={}
    for shape in keys or [None]:
        name=shape.name if shape else 'Basis';co=co_array(shape.data) if shape else basis
        ring=co.reshape((count,old_rings,sides,3))
        differences=[]
        for strand in range(count):
            for r in range(old_rings):
                if r in kept[strand]:continue
                a=max(k for k in kept[strand] if k<r);b=min(k for k in kept[strand] if k>r);t=(r-a)/(b-a)
                differences.append(ring[strand,r]-(ring[strand,a]*(1-t)+ring[strand,b]*t))
        deviations=np.concatenate(differences,axis=0) if differences else np.zeros((1,3))
        distances=np.linalg.norm(deviations@matrix.T,axis=-1)
        metrics[name]={'maxOmittedRingChordErrorMeters':float(distances.max()),'rmsMeters':float(np.sqrt(np.mean(distances**2)))}
        if distances.max()>max_chord_error:
            raise RuntimeError(f'{source.name}/{name}: strand chord error {distances.max()} exceeds {max_chord_error}')
    faces=[]
    start=0
    for s in range(count):
        for r in range(len(kept[s])-1):
            for k in range(sides):
                a=start+r*sides+k;b=start+r*sides+(k+1)%sides
                faces.append((a,b,b+sides,a+sides))
        start+=len(kept[s])*sides
    mesh=bpy.data.meshes.new(source.data.name+' derived strand rings')
    mesh.from_pydata(basis[indices].tolist(),[],faces);mesh.update()
    for material in source.data.materials:mesh.materials.append(material)
    for polygon in mesh.polygons:polygon.use_smooth=True
    original_uv=source.data.uv_layers.active
    if not original_uv:raise RuntimeError('Strand UVs missing')
    uv_by_vertex={}
    for loop in source.data.loops:
        value=tuple(original_uv.data[loop.index].uv)
        if loop.vertex_index in uv_by_vertex and max(abs(a-b) for a,b in zip(value,uv_by_vertex[loop.vertex_index]))>1e-6:
            raise RuntimeError('Unexpected split UV requires per-loop preservation: '+source.name)
        uv_by_vertex[loop.vertex_index]=value
    layer=mesh.uv_layers.new(name='UVMap')
    for loop in mesh.loops:layer.data[loop.index].uv=uv_by_vertex[int(indices[loop.vertex_index])]
    result=source.copy();result.data=mesh;bpy.context.collection.objects.link(result)
    for group in list(result.vertex_groups):result.vertex_groups.remove(group)
    groups={g.index:result.vertex_groups.new(name=g.name) for g in source.vertex_groups}
    for i,old in enumerate(indices):
        for weight in source.data.vertices[int(old)].groups:groups[weight.group].add([i],weight.weight,'REPLACE')
    if keys:
        for shape in keys:
            key=result.shape_key_add(name=shape.name,from_mix=False)
            key.slider_min=shape.slider_min;key.slider_max=shape.slider_max
            key.data.foreach_set('co',co_array(shape.data)[indices].ravel())
        attach_drivers(result,rig,deformation)
    runtime_triangles=sum((len(rings)-1)*sides*2 for rings in kept)
    report={'name':source.name,'strands':count,'sourceTriangles':count*24,'runtimeTriangles':runtime_triangles,
            'sourceVertices':len(basis),'runtimeVertices':len(indices),'initialRetainedRings':initial_rings,
            'ringsPerStrandHistogram':{str(n):sum(len(rings)==n for rings in kept) for n in range(2,6)},
            'preservedEveryRootAndTip':True,'retainedVertexShapeErrorMeters':0,
            'shapeChordErrors':metrics,'errorScope':'Exact omitted-ring chord error, not a full surface Hausdorff bound.'}
    result['runtime_reduction_source_triangles']=count*24
    result['runtime_reduction_triangles']=runtime_triangles
    result['fur_rings']=-1 # adaptive per-strand rings; actual counts are in report
    return result,report
