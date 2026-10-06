"""Rest-aware three-phalange free-hand acting for the isolated anatomy study."""
import math
import bpy
from mathutils import Quaternion,Vector
from humanoid_arms import put_rotation


def apply(rig,clip,phase):
    hand=rig.pose.bones['Hand_L'];delta=hand.matrix.to_quaternion()@hand.bone.matrix_local.to_quaternion().inverted()
    axis=(rig.data.bones['Finger1_0_L'].head_local-rig.data.bones['Finger1_3_L'].head_local).normalized()
    along=hand.bone.tail_local-hand.bone.head_local;along-=axis*along.dot(axis);along.normalize();palm=axis.cross(along).normalized()
    # Numerical values are authoring proposals; actual native fist/contact
    # views, not joint targets, decide whether these poses are usable.
    activity=.52 if clip=='Run' else .08
    if clip=='Melee':activity=.08+.92*math.sin(math.pi*min(1,max(0,phase)))**.65
    if clip=='Hit':activity=.20+.18*math.sin(math.pi*phase)**2
    angles=[12+44*activity,23+58*activity,8+43*activity]
    changed=[]
    for digit in range(4):
        parent=hand.matrix.to_quaternion();total=0.
        first=rig.data.bones[f'Finger1_{digit}_L'];reference=first.tail_local-first.head_local;reference-=axis*reference.dot(axis);reference.normalize()
        for segment,angle in enumerate(angles,1):
            bone=rig.data.bones[f'Finger{segment}_{digit}_L'];direction=bone.tail_local-bone.head_local;direction-=axis*direction.dot(axis);direction.normalize()
            bind=math.atan2(axis.dot(reference.cross(direction)),reference.dot(direction));total+=math.radians(angle+(3-digit)*1.2)
            desired=delta@Quaternion(axis,total-bind)@bone.matrix_local.to_quaternion()
            put_rotation(rig,bone.name,desired,parent);parent=desired;changed.append(bone.name)
    first=rig.data.bones['Thumb1_L'];thumb_axis=(first.tail_local-first.head_local).normalized().cross(palm).normalized()
    parent=hand.matrix.to_quaternion();total=0.
    for segment,angle in enumerate([4+22*activity,8+36*activity],1):
        bone=rig.data.bones[f'Thumb{segment}_L'];total+=math.radians(angle)
        desired=delta@Quaternion(thumb_axis,total)@bone.matrix_local.to_quaternion()
        put_rotation(rig,bone.name,desired,parent);parent=desired;changed.append(bone.name)
    bpy.context.view_layer.update();return changed
