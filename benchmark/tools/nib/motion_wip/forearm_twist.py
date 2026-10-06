"""Prepared Nib forearm deformation extension; no runtime contract promotion.

The helper separates axial pronation from captured elbow direction. Existing
bone world bind matrices remain unchanged. Author every new clip against the
resulting skeleton; an old clip that twists LowerArm still has the old fault.
"""
import numpy as np

NAMES=('ForearmTwist_L','ForearmTwist_R')


def smooth(a,b,t):
    v=np.clip((np.asarray(t)-a)/(b-a),0,1)
    return v*v*(3-2*v)


def twist_fraction(points,elbow,wrist):
    """Zero twist at olecranon; gradual axial rotation into the distal radius.

    Fractions are provisional anatomical fitting values, not approved canon.
    Do not drive this field by global Z: the bind forearm is diagonal.
    """
    axis=np.asarray(wrist)-np.asarray(elbow)
    t=(np.asarray(points)-elbow)@axis/(axis@axis)
    return smooth(.12,.90,t)


def twist_weights(points,elbow,wrist):
    """LowerArm (zero), ForearmTwist (half), Hand (full) axial rotation.

    Adjacent roll difference is at most 45 degrees for 90-degree pronation,
    avoiding the 29 percent radius loss of a single zero/full LBS blend.
    Actual posed surfaces still require checking; this is not DQS evidence.
    """
    axis=np.asarray(wrist)-np.asarray(elbow)
    t=(np.asarray(points)-elbow)@axis/(axis@axis)
    proximal=smooth(.10,.48,t);distal=smooth(.48,.94,t)
    return np.column_stack((1-proximal,proximal-distal,distal))


def install(rig):
    import bpy
    from mathutils import Matrix
    before={b.name:b.matrix_local.copy() for b in rig.data.bones}
    if any(name in rig.data.bones for name in NAMES):
        raise RuntimeError('Refusing duplicate forearm-twist extension')
    if any(rig.data.bones['Hand_'+s].parent.name!='LowerArm_'+s for s in ['L','R']):
        raise RuntimeError('Unexpected existing Hand hierarchy')
    bpy.ops.object.select_all(action='DESELECT');rig.hide_set(False);rig.select_set(True)
    bpy.context.view_layer.objects.active=rig;bpy.ops.object.mode_set(mode='EDIT')
    for side in ['L','R']:
        parent=rig.data.edit_bones['LowerArm_'+side]
        bone=rig.data.edit_bones.new('ForearmTwist_'+side)
        bone.head=parent.head.copy();bone.tail=parent.tail.copy();bone.roll=parent.roll
        bone.parent=parent;bone.use_connect=False;bone.use_deform=True
        # Parent reassignment does not move an unconnected edit bone. Writing
        # its matrix again needlessly reconstructs roll and changes float bind.
        hand=rig.data.edit_bones['Hand_'+side]
        hand.use_connect=False;hand.parent=bone
    bpy.ops.object.mode_set(mode='OBJECT')
    maximum=0.;maximum_translation=0.;maximum_angle=0.;bind_differences={}
    for name,matrix in before.items():
        current=rig.data.bones[name].matrix_local
        error=max(abs(a-b) for ra,rb in zip(matrix,current) for a,b in zip(ra,rb))
        translation=(matrix.translation-current.translation).length
        qa=np.asarray(matrix.to_quaternion(),dtype=np.float64);qa/=np.linalg.norm(qa)
        qb=np.asarray(current.to_quaternion(),dtype=np.float64);qb/=np.linalg.norm(qb)
        if qa@qb<0:qb=-qb
        angle=float(np.degrees(4*np.arcsin(min(1.,np.linalg.norm(qa-qb)*.5))))
        maximum=max(maximum,error)
        maximum_translation=max(maximum_translation,translation)
        maximum_angle=max(maximum_angle,angle)
        if error:bind_differences[name]={'maximumMatrixElementDifference':error,'translationDifferenceMeters':translation,'rotationDifferenceDegrees':angle}
        # Blender's edit/data conversion can round untouched float32 frames by
        # one ULP. Preserve the measured differences, rather than call exact
        # byte equality or repeatedly reject invisible representation noise.
        if error>1e-6 or translation>1e-7:
            raise RuntimeError('Twist extension changed global bind: '+name+' maximum matrix element difference '+str(error))
    for name in NAMES:
        rig.pose.bones[name].matrix_basis=Matrix.Identity(4)
        rig.pose.bones[name].rotation_mode='QUATERNION'
    return {'addedBones':list(NAMES),'globalBindMaximumElementError':maximum,
        'globalBindMaximumTranslationErrorMeters':maximum_translation,
        'globalBindMaximumRotationErrorDegrees':maximum_angle,
        'bindDifferences':bind_differences,'bindTolerance':{'matrixElements':1e-6,'translationMeters':1e-7},
        'parentContract':{name:'LowerArm_'+name[-1] for name in NAMES},
        'reparentedHands':{side:'ForearmTwist_'+side for side in ['L','R']},
        'twistAxis':'Blender local +Y; same global elbow-to-wrist rest direction and roll as LowerArm',
        'animationContract':'LowerArm captured swing/flex; ForearmTwist half axial pronation; Hand desired orientation includes full pronation (remaining half local)',
        'requiresFreshMatchingClips':True}


def split_existing_weights(obj,rig):
    """Split LowerArm weight over zero/half/full pronation transforms.

    Other body, facial, hand and digit weights are untouched. This function is
    appropriate for retained forearm wraps and old anatomy diagnostic controls.
    A new anatomical cage receives topology-aware elbow/shoulder weights first.
    """
    transform=rig.matrix_world.inverted()@obj.matrix_world
    p=np.asarray([tuple(transform@v.co) for v in obj.data.vertices],dtype=np.float64)
    original_names={g.index:g.name for g in obj.vertex_groups}
    before=[{original_names[g.group]:float(g.weight) for g in v.groups} for v in obj.data.vertices]
    statistics={}
    for side in ['L','R']:
        name='LowerArm_'+side;target='ForearmTwist_'+side
        group=obj.vertex_groups.get(name)
        if group is None:continue
        if obj.vertex_groups.get(target):raise RuntimeError('Twist weights already exist: '+obj.name)
        b=rig.data.bones[name]
        fraction=twist_weights(p,np.asarray(b.head_local),np.asarray(b.tail_local))
        values=np.asarray([row.get(name,0.) for row in before]);transfer=values[:,None]*fraction
        if transfer[:,1:].max(initial=0)<=1e-9:continue
        twist=obj.vertex_groups.new(name=target)
        hand_name='Hand_'+side;hand=obj.vertex_groups.get(hand_name) or obj.vertex_groups.new(name=hand_name)
        for i,(old,new) in enumerate(zip(values,transfer)):
            if old<=0:continue
            group.add([i],float(new[0]),'REPLACE')
            if new[1]>0:twist.add([i],float(new[1]),'REPLACE')
            if new[2]>0:hand.add([i],float(before[i].get(hand_name,0)+new[2]),'REPLACE')
        statistics[side]={'weightedVertices':int(np.count_nonzero(transfer[:,1:].sum(axis=1)>0)),
            'maximumTwistWeight':float(transfer[:,1].max()),'maximumAddedHandWeight':float(transfer[:,2].max()),
            'halfTwistProgressRange':[.10,.48],'fullTwistProgressRange':[.48,.94]}
    after_names={g.index:g.name for g in obj.vertex_groups};maximum=0.;influences=0
    for vertex,row in zip(obj.data.vertices,before):
        after={after_names[g.group]:float(g.weight) for g in vertex.groups}
        maximum=max(maximum,abs(sum(row.values())-sum(after.values())))
        influences=max(influences,sum(v>1e-7 for v in after.values()))
        for name,value in row.items():
            if not name.startswith(('LowerArm_','Hand_')) and after.get(name,0)!=value:
                raise RuntimeError('Twist split changed unrelated influence')
    if maximum>2e-6 or influences>8:raise RuntimeError('Invalid split forearm weights')
    return {'component':obj.name,'sides':statistics,'weightSumDifference':maximum,'maximumInfluences':influences}
