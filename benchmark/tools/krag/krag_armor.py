"""Curved overlapping scrap-steel shoulder cap, fitted to the Krag anatomy.

Provisional reconstruction of sheet 01's rounded layered cap, leather retention
straps, rolled edges and rivets. Actual mesh review is required before acceptance.
"""
import bpy, math
from mathutils import Vector


def build(c):
    mesh,tube,ball=c['mesh'],c['tube'],c['uvball']
    paint,steel,brass,leather=c['paint'],c['steel'],c['brass'],c['leather']
    group,bone='Armor','UpperArm_L'

    def point(phi,theta,lift=0):
        normal=Vector((math.sin(phi),math.cos(phi)*math.cos(theta),math.cos(phi)*math.sin(theta)))
        location=Vector((.351+.218*math.sin(phi),.010+.198*math.cos(phi)*math.cos(theta),1.594+.215*math.cos(phi)*math.sin(theta)))
        return location+normal*lift

    def surface(name,start,end,offset,material):
        vs=[];faces=[];nx=23;ny=49
        for i in range(nx):
            t=i/(nx-1);phi=start+(end-start)*t
            for j in range(ny):
                theta=-.13+(math.pi+.26)*j/(ny-1)
                hammer=.0017*math.sin(theta*5.3+phi)*math.sin(t*math.pi)
                vs.append(point(phi,theta,offset+hammer))
        for i in range(nx-1):
            for j in range(ny-1):
                k=i*ny+j;faces.append((k,k+ny,k+ny+1,k+1))
        obj=mesh(name,vs,faces,material,group,bone)
        bpy.context.view_layer.objects.active=obj
        solid=obj.modifiers.new('Forged overlapping steel thickness','SOLIDIFY');solid.thickness=.007;bpy.ops.object.modifier_apply(modifier=solid.name)
        bevel=obj.modifiers.new('Worn forged plate edges','BEVEL');bevel.width=.0022;bevel.segments=3;bpy.ops.object.modifier_apply(modifier=bevel.name)
        return obj

    surface('Rounded structural shoulder shell',-.83,1.33,-.006,steel)
    bands=[('Inner crown',-.83,.07,.012),('Middle crown',-.075,.71,.008),('Outer arm cap',.58,1.33,.004)]
    for name,start,end,lift in bands:
        surface(name,start,end,lift,paint)
        tube(name+' rolled overlap',[point(end,-.13+(math.pi+.26)*j/48,lift+.003) for j in range(49)],.0042,steel,group,bone,10)
        # Rivets follow the local plate curvature, with no floating flat row.
        for theta in [.18,.64,1.12,1.62,2.12,2.61,2.98]:
            phi=end-.07;position=point(phi,theta,lift+.005)
            ball(name+' retaining rivet',position,(.0065,.0065,.0065),brass,group,bone,seg=12,rings=8)
    for theta in [-.13,math.pi+.13]:
        tube('Round cap side rim',[point(-.83+(1.33+.83)*i/48,theta,.007) for i in range(49)],.0045,steel,group,bone,10)
    # Broad leather strips visibly retain the nested shells.
    for theta in [.43,2.73]:
        vs=[];faces=[];steps=37
        for i in range(steps):
            phi=-.89+2.25*i/(steps-1)
            for edge in [-1,1]:vs.append(point(phi,theta+edge*.095,.025))
        for i in range(steps-1):k=2*i;faces.append((k,k+2,k+3,k+1))
        obj=mesh('Pauldron retaining leather strap',vs,faces,leather,group,bone)
        bpy.context.view_layer.objects.active=obj
        solid=obj.modifiers.new('Thick leather retention','SOLIDIFY');solid.thickness=.005;bpy.ops.object.modifier_apply(modifier=solid.name)
        for phi in [-.62,.19,.87]:
            ball('Pauldron strap brass stud',point(phi,theta,.033),(.008,.008,.008),brass,group,bone,seg=12,rings=8)
