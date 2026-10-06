"""Fitted compressed scarf loops and bib tension for the isolated v5 study."""
import bpy, math
from array import array as numeric_array
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
                rx=.046+winding*.008+across*.012
                ry=.046+winding*.011+across*.017
                fold=.0018*math.sin(a*9+winding*1.2)+.0010*math.sin(a*17-across*4)
                x=rx*math.cos(a)+.003*math.sin(a*2+winding)
                y=.005+(ry+.005*ridge+fold)*math.sin(a)
                # Adjacent wraps overlap in both radius and height. The v5b
                # .021 m front descent per wrap exceeded its .014 m width,
                # leaving visible open bands rather than compressed fabric.
                z=1.030-winding*.009-across*.021-front**1.4*(.010+winding*.004)+.005*math.cos(a*2+.4*winding)
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
    # Preserve the fixed proportions while recovering the reference's waist
    # taper in both skin and the fitted underlayer. The belt remains the anchor.
    for piece in collection.objects:
        if piece.get('bone')!='BodyAnatomy' and piece.name!='Sleeveless dust undershirt':continue
        inverse=piece.matrix_world.inverted()
        arrays=[key.data for key in piece.data.shape_keys.key_blocks] if piece.data.shape_keys else [piece.data.vertices]
        fitted_offsets={}
        for array_index,array in enumerate(arrays):
            for vertex_index,vertex in enumerate(array):
                if array_index:
                    vertex.co+=fitted_offsets[vertex_index]
                    continue
                original_local=vertex.co.copy()
                p=piece.matrix_world@vertex.co
                if .675<p.z<.875 and abs(p.x)<.12:
                    taper=.12*math.exp(-((p.z-.755)/.065)**2)
                    p.x*=1-taper;p.y*=1-taper*.22
                    vertex.co=inverse@p
                fitted_offsets[vertex_index]=vertex.co-original_local
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
    trousers=[]
    # Replace the periodic inflated-ring profile with a broad cloth silhouette,
    # compression at the gathered hem and directional folds from knee/hip.
    for side,sign in [('L',1),('R',-1)]:
        piece=bpy.data.objects.get('Shaped overalls trouser '+side)
        if not piece:continue
        inverse=piece.matrix_world.inverted()
        arrays=[key.data for key in piece.data.shape_keys.key_blocks] if piece.data.shape_keys else [piece.data.vertices]
        def old_profile(t):
            return (.055-t*.018+.010*math.sin(t*math.pi*13)**3,.057-t*.020+.007*math.cos(t*math.pi*17))
        def profile(t,values):
            controls=[0,.18,.40,.59,.77,1]
            for i in range(len(controls)-1):
                if controls[i]<=t<=controls[i+1]:
                    q=(t-controls[i])/(controls[i+1]-controls[i]);q=q*q*(3-2*q)
                    return values[i]*(1-q)+values[i+1]*q
            return values[0] if t<0 else values[-1]
        fitted_offsets={}
        for array_index,array in enumerate(arrays):
            for vertex_index,vertex in enumerate(array):
                if array_index:
                    vertex.co+=fitted_offsets[vertex_index]
                    continue
                original_local=vertex.co.copy()
                p=piece.matrix_world@vertex.co;t=max(0,min(1,(.604-p.z)/.400))
                center=Vector((sign*(.066+.008*math.sin(t*math.pi)),.009+.009*math.sin(t*7),p.z))
                old_x,old_y=old_profile(t);offset=p-center
                angle=math.atan2(offset.y/max(old_y,.008),offset.x/max(old_x,.008))
                radius_x=profile(t,[.054,.065,.067,.058,.054,.042])
                radius_y=profile(t,[.057,.067,.065,.058,.051,.038])
                # Long diagonal tension folds below the hip, local knee folds,
                # and a small nonperiodic bunching field at the rolled cuff.
                hip=.0034*math.sin(angle*5+t*8)*math.exp(-((t-.27)/.24)**2)
                knee=.0028*math.sin(angle*3-t*17)*math.exp(-((t-.61)/.13)**2)
                cuff=.0038*math.sin(angle*7+t*13)*math.exp(-((t-.94)/.065)**2)
                fold=hip+knee+cuff
                # Preserve cap/interior vertices relative to their cross-section.
                rho=1 if .02<t<.98 else min(1,math.sqrt((offset.x/max(old_x,.008))**2+(offset.y/max(old_y,.008))**2))
                p.x=center.x+math.cos(angle)*(radius_x+fold)*rho
                p.y=center.y+math.sin(angle)*(radius_y+fold*.8)*rho
                vertex.co=inverse@p
                fitted_offsets[vertex_index]=vertex.co-original_local
        trousers.append(piece.name)
        for attached in collection.objects:
            if attached.name.startswith(('Cargo sewn pocket '+side,'Cargo pocket flap '+side)):
                attached.location.x+=sign*.028
            elif attached.name.startswith('Knee patched panel '+side):
                attached.location.y-=.015
            elif attached.name.startswith('Knee visible stitch') and attached.get('bone')=='Shin_'+side:
                attached.location.y-=.015
            elif attached.name.startswith('Trouser raised seam '+side):
                # Side seams follow the broader gathered silhouette.
                for vertex in attached.data.vertices:
                    p=attached.matrix_world@vertex.co;t=max(0,min(1,(.604-p.z)/.400))
                    center=sign*(.066+.008*math.sin(t*math.pi))
                    direction=1 if p.x>center else -1
                    p.x=center+direction*(profile(t,[.054,.065,.067,.058,.054,.042])+.001)
                    vertex.co=attached.matrix_world.inverted()@p
    # The FBX base geometry comes from mesh positions, while relative targets
    # come from key-block coordinates. Keep both representations in agreement
    # after editing the Basis of an existing shaped garment/body.
    for piece in collection.objects:
        if piece.type!='MESH' or not piece.data.shape_keys:continue
        if piece.get('bone')!='BodyAnatomy' and piece.name not in changed+trousers+['Sleeveless dust undershirt']:continue
        coordinates=numeric_array('f',[0])*(len(piece.data.vertices)*3)
        piece.data.shape_keys.key_blocks['Basis'].data.foreach_get('co',coordinates)
        piece.data.vertices.foreach_set('co',coordinates);piece.data.update()
    return {'scarfTriangles':sum(len(p.vertices)-2 for p in obj.data.polygons),'bibPiecesReformed':changed,'trousersReformed':trousers,
            'status':'Native cloth review required in Front/Back/Side/Shoot; no simulation.'}
