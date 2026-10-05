"""Continuous torso/shoulder/arm surfaces, keeping restorative loadouts separate."""
import bpy
from mathutils import Vector

def build_continuous_anatomy(g):
    objects=g['OBJECTS'];tube=g['tube'];skin=g['SKIN'];shade=g['shade'];uv=g['uv'];apply=g['apply']
    core=tube('Underlying wiry thorax',[(0,.010,.66),(0,.009,.73),(0,.010,.84),(0,.008,.91),(0,.006,.945),(0,.007,.969),(0,.007,.991)],[(.079,.053),(.082,.058),(.098,.069),(.116,.069),(.119,.063),(.086,.046),(.039,.033)],skin,'BodyAnatomy',sides=40,res=2)
    neck=next(o for o in objects if o.name=='Adult neck')
    left=next(o for o in objects if o.name=='Continuous organic arm L')
    right=next(o for o in objects if o.name=='Continuous organic arm R')
    retained=next(o for o in objects if o.name=='Retained upper arm for replacement')
    for variant,arm in [('organic',left),('grip',retained)]:
        bpy.ops.object.select_all(action='DESELECT');copies=[]
        for src in [core,neck,arm,right]:
            obj=src.copy();obj.data=src.data.copy();g['COL'].objects.link(obj);obj.select_set(True);copies.append(obj)
        bpy.context.view_layer.objects.active=copies[0];bpy.ops.object.join();body=copies[0];body.name='Continuous Nib anatomy '+variant
        remesh=body.modifiers.new('United thorax shoulder elbow anatomy','REMESH');remesh.mode='VOXEL';remesh.voxel_size=.0025;apply(body,remesh)
        smooth=body.modifiers.new('Organic transition relaxation','SMOOTH');smooth.factor=.55;smooth.iterations=5;apply(body,smooth)
        subdiv=body.modifiers.new('Smooth deformation cage','SUBSURF');subdiv.levels=1;apply(body,subdiv)
        body['bone']='BodyAnatomy';body['variant']=variant;objects.append(body);shade(body);uv(body)
    for old in [core,neck,left,right,retained]:
        objects.remove(old);bpy.data.objects.remove(old,do_unlink=True)

def anatomical_weights(point,bones):
    # Skin flows continuously over the shoulder into the arm. Cloth remains separate.
    sign=1 if point.x>=0 else -1;side='L' if sign==1 else 'R'
    upper='UpperArm_'+side;lower='LowerArm_'+side
    elbow=max(0,min(1,(.800-point.z)/.045))
    arm=max(0,min(1,(abs(point.x)-.080)/.060))
    arm=arm*arm*(3-2*arm)
    neck=max(0,min(1,(point.z-.950)/.070))*max(0,1-(abs(point.x)/.060)**2)
    torso={'Neck':neck,'Chest':1-neck}
    if point.z<.87:
        chest=max(0,min(1,(point.z-.73)/.14));torso={'Spine':1-chest,'Chest':chest}
    weights={upper:arm*(1-elbow),lower:arm*elbow}
    for name,value in torso.items():weights[name]=value*(1-arm)
    return weights
