"""Fit the CC0 iris as opaque surface pigment, without a cornea shader.

The matching source globe is the geometric authority. Subdivision precedes
projection, so a later smoothing operation cannot bury the colored surface.
"""
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

def fit_opaque_eye(sclera,iris,sclera_source,iris_source,fit,drop,subdivide):
    subdivide(sclera,1);subdivide(iris,1)
    shell=[sclera_source@v.co for v in sclera.data.vertices]
    faces=[list(p.vertices) for p in sclera.data.polygons]
    tree=BVHTree.FromPolygons(shell,faces)
    center=sclera_source.translation.copy()
    projected=[];shifts=[]
    for vertex in iris.data.vertices:
        local=vertex.co.copy();radius=(local.x*local.x+local.z*local.z)**.5
        t=max(0,min(1,(radius-.0023)/(.006-.0023)));weight=1-t*t*(3-2*t)
        local.x*=1-.55*weight;local.z*=1+.65*weight
        p=iris_source@local
        origin=Vector((p.x,center.y-.060,p.z))
        hit,normal,face,distance=tree.ray_cast(origin,Vector((0,1,0)),.12)
        if hit is None:raise RuntimeError('Iris extends outside matching source globe')
        # The original iris has folded inner/outer surfaces. Retain a tiny
        # signed relief from the source Y rather than creating coincident loops.
        relief=max(-.000015,min(.000015,(local.y+.0144)*.025))
        target=Vector((p.x,hit.y-.00015+relief,p.z))
        shifts.append(target.y-p.y);projected.append(target)
    for obj,points in [(sclera,shell),(iris,projected)]:
        fitted=fit(np.asarray(points,dtype=np.float64))
        obj.data.vertices.foreach_set('co',fitted.astype(np.float32).ravel())
        obj.matrix_world=Matrix.Translation((0,0,drop));obj.data.update()
    return {'representation':'Opaque anterior iris pigment over dark globe; existing pupil opening retained',
            'sourceCenter':list(center),'sourceProjectionShiftYRangeMeters':[min(shifts),max(shifts)],
            'sourceGlobeClearanceMeters':.00015,'scleraVertices':len(shell),'irisVertices':len(projected),
            'subdivisionAfterProjection':False}
