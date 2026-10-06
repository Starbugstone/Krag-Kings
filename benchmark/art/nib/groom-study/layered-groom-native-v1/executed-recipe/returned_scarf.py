"""Ungenerated gathered scarf with returned sections and bounded skin fit.

The former three conical rings are replaced by one folded continuous sheet.
Anatomical support refines the silhouette, not the source of the silhouette.
"""
import math
import bpy,numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree


from cloth_pattern import point as pattern_point, smooth, segment_distance


def skin_tree(objects):
    vertices=[];triangles=[]
    for obj in objects:
        obj.data.calc_loop_triangles();offset=len(vertices)
        vertices.extend(obj.matrix_world@v.co for v in obj.data.vertices)
        for tri in obj.data.loop_triangles:
            points=[vertices[offset+i]for i in tri.vertices]
            if min(p.z for p in points)<.91 or max(abs(p.x)for p in points)>.13:continue
            triangles.append(tuple(offset+i for i in tri.vertices))
    if not triangles:raise RuntimeError('No actual upper torso/neck support')
    return BVHTree.FromPolygons(vertices,triangles,all_triangles=True)


def create(collection,rig,material,body,head):
    support=skin_tree([body,head]);N=160;M=49;points=[];uv=[];faces=[];fits=[];required_offsets=np.zeros(N)
    for j in range(M):
        v=j/(M-1)
        for i in range(N):
            angle=i/N*math.tau;x,y,z=pattern_point(angle,v)
            radius=math.hypot(x,y-.008)
            p=Vector((x,y,z));direction=Vector((x,y-.008,0)).normalized()
            center=Vector((0,.008,z));hit,n,index,distance=support.ray_cast(center+direction*.012,direction,.14)
            delta=0.
            if hit is not None and n.dot(direction)>.10:
                required=(hit-center).length+.0035
                if required>radius:
                    delta=required-radius
                    if delta>.030:raise RuntimeError('Scarf pattern enters actual anatomy by over30mm; revise pattern '+str((i,j,delta)))
                    required_offsets[i]=max(required_offsets[i],delta)
            # Front support cannot lift the low cowl toward the shoulders.
            points.append(tuple(p));uv.append((i/N*.62,v*.20))
    # Transport each entire folded section along one radial vector. Separate
    # layers never snap independently onto the same body surface. A smooth
    # periodic majorant retains every measured minimum support requirement.
    offsets=required_offsets.copy()
    for _ in range(2):
        offsets=sum(np.roll(offsets,k)*w for k,w in [(-2,1),(-1,4),(0,6),(1,4),(2,1)])/16
    offsets+=max(0.,float(np.max(required_offsets-offsets)))
    if float(offsets.max())>.030:raise RuntimeError('Whole scarf section needs over30mm of support transport; inspect pattern')
    unfit=np.asarray(points,dtype=np.float64).reshape((M,N,3));fitted=unfit.copy()
    for i in range(N):
        direction=unfit[0,i,:2]-np.array([0,.008]);direction/=np.linalg.norm(direction)
        fitted[:,i,:2]+=direction*offsets[i]
    preservation=0.
    for i in range(N):
        preservation=max(preservation,float(np.max(np.abs((fitted[:,i]-fitted[0,i])-(unfit[:,i]-unfit[0,i])))))
    if preservation>1e-7:raise RuntimeError('Coherent cloth section transport changed its fold geometry')
    if np.any(offsets+1e-12<required_offsets):raise RuntimeError('Smoothed support transport lost required clearance')
    points=[tuple(v)for v in fitted.reshape((-1,3))];fits=offsets.tolist()
    for j in range(M-1):
        for i in range(N):
            a=j*N+i;b=j*N+(i+1)%N;faces.append((a,b,b+N,a+N))
    mesh=bpy.data.meshes.new('Nib returned woven sheet');mesh.from_pydata(points,[],faces);mesh.update()
    layer=mesh.uv_layers.new(name='UVMap')
    for poly in mesh.polygons:
        poly.use_smooth=True
        for li in poly.loop_indices:
            loop=mesh.loops[li];u,v=uv[loop.vertex_index]
            if poly.index%N==N-1 and loop.vertex_index%N==0:u=.62
            layer.data[li].uv=(u,v)
    mesh.materials.append(material)
    obj=bpy.data.objects.new('Nib gathered returned desert scarf',mesh);collection.objects.link(obj)
    bpy.context.view_layer.objects.active=obj;obj.select_set(True)
    solid=obj.modifiers.new('Woven thickness and free edges','SOLIDIFY');solid.thickness=.0013;solid.offset=0;solid.use_even_offset=True
    bpy.ops.object.modifier_apply(modifier=solid.name)
    obj.parent=rig;groups={n:obj.vertex_groups.new(name=n)for n in ['Chest','Neck']}
    for vertex in obj.data.vertices:
        # The upper gathered edge follows some neck motion; the hanging fronts
        # remain chest-supported. It does not inherit Jaw or Head.
        z=vertex.co.z;neck=.36*smooth((z-.989)/.041)
        groups['Chest'].add([vertex.index],1-neck,'REPLACE')
        if neck>1e-8:groups['Neck'].add([vertex.index],neck,'REPLACE')
    mod=obj.modifiers.new('Portable scarf deformation','ARMATURE');mod.object=rig;mod.use_deform_preserve_volume=False
    obj['variant']='all';obj['bone']='Chest';obj['construction']='Single woven sheet, two actual returned folds, unequal front sag, gathered back'
    # Preserve visible return evidence after actual skin conformance. The front
    # and back radial sections must still rise at least twice across the width.
    p=np.asarray(points).reshape((M,N,3));returns={}
    for label,i in [('front',3*N//4),('back',N//4),('left',0),('right',N//2)]:
        dz=np.diff(p[:,i,2]);returns[label]={'upwardSamples':int(np.sum(dz>.00005)),'downwardSamples':int(np.sum(dz<-.00005)),
            'minZ':float(p[:,i,2].min()),'maxZ':float(p[:,i,2].max())}
        if returns[label]['upwardSamples']<4:raise RuntimeError('Actual fitted section erased returned cloth folds')
    nearest_separation=1.0
    for i in range(0,N,4):
        section=p[:,i]
        for a in range(M-1):
            for b in range(a+4,M-1):
                nearest_separation=min(nearest_separation,segment_distance(section[a],section[a+1],section[b],section[b+1]))
    if nearest_separation<.0018:raise RuntimeError('Actual skin fit collapses nonadjacent scarf folds '+str(nearest_separation))
    return obj,{'maximumSectionInternalCoordinateErrorMeters':preservation,'rawRequiredOffsetsMeters':required_offsets.tolist(),'coherentSectionOffsetsMeters':offsets.tolist(),'minimumFittedNonadjacentSectionDistanceMeters':nearest_separation,'construction' :'Actual returned surface, no cloth simulation','radialFitMaximumMeters':max(fits),'sections':returns,
                'fittingValuesProvisional':True,'chestNeckOnly':True,'minimumFabricThicknessMeters':.0013,
                'posedCollisionAndAppearancePending':True}
