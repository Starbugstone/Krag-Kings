"""Fit leather harness construction to the actual authored anatomical surface."""
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def build(c):
    vertices=[];faces=[]
    for obj in bpy.data.objects:
        if obj.type!='MESH' or obj.get('module') not in {'Body','BioArm_L','BioArm_R'}:
            continue
        offset=len(vertices)
        vertices.extend(obj.matrix_world@v.co for v in obj.data.vertices)
        faces.extend(tuple(offset+i for i in face.vertices) for face in obj.data.polygons)
    skin=BVHTree.FromPolygons(vertices,faces,all_triangles=False)

    def fitted(point,front=True,clearance=.011):
        point=Vector(point)
        origin=Vector((point.x,-1 if front else 1,point.z))
        hit,normal,_,_=skin.ray_cast(origin,Vector((0,1 if front else -1,0)),2)
        if hit is not None:
            point.y=hit.y+(-clearance if front else clearance)
        return point

    def strip(name,path,width,front=True):
        path=[Vector(p) for p in path];samples=[]
        for a,b in zip(path[:-1],path[1:]):
            samples.extend(a.lerp(b,i/9) for i in range(9))
        samples.append(path[-1]);vs=[];fs=[];across=7
        for i,p in enumerate(samples):
            tangent=samples[min(i+1,len(samples)-1)]-samples[max(0,i-1)]
            width_axis=Vector((tangent.z,0,-tangent.x)).normalized()
            for j in range(across):
                vs.append(fitted(p+width_axis*width*(j/(across-1)-.5),front))
        for i in range(len(samples)-1):
            for j in range(across-1):
                k=i*across+j;face=(k,k+1,k+1+across,k+across)
                fs.append(face if front else tuple(reversed(face)))
        obj=c['mesh'](name,vs,fs,c['leather'],'Harness','Chest')
        bpy.context.view_layer.objects.active=obj
        solid=obj.modifiers.new('Harness leather thickness','SOLIDIFY');solid.thickness=.007
        bpy.ops.object.modifier_apply(modifier=solid.name)
        edge=obj.modifiers.new('Soft leather cut edge','BEVEL');edge.width=.0018;edge.segments=2
        bpy.ops.object.modifier_apply(modifier=edge.name)
        for i in range(0,len(samples)-1,2):
            tangent=samples[min(i+1,len(samples)-1)]-samples[max(0,i-1)]
            width_axis=Vector((tangent.z,0,-tangent.x)).normalized()
            for sign in [-1,1]:
                a=fitted(samples[i]+width_axis*sign*(width*.5-.007),front,.017)
                b=fitted(samples[i].lerp(samples[i+1],.65)+width_axis*sign*(width*.5-.007),front,.017)
                c['tube']('Recessed harness saddle stitch',[a,b],.00075,c['cloth'],'Harness','Chest',6)
        return obj

    strip('Fitted diagonal front harness',[(-.271,0,1.245),(-.208,0,1.303),(-.105,0,1.370),(.012,0,1.440),(.122,0,1.506),(.217,0,1.579),(.286,0,1.657)],.081)
    strip('Shoulder armor load strap',[(.158,0,1.404),(.187,0,1.510),(.226,0,1.622),(.270,0,1.710)],.051)
    strip('Fitted back harness',[(-.285,0,1.642),(-.175,0,1.502),(-.033,0,1.400),(.103,0,1.326),(.247,0,1.257)],.071,False)
    for x,z in [(.165,1.436),(.207,1.572),(.224,1.622)]:
        c['uvball']('Shoulder harness retaining rivet',fitted((x,0,z),True,.020),(.0045,.0026,.0045),c['brass'],'Harness','Chest',seg=12,rings=8)
    c['torus']('Harness load attachment ring',fitted((.115,0,1.489),True,.023),.021,.0036,c['brass'],'Harness','Chest')
    for x,z in [(.187,1.556),(-.131,1.353)]:
        p=fitted((x,0,z),True,.022)
        frame=c['box']('Fitted harness buckle',p,(.089,.014,.053),c['brass'],'Harness','Chest',bevel=.004)
        frame.rotation_euler.y=-.54
        aperture=c['box']('Leather through harness buckle',p+Vector((0,-.009,0)),(.064,.011,.031),c['leather'],'Harness','Chest',bevel=.003)
        aperture.rotation_euler.y=-.54
        c['tube']('Buckle cross pin',[p+Vector((-.033,-.018,.017)),p+Vector((.034,-.018,-.018))],.0024,c['brass'],'Harness','Chest',8)
