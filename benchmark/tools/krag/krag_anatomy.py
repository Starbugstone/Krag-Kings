"""Continuous anatomical cage adapted to the approved Krag proportions.

Source: Blender Studio Human Base Meshes 1.4.1, body_male_realistic.
The official bundle README declares the included base meshes CC0. The complete
original bundle, README, and conflicting unrelated Rain Rig text are preserved
under art/reference-anatomy; see art/krag/anatomy-study/library-inventory.json.
This is a provisional adapted Krag sculpt, not approved final character art.
"""
import bpy, hashlib
import numpy as np
from anatomy_warp_study import warp


def build(context):
    root=context['ROOT']
    source=root/'benchmark/art/reference-anatomy/blender-studio-human-base-meshes/source/human-base-meshes-bundle-v1.4.1/human_base_meshes_bundle.blend'
    with bpy.data.libraries.load(str(source),link=False) as (available,loaded):
        assert 'GEO-body_male_realistic' in available.objects
        loaded.objects=['GEO-body_male_realistic']
    reference=loaded.objects[0]
    original=reference.data
    raw=np.asarray([tuple(v.co) for v in original.vertices],dtype=float)
    # The exposed torso and both complete arms remain one connected surface.
    # Covered pelvis/legs and the human head are explicitly excluded.
    keep=(raw[:,2]<1.445)&((raw[:,2]>.945)|((np.abs(raw[:,0])>.240)&(raw[:,2]>.70)))
    faces=[list(face.vertices) for face in original.polygons if all(keep[i] for i in face.vertices)]
    used=sorted({i for face in faces for i in face});index={old:new for new,old in enumerate(used)}
    vertices=warp(raw[used]);polygons=[[index[i] for i in face] for face in faces]
    # The source crop cuts through several sloping neck loops. Extend those
    # boundary vertices into the enclosed skull instead of leaving a visible
    # sawtooth opening underneath the chin. Preserve the shoulder topology.
    from collections import Counter
    edge_uses=Counter(tuple(sorted((a,b))) for face in polygons for a,b in zip(face,face[1:]+face[:1]))
    neck_boundary={i for edge,count in edge_uses.items() if count==1 for i in edge if vertices[i,2]>1.70}
    for i in neck_boundary:
        vertices[i,2]=1.840
    collar=np.clip((vertices[:,2]-1.68)/.17,0,1)
    collar*=np.clip((.24-np.abs(vertices[:,0]))/.09,0,1)
    vertices[:,0]*=1+.11*collar
    vertices[:,1]=.016+(vertices[:,1]-.016)*(1+.10*collar)
    mesh=bpy.data.meshes.new('Krag continuous anatomical control cage')
    mesh.from_pydata(vertices,[],polygons);mesh.update()
    mesh.materials.append(context['skin'])
    for face in mesh.polygons:face.use_smooth=True
    obj=bpy.data.objects.new('Krag adapted anatomical sculpt',mesh)
    bpy.context.collection.objects.link(obj);context['mark'](obj,'Body')
    obj['anatomical_source']='Blender Studio Human Base Meshes 1.4.1 / GEO-body_male_realistic / CC0'
    obj['anatomical_source_sha256']=hashlib.sha256(source.read_bytes()).hexdigest()
    obj['anatomical_status']='Provisional adaptation: retained connected torso/arm/hand topology; fixed Krag body proportions; no human head'
    # Preserve the editable low-resolution cage independently of evaluated skin.
    cage=obj.copy();cage.data=obj.data.copy();cage.name='EDITABLE Krag anatomical control cage'
    for key in ['module','rig_bone']:
        if key in cage:del cage[key]
    collection=bpy.data.collections.get('Authoring control cages') or bpy.data.collections.new('Authoring control cages')
    if collection.name not in bpy.context.scene.collection.children:bpy.context.scene.collection.children.link(collection)
    collection.objects.link(cage);cage.hide_render=True;cage.hide_set(True)
    bpy.context.view_layer.objects.active=obj;obj.select_set(True)
    subdivision=obj.modifiers.new('Cinematic anatomical surface','SUBSURF');subdivision.levels=3;subdivision.render_levels=3
    bpy.ops.object.modifier_apply(modifier=subdivision.name)
    bpy.data.objects.remove(reference,do_unlink=True)
    if original.users==0:bpy.data.meshes.remove(original)
    return obj


def smooth_segment_weights(point,bones,candidates):
    """Continuous field over each anatomical chain, avoiding nearest-two seams.

    A smooth compact taper eliminates a bone only after its influence has
    reached zero. All candidates in the short chain participate; skinning does
    not abruptly exchange a second-nearest bone across a surface edge.
    """
    distances=[]
    for name in candidates:
        a,b=bones[name];axis=b-a;t=max(0,min(1,(point-a).dot(axis)/axis.length_squared))
        distances.append((point-(a+t*axis)).length)
    minimum=min(distances)
    weights=[]
    for name,distance in zip(candidates,distances):
        ratio=distance/max(.015,minimum)
        taper=max(0,min(1,(2.8-ratio)/.8));taper=taper*taper*(3-2*taper)
        value=taper/max(.018,distance)**5
        if value>0:weights.append((name,value))
    total=sum(value for name,value in weights)
    return [(name,value/total) for name,value in weights]


def hand_landmarks(side):
    """Provisional internal joints fitted to the same source cage before warping.

    These must be evaluated on an actual posed hand/grip review. Source fingers
    run along a naturally relaxed palm; no separate primitive digits are added.
    """
    sign=1 if side=='L' else -1
    source={
        'Finger_0':[(.401,-.050,.805),(.423,-.063,.765),(.424,-.063,.729)],
        'Finger_1':[(.401,-.091,.812),(.426,-.105,.756),(.427,-.111,.719)],
        'Finger_2':[(.400,-.121,.809),(.430,-.134,.757),(.432,-.142,.720)],
        'Finger_3':[(.396,-.148,.813),(.421,-.160,.778),(.419,-.165,.744)],
        'Thumb':[(.373,-.110,.867),(.380,-.157,.839),(.389,-.174,.819)],
    }
    return {name:[tuple(point) for point in warp(np.asarray(points)*np.array([sign,1,1]))] for name,points in source.items()}


def anatomical_weights(point,bones):
    """Continuous regional skin weights across the shared torso/arm partitions.

    Joint transitions follow the actual shoulder-elbow-wrist chain. A nearby
    forearm cannot suddenly replace a clavicle as a shoulder's second influence.
    This is provisional authored weighting and requires actual action review.
    """
    def smooth(a,b,value):
        value=max(0,min(1,(value-a)/(b-a)))
        return value*value*(3-2*value)
    def merge(weights,name,value):
        if value>0:weights[name]=weights.get(name,0)+value
    z=point.z;side='L' if point.x>=0 else 'R'
    upper=smooth(1.29,1.46,z);lower=smooth(1.075,1.23,z)
    neck=smooth(1.66,1.79,z)*(1-smooth(.10,.23,abs(point.x)))
    torso={'Pelvis':(1-lower)*(1-neck),'Spine':lower*(1-upper)*(1-neck),'Chest':upper*(1-neck),'Neck':neck}
    shoulder,elbow=bones['UpperArm_'+side];_,wrist=bones['LowerArm_'+side]
    elbow_axis=(shoulder-wrist).normalized()
    forearm=1-smooth(-.065,.065,(point-elbow).dot(elbow_axis))
    wrist_axis=(elbow-wrist).normalized()
    hand=1-smooth(-.035,.055,(point-wrist).dot(wrist_axis))
    collar=(1-smooth(-.025,.100,(point-shoulder).dot((elbow-shoulder).normalized())))*.58
    arm={'Clavicle_'+side:collar*(1-forearm),'UpperArm_'+side:(1-forearm)*(1-collar),'LowerArm_'+side:forearm*(1-hand),'Hand_'+side:forearm*hand}
    digit_names=[name for name in bones if name.startswith(('Finger','Thumb')) and name.endswith('_'+side)]
    if hand>.001 and z<1.02:
        digit_weights=smooth_segment_weights(point,bones,digit_names)
        distances=[]
        for name in digit_names:
            a,b=bones[name];axis=b-a;t=max(0,min(1,(point-a).dot(axis)/axis.length_squared))
            distances.append((point-(a+t*axis)).length)
        digits=(1-smooth(.020,.063,min(distances)))*(1-smooth(.955,1.015,z))
        transferred=arm['Hand_'+side]*digits;arm['Hand_'+side]-=transferred
        for name,value in digit_weights:merge(arm,name,value*transferred)
    arm_fraction=smooth(.235,.359,abs(point.x))
    weights={}
    for name,value in torso.items():merge(weights,name,value*(1-arm_fraction))
    for name,value in arm.items():merge(weights,name,value*arm_fraction)
    return list(weights.items())
