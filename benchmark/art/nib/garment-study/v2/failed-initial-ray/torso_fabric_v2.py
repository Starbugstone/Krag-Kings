"""Prepared actual-torso correspondence for a narrow sewn Nib undershirt."""
import numpy as np
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def support(body):
    body.data.calc_loop_triangles()
    points=np.asarray([tuple(body.matrix_world@v.co) for v in body.data.vertices],dtype=np.float64)
    triangles=np.asarray([t.vertices[:] for t in body.data.loop_triangles],dtype=np.int32)
    domain=np.empty(len(points),dtype=np.float32)
    attribute=body.data.attributes.get('Nib_ArmDomain')
    if attribute is None:raise RuntimeError('Missing actual anatomical torso/arm support domain')
    attribute.data.foreach_get('value',domain)
    # Exclude the arm surface from correspondence. A side ray must never pick
    # the nearby medial upper arm and turn a tank-top edge into a sleeve.
    valid=np.max(domain[triangles],axis=1)<.14
    triangles=triangles[valid]
    return BVHTree.FromPolygons(points,triangles,all_triangles=True),points,triangles


def fit(pattern,body):
    tree,_,triangles=support(body);points=pattern['points'].copy();rows=[]
    for i,(p,d) in enumerate(zip(points,pattern['directions'])):
        hit,normal,tri,distance=tree.ray_cast(Vector(p+d*.18),Vector(-d),.36)
        if hit is None or normal.dot(Vector(d))<.05:
            raise RuntimeError('Sewn shirt lacks outward actual torso support at '+str((i,pattern['regions'][i],p.tolist())))
        # Fit ease is textile thickness/air clearance; it does not move skin.
        ease=.006+.002*(1-pattern['pins'][i])
        target=np.asarray(hit)+np.asarray(normal)*ease
        shift=float(np.linalg.norm(target-p))
        if shift>.065:raise RuntimeError('New sewn-panel guide misses actual torso by over65mm at '+str((i,shift)))
        points[i]=target;rows.append((shift,int(tri),float(normal.dot(Vector(d)))))
    pattern['points']=points
    return {'method':'Directional actual torso-only ray correspondence; source ArmDomain <0.14',
            'maximumGuideAdjustmentMeters':max(r[0] for r in rows),'minimumOutwardNormalDot':min(r[2] for r in rows),
            'supportTriangles':len(triangles),'maximumPermittedGuideAdjustmentMeters':.065,
            'sourcePointsMoved':False,'visualAcceptance':False}


def bind(obj,rig,body):
    tree,points,triangles=support(body);names=[g.name for g in body.vertex_groups]
    weights=np.zeros((len(points),len(names)),dtype=np.float64)
    for vertex in body.data.vertices:
        for g in vertex.groups:weights[vertex.index,g.group]=g.weight
    output=[];largest=0.
    for vertex in obj.data.vertices:
        p=obj.matrix_world@vertex.co;hit,_,index,distance=tree.find_nearest(p)
        if hit is None:raise RuntimeError('No torso-only garment weight correspondence')
        largest=max(largest,distance);ids=triangles[index];a,b,c=points[ids];v0=b-a;v1=c-a;q=np.asarray(hit)-a
        gram=np.asarray([[v0@v0,v0@v1],[v0@v1,v1@v1]])
        if np.linalg.det(gram)<1e-18:raise RuntimeError('Degenerate torso support triangle')
        v,w=np.linalg.solve(gram,np.asarray([q@v0,q@v1]));bary=np.maximum([1-v-w,v,w],0);bary/=sum(bary)
        row=bary@weights[ids]
        # Portable LBS is identical to the anatomy support, with four largest
        # normalized influences retained. No Blender-only preserve-volume mode.
        keep=np.argsort(row)[-4:];clean=np.zeros_like(row);clean[keep]=row[keep];clean/=sum(clean);output.append(clean)
    output=np.asarray(output);obj.vertex_groups.clear();groups=[obj.vertex_groups.new(name=n) for n in names]
    for i,row in enumerate(output):
        for group,value in zip(groups,row):
            if value>1e-8:group.add([i],float(value),'REPLACE')
    world=obj.matrix_world.copy();obj.parent=rig;obj.matrix_world=world
    mod=obj.modifiers.new('Portable torso garment skinning','ARMATURE');mod.object=rig;mod.use_deform_preserve_volume=False
    arm_indices=[i for i,n in enumerate(names) if n.startswith(('UpperArm','LowerArm','ForearmTwist','Hand'))]
    return {'maximumBodySupportDistanceMeters':largest,'maximumInfluences':int(np.count_nonzero(output>1e-8,axis=1).max()),
            'maximumCombinedArmWeight':float(output[:,arm_indices].sum(1).max()),'support':'actual torso-only triangles'}
