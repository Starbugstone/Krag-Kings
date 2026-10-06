"""Fit the CC0 coherent hand cage to the existing Nib hand/finger contract.

This is a next-pass authoring module, not part of the pinned runtime derivative.
Both hands retain finger names; right anatomical finger ordering is corrected.
"""
import bpy, bmesh, math
from mathutils import Vector, Matrix

SOURCE_CHAINS={
 'Index':[(.039,.002,-.080),(.046,.006,-.124),(.051,.010,-.160),(.054,.012,-.186)],
 'Middle':[(.012,.002,-.086),(.014,.006,-.134),(.017,.010,-.176),(.019,.012,-.203)],
 'Ring':[(-.014,.004,-.081),(-.014,.010,-.128),(-.012,.015,-.165),(-.013,.018,-.191)],
 'Little':[(-.038,.008,-.067),(-.044,.013,-.109),(-.049,.017,-.139),(-.052,.020,-.162)],
 'Thumb':[(.032,.012,-.005),(.068,.020,-.060),(.090,.023,-.106)]}

def closest(point,a,b):
    delta=b-a;t=max(0,min(1,(point-a).dot(delta)/delta.length_squared))
    return (point-a-delta*t).length,t

def rebuild_hands(library,collection,rig,discard):
    bpy.context.view_layer.objects.active=rig
    bpy.ops.object.select_all(action='DESELECT');rig.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    # v4b assigned Index to the little-finger side of the right palm. Move the
    # named bones to their anatomical positions, keeping stable names/actions.
    for finger,target_x in [('Index',-.209),('Middle',-.221),('Ring',-.233),('Little',-.245)]:
        for segment in range(1,4):
            bone=rig.data.edit_bones[finger+str(segment)+'_R']
            bone.head.x=target_x;bone.tail.x=target_x
    bpy.ops.object.mode_set(mode='OBJECT');rig.select_set(False)
    report={'referenceObject':'Hand  - Realistic','referenceAuthor':'Dan Ulrich','license':'CC0 in asset metadata and bundle README',
            'rightFingerOrderCorrected':True,'requiresMatchingReexportedClips':True,'hands':[]}
    for side,sign in [('L',1),('R',-1)]:
        with bpy.data.libraries.load(str(library),link=False) as (available,requested):requested.objects=['Hand  - Realistic']
        hand=requested.objects[0]
        for c in list(hand.users_collection):c.objects.unlink(hand)
        collection.objects.link(hand);hand.modifiers.clear();hand.vertex_groups.clear()
        hand.name='Nib v5 coherent hand '+side
        hand.parent=None;hand.matrix_parent_inverse=Matrix.Identity(4);hand.matrix_world=Matrix.Identity(4)
        hand.data.materials.clear()
        hand.data.materials.append(bpy.data.materials['Nib_Skin']);hand.data.materials.append(bpy.data.materials['Nib_Leather'])
        # Native topology remains connected; no separate finger cylinders.
        original=[v.co.copy() for v in hand.data.vertices]
        mapping=[]
        for finger,coords in SOURCE_CHAINS.items():
            for segment in range(len(coords)-1):
                name=finger+str(segment+1)+'_'+side
                a,b=Vector(coords[segment]),Vector(coords[segment+1]);target=rig.data.bones[name]
                source_axis=(b-a).normalized();dest_axis=(target.tail_local-target.head_local).normalized()
                # Mirror across the source palm and turn its palmar +Y forward.
                pre=Matrix.Diagonal(Vector((-sign,-1,1)))
                source_direction=(pre@source_axis).normalized()
                rotation=source_direction.rotation_difference(dest_axis).to_matrix()
                mapping.append((name,a,b,target.head_local.copy(),source_axis,pre,rotation,target.length/(b-a).length))
        groups={name:hand.vertex_groups.new(name=name) for name,*_ in mapping}
        groups['Hand_'+side]=hand.vertex_groups.new(name='Hand_'+side)
        def palm(point):
            return Vector((sign*.227-sign*(point.x-.008)*.43,-.043-point.y*.43,.610+point.z*.39))
        for vertex,point in zip(hand.data.vertices,original):
            transforms=[]
            for name,a,b,target,axis,pre,rotation,along_scale in mapping:
                distance,t=closest(point,a,b)
                # Smooth compact support keeps palm/web vertices connected.
                strength=math.exp(-(distance/.025)**4)
                if point.z>a.z+.015 and not name.startswith('Thumb'):strength*=.1
                offset=point-a;along=axis*offset.dot(axis);across=offset-along
                transformed=target+rotation@(pre@(along*along_scale+across*.43))
                transforms.append((name,strength,transformed))
            knuckle=max(0,min(1,(-point.z-.046)/.035))
            thumb=max(0,min(1,(point.x-.030)/.040))*max(0,min(1,(-point.z+.005)/.055))
            blend=max(knuckle,thumb)
            total=sum(weight for _,weight,_ in transforms)
            if total<1e-10:blend=0
            result=palm(point)*(1-blend)
            if blend:
                ranked=sorted(transforms,key=lambda item:-item[1])[:4];normal=sum(w for _,w,_ in ranked)
                for name,weight,transformed in ranked:
                    weight=weight/normal*blend;result+=transformed*weight
                    if weight>1e-6:groups[name].add([vertex.index],weight,'REPLACE')
            if blend<1:groups['Hand_'+side].add([vertex.index],1-blend,'REPLACE')
            vertex.co=result
        # The palm/proximal finger surface represents the fitted fingerless
        # glove. Its topology flows through webs; distal fingertips remain skin.
        for polygon in hand.data.polygons:
            z=sum(original[i].z for i in polygon.vertices)/len(polygon.vertices)
            x=sum(original[i].x for i in polygon.vertices)/len(polygon.vertices)
            polygon.material_index=1 if z>-.123 and not (x>.063 and z<-.073) else 0
            polygon.use_smooth=True
        bm=bmesh.new();bm.from_mesh(hand.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(hand.data);bm.free()
        bpy.context.view_layer.objects.active=hand
        sub=hand.modifiers.new('Coherent finger and knuckle surface','SUBSURF');sub.levels=2
        bpy.ops.object.modifier_apply(modifier=sub.name)
        # Subdivision interpolates adjacent fields; enforce an explicit bounded
        # influence set on this newly authored source before pose review/export.
        normalized=[]
        for vertex in hand.data.vertices:
            weights=sorted([(hand.vertex_groups[g.group].name,g.weight) for g in vertex.groups if g.weight>1e-7],key=lambda item:-item[1])[:4]
            total=sum(weight for _,weight in weights)
            if total<1e-7:raise RuntimeError('Unweighted coherent hand vertex')
            normalized.append([(name,weight/total) for name,weight in weights])
        hand.vertex_groups.clear()
        for name in sorted({name for row in normalized for name,_ in row}):hand.vertex_groups.new(name=name)
        for index,row in enumerate(normalized):
            for name,weight in row:hand.vertex_groups[name].add([index],weight,'REPLACE')
        hand.parent=rig;mod=hand.modifiers.new('Nib deformation','ARMATURE');mod.object=rig
        hand['bone']='Hand_'+side;hand['variant']='natural' if side=='L' else 'all'
        for obj in list(collection.objects):
            if obj is hand:continue
            if obj.name.startswith(('Leather glove palm '+side,'Finger '+side+' ','Fingerless glove '+side+' ','Fingernail '+side,'Thumb '+side,'Thumb glove '+side)):
                discard(obj)
        report['hands'].append({'side':side,'vertices':len(hand.data.vertices),'triangles':sum(len(p.vertices)-2 for p in hand.data.polygons)})
    report['status']='Native hand/grip review required; this changes right finger bind positions and cannot reuse old standalone FBX clips.'
    return report
