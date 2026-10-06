"""Prepared finite-width alpha sheets; atlas strands supply individual tips.

No thick opaque tube bundles or paired sheets converging to a single triangle.
All roots use actual same-side support; transparent margins stay in UV tile.
"""
import math,sys
from pathlib import Path
import bpy,numpy as np
from mathutils import Vector,Quaternion
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE.parent/'identity_wip'),str(HERE.parent/'v5_wip')]
from fit_card_roots_v3 import smooth
from nib_groom_v5 import avoid_goggles


def emit(name,guides,collection,rig,material,bone,surface):
    points=[];faces=[];uvs=[];normals=[];attachments=[]
    times=[0,.12,.29,.49,.70,.87,1.0];cross=[-1,0,1]
    for index,g in enumerate(guides):
        root=Vector(g['root']);middle=Vector(g['middle']);tip=Vector(g['tip']);direction=Vector(g['normal'])
        skin,normal,support,distance,switch=surface.find_facing(root,direction)
        if distance>.002:raise RuntimeError('Sampled fur root is not on its source skin')
        base=len(points);tile=g['tile']
        for row,t in enumerate(times):
            center=root*(1-t)**2+middle*2*t*(1-t)+tip*t*t
            tangent=(2*(1-t)*(middle-root)+2*t*(tip-middle)).normalized()
            across=tangent.cross(normal)
            if across.length<1e-7:raise RuntimeError('Fur guide has no transverse direction')
            across.normalize();across=Quaternion(tangent,g['rollRadians']*smooth(t/.35))@across
            facing=across.cross(tangent).normalized()
            if facing.dot(normal)<0:facing.negate()
            width=g['halfWidthMeters']*(.78+.22*math.sin(math.pi*t))*(1-(1-g['widthEndFraction'])*t)
            # Root burial is independent of end width. Independent alpha tips
            # terminate naturally instead of being forced into one shared point.
            center+=(skin-root)*(1-smooth(t/.29))
            for u in cross:
                cup=width*.11*(1-u*u)*math.sin(math.pi*t)
                p=center+across*(u*width)+facing*cup
                shade=normal.lerp(facing,smooth(t/.45)*.62).normalized()
                if row==0:
                    q,n,face,dist,side_switch=surface.find_facing(p,direction)
                    if dist>.006:raise RuntimeError('Broad clump root crossed its anatomical boundary')
                    p,depth,opposing=surface.embedded(q,face);shade=n
                    attachments.append({'guide':index,'column':u,'support':surface.origins[face],
                        'distanceMeters':dist,'burialMeters':depth,'opposingClearanceMeters':opposing,'sideSwitch':side_switch})
                if bone=='Head':
                    fitted=avoid_goggles(p)
                    if row==0 and (fitted-p).length>.00005:raise RuntimeError('Clump root crosses goggle lens')
                    p=fitted
                points.append(tuple(p));pad=8/512
                uvs.append(((tile%4+pad+(u+1)*.5*(1-2*pad))/4,(tile//4+pad+t*(1-2*pad))/4))
                normals.append(tuple(shade))
        for row in range(len(times)-1):
            for col in range(2):
                a=base+row*3+col;faces.append((a,a+1,a+4,a+3))
    mesh=bpy.data.meshes.new(name+' finite alpha surface');mesh.from_pydata(points,[],faces);mesh.update()
    layer=mesh.uv_layers.new(name='UVMap')
    for loop in mesh.loops:layer.data[loop.index].uv=uvs[loop.vertex_index]
    for poly in mesh.polygons:poly.use_smooth=True
    mesh.normals_split_custom_set([normals[l.vertex_index]for l in mesh.loops]);mesh.materials.append(material)
    obj=bpy.data.objects.new(name,mesh);collection.objects.link(obj);obj.parent=rig
    obj.vertex_groups.new(name=bone).add(list(range(len(points))),1,'REPLACE')
    mod=obj.modifiers.new('Nib deformation','ARMATURE');mod.object=rig;mod.use_deform_preserve_volume=False
    obj['variant']='all';obj['bone']=bone;obj['fur_cards']=len(guides);obj['fur_guides']=len(guides)
    obj['fur_design']='Finite transparent ends; layered undercoat/guard locks; no shared pointed tip or opaque bundle'
    return obj,{'guides':len(guides),'cards':len(guides),'verticesPerCard':21,'trianglesPerCard':24,
                'rootCorners':attachments,'retainedAtlas':'4x4 fine-strands-v1; threshold .45; double-sided; OpenGL +Y'}
