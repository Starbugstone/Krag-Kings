"""Prepared actual-torso correspondence for a narrow sewn Nib undershirt."""
import numpy as np
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from sewn_undershirt_v2 import relax_projection


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
        hit,normal,tri,distance=tree.find_nearest(Vector(p))
        if hit is None:raise RuntimeError('Missing actual torso surface at '+str(i))
        alignment=float(normal.dot(Vector(d)))
        # Flat sewn guides overhang a curved/open waist. Nearest exterior
        # correspondence is appropriate here; a front ray miss is not proof
        # that loose fabric should be narrowed to the skin's silhouette.
        if alignment<-.10 or distance>.065:
            raise RuntimeError('Sewn guide selects wrong/far torso side at '+str((i,pattern['regions'][i],distance,alignment)))
        ease=.008+.004*(1-pattern['pins'][i])
        delta=p-np.asarray(hit);n=np.asarray(normal);tangent=delta-n*(delta@n)
        tangent*=min(.25,.004/max(np.linalg.norm(tangent),1e-12))
        target=np.asarray(hit)+n*ease+tangent
        shift=float(np.linalg.norm(target-p))
        if shift>.065:raise RuntimeError('Sewn-panel fit exceeds65mm guide correction at '+str((i,shift)))
        points[i]=target;rows.append({'vertex':i,'triangle':int(tri),'guideDistanceMeters':float(distance),
            'adjustmentMeters':shift,'normalDirectionDot':alignment,'easeMeters':float(ease),'normal':list(normal)})
    points,fairing=relax_projection(points,pattern['faces'],pattern['pins'])
    faces=np.asarray(pattern['faces'],dtype=np.int32)
    area=np.linalg.norm(np.cross(points[faces[:,1]]-points[faces[:,0]],points[faces[:,2]]-points[faces[:,0]]),axis=1)
    if np.any(area<1e-12):raise RuntimeError('Sewn torso correspondence collapsed a panel face')
    face_normal=np.cross(points[faces[:,1]]-points[faces[:,0]],points[faces[:,2]]-points[faces[:,0]])
    support_normal=np.asarray([r['normal'] for r in rows])[faces].mean(1)
    dots=np.sum(face_normal*support_normal,axis=1)/np.maximum(np.linalg.norm(face_normal,axis=1)*np.linalg.norm(support_normal,axis=1),1e-20)
    if np.any(dots<0):raise RuntimeError('Sewn torso correspondence folds a panel against its actual support')
    pattern['points']=points
    return {'method':'Nearest actual torso-only surface with explicit8-12mm ease; source ArmDomain <0.14',
            'maximumGuideAdjustmentMeters':max(r['adjustmentMeters'] for r in rows),'minimumSupportDirectionDot':min(r['normalDirectionDot'] for r in rows),
            'supportTriangles':len(triangles),'maximumPermittedGuideAdjustmentMeters':.065,
            'minimumFittedQuadCornerDoubleAreaMetersSquared':float(area.min()),'surfaceFairing':fairing,'minimumSupportNormalDot':float(dots.min()),'correspondence':rows,
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
