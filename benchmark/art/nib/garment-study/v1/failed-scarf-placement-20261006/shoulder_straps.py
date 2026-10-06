"""Fresh fitted leather routes on actual anatomy, replacing obsolete straps.

Exterior projection has explicit front/crest/back direction so a control inside
new anatomy cannot bind to the opposite/front surface. Dimensions are fitting
proposals, not new canon; native front/back/action review remains mandatory.
"""
import math,json
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector
from fitted_fabric import tree,bind_to_body


def smooth_curve(values,subdivisions=8):
    values=np.asarray(values,float);out=[]
    for i in range(len(values)-1):
        a=values[max(0,i-1)];b=values[i];c=values[i+1];d=values[min(len(values)-1,i+2)]
        for j in range(subdivisions):
            t=j/subdivisions;out.append(.5*((2*b)+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t))
    return np.asarray(out+[values[-1]])


def build(name,side,material,collection,rig,body,shirt):
    seed=np.asarray([(side*.060,-.073,.880),(side*.073,-.060,.933),
        (side*.080,-.020,.978),(side*.080,.012,.997),(side*.079,.050,.950),
        (side*.055,.067,.893),(side*.017,.074,.816),(-side*.052,.067,.729)])
    direction=np.asarray([(0,-1,.10),(0,-1,.4),(0,-.65,.8),(0,0,1),
        (0,1,.45),(0,1,.1),(0,1,0),(0,1,0)],float)
    raw=smooth_curve(seed);dirs=smooth_curve(direction);dirs/=np.linalg.norm(dirs,axis=1)[:,None]
    supports=[('body',tree(body)[0],.0115)];shirt_tree=tree(shirt)[0]
    centers=[];normals=[];routing=[]
    for i,(p,d) in enumerate(zip(raw,dirs)):
        origin=Vector(p+d*.24);axis=Vector(-d);candidates=[]
        for label,support,clearance in supports:
            hit,normal,triangle,distance=support.ray_cast(origin,axis,.48)
            if hit is None:continue
            if normal.dot(Vector(d))<.05:continue
            # One leather layer crosses above the other at the centre back.
            crossed=(side>0)*math.exp(-((p[0])/.022)**2)*max(0,float(d[1]))
            point=hit+normal*(clearance+.0032*crossed)
            candidates.append((float(np.dot(point,d)),np.asarray(point),np.asarray(normal),label,triangle))
        if not candidates:raise RuntimeError('No outward shoulder route support at row '+str(i))
        _,center,normal,label,triangle=max(candidates,key=lambda item:item[0]);shift=float(np.linalg.norm(center-p))
        if shift>.09:raise RuntimeError('Fresh strap route escapes90mm anatomy neighborhood')
        centers.append(center);normals.append(normal);routing.append({'row':i,'regionDirection':d.tolist(),
            'support':label,'supportTriangle':triangle,'seed':p.tolist(),'center':center.tolist(),'routeAdjustmentMeters':shift})
    centers=np.asarray(centers);normals=np.asarray(normals)
    # Keep one continuous anatomical route. The rejected attempt switched
    # independently between distant shirt/body ray hits, causing a112deg kink.
    # Shirt folds contribute only a local outward clearance envelope. A bounded
    # slope spreads each required lift along the strap instead of rerouting it.
    arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(centers,axis=0),axis=1))]
    required=np.zeros(len(centers));clearance_rows=[]
    for i,(center,body_normal) in enumerate(zip(centers,normals)):
        hit,n,triangle,distance=shirt_tree.find_nearest(Vector(center))
        if hit is None or distance>.025:continue
        n=np.asarray(n)
        if n@body_normal<0:n=-n
        alignment=float(n@body_normal)
        if alignment<.25:continue
        signed=float((center-np.asarray(hit))@n)
        required[i]=max(0.,(.0045-signed)/alignment)
        clearance_rows.append({'row':i,'triangle':triangle,'signedShirtGapMeters':signed,'requiredOutwardLiftMeters':float(required[i])})
    envelope=np.maximum(0,np.max(required[None,:]-.45*abs(arc[:,None]-arc[None,:]),axis=1))
    if envelope.max()>.035:raise RuntimeError('Shirt clearance requires over35mm outward strap lift; inspect actual cloth before continuing')
    centers+=normals*envelope[:,None]
    for i,row in enumerate(routing):row['shirtClearanceLiftMeters']=float(envelope[i]);row['center']=centers[i].tolist()
    Path(__file__).resolve().parents[4].joinpath('benchmark/local/nib-fresh-strap-route-'+str(side)+'.json').write_text(json.dumps({'routing':routing,'shirtClearance':clearance_rows},indent=2)+'\n',newline='\n')
    segments=np.diff(centers,axis=0);length=np.linalg.norm(segments,axis=1)
    if np.any(length<.0002):raise RuntimeError('Fresh strap route has collapsed longitudinal segment')
    cos=np.sum(segments[:-1]*segments[1:],axis=1)/(length[:-1]*length[1:]);bend=np.degrees(np.arccos(np.clip(cos,-1,1)))
    if bend.max()>70:raise RuntimeError('Fresh strap route has abrupt kink above70degrees: '+str(float(bend.max())))
    widths=[];normal_frame=[]
    for i,c in enumerate(centers):
        tangent=centers[min(i+1,len(centers)-1)]-centers[max(i-1,0)];tangent/=np.linalg.norm(tangent)
        width=np.cross(normals[i],tangent);width/=np.linalg.norm(width);normal=np.cross(tangent,width)
        if np.dot(normal,normals[i])<0:width=-width;normal=-normal
        widths.append(width);normal_frame.append(normal)
    sides=12;points=[];faces=[];uv=[];distance=np.r_[0,np.cumsum(length)];total=float(distance[-1])
    for i,c in enumerate(centers):
        for j in range(sides):
            a=j/sides*math.tau
            # Rounded rectangular ribbon: broad leather face and softened edge.
            x=math.copysign(abs(math.cos(a))**.38,math.cos(a))*.0095
            y=math.copysign(abs(math.sin(a))**.55,math.sin(a))*.0015
            points.append(c+widths[i]*x+normal_frame[i]*y)
    for i in range(len(centers)-1):
        for j in range(sides):faces.append((i*sides+j,i*sides+(j+1)%sides,(i+1)*sides+(j+1)%sides,(i+1)*sides+j))
    faces.extend([tuple(reversed(range(sides))),tuple((len(centers)-1)*sides+j for j in range(sides))])
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(points,[],faces);mesh.update();mesh.materials.append(material)
    obj=bpy.data.objects.new(name,mesh);collection.objects.link(obj);obj['bone']='Torso';obj['variant']='all'
    layer=mesh.uv_layers.new(name='UVMap')
    for face in mesh.polygons:
        cap=face.index>=(len(centers)-1)*sides
        seam=any(mesh.loops[k].vertex_index%sides==sides-1 for k in face.loop_indices)
        for k in face.loop_indices:
            vertex=mesh.loops[k].vertex_index;j=vertex%sides;i=vertex//sides
            if cap:
                a=j/sides*math.tau;layer.data[k].uv=(.5+.48*math.cos(a),.5+.48*math.sin(a))
            else:layer.data[k].uv=(1. if seam and j==0 else j/sides,distance[i]/.4)
        face.use_smooth=True
    binding=bind_to_body(obj,rig,body)
    return obj,{'object':name,'construction':'New closed rounded leather ribbon, intentional replacement of obsolete strap mesh',
        'widthMeters':.019,'thicknessMeters':.003,'routeLengthMeters':total,'maximumAdjacentSegmentAngleDegrees':float(bend.max()),
        'maximumRouteAdjustmentMeters':max(r['routeAdjustmentMeters'] for r in routing),'routing':routing,'binding':binding,
        'maximumShirtClearanceLiftMeters':float(envelope.max()),'shirtClearanceEnvelopeSlope':.45,'shirtClearanceSamples':clearance_rows,
        'artisticAcceptance':False,'geometryPreservation':'Body/bind/actions untouched; old strap archived; new strap topology/UVs authored'}
