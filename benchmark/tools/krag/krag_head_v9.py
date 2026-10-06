"""Provisional continuous Krag face adapted from the official CC0 animation head.

This preserves the reference eye, lip, nose, cheek and jaw loops. It is an
unaccepted anatomy pass; source proportions are fitted toward concept sheet 01.
Coordinates returned here precede the common Krag head proportion transform.
"""
import bpy,json,sys
import numpy as np
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree


def fit(points):
    x,y,z=np.asarray(points,dtype=float).T
    front=np.clip((-y-.005)/.065,0,1)
    gaussian=lambda value,center,width:np.exp(-((value-center)/width)**2)
    target_z=np.interp(z,[.02,.13,.18,.222,.234,.268,.3100375,.337,.436],
                         [1.54,1.650,1.705,1.777,1.799,1.860,1.934,1.974,2.107])
    width=np.interp(z,[.02,.13,.18,.222,.268,.3100375,.337,.38,.436],
                      [1.55,1.82,2.26,2.34,2.23,2.18,2.02,2.00,1.92])
    target_x=x*width
    target_y=y*1.40+.013
    # Broad projecting mandible and muzzle, with a low, flattened nasal bridge.
    mouth=gaussian(x,0,.060)*gaussian(z,.232,.030)*front
    chin=gaussian(x,0,.066)*gaussian(z,.183,.026)*front
    target_y-=.064*mouth+.112*chin
    # Deep upper muzzle and underbite remain one connected lip/cheek surface.
    upper_muzzle=gaussian(x,0,.066)*gaussian(z,.255,.020)*front
    target_y-=.038*upper_muzzle
    lower_lip=gaussian(x,0,.045)*gaussian(z,.224,.010)*front
    target_y-=.007*lower_lip
    target_x*=1+.14*mouth
    target_z-=.010*(np.clip(abs(x)/.053,0,1)**1.5)*mouth
    nose=gaussian(x,0,.030)*gaussian(z,.271,.030)*front
    target_x*=1+.85*nose
    target_y-=.028*nose
    target_y+=.011*gaussian(x,0,.026)*gaussian(z,.295,.021)*front
    # The earlier human-derived nose sat too low, leaving a long eye/nose
    # interval and a short thin upper muzzle. Lift the complete nasal mass
    # without moving the mouth seam; retain the real nostril opening loops.
    nasal_lift=gaussian(x,0,.042)*gaussian(z,.271,.021)*front
    target_z+=.025*nasal_lift
    alar=gaussian(abs(x),.019,.010)*gaussian(z,.262,.015)*front
    target_y-=.012*alar
    target_x+=np.sign(x)*.004*alar
    # The same transformation is applied to the complete eye assemblies, so
    # lids and globes share their fitting field instead of being placed by eye.
    ocular=gaussian(abs(x),.0358764,.026)*gaussian(z,.3100375,.024)*front
    target_y-=.0165*ocular
    target_z-=(z-.3100375)*.10*ocular
    target_x-=np.sign(x)*(abs(x)-.0358764)*.08*ocular
    # Continuous sloping supraorbital bone: low inner frown and rising outer
    # brow, with eye opening retained rather than flattened to a horizontal slit.
    brow=gaussian(abs(x),.036,.021)*gaussian(z,.321+.43*abs(x),.010)*front
    target_y-=(.058+.003*np.tanh(x/.012))*brow
    target_z-=(.017+.0015*np.tanh(x/.012))*gaussian(abs(x),.022,.019)*brow
    # A recessed central bridge separates the paired ridges; overlapping broad
    # fields in v9b had turned the brow into one horizontal shelf.
    central_brow=gaussian(x,0,.011)*gaussian(z,.338,.021)*front
    target_y+=.016*central_brow
    # Flatter cheek planes, with the uninterrupted nasolabial surface retained.
    cheek=gaussian(abs(x),.057,.022)*gaussian(z,.276,.030)*front
    target_y-=.006*cheek
    target_x+=np.sign(x)*.007*cheek
    zygoma=gaussian(abs(x),.058,.023)*gaussian(z,.291,.019)*front
    target_y-=.030*zygoma
    masseter=gaussian(abs(x),.064,.018)*gaussian(z,.231,.034)*front
    target_y-=.010*masseter
    target_x+=np.sign(x)*.006*masseter
    # Preserve the crown while rounding down the lateral scalp, instead of a
    # broad flat plateau. This is a regional cage warp, not an added skull lobe.
    scalp=np.clip((z-.346)/.055,0,1)
    target_z-=.018*np.clip(abs(x)/.081,0,1)**1.7*scalp
    # Small rounded Krag ears retain the source auricle topology. Compress only
    # the outer lateral region rather than adding disconnected ear primitives.
    auricle=np.clip((abs(x)-.068)/.019,0,1)*np.clip((y+.056)/.025,0,1)
    auricle*=gaussian(z,.289,.049)
    target_x=target_x*(1-auricle)+np.sign(x)*(.178+(abs(x)-.068)*.65)*auricle
    return np.column_stack((target_x,target_y,target_z))


def sculpt_face(raw,points):
    """Low relief anatomically placed folds on the continuous dense face."""
    x,y,z=raw.T;result=points.copy()
    front=np.clip((-y-.045)/.060,0,1)
    gaussian=lambda a,c,w:np.exp(-((a-c)/w)**2)
    relief=np.zeros(len(raw))
    # Paired glabellar furrows divide the heavy frown, not the eyelid margins.
    for sign in [-1,1]:
        glabella=gaussian(x,sign*.012,.0016)*gaussian(z,.350,.023)
        relief+=.0019*glabella
        # Nasolabial furrows run from the nasal ala toward the mouth corners.
        t=np.clip((.271-z)/.043,0,1)
        line=sign*(.026+.017*t)
        extent=gaussian(z,.251,.026)
        relief+=.0021*gaussian(x,line,.0015)*extent
        relief-=.0015*gaussian(x,line+sign*.0032,.0026)*extent
        for dz,slope in [(0,.20),(.007,.32),(-.006,-.12)]:
            linez=.309+dz+slope*(abs(x)-.056)
            relief+=.0010*gaussian(z,linez,.0011)*gaussian(abs(x),.065,.011)
    for height,strength in [(.357,.0012),(.375,.0009)]:
        line=height+.045*(abs(x)/.10)**2+.0013*np.sin(x*130)
        relief+=strength*gaussian(z,line,.0014)*gaussian(x,0,.067)
    # Chin-to-lower-lip crease remains low relief; the mouth seam is real topology.
    relief+=.0015*gaussian(z,.207+.045*abs(x),.0018)*gaussian(x,0,.043)
    result[:,1]+=relief*front
    return result


def build(c):
    iris_detail='--iris-detail' in sys.argv
    if iris_detail:
        import krag_iris_material
        krag_iris_material.configure(c['iris'])
    source=c['ROOT']/'benchmark/art/reference-anatomy/blender-studio-human-base-meshes/source/human-base-meshes-bundle-v1.4.1/human_base_meshes_bundle.blend'
    names=['GEO-head_animation_realistic']
    names += ['GEO-head_animation_realistic.'+part+'.'+side for part in ['iris','sclera'] for side in ['L','R']]
    with bpy.data.libraries.load(str(source),link=False) as (available,loaded):
        loaded.objects=names
    reference={o.name:o for o in loaded.objects}
    head=reference['GEO-head_animation_realistic']
    # Appended but unlinked objects can expose identity matrix_world until the
    # intact parent hierarchy has been evaluated. Cache only after linking.
    for obj in reference.values():
        if obj.name not in bpy.context.collection.objects:
            bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.update()
    # Cache all source transforms BEFORE moving the head or clearing eye parents.
    # The library's eyes are parented to its head and inherit those transforms.
    matrices={name:obj.matrix_world.copy() for name,obj in reference.items()}
    source_head_inverse=matrices[head.name].inverted()
    landmarks={};eye_audit={}
    for side,sign in [('L',1),('R',-1)]:
        eye_name='GEO-head_animation_realistic.sclera.'+side
        source_center=source_head_inverse@matrices[eye_name].translation
        expected=np.asarray((sign*.0358764,-.1153812,.3100375))
        if np.linalg.norm(np.asarray(source_center)-expected)>.00005:
            raise RuntimeError('Invalid evaluated reference eye center '+side+': '+str(tuple(source_center)))
        eye_audit[side]={'sourceCenterMeters':list(source_center),'expectedSourceCenterMeters':expected.tolist(),
                         'sourceCenterErrorMeters':float(np.linalg.norm(np.asarray(source_center)-expected))}
        landmarks['Eye_'+side]=tuple(fit([source_center])[0])
        for name,point in {'LidUpper':(sign*.0358764,-.126,.319),
                           'LidLower':(sign*.0358764,-.126,.301),
                           'BrowInner':(sign*.020,-.110,.332),
                           'BrowOuter':(sign*.056,-.105,.333),
                           'Cheek':(sign*.060,-.082,.280),
                           'MouthCorner':(sign*.043,-.112,.234)}.items():
            landmarks[name+'_'+side]=tuple(fit([point])[0])
    for name,point in {'JawPivot':(0,-.011,.281),'JawTail':(0,-.105,.190),
                       'LipUpper':(0,-.121,.239),'LipLower':(0,-.124,.225),
                       'NoseTip':(0,-.159,.270),
                       'TongueBase':(0,-.025,.211),'TongueMiddle':(0,-.065,.211),
                       'TongueTip':(0,-.102,.212)}.items():
        landmarks[name]=tuple(fit([point])[0])
    c['continuous_head_landmarks']=landmarks
    c['continuous_head_eye_audit']=eye_audit
    # Subdivide the optical geometry BEFORE projecting onto the shell. A later
    # Catmull-Clark pass could shrink the fitted iris below the opaque cornea.
    for name,obj in reference.items():
        if obj is head:continue
        obj.modifiers.clear();bpy.context.view_layer.objects.active=obj
        optical_subdivision=obj.modifiers.new('Smooth optical surface before fit','SUBSURF')
        optical_subdivision.levels=1
        bpy.ops.object.modifier_apply(modifier=optical_subdivision.name)
    points={name:np.asarray([tuple(source_head_inverse@matrices[name]@v.co) for v in obj.data.vertices],dtype=float)
            for name,obj in reference.items()}
    for side in ['L','R']:
        shell_name='GEO-head_animation_realistic.sclera.'+side
        iris_name='GEO-head_animation_realistic.iris.'+side
        shell=reference[shell_name]
        surface=BVHTree.FromPolygons([Vector(p) for p in points[shell_name]],
                                     [tuple(p.vertices) for p in shell.data.polygons])
        iris_points=points[iris_name].copy();original_iris=iris_points.copy()
        iris_relief=np.clip((original_iris[:,1]-np.median(original_iris[:,1]))*.025,-.000015,.000015)
        for point,relief in zip(iris_points,iris_relief):
            hit,normal,index,distance=surface.ray_cast(Vector((point[0],-.5,point[2])),Vector((0,1,0)))
            if hit is None:raise RuntimeError('Source iris outside ocular shell: '+side)
            point[1]=hit.y-.00010+relief
        points[iris_name]=iris_points
        eye_audit[side]['opaqueIrisProjection']={'clearanceMeters':.00010,
            'maximumForwardAdjustmentMeters':float(np.max(original_iris[:,1]-iris_points[:,1])),
            'preservedFoldReliefLimitMeters':.000015,
            'note':'Opaque runtime iris/pupil lies on curved ocular shell; original CC0 iris is behind a clear corneal surface.'}
    eye_surfaces={}
    for side in ['L','R']:
        name='GEO-head_animation_realistic.sclera.'+side
        center=np.asarray(tuple(source_head_inverse@matrices[name].translation))
        eye_surfaces[side]={'center':center.tolist(),'radius':float(np.quantile(np.linalg.norm(points[name]-center,axis=1),.90))}
    head['krag_reference_eye_surfaces']=json.dumps(eye_surfaces)
    head['krag_fitted_face_landmarks']=json.dumps(landmarks)
    original_face_sets=[v.value for v in head.data.attributes['.sculpt_face_set'].data]
    for name,obj in reference.items():
        obj.parent=None;obj.matrix_world=Matrix.Identity(4)
        obj.modifiers.clear();obj.vertex_groups.clear()
        for collection in list(obj.users_collection):collection.objects.unlink(obj)
        bpy.context.collection.objects.link(obj)
        original=points[name]
        attribute=obj.data.attributes.new('krag_reference_position','FLOAT_VECTOR','POINT')
        attribute.data.foreach_set('vector',original.astype(np.float32).ravel())
        obj.data.vertices.foreach_set('co',fit(original).astype(np.float32).ravel())
        obj.data.materials.clear()
        if obj is head:
            obj.name='Head_Sculpt';c['mark'](obj,'Head','Head')
            obj.data.materials.append(c['face_skin']);obj.data.materials.append(c['dark'])
            # A continuously interpolated field replaces the abrupt polygon
            # material cutoff that created a visible cap on the failed v9 head.
            rx,ry,rz=original.T
            smooth=lambda t: np.clip(t,0,1)**2*(3-2*np.clip(t,0,1))
            region=np.maximum.reduce((smooth((rz-.354)/.048),
                                      .72*smooth((abs(rx)-.050)/.030),
                                      smooth((ry+.020)/.050),
                                      smooth((.190-rz)/.050)))
            attribute=obj.data.attributes.new('Krag_SkinRegion','FLOAT','POINT')
            attribute.data.foreach_set('value',region.astype(np.float32))
            for polygon in obj.data.polygons:
                polygon.material_index=1 if original_face_sets[polygon.index]==7 else 0
            cage=obj.copy();cage.data=obj.data.copy();cage.name='EDITABLE Krag continuous facial cage'
            cage['krag_head_control_cage']=True
            for key in ['module','rig_bone']:
                if key in cage:del cage[key]
            collection=bpy.data.collections.get('Authoring control cages')
            collection.objects.link(cage);cage.hide_render=True;cage.hide_set(True)
            levels=2
        else:
            side=name.rsplit('.',1)[-1];part='iris' if '.iris.' in name else 'sclera'
            obj.name='Continuous reference '+part+' '+side;c['mark'](obj,'Face','Eye_'+side)
            obj.data.materials.append(c['iris'] if part=='iris' else c['eye'])
            obj.data.materials.append(c['dark'])
            if part=='iris':
                # Retain the modeled iris cup and recessed pupil, assigning a
                # dark pupil to its central source-local radial region.
                center=np.asarray(tuple(source_head_inverse@matrices[name].translation))
                if iris_detail:krag_iris_material.coordinates(obj,original,center)
                for polygon in obj.data.polygons:
                    q=original[list(polygon.vertices)].mean(0)-center
                    if np.hypot(q[0],q[2])<.0027:polygon.material_index=1
            levels=0
        for polygon in obj.data.polygons:polygon.use_smooth=True
        bpy.context.view_layer.objects.active=obj
        if levels:
            subdivision=obj.modifiers.new('Continuous facial sculpt surface','SUBSURF');subdivision.levels=levels;subdivision.render_levels=levels
            bpy.ops.object.modifier_apply(modifier=subdivision.name)
        if obj is head:
            raw=np.empty(len(obj.data.vertices)*3,dtype=np.float32)
            obj.data.attributes['krag_reference_position'].data.foreach_get('vector',raw)
            current=np.empty_like(raw);obj.data.vertices.foreach_get('co',current)
            obj.data.vertices.foreach_set('co',sculpt_face(raw.reshape(-1,3),current.reshape(-1,3)).astype(np.float32).ravel())
        obj['anatomical_source']='Blender Studio Human Base Meshes 1.4.1 / animation head and matching ocular topology / CC0'
        obj['anatomical_status']='Unaccepted Krag facial topology adaptation; visual and expression review required'
    # Tusks remain the approved silhouette cue, emerging beside the lower lip.
    for side in [-1,1]:
        anchor=fit([(side*.033,-.122,.228)])[0]
        c['tube']('Lower ivory tusk',[anchor,anchor+np.array((side*.001,-.015,.017)),anchor+np.array((-side*.003,-.016,.034))],
                  [.009,.005,.0005],c['bone'],'Face','Jaw',16)
    interior(c)
    return head


def interior(c):
    """Provisional teeth/gums/tongue fitted to the new mouth in the same space."""
    gum=c['mat']('Krag_OralTissue',(.13,.041,.025),0,.43)
    tongue=c['mat']('Krag_Tongue',(.115,.045,.032),0,.37)
    c['uvball']('Provisional deep oral lining',fit([(0,-.028,.230)])[0],(.105,.114,.084),c['dark'],'MouthInterior','Head',seg=40,rings=24)
    for upper in [True,False]:
        source_z=.241 if upper else .217;bone='Head' if upper else 'Jaw'
        points=fit([(x,-.101+.014*(abs(x)/.038)**2,source_z) for x in [-.038,-.026,-.013,0,.013,.026,.038]])
        c['tube']('Fitted upper gum' if upper else 'Fitted lower gum',points,.009,gum,'MouthInterior',bone,16)
        for i in range(8):
            x=(i-3.5)*.0088;center=fit([(x,-.109+.013*(abs(x)/.035)**2,source_z)])[0]
            center[2]+=-.010 if upper else .009
            c['box'](('Upper' if upper else 'Lower')+' fitted provisional tooth '+str(i),center,(.016,.020,.021 if upper else .018),c['bone'],'MouthInterior',bone,bevel=.0035)
    middle=fit([(0,-.065,.210)])[0];front=fit([(0,-.101,.211)])[0]
    c['uvball']('Fitted tongue body',middle,(.054,.049,.011),tongue,'MouthInterior','Tongue_01',seg=36,rings=20)
    c['uvball']('Fitted tongue front',front,(.040,.030,.010),tongue,'MouthInterior','Tongue_02',seg=32,rings=20)
