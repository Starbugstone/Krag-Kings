"""Prepared narrow layered cards with directly fitted tapered root corners.

Uses the established4x4 fine-strands atlas and actual same-side skin support.
No image/shader change or transparent sorting is introduced.
"""
import math,random,sys
from pathlib import Path
import bpy,numpy as np
from mathutils import Vector,Quaternion
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE.parent/'identity_wip'),str(HERE.parent/'v5_wip')]
from nib_groom_v5 import avoid_goggles
from fit_card_roots_v3 import smooth


def emit(name,guides,collection,rig,material,bone,surface):
    points=[];faces=[];uvs=[];normals=[];root_records=[];cards=0
    times=[0,.16,.34,.56,.79]
    for number,guide in enumerate(guides):
        root=Vector(guide['root']);mid=Vector(guide['middle']);tip=Vector(guide['tip']);guide_normal=Vector(guide['normal'])
        skin,normal,support,distance,switch=surface.find_facing(root,guide_normal)
        if distance>.002:raise RuntimeError('New guide root left sampled surface')
        rng=random.Random(guide['seed']+1833)
        for layer,sign in enumerate([-1,1]):
            base=len(points);angle=sign*rng.uniform(.13,.24);tile=(guide['seed']+layer*7)%12
            # Unequal tips prevent paired cards reading as identical cut strips.
            length=rng.uniform(.91,1.05);layer_tip=root+(tip-root)*length
            def uv(u,v):
                pad=8/512;return ((tile%4+pad+u*(1-2*pad))/4,(tile//4+pad+v*(1-2*pad))/4)
            for row,t in enumerate(times):
                center=root*(1-t)**2+mid*(2*t*(1-t))+layer_tip*t*t
                tangent=(2*(1-t)*(mid-root)+2*t*(layer_tip-mid)).normalized()
                across=tangent.cross(normal)
                if across.length<1e-6:raise RuntimeError('Narrow card guide is normal to skin')
                across.normalize();across=Quaternion(tangent,angle*smooth(t/.45))@across
                # A narrow emerging root opens smoothly into the clump body;
                # old cards began at72% width with a conspicuous straight band.
                width=guide['halfWidthMeters']*(.18+.95*math.sin(t*math.pi)**.8)*(1-t)**.42
                center+=(skin-root)*(1-smooth(t/.34))
                for side,u in [(-1,0),(1,1)]:
                    point=center+across*(width*side);shading=normal.lerp(across.cross(tangent).normalized(),.30).normalized()
                    if row==0:
                        support_point,corner_normal,face,corner_distance,corner_switch=surface.find_facing(point,guide_normal)
                        if corner_distance>.002:raise RuntimeError('Narrow card root corner lost its local skin')
                        point,burial,opposing=surface.embedded(support_point,face)
                        if bone=='Head' and (avoid_goggles(point)-point).length>.00005:raise RuntimeError('New root crosses actual lens envelope')
                        shading=corner_normal
                        root_records.append({'guide':number,'layer':layer,'corner':side,'support':surface.origins[face],
                            'burialMeters':burial,'opposingClearanceMeters':opposing,'surfaceDistanceMeters':corner_distance,
                            'sameSideSwitch':corner_switch})
                    elif bone=='Head':point=avoid_goggles(point)
                    points.append(tuple(point));uvs.append(uv(u,t));normals.append(tuple(shading))
            point=avoid_goggles(layer_tip)if bone=='Head'else layer_tip
            end=len(points);points.append(tuple(point));uvs.append(uv(.5,1));normals.append(normals[-1])
            for row in range(len(times)-1):
                a=base+row*2;faces.append((a,a+1,a+3,a+2))
            faces.append((base+8,base+9,end));cards+=1
    mesh=bpy.data.meshes.new(name+' regional cards');mesh.from_pydata(points,[],faces);mesh.update()
    atlas=mesh.uv_layers.new(name='UVMap')
    for loop in mesh.loops:atlas.data[loop.index].uv=uvs[loop.vertex_index]
    for polygon in mesh.polygons:polygon.use_smooth=True
    mesh.normals_split_custom_set([normals[l.vertex_index]for l in mesh.loops]);mesh.materials.append(material)
    obj=bpy.data.objects.new(name,mesh);collection.objects.link(obj);obj.parent=rig
    obj.vertex_groups.new(name=bone).add(list(range(len(points))),1,'REPLACE')
    modifier=obj.modifiers.new('Nib deformation','ARMATURE');modifier.object=rig;modifier.use_deform_preserve_volume=False
    obj['variant']='all';obj['bone']=bone;obj['fur_cards']=cards;obj['fur_guides']=len(guides)
    obj['fur_design']='Narrow staggered curved clumps; actual same-side buried roots; established masked fine-strands atlas'
    return obj,{'guides':len(guides),'cards':cards,'rootCorners':root_records,'rootWidthFactor':.18,'layerAngleRadiansRange':[.13,.24],
                'pointAndAtlasLayout':'Two11-point cards per guide, nine triangles each, existing4x4 tiles/padding'}
