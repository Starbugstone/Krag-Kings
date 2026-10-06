"""Fitted compressed scarf loops and bib tension for the isolated v5 study."""
import bpy, math
from mathutils import Vector

def revise_cloth(collection,rig):
    old=bpy.data.objects.get('Draped desert scarf')
    if old:
        data=old.data;bpy.data.objects.remove(old,do_unlink=True)
        if data.users==0:bpy.data.meshes.remove(data)
    vertices=[];faces=[];uvs=[];N=112;M=13
    for winding in range(3):
        start=len(vertices)
        for j in range(M):
            across=j/(M-1);ridge=math.sin(across*math.pi)
            for i in range(N):
                a=i/N*math.tau;front=max(0,-math.sin(a));back=max(0,math.sin(a))
                rx=.046+winding*.009+across*.009
                ry=.046+winding*.013+across*.014
                fold=.0018*math.sin(a*9+winding*1.2)+.0010*math.sin(a*17-across*4)
                x=rx*math.cos(a)+.003*math.sin(a*2+winding)
                y=.005+(ry+.005*ridge+fold)*math.sin(a)
                z=1.006-winding*.013-across*.014-front**1.4*(.012+winding*.012)+.005*math.cos(a*2+.4*winding)
                z+=fold*ridge
                vertices.append((x,y,z));uvs.append((i/N*2,across*.22+winding*.25))
        for j in range(M-1):
            for i in range(N):
                a=start+j*N+i;b=start+j*N+(i+1)%N;faces.append((a,b,b+N,a+N))
    mesh=bpy.data.meshes.new('Three compressed scarf wraps');mesh.from_pydata(vertices,[],faces);mesh.update()
    obj=bpy.data.objects.new('Nib v5 layered desert scarf',mesh);collection.objects.link(obj)
    mesh.materials.append(bpy.data.materials['Nib_Cloth']);layer=mesh.uv_layers.new(name='UVMap')
    for loop in mesh.loops:layer.data[loop.index].uv=uvs[loop.vertex_index]
    for p in mesh.polygons:p.use_smooth=True
    bpy.context.view_layer.objects.active=obj
    solid=obj.modifiers.new('Woven hem thickness','SOLIDIFY');solid.thickness=.0015
    bpy.ops.object.modifier_apply(modifier=solid.name)
    sub=obj.modifiers.new('Soft pressed cloth','SUBSURF');sub.levels=1;bpy.ops.object.modifier_apply(modifier=sub.name)
    obj.parent=rig;group=obj.vertex_groups.new(name='Chest');group.add(list(range(len(obj.data.vertices))),1,'REPLACE')
    obj['variant']='all';obj['bone']='Chest'
    mod=obj.modifiers.new('Nib deformation','ARMATURE');mod.object=rig
    changed=[]
    # Apply the same world-space field to cloth, pockets and stitches so the
    # attachments follow the fabric rather than floating over a changed bib.
    for piece in collection.objects:
        if not piece.name.startswith(('Overalls draped bib','Bib sewn chest pocket','Bib pocket flap','Bib stitched outer seam','Bib hand stitching')):continue
        inverse=piece.matrix_world.inverted()
        points=[k.data for k in piece.data.shape_keys.key_blocks] if piece.data.shape_keys else [piece.data.vertices]
        for data in points:
            for vertex in data:
                p=piece.matrix_world@vertex.co
                u=p.x/.085;t=max(0,min(1,(p.z-.682)/.212))
                swelling=.012*max(0,1-u*u)*math.sin(t*math.pi*.78)
                tension=.0033*math.sin(24*t+u*7)*math.sin(t*math.pi)**2
                p.y-=swelling+tension
                vertex.co=inverse@p
        changed.append(piece.name)
    return {'scarfTriangles':sum(len(p.vertices)-2 for p in obj.data.polygons),'bibPiecesReformed':changed,
            'status':'Native cloth review required in Front/Back/Side/Shoot; no simulation.'}
