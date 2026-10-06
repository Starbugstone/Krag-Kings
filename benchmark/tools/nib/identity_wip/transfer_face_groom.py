"""Prepared bounded surface-correspondence transfer of attached head groom."""
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def transfer(head, basis, delta, objects):
    head.data.calc_loop_triangles()
    triangles=np.asarray([t.vertices[:] for t in head.data.loop_triangles],np.int32)
    world=np.asarray([head.matrix_world@Vector(p) for p in basis],np.float64)
    direction=np.asarray(head.matrix_world.to_3x3(),np.float64)
    world_delta=np.asarray(delta)@direction.T
    deformed=world+world_delta
    def face_normals(points):
        q=points[triangles];n=np.cross(q[:,1]-q[:,0],q[:,2]-q[:,0])
        return n/np.maximum(np.linalg.norm(n,axis=1)[:,None],1e-20)
    original_normals=face_normals(world);deformed_normals=face_normals(deformed)
    tree=BVHTree.FromPolygons(world.tolist(),triangles.tolist(),all_triangles=True)
    records=[]
    for obj in objects:
        if obj.data.shape_keys:raise RuntimeError('Explicit shaped groom transfer required for '+obj.name)
        original=np.asarray([v.co[:] for v in obj.data.vertices],np.float64)
        result=original.copy();inverse=obj.matrix_world.inverted()
        existing_normals=[Vector(n.vector) for n in obj.data.corner_normals] if obj.data.has_custom_normals else None
        rotations={}
        maximum=0.;changed=0
        for index,point in enumerate(original):
            current=obj.matrix_world@Vector(point)
            hit,normal,face,distance=tree.find_nearest(current)
            if hit is None:raise RuntimeError('Head groom has no face correspondence')
            if distance>=.025:continue
            p=world[triangles[face]];u=p[1]-p[0];v=p[2]-p[0];w=np.asarray(hit)-p[0]
            uu=float(u@u);uv=float(u@v);vv=float(v@v);uw=float(u@w);vw=float(v@w);denom=uu*vv-uv*uv
            if denom<=1e-28:raise RuntimeError('Degenerate groom-transfer support')
            b=(vv*uw-uv*vw)/denom;c=(uu*vw-uv*uw)/denom
            weights=np.asarray([1-b-c,b,c])
            if weights.min()<-1e-4:raise RuntimeError('Groom correspondence outside support triangle')
            weights=np.maximum(weights,0);weights/=weights.sum()
            t=max(0,min(1,(distance-.004)/.021));fade=1-t*t*(3-2*t)
            displacement=(weights@world_delta[triangles[face]])*fade
            maximum=max(maximum,float(np.linalg.norm(displacement)))
            result[index]=inverse@(current+Vector(displacement))
            changed+=int(np.linalg.norm(result[index]-point)>1e-9)
            if existing_normals is not None and np.linalg.norm(displacement)>1e-9:
                old_normal=Vector(original_normals[face]);new_normal=Vector(deformed_normals[face])
                rotations[index]=old_normal.rotation_difference(old_normal.lerp(new_normal,fade).normalized())
        if maximum>.005:raise RuntimeError('Groom exceeds bounded source face displacement')
        obj.data.vertices.foreach_set('co',result.astype(np.float32).ravel());obj.data.update()
        if existing_normals is not None:
            to_world=obj.matrix_world.to_3x3().inverted().transposed();to_local=obj.matrix_world.to_3x3().transposed()
            for loop in obj.data.loops:
                if loop.vertex_index in rotations:
                    existing_normals[loop.index]=(to_local@(rotations[loop.vertex_index]@(to_world@existing_normals[loop.index]))).normalized()
            obj.data.normals_split_custom_set(existing_normals)
        obj.data.calc_loop_triangles();local_tri=np.asarray([t.vertices[:] for t in obj.data.loop_triangles],int)
        def area(points):
            q=points[local_tri];return np.linalg.norm(np.cross(q[:,1]-q[:,0],q[:,2]-q[:,0]),axis=1)
        old_area=area(original);new_area=area(result)
        introduced=int(np.sum((old_area>1e-16)&(new_area<=1e-16)))
        if introduced:raise RuntimeError('Skin-following groom transfer introduced a degenerate triangle')
        records.append({'object':obj.name,'changedVertices':changed,'maximumWorldMoveMeters':maximum,
            'method':'Closest original face triangle barycentric displacement; exact near-surface follow, smooth falloff by25mm',
            'customNormalsTransported':existing_normals is not None,'introducedDegenerateTriangles':introduced,
            'topologyUVsWeightsMaterialsUnchanged':True,'requiresActualRootAndGuideFlowReview':True})
    return records
