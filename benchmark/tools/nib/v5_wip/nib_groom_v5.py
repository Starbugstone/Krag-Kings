"""Scalp-bound clumped Nib groom for the separate v5 native study.

All guides are deterministic. Runtime/cinematic density only changes the number
of strands around each existing guide; it never changes the guide field itself.
Opaque triangles avoid full strand simulation. Real costs are reported by caller.
"""
import bpy, math, random
from mathutils import Vector
from mathutils.bvhtree import BVHTree

EAR_CENTERS=[(.066,1.210),(.114,1.250),(.170,1.289),(.220,1.333),(.269,1.379),(.309,1.417)]
EAR_WIDTHS=[.009,.056,.069,.060,.036,.0004]

def ear_coordinates(point):
    xz=Vector((abs(point.x),point.z));best=None
    for i in range(5):
        a=Vector(EAR_CENTERS[i]);b=Vector(EAR_CENTERS[i+1]);d=b-a
        q=max(0,min(1,(xz-a).dot(d)/d.length_squared));center=a+d*q
        distance=(xz-center).length_squared
        if best is None or distance<best[0]:
            width=EAR_WIDTHS[i]*(1-q)+EAR_WIDTHS[i+1]*q
            u=(xz-center).dot(Vector((.64,-.77)))/max(width,.001)
            best=(distance,(i+q)/5,u)
    return best[1],best[2]

def deepen_ears(collection):
    changed=[]
    for obj in collection.objects:
        if obj.type!='MESH' or not obj.name.startswith(('Fennec cupped ear','Ear inner velvet','Rounded auricle cartilage rim','Auricle basal cartilage fold')):continue
        inverse=obj.matrix_world.inverted()
        for vertex in obj.data.vertices:
            p=obj.matrix_world@vertex.co;t,u=ear_coordinates(p);u=max(-1,min(1,u))
            belly=math.sin(math.pi*t)**.65
            p.y+=.021*belly*(1-u*u)-.005*belly*abs(u)**6-.009*t**7
            vertex.co=inverse@p
        obj.data.update();changed.append(obj.name)
    return changed

def avoid_goggles(point):
    point=point.copy()
    for side in [-1,1]:
        dx=point.x-side*.040;dz=point.z-1.228;r=math.hypot(dx,dz)
        if r<.033 and point.y<-.048:
            # Keep the guide behind the real gasket/lens envelope. Fine hairs
            # may emerge around its silhouette, never lie across the glass.
            point.y=max(point.y,-.048+.003*(1-r/.033))
    return point

def fine_face_fuzz(head,collection,rig,material,cinematic=False):
    """Fine fuzz inherits each surface root's weights and every facial delta."""
    rng=random.Random(28913);candidates=[]
    for v in head.data.vertices:
        x,y,z=v.co
        if y>-.023 or not 1.075<z<1.210:continue
        if .014<abs(x)<.071 and 1.141<z<1.181:continue
        if abs(x)<.043 and 1.098<z<1.146:continue
        candidates.append(v.index)
    if not candidates:raise RuntimeError('No facial fuzz root surface')
    vertices=[];faces=[];roots=[];rng.shuffle(candidates)
    for i in range(2700 if cinematic else 900):
        source=head.data.vertices[rng.choice(candidates)];root=source.co;normal=source.normal.normalized()
        direction=(normal+Vector((root.x*2,.05,-.65))).normalized()
        length=rng.uniform(.0008,.0020);axis=direction.cross(Vector((0,1,0))).normalized();other=direction.cross(axis).normalized()
        start=len(vertices);radius=rng.uniform(.000020,.000040)
        for j in range(2):
            center=root+normal*.00005+direction*(length*j)
            for k in range(3):
                a=k/3*math.tau;vertices.append(tuple(center+(axis*math.cos(a)+other*math.sin(a))*(radius if j==0 else .000002)));roots.append(source.index)
        for k in range(3):faces.append((start+k,start+(k+1)%3,start+3+(k+1)%3,start+3+k))
    mesh=bpy.data.meshes.new('Fine skin fuzz following facial topology');mesh.from_pydata(vertices,[],faces);mesh.update()
    obj=bpy.data.objects.new('Nib v5 fine facial fuzz',mesh);collection.objects.link(obj);obj.matrix_world=head.matrix_world.copy()
    mesh.materials.append(material);uv=mesh.uv_layers.new(name='UVMap')
    for loop in mesh.loops:uv.data[loop.index].uv=((loop.vertex_index%3)/3,(loop.vertex_index%6)//3)
    for polygon in mesh.polygons:polygon.use_smooth=True
    groups={group.name:obj.vertex_groups.new(name=group.name) for group in head.vertex_groups}
    for index,root in enumerate(roots):
        for group in head.data.vertices[root].groups:
            groups[head.vertex_groups[group.group].name].add([index],group.weight,'REPLACE')
    obj.shape_key_add(name='Basis');basis=head.data.shape_keys.key_blocks['Basis']
    for source_key in head.data.shape_keys.key_blocks:
        if source_key.name=='Basis':continue
        target=obj.shape_key_add(name=source_key.name)
        for index,root in enumerate(roots):target.data[index].co=mesh.vertices[index].co+source_key.data[root].co-basis.data[root].co
    world=obj.matrix_world.copy();obj.parent=rig;obj.matrix_world=world
    mod=obj.modifiers.new('Nib deformation','ARMATURE');mod.object=rig
    obj['variant']='all';obj['bone']='FaceSurfaceFuzz';obj['fur_strands']=len(roots)//6;obj['fur_guides']=len(roots)//6;obj['fur_rings']=2
    obj['fur_design']='Fine concept-visible skin fuzz; surface-root morph and weight inheritance'
    return obj

def strand_mesh(name,guide_clumps,collection,rig,material,bone='Head',cinematic=False):
    vertices=[];faces=[];uvs=[];rng=random.Random(8141)
    count=0;rings=7 if cinematic else 4;sides=3
    for root,normal,mid,tip,width,seed in guide_clumps:
        rng.seed(seed)
        tangent=normal.cross(Vector((0,0,1)))
        if tangent.length<.01:tangent=normal.cross(Vector((0,1,0)))
        tangent.normalize();bitangent=normal.cross(tangent).normalized()
        # Nested random seeds retain the runtime subset in the denser master.
        density=28 if cinematic else 12
        for strand in range(density):
            strand_rng=random.Random(seed*100+strand)
            radial=width*math.sqrt(strand_rng.random());angle=strand_rng.random()*math.tau
            offset=tangent*(radial*math.cos(angle))+bitangent*(radial*math.sin(angle))
            length=1+strand_rng.uniform(-.12,.12)
            start=root+offset
            middle=mid+offset*.62
            end=root+(tip-root)*length+offset*.12
            radius=strand_rng.uniform(.00010,.00024)
            base=len(vertices)
            for j in range(rings):
                t=j/(rings-1);point=start*(1-t)**2+middle*(2*t*(1-t))+end*t*t
                if bone=='Head':point=avoid_goggles(point)
                direction=(2*(1-t)*(middle-start)+2*t*(end-middle)).normalized()
                across=direction.cross(normal)
                if across.length<.01:across=direction.cross(Vector((1,0,0)))
                across.normalize();other=direction.cross(across).normalized()
                taper=radius*(1-t)**.8+.000006
                for k in range(sides):
                    a=k/sides*math.tau;vertices.append(tuple(point+taper*(math.cos(a)*across+math.sin(a)*other)));uvs.append((k/sides,t))
            for j in range(rings-1):
                for k in range(sides):
                    a=base+j*sides+k;b=base+j*sides+(k+1)%sides
                    faces.append((a,b,b+sides,a+sides))
            count+=1
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(vertices,[],faces);mesh.update()
    obj=bpy.data.objects.new(name,mesh);collection.objects.link(obj)
    mesh.materials.append(material)
    layer=mesh.uv_layers.new(name='UVMap')
    for loop in mesh.loops:layer.data[loop.index].uv=uvs[loop.vertex_index]
    for polygon in mesh.polygons:polygon.use_smooth=True
    obj['bone']=bone;obj['variant']='all';obj['fur_strands']=count;obj['fur_rings']=rings
    obj['fur_guides']=len(guide_clumps);obj['fur_design']='v5 deterministic clumped guides, no simulation'
    obj.parent=rig;group=obj.vertex_groups.new(name=bone);group.add(list(range(len(vertices))),1,'REPLACE')
    mod=obj.modifiers.new('Nib deformation','ARMATURE');mod.object=rig
    return obj

def build_groom(head,collection,rig,material,cinematic=False):
    """Roots are sampled from the actual fitted scalp, with outward clearance."""
    rng=random.Random(651220)
    points=[]
    for vertex in head.data.vertices:
        point=head.matrix_world@vertex.co
        normal=(head.matrix_world.to_3x3()@vertex.normal).normalized()
        z=point.z+.032
        if z<1.16 or (point.y<-.01 and z<1.207):continue
        if normal.z<-.2:continue
        points.append((point,normal))
    if not points:raise RuntimeError('No fitted scalp root samples')
    clumps=[]
    for index in range(730):
        root,normal=rng.choice(points);root=root+normal*.0003
        front=root.y<-.015
        if front:flow=Vector((-.026,-.004,-.013))
        else:flow=Vector((math.copysign(.019,root.x),.009,-.025))
        # Subtract the inward component and lift the whole path off the scalp.
        flow-=normal*flow.dot(normal)
        if flow.length<.006:flow=normal.cross(Vector((1,0,0)))*.026
        flow.normalize();flow*=rng.uniform(.031,.052)
        mid=root+flow*.42+normal*rng.uniform(.012,.021)
        tip=root+flow+normal*rng.uniform(.007,.012)
        clumps.append((root,normal,mid,tip,.0024,1000+index))
    output=[strand_mesh('Nib v5 scalp clumped coat',clumps,collection,rig,material,cinematic=cinematic)]
    # Ear roots use the actual closed cupped auricle. A nearer surface query
    # fits each clump to its rim/interior rather than relying on old dimensions.
    for side,sign in [('L',1),('R',-1)]:
        ear=next(o for o in collection.objects if o.name.startswith('Fennec cupped ear ') and o.get('bone')=='Ear_'+side)
        rim=[];base=[];interior=[]
        for vertex in ear.data.vertices:
            point=ear.matrix_world@vertex.co;normal=(ear.matrix_world.to_3x3()@vertex.normal).normalized()
            if normal.y<-.25 and abs(point.x)>.075:
                t,u=ear_coordinates(point)
                if abs(u)>.66:rim.append((point,normal,t,u))
                elif t<.35:base.append((point,normal,t,u))
                else:interior.append((point,normal,t,u))
        clumps=[]
        for index in range(330):
            choice=rng.random();candidates=rim if choice<.75 else base if choice<.96 else interior
            root,normal,along,u=rng.choice(candidates or rim)
            root=root+normal*.0003
            flow=Vector((-sign*u*.021,-.002,u*.019))
            flow+=Vector((sign*.005,0,.008))
            flow-=normal*flow.dot(normal)
            flow*=rng.uniform(.75,1.45)
            mid=root+flow*.44+normal*rng.uniform(.010,.018)
            tip=root+flow+normal*rng.uniform(.005,.010)
            clumps.append((root,normal,mid,tip,.0024,3000+(0 if sign==1 else 1000)+index))
        output.append(strand_mesh('Nib v5 auricle clumped coat '+side,clumps,collection,rig,material,'Ear_'+side,cinematic))
    # A longer tapered chin cluster follows the jaw, with irregular strand ends.
    points=[]
    for vertex in head.data.vertices:
        p=head.matrix_world@vertex.co;z=p.z+.032
        if abs(p.x)<.015 and 1.066<z<1.083 and p.y<-.024:
            n=(head.matrix_world.to_3x3()@vertex.normal).normalized();points.append((p,n))
    if points:
        clumps=[]
        for index in range(24):
            root,normal=rng.choice(points);tip=root+Vector((root.x*.12,.001,-rng.uniform(.014,.022)))
            clumps.append((root,normal,root.lerp(tip,.5)+normal*.002,tip,.0015,5000+index))
        output.append(strand_mesh('Nib v5 tapered chin tuft',clumps,collection,rig,material,'Jaw',cinematic))
    output.append(fine_face_fuzz(head,collection,rig,material,cinematic))
    return output
