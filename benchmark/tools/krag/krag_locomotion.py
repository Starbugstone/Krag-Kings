"""Grounded in-place locomotion, with stance velocity matching declared travel speed.
The analytic two-link solver accounts for pelvis settle and keeps ankle targets flat.
"""
import math
from mathutils import Vector, Matrix
from math import sin,cos,pi
CYCLES={
 'Walk':dict(durationSeconds=1.2,speedMetersPerSecond=1.15,stanceFraction=.62,swingClearanceMeters=.075,pelvisDrop=.135),
 'Run':dict(durationSeconds=.6,speedMetersPerSecond=3.2,stanceFraction=.42,swingClearanceMeters=.145,pelvisDrop=.145)}

def manifest():
    return {name:{**{k:v for k,v in c.items() if k!='pelvisDrop'},'cycleSeconds':c['durationSeconds'],'leftContacts':[0.0],'rightContacts':[0.5],'leftFootBone':'Foot_L','rightFootBone':'Foot_R','rootMotion':False,'stanceHalfStrideMeters':c['speedMetersPerSecond']*c['durationSeconds']*c['stanceFraction']/2,'status':'Authored targets; actual mesh/engine contact verification pending'} for name,c in CYCLES.items()}

def point(c,t,side):
    phase=(t+(0 if side=='L' else .5))%1;stance=c['stanceFraction'];reach=c['speedMetersPerSecond']*c['durationSeconds']*stance/2
    if phase<stance:
        u=phase/stance;y=-reach+2*reach*u;z=.240
    else:
        u=(phase-stance)/(1-stance)
        # Cubic Hermite velocity continuity: both ends match backward stance velocity.
        tangent=2*reach*(1-stance)/stance
        y=(2*u**3-3*u**2+1)*reach+(u**3-2*u**2+u)*tangent+(-2*u**3+3*u**2)*(-reach)+(u**3-u**2)*tangent
        z=.240+c['swingClearanceMeters']*sin(pi*u)**1.5
    return Vector(((.19 if side=='L' else -.19),.026+y,z)),phase

def orient(pb,head,tail):
    rest=pb.bone.matrix_local.to_3x3();rest_dir=pb.bone.tail_local-pb.bone.head_local
    q=rest_dir.rotation_difference(tail-head);m=(q.to_matrix()@rest).to_4x4();m.translation=head;pb.matrix=m

def pose(rig,name,t):
    c=CYCLES[name];wave=sin(2*pi*t);settle=-.013*(1-cos(4*pi*t))
    rig.pose.bones['Pelvis'].location.y=-c['pelvisDrop']+settle
    # Front loaded heavy torso: restrained shoulder opposition and planted impact settle.
    rig.pose.bones['Chest'].rotation_euler=(.050 if name=='Walk' else .100,0,.037*wave)
    rig.pose.bones['Spine'].rotation_euler=(.015,0,-.024*wave)
    rig.pose.bones['Head'].rotation_euler=(-.035 if name=='Walk' else -.075,0,-.021*wave)
    rig.id_data.update_tag()
    import bpy
    bpy.context.view_layer.update()
    metrics=[]
    for s,side in [(1,'L'),(-1,'R')]:
        target,phase=point(c,t,side);th=rig.pose.bones['Thigh_'+side];sh=rig.pose.bones['Shin_'+side];foot=rig.pose.bones['Foot_'+side]
        hip=th.head.copy();a=th.bone.length;b=sh.bone.length;axis=target-hip;d=axis.length
        if d>a+b-.002:
            raise ValueError(f'{name} unreachable ankle at {t:.3f} {side}: {d:.4f}>{a+b:.4f}')
        axis.normalize();along=(a*a+d*d-b*b)/(2*d);height=math.sqrt(max(0,a*a-along*along))
        forward=Vector((0,-1,0));forward=(forward-axis*forward.dot(axis)).normalized();knee=hip+axis*along+forward*height
        orient(th,hip,knee);bpy.context.view_layer.update();orient(sh,knee,target);bpy.context.view_layer.update()
        # Preserve neutral sole orientation; no floating/toe swivel during stance.
        fm=foot.bone.matrix_local.copy();fm.translation=target;foot.matrix=fm
        w=sin(phase*2*pi);rig.pose.bones['UpperArm_'+side].rotation_euler=(-w*(.18 if name=='Walk' else .36),0,s*.035)
        rig.pose.bones['LowerArm_'+side].rotation_euler=(-.16- max(0,w)*(.06 if name=='Walk' else .19),0,0)
        bpy.context.view_layer.update();metrics.append(dict(side=side,phase=phase,ankleTarget=list(target),ankleActual=list(foot.head),errorMeters=(foot.head-target).length))
    return metrics
