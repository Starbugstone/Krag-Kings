"""Provisional continuous Krag face adapted from the official CC0 animation head.

This preserves the reference eye, lip, nose, cheek and jaw loops. It is an
unaccepted anatomy pass; source proportions are fitted toward concept sheet 01.
Coordinates returned here precede the common Krag head proportion transform.
"""
import bpy,json
import numpy as np
from mathutils import Matrix


def fit(points):
    x,y,z=np.asarray(points,dtype=float).T
    front=np.clip((-y-.005)/.065,0,1)
    gaussian=lambda value,center,width:np.exp(-((value-center)/width)**2)
    target_z=np.interp(z,[.02,.13,.18,.222,.234,.268,.3100375,.337,.436],
                         [1.60,1.733,1.775,1.829,1.845,1.916,1.964,1.995,2.107])
    width=np.interp(z,[.02,.13,.18,.222,.268,.3100375,.337,.38,.436],
                      [1.45,1.65,2.22,2.23,2.04,1.98,1.98,1.94,1.86])
    target_x=x*width
    target_y=y*1.40+.013
    # Broad projecting mandible and muzzle, with a low, flattened nasal bridge.
    mouth=gaussian(x,0,.060)*gaussian(z,.232,.030)*front
    chin=gaussian(x,0,.066)*gaussian(z,.183,.026)*front
    target_y-=.037*mouth+.039*chin
    target_x*=1+.10*mouth
    target_z-=.008*(np.clip(abs(x)/.053,0,1)**1.5)*mouth
    nose=gaussian(x,0,.030)*gaussian(z,.271,.030)*front
    target_x*=1+.25*nose
    target_y+=.011*gaussian(x,0,.026)*gaussian(z,.295,.021)*front
    # The same transformation is applied to the complete eye assemblies, so
    # lids and globes share their fitting field instead of being placed by eye.
    ocular=gaussian(abs(x),.0358764,.026)*gaussian(z,.3100375,.024)*front
    target_y-=.0165*ocular
    target_z-=(z-.3100375)*.38*ocular
    target_x-=np.sign(x)*(abs(x)-.0358764)*.16*ocular
    brow=gaussian(abs(x),.033,.030)*gaussian(z,.334,.014)*front
    target_y-=.026*brow
    target_z-=.008*gaussian(abs(x),.018,.022)*brow
    # Flatter cheek planes, with the uninterrupted nasolabial surface retained.
    cheek=gaussian(abs(x),.057,.022)*gaussian(z,.276,.030)*front
    target_y+=.006*cheek
    target_x+=np.sign(x)*.005*cheek
    # Small rounded Krag ears retain the source auricle topology. Compress only
    # the outer lateral region rather than adding disconnected ear primitives.
    auricle=np.clip((abs(x)-.068)/.019,0,1)*np.clip((y+.056)/.025,0,1)
    auricle*=gaussian(z,.289,.049)
    target_x=target_x*(1-auricle)+np.sign(x)*(.139+(abs(x)-.068)*.80)*auricle
    return np.column_stack((target_x,target_y,target_z))


def build(c):
    source=c['ROOT']/'benchmark/art/reference-anatomy/blender-studio-human-base-meshes/source/human-base-meshes-bundle-v1.4.1/human_base_meshes_bundle.blend'
    names=['GEO-head_animation_realistic']
    names += ['GEO-head_animation_realistic.'+part+'.'+side for part in ['iris','sclera'] for side in ['L','R']]
    with bpy.data.libraries.load(str(source),link=False) as (available,loaded):
        loaded.objects=names
    reference={o.name:o for o in loaded.objects}
    head=reference['GEO-head_animation_realistic']
    # Cache all source transforms BEFORE moving the head or clearing eye parents.
    # The library's eyes are parented to its head and inherit those transforms.
    matrices={name:obj.matrix_world.copy() for name,obj in reference.items()}
    source_head_inverse=matrices[head.name].inverted()
    landmarks={}
    for side,sign in [('L',1),('R',-1)]:
        eye_name='GEO-head_animation_realistic.sclera.'+side
        source_center=source_head_inverse@matrices[eye_name].translation
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
    points={name:np.asarray([tuple(source_head_inverse@matrices[name]@v.co) for v in obj.data.vertices],dtype=float)
            for name,obj in reference.items()}
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
            obj.data.materials.append(c['face_skin']);obj.data.materials.append(c['skin']);obj.data.materials.append(c['dark'])
            for polygon in obj.data.polygons:
                raw=original[list(polygon.vertices)].mean(0)
                polygon.material_index=2 if original_face_sets[polygon.index]==7 else (1 if raw[2]>.366 or raw[1]>.015 else 0)
            cage=obj.copy();cage.data=obj.data.copy();cage.name='EDITABLE Krag continuous facial cage'
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
                for polygon in obj.data.polygons:
                    q=original[list(polygon.vertices)].mean(0)-center
                    if np.hypot(q[0],q[2])<.0027:polygon.material_index=1
            levels=1
        for polygon in obj.data.polygons:polygon.use_smooth=True
        bpy.context.view_layer.objects.active=obj
        subdivision=obj.modifiers.new('Continuous facial sculpt surface','SUBSURF');subdivision.levels=levels;subdivision.render_levels=levels
        bpy.ops.object.modifier_apply(modifier=subdivision.name)
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
