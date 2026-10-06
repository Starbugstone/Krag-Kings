"""Authored broad cowl rest surface, constrained by actual opened jaw and skin.

The failed long wrapped-strip simulations are preserved. This pattern authors
large cloth construction directly; no physics success is claimed. Fine fabric
weave, seam construction and moving-pose review remain separate acceptance.
"""
import math,json
import numpy as np
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def initial_sheet(front_top,length=177,width=29):
    vertices=[];faces=[]
    for i in range(length):
        u=i/(length-1);a=math.pi/2-.13+2*math.pi*1.04*u
        front=max(0.,-math.sin(a));back=max(0.,math.sin(a))
        # High wide nape/shoulder support leads into a low open front. The front
        # upper edge is bounded by the actual opened chin, not a guessed radius.
        t=max(0.,min(1.,(front-.10)/.84));front_drape=t*t*t*(10+t*(-15+6*t))
        top=1.808+.018*back-(1.808-front_top)*front_drape+.010*math.cos(a+.35)*front
        drop=.048+.092*front**1.25+.040*back
        radius=.164+.039*front+.019*abs(math.cos(a))
        for j in range(width):
            v=j/(width-1);q=v+.065*math.sin(a+.7)*math.sin(math.pi*v)
            f1=.31+.16*math.sin(a+.45);f2=.68+.12*math.sin(2*a-.9)
            # Unequal broad crossing folds with a real flat between them;
            # not lathed torus rings or a repeated terrace cross-section.
            roll1=math.exp(-((q-f1)/(.11+.02*math.cos(a)))**2)
            roll2=math.exp(-((q-f2)/(.17+.025*math.sin(a+.4)))**2)
            valley=math.exp(-((q-f1-.16)/.11)**2)
            r=radius+(.025+.048*front)*q+.016*roll1+.011*roll2-.006*valley
            z=top-drop*q-.013*front*math.sin(math.pi*q)
            z+=.012*math.sin(a+2.1*q)*math.sin(math.pi*q)
            angle=a+.095*math.sin(math.pi*q)*math.sin(a-.25)
            # Short overlapping ends live at the nape, with a small separation;
            # no extra turn or concentrated side knot is required.
            end=max(0.,(u-.93)/.07);r+=.008*end
            vertices.append((r*math.cos(angle),.019+r*math.sin(angle),z))
    for i in range(length-1):
        for j in range(width-1):
            k=i*width+j;faces.append((k,k+1,k+width+1,k+width))
    return np.asarray(vertices),faces


def surface_tree(obj,exterior=False):
    mesh=obj.data;basis=mesh.shape_keys.key_blocks['Basis'].data if mesh.shape_keys else mesh.vertices
    tags=mesh.attributes.get('.sculpt_face_set');faces=[]
    for polygon in mesh.polygons:
        if exterior and tags and tags.data[polygon.index].value in [7,5,6]:continue
        faces.append(tuple(polygon.vertices))
    return BVHTree.FromPolygons([obj.matrix_world@v.co for v in basis],faces)


def build(c):
    chin=float(c['actual_open_chin_min_z']);front_top=min(1.621,chin-.022)
    if not 1.54<front_top<1.67:raise RuntimeError('Actual opened chin requires unexpected cowl landmark '+str(front_top))
    vertices,faces=initial_sheet(front_top)
    o=c['mesh']('Broad open-neck chest cowl',vertices,faces,c['cloth'],'Scarf','Chest')
    body=c['actual_body'];head=c['actual_head'];skin=[surface_tree(body),surface_tree(head,True)]
    gear=[surface_tree(obj)for obj in bpy.data.objects if obj.type=='MESH'and obj.get('module')in['Armor','Harness']]
    # Bounded conformance keeps the rest silhouette. No vertical support ray
    # can pull the front panel up onto the neck or jaw.
    correction=[]
    for vertex in o.data.vertices:
        start=vertex.co.copy();origin=Vector((0,.019,vertex.co.z));direction=vertex.co-origin;radius=direction.length;direction.normalize()
        required=radius
        for tree in skin:
            hit,normal,index,distance=tree.ray_cast(origin,direction,.34)
            if hit is not None:required=max(required,distance+.007)
        if required>.33:raise RuntimeError('Authored cowl hits distant shoulder/arm, not the intended neck/chest surface')
        if required>radius:vertex.co=origin+direction*required
        for tree in skin+gear:
            point,normal,index,distance=tree.find_nearest(vertex.co)
            if point is None:continue
            signed=(vertex.co-point).dot(normal)
            if signed<.005 and distance<.020:vertex.co=point+normal*.005
        d=(vertex.co-start).length;correction.append(d)
        if d>.055:raise RuntimeError('Authored cowl conformance exceeds unchanged55mm gate')
    fitted=np.asarray([tuple(v.co)for v in o.data.vertices])
    frontal=(-fitted[:,1]+.019)/np.maximum(np.linalg.norm(fitted[:,:2]-[0,.019],axis=1),1e-9)>.94
    if fitted[frontal,2].max()>chin-.010:raise RuntimeError('Authored front cowl rises into the actual opened-chin landmark')
    if fitted[:,2].min()<1.39 or fitted[:,2].max()>1.95:raise RuntimeError('Authored cowl leaves intended chest/neck extent')
    cage=o.copy();cage.data=o.data.copy();cage.name='EDITABLE v9md authored cowl rest surface'
    for key in ['module','rig_bone']:
        if key in cage:del cage[key]
    bpy.data.collections['Authoring control cages'].objects.link(cage);cage.hide_render=True;cage.hide_set(True)
    bpy.context.view_layer.objects.active=o
    sub=o.modifiers.new('Smooth authored textile folds','SUBSURF');sub.levels=1;bpy.ops.object.modifier_apply(modifier=sub.name)
    solid=o.modifiers.new('Woven cowl thickness','SOLIDIFY');solid.thickness=.003;solid.offset=0;bpy.ops.object.modifier_apply(modifier=solid.name)
    for polygon in o.data.polygons:polygon.use_smooth=True
    report={'status':'Actual authored broad rest surface; no physics generation or artistic acceptance claim','method':'High shoulder/nape support, low open front and asymmetric broad crossing cloth folds, bounded exact-surface conformance',
        'actualOpenChinMinimumZ':chin,'frontTopDesignZ':front_top,'actualFrontMaximumZ':float(fitted[frontal,2].max()),
        'maxConformanceMeters':max(correction),'initialBoundsMeters':[vertices.min(0).tolist(),vertices.max(0).tolist()],
        'fittedBoundsMeters':[fitted.min(0).tolist(),fitted.max(0).tolist()],
        'restCageVertices':len(vertices),'restCageFaces':len(faces),'surfaceSubdivision':1,'thicknessMeters':.003,
        'pending':['Actual concept silhouette','Open-jaw/profile and shoulder clearance','Raised-arm contact','Cloth weave, edge seams and weathering']}
    o['authored_cowl_study']=json.dumps(report);c['scarf_cloth_study']=report
    return o
