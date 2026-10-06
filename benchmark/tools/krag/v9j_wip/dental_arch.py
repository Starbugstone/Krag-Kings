"""Provisional fitted dental arches and seated tongue for actual source review.

This replaces the sparse independently sized boxes. Crown width follows the
saved fitted arch, so nonlinear creature proportions cannot leave large gaps.
No design or contact acceptance is implied by generating this geometry.
"""
import numpy as np
import bpy


def components(mesh):
    adjacency=[[] for _ in mesh.vertices]
    for edge in mesh.edges:
        a,b=edge.vertices;adjacency[a].append(b);adjacency[b].append(a)
    seen=set();result=[]
    for start in range(len(adjacency)):
        if start in seen:continue
        queue=[start];seen.add(start);part=[]
        while queue:
            i=queue.pop();part.append(i)
            for j in adjacency[i]:
                if j not in seen:seen.add(j);queue.append(j)
        result.append(np.asarray(sorted(part),dtype=int))
    return result


class Surface:
    def __init__(self):
        self.vertices=[];self.faces=[];self.materials=[];self.weights=[];self.uv=[]
    def patch(self,rings,material,weight,close_start=True,close_end=True):
        rings=np.asarray(rings);base=len(self.vertices);n=len(rings[0]);count=len(rings)
        self.vertices.extend(rings.reshape(-1,3).tolist())
        for i,ring in enumerate(rings):
            for j,p in enumerate(ring):
                self.weights.append(weight(p) if callable(weight) else dict(weight))
                self.uv.append((j/n,i/max(1,count-1)))
        for i in range(count-1):
            for j in range(n):
                a=base+i*n+j;b=base+i*n+(j+1)%n
                self.faces.append((a,b,b+n,a+n));self.materials.append(material)
        for index,reverse in [(0,True),(count-1,False)]:
            if (index==0 and not close_start) or (index==count-1 and not close_end):continue
            center=rings[index].mean(0);center_index=len(self.vertices)
            self.vertices.append(center.tolist());self.weights.append(weight(center) if callable(weight) else dict(weight));self.uv.append((.5,index/max(1,count-1)))
            for j in range(n):
                face=(center_index,base+index*n+j,base+index*n+(j+1)%n)
                self.faces.append(tuple(reversed(face)) if reverse else face);self.materials.append(material)


def tooth(surface,center,tangent,width,height,depth,upper,kind):
    # A cervical neck, convex labial body and differentiated incisal/occlusal
    # surface share continuous rings. Long axis remains mandibular vertical.
    normal=np.asarray((tangent[1],-tangent[0],0.));direction=-1 if upper else 1
    root=np.asarray(center).copy();root[2]-=direction*height*.5
    count=40;theta=np.linspace(0,2*np.pi,count,endpoint=False)
    levels=np.asarray([0,.07,.18,.34,.58,.78,.90,.97,1.])
    widths=np.interp(levels,[0,.18,.58,.90,1],[.59,.76,1,.98,.91])
    depths=np.interp(levels,[0,.18,.58,.90,1],[.60,.78,1,.75,.23 if kind=='incisor' else .66])
    rings=[]
    for q,w,d in zip(levels,widths,depths):
        sx=np.sign(np.cos(theta))*abs(np.cos(theta))**.63
        sy=np.sign(np.sin(theta))*abs(np.sin(theta))**.70
        points=root+sx[:,None]*tangent*width*.5*w+sy[:,None]*normal*depth*.5*d
        points[:,2]+=direction*height*q
        # Gentle incisal edge curvature; posterior cusps are not block caps.
        if kind=='incisor':points[:,2]-=direction*.0008*q**8*(abs(sx)**2)
        elif kind=='canine':points[:,2]+=direction*.002*q**8*(1-abs(sx))
        else:points[:,2]+=direction*.0012*q**8*np.cos(2*theta)**2
        points[:,1]-=.0006*np.sin(np.pi*q)**2*(1+sy)*.5
        rings.append(points)
    surface.patch(rings,0,{'Head' if upper else 'Jaw':1.})


def catmull(points,steps=12):
    points=np.asarray(points);result=[];parameters=[]
    for i in range(len(points)-1):
        a,b,c,d=points[max(0,i-1)],points[i],points[i+1],points[min(len(points)-1,i+2)]
        for t in np.linspace(0,1,steps,endpoint=False):
            result.append(.5*((2*b)+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t))
            parameters.append(i+t)
    return np.asarray(result+[points[-1]]),np.asarray(parameters+[len(points)-1])


def gums(surface,root_points,upper):
    curve,parameters=catmull(root_points,14);rings=[];sign=1 if upper else-1
    for i,(p,t) in enumerate(zip(curve,parameters)):
        tangent=curve[min(i+1,len(curve)-1)]-curve[max(0,i-1)];tangent[2]=0;tangent/=np.linalg.norm(tangent)
        outward=np.asarray((tangent[1],-tangent[0],0.))
        theta=np.linspace(0,2*np.pi,24,endpoint=False)
        # Tissue extends around roots; its tooth-facing boundary scallops
        # smoothly between adjacent crowns, rather than a uniform tube.
        scallop=.0011*np.cos(2*np.pi*t)
        points=p+outward[None,:]*np.cos(theta)[:,None]*.0065
        points[:,2]+=sign*.0042+np.sin(theta)*.0062
        points[:,2]+=sign*scallop*((1-sign*np.sin(theta))*.5)**2
        rings.append(points)
    surface.patch(rings,1,{'Head' if upper else 'Jaw':1.})


def tongue(surface,rows,rig):
    low=rows[False];front=min(p[1] for p in low)+.013
    back=max(front+.095,float(rig.data.bones['Tongue_01'].head_local.y)+.009)
    z=float(np.mean([p[2] for p in low[3:5]]))-.009
    theta=np.linspace(0,2*np.pi,40,endpoint=False);rings=[]
    for t in np.linspace(.015,.985,40):
        width=.038*np.sin(np.pi*t)**.48
        height=.0085*np.sin(np.pi*t)**.45
        center=np.asarray((0,back+(front-back)*t,z+.0015*np.sin(np.pi*t)))
        points=center+np.column_stack((width*np.cos(theta),np.zeros(len(theta)),height*np.sin(theta)))
        # A shallow median sulcus belongs to the same continuous tongue mesh.
        points[:,2]-=.0005*np.exp(-(points[:,0]/.003)**2)*np.clip(np.sin(theta),0,1)
        rings.append(points)
    def weights(p):
        t=np.clip((back-p[1])/(back-front),0,1);f=np.clip((t-.38)/.40,0,1);f=f*f*(3-2*f)
        return {'Tongue_01':float(1-f),'Tongue_02':float(f)}
    surface.patch(rings,2,weights)
    return {'posteriorY':back,'anteriorY':front,'neutralCenterZ':z,'halfWidthMeters':.038,'halfHeightMeters':.0085}


def rebuild(old,rig):
    if not np.allclose(np.asarray(old.matrix_world),np.eye(4),atol=1e-6):raise RuntimeError('Expected source oral coordinates in rig space')
    basis=np.asarray([tuple(p.co) for p in old.data.shape_keys.key_blocks['Basis'].data])
    ivory={v for p in old.data.polygons if old.data.materials[p.material_index].name=='Krag_Ivory' for v in p.vertices}
    head_index=old.vertex_groups['Head'].index
    rows={True:[],False:[]}
    for part in components(old.data):
        if int(part[0]) not in ivory:continue
        upper=any(g.group==head_index and g.weight>.99 for g in old.data.vertices[int(part[0])].groups)
        points=basis[part];center=(points.min(0)+points.max(0))*.5
        rows[upper].append(center)
    for upper in [True,False]:
        rows[upper]=np.asarray(sorted(rows[upper],key=lambda p:p[0]))
        if len(rows[upper])!=8:raise RuntimeError('Expected eight existing fitted anterior crowns per row')
    surface=Surface();report={'anteriorRows':{},'tuskRootTargets':{}}
    gum_paths={}
    for upper in [True,False]:
        centers=rows[upper];direction=-1 if upper else 1;height=.01374 if upper else .01178
        # Preserve the closed bite envelope at the incisors. Posterior crowns
        # continue the fitted dental arch beneath the cheeks.
        left=centers[0].copy();right=centers[-1].copy()
        left_extra=[];right_extra=[]
        for amount in [1,2]:
            a=left+np.asarray((-.006*amount,.020*amount,-.0005*amount));b=right+np.asarray((.006*amount,.020*amount,-.0005*amount))
            left_extra.append(a);right_extra.append(b)
        guide=np.asarray(list(reversed(left_extra))+list(centers)+right_extra)
        roots=guide.copy();roots[:,2]-=direction*height*.5;gum_paths[upper]=roots
        gums(surface,roots,upper)
        specs=[]
        for i,center in enumerate(guide):
            tangent=guide[min(i+1,len(guide)-1)]-guide[max(i-1,0)];tangent[2]=0;tangent/=np.linalg.norm(tangent)
            distances=[]
            if i>0:distances.append(np.linalg.norm((center-guide[i-1])[:2]))
            if i<len(guide)-1:distances.append(np.linalg.norm((guide[i+1]-center)[:2]))
            width=float(min(distances)*.93)
            anterior=i-2
            if not upper and anterior in [1,6]:
                report['tuskRootTargets']['R' if center[0]<0 else 'L']=roots[i].tolist()
                continue
            kind='incisor' if 2<=anterior<=5 else 'canine' if upper and anterior in [1,6] else 'premolar'
            depth=.0145 if kind=='incisor' else .0165
            tooth(surface,center,tangent,width,height,depth,upper,kind)
            specs.append({'center':center.tolist(),'widthMeters':width,'heightMeters':height,'kind':kind})
        report['anteriorRows']['upper' if upper else 'lower']=specs
    report['tongue']=tongue(surface,rows,rig)
    mesh=bpy.data.meshes.new('Krag continuous provisional oral anatomy v9j')
    mesh.from_pydata(surface.vertices,[],surface.faces);mesh.update()
    # Dental and wet oral surfaces require submillimetre relief; the old
    # generic 1.8 mm noise bump is much too large for a tooth crown.
    for source_name,new_name,roughness,distance in [
        ('Krag_Ivory','Krag_DentalEnamel',.27,.000035),
        ('Krag_OralTissue','Krag_Gingiva',.36,.00008),
        ('Krag_Tongue','Krag_OralTongue',.31,.00012)]:
        material=bpy.data.materials[source_name].copy();material.name=new_name
        for node in material.node_tree.nodes:
            if node.type=='BUMP':node.inputs['Distance'].default_value=distance;node.inputs['Strength'].default_value=.22
            elif node.type=='BSDF_PRINCIPLED':
                node.inputs['Roughness'].default_value=roughness
                node.inputs['Subsurface Weight'].default_value=.035 if source_name=='Krag_Ivory' else .08
                node.inputs['IOR'].default_value=1.46 if source_name=='Krag_Ivory' else 1.38
        material['status']='Provisional anatomical source material; actual UV bake required before runtime export'
        mesh.materials.append(material)
    for polygon,material in zip(mesh.polygons,surface.materials):polygon.material_index=material;polygon.use_smooth=True
    # Outward normals are recalculated on the actual closed components.
    import bmesh
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    if not np.allclose(np.asarray([tuple(v.co)for v in mesh.vertices]),np.asarray(surface.vertices),atol=1e-7):raise RuntimeError('Normal repair changed vertex indexing')
    if any(abs(sum(w.values())-1)>1e-7 for w in surface.weights):raise RuntimeError('Oral bone weights must sum to one')
    uv=mesh.uv_layers.new(name='UVMap')
    for polygon in mesh.polygons:
        values=[surface.uv[mesh.loops[i].vertex_index]for i in polygon.loop_indices]
        wraps=max(p[0]for p in values)-min(p[0]for p in values)>.5
        for i,(u,v)in zip(polygon.loop_indices,values):uv.data[i].uv=(u+1 if wraps and u<.5 else u,v)
    obj=bpy.data.objects.new(old.name+'_v9j',mesh);bpy.context.collection.objects.link(obj)
    for key in old.keys():obj[key]=old[key]
    obj['oralAnatomyStatus']='Provisional source study; neutral/open occlusion and likeness not accepted'
    for bone in ['Head','Jaw','Tongue_01','Tongue_02']:
        group=obj.vertex_groups.new(name=bone)
        for i,weights in enumerate(surface.weights):
            if weights.get(bone,0)>0:group.add([i],weights[bone],'REPLACE')
    modifier=obj.modifiers.new('Krag facial skeleton','ARMATURE');modifier.object=rig
    obj.parent=old.parent;obj.matrix_world=old.matrix_world.copy();obj.hide_render=old.hide_render
    # Explicit Basis only. Rigid crowns/gums and blended tongue respond to
    # skeletal articulation, not recycled mixed expression shape values.
    obj.shape_key_add(name='Basis',from_mix=False)
    previous_name=old.name;bpy.data.objects.remove(old,do_unlink=True);obj.name=previous_name
    report['vertices']=len(mesh.vertices);report['polygons']=len(mesh.polygons)
    report['removedExtraOpaqueEllipsoid']=True
    report['retainedCavity']='Continuous head topology oral bag set7'
    return obj,report
