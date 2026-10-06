"""Broad continuous draped cloth with unequal folded sections.

This replaces the failed multi-turn gathered strip. It is an authored fabric
surface, not simulated cloth, and must be reviewed for folds/intersections.
"""
import math
import numpy as np
import bpy

def build(c):
    vertices=[];faces=[];length=257;width=49
    # Cloth cross section has broad flat areas separated by narrow folds.
    # It never sweeps closed circles around its width, unlike the failed tubes.
    knots=np.asarray([0,.12,.23,.28,.43,.48,.70,.76,1.])
    radial=np.asarray([0,.08,.30,.18,.48,.29,.78,.55,1.])
    for i in range(length):
        u=i/(length-1);theta=.16+2*math.pi*1.045*u
        front=max(0,-math.sin(theta));back=max(0,math.sin(theta));side=abs(math.cos(theta))
        asym=.012*math.cos(theta+.5)+.007*math.sin(3*theta+.4)
        # Front neckline sags below the measured chin; the rear edge remains
        # high on the nape. A high circular neckline would cover the muzzle.
        upper_z=1.872+.021*back-.125*front+.010*math.cos(theta+.7)
        drop=.110+.040*front+.018*side
        upper_radius=.153+.014*side+.008*front
        spread=.030+.086*front+.020*side
        for j in range(width):
            v=j/(width-1)
            # Change fold heights and widths around the loop; the front is
            # intentionally asymmetrical rather than concentric parallel rings.
            q=v+.041*math.sin(2*theta+.9)*math.sin(math.pi*v)
            q+=.019*math.sin(5*theta+v*4)*math.sin(math.pi*v)
            q=max(0,min(1,q))
            r=upper_radius+spread*float(np.interp(q,knots,radial))
            z=upper_z-drop*q+asym*q
            r+=.007*math.sin(3*theta+4*v)*math.sin(math.pi*v)**2
            z+=.006*math.sin(5*theta-2*v)*math.sin(math.pi*v)
            # Both ends tuck under the armored shoulder. A modest lower-edge
            # sag prevents an exposed vertical flap and retains real thickness.
            end=math.exp(-(u/.055)**2)+math.exp(-((1-u)/.055)**2)
            z-=.018*end*v; r+=.005*end
            vertices.append((r*math.cos(theta),.019+r*math.sin(theta),z))
    for i in range(length-1):
        for j in range(width-1):
            k=i*width+j;faces.append((k,k+width,k+width+1,k+1))
    o=c['mesh']('Broad folded woven scarf',vertices,faces,c['cloth'],'Scarf','Chest')
    bpy.context.view_layer.objects.active=o
    sub=o.modifiers.new('Soft textile fold transitions','SUBSURF');sub.levels=1
    bpy.ops.object.modifier_apply(modifier=sub.name)
    solid=o.modifiers.new('Woven cloth thickness','SOLIDIFY');solid.thickness=.0024
    solid.offset=0;bpy.ops.object.modifier_apply(modifier=solid.name)
    o['construction']='One 1.045-turn broad fabric sheet, uneven open cross-sectional folds and broad flats; not cloth-simulated'
    o['status']='Unaccepted replacement for v9e tubular scarf; actual front/profile/back and pose intersection review required'
    return o
