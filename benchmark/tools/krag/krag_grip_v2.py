"""Provisional source-only firearm mount and articulated hand contact targets.

Requires actual neutral/Shoot closeups. This does not patch the pinned v7 asset.
Targets are expressed in the continuous anatomical hand's rest space and then
carried through the current Hand bone, so every body action retains the grip.
"""
import math
import bpy
from mathutils import Vector,Matrix
from krag_locomotion import orient

def mount(context):
    bpy.context.view_layer.update()
    landmarks=context['krag_anatomy'].hand_landmarks('R')
    knuckles=[Vector(landmarks['Finger_'+str(j)][0]) for j in range(4)]
    row=knuckles[-1]-knuckles[0];row.z=0;row.normalize()
    normal=Vector((-row.y,row.x,0))
    center=sum(knuckles,Vector())/4+normal*.055+Vector((0,0,.008))
    handle=bpy.data.objects['Hand cannon wooden grip']
    original_center=handle.matrix_world.translation.copy()
    old_axis=(handle.matrix_world.to_3x3()@Vector((0,0,1))).normalized()
    rotation=old_axis.rotation_difference(row).to_matrix().to_4x4()
    transform=Matrix.Translation(center)@rotation@Matrix.Translation(-original_center)
    length=(knuckles[-1]-knuckles[0]).length+.020
    attachment_shift=row*((length-.117)/2)
    for obj in bpy.data.objects:
        if obj.type=='MESH' and obj.get('module')=='Weapon_R':
            obj.matrix_world=transform@obj.matrix_world
            if obj!=handle:obj.matrix_world=Matrix.Translation(attachment_shift)@obj.matrix_world
    for vertex in handle.data.vertices:
        vertex.co.x*=.72;vertex.co.y*=.64;vertex.co.z*=length/.117
    shift=context['WEAPON_REST_SHIFT']
    muzzle=transform@(Vector((-.450,-.048,.567))+shift)+attachment_shift
    aim=transform@(Vector((-.450,-.048,.467))+shift)+attachment_shift
    return {'center':list(center),'rowAxis':list(row),'palmNormal':list(normal),
        'handleLengthMeters':length,'handleCrossSectionMeters':[.090*.72,.066*.64],
        'muzzle':list(muzzle),'aim':list(aim),
        'status':'Anatomical contact proposal; posed mesh/hand/weapon review required'}

def solve_chain(first,second,target,pole):
    start=first.head.copy();axis=target-start;distance=axis.length
    a,b=first.bone.length,second.bone.length
    if not abs(a-b)+1e-5<distance<a+b-1e-5:raise ValueError('Unreachable grip target '+first.name)
    axis.normalize();along=(a*a+distance*distance-b*b)/(2*distance)
    height=math.sqrt(max(0,a*a-along*along))
    bend=pole-axis*pole.dot(axis)
    if bend.length<1e-6:raise ValueError('Degenerate grip bend plane')
    bend.normalize();joint=start+axis*along+bend*height
    orient(first,start,joint);bpy.context.view_layer.update()
    orient(second,joint,target);bpy.context.view_layer.update()
    error=(second.tail-target).length
    if error>2e-5:raise AssertionError('Finger endpoint missed grip target '+first.name)
    return error

def pose(rig,spec,left_fist=False):
    bpy.context.view_layer.update();hand=rig.pose.bones['Hand_R']
    delta=hand.matrix@hand.bone.matrix_local.inverted()
    center=Vector(spec['center']);row=Vector(spec['rowAxis']);normal=Vector(spec['palmNormal'])
    errors=[]
    for j in range(4):
        first=rig.pose.bones['Finger1_'+str(j)+'_R'];second=rig.pose.bones['Finger2_'+str(j)+'_R']
        rest=first.bone.head_local
        target=center+row*(rest-center).dot(row)+normal*.053+Vector((0,0,-.005))
        errors.append(solve_chain(first,second,delta@target,delta.to_3x3()@Vector((0,0,-1))))
    target=center+normal*.050+row*.025+Vector((0,0,.038))
    errors.append(solve_chain(rig.pose.bones['Thumb1_R'],rig.pose.bones['Thumb2_R'],
        delta@target,delta.to_3x3()@Vector((0,0,1))))
    if left_fist:
        hand=rig.pose.bones['Hand_L'];delta=hand.matrix@hand.bone.matrix_local.inverted()
        for j in range(4):
            first=rig.pose.bones['Finger1_'+str(j)+'_L'];second=rig.pose.bones['Finger2_'+str(j)+'_L']
            target=first.bone.head_local+Vector((-.052,0,.017))
            errors.append(solve_chain(first,second,delta@target,delta.to_3x3()@Vector((0,0,-1))))
    return {'maximumFingerEndpointErrorMeters':max(errors),
            'status':'Skeleton target check only; skin contact and intersections require actual pose review'}
