"""Prepared curved masked-card geometry, not generated or integrated yet."""
import math,sys
from pathlib import Path
import bpy
from mathutils import Vector,Quaternion
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'v5_wip'))
from nib_groom_v5 import avoid_goggles

def emit_cards(name,guides,collection,rig,material,bone):
    vertices=[];faces=[];uvs=[];point_normals=[];card_count=0
    for guide in guides:
        root=Vector(guide['root']);mid=Vector(guide['middle']);tip=Vector(guide['tip']);normal=Vector(guide['normal'])
        short=guide['shortNap'];segments=3 if short else 5
        for layer,angle in enumerate([0] if short else [-.40,.40]):
            base=len(vertices);tile=12+guide['seed']%4 if short else (guide['seed']+layer*7)%12
            def atlas(u,v):
                # Each 512px tile reserves 8px padding on all sides.
                pad=8/512;u=pad+u*(1-2*pad);v=pad+v*(1-2*pad)
                return ((tile%4+u)/4,(tile//4+v)/4)
            for j in range(segments):
                t=j/segments;center=root*(1-t)**2+mid*(2*t*(1-t))+tip*t*t
                if bone=='Head':center=avoid_goggles(center)
                tangent=(2*(1-t)*(mid-root)+2*t*(tip-mid)).normalized()
                across=tangent.cross(normal)
                if across.length<1e-6:across=tangent.cross(Vector((1,0,0)))
                if across.length<1e-6:across=tangent.cross(Vector((0,1,0)))
                across.normalize();across=Quaternion(tangent,angle)@across
                width=guide['halfWidthMeters']*(.72+.38*math.sin(t*math.pi))*(1-t)**.35
                shading=normal.lerp(across.cross(tangent).normalized(),.35).normalized()
                for sign,u in [(-1,0),(1,1)]:
                    point=center+across*(width*sign)
                    if bone=='Head':point=avoid_goggles(point)
                    vertices.append(tuple(point));uvs.append(atlas(u,t));point_normals.append(tuple(shading))
            end=len(vertices);vertices.append(tuple(avoid_goggles(tip) if bone=='Head' else tip));uvs.append(atlas(.5,1));point_normals.append(point_normals[-1])
            for j in range(segments-1):
                a=base+j*2;faces.append((a,a+1,a+3,a+2))
            faces.append((base+(segments-1)*2,base+(segments-1)*2+1,end));card_count+=1
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(vertices,[],faces);mesh.update()
    layer=mesh.uv_layers.new(name='UVMap')
    for loop in mesh.loops:layer.data[loop.index].uv=uvs[loop.vertex_index]
    for polygon in mesh.polygons:polygon.use_smooth=True
    mesh.normals_split_custom_set([point_normals[loop.vertex_index] for loop in mesh.loops])
    mesh.materials.append(material);obj=bpy.data.objects.new(name,mesh);collection.objects.link(obj)
    obj.parent=rig;group=obj.vertex_groups.new(name=bone);group.add(list(range(len(vertices))),1,'REPLACE')
    modifier=obj.modifiers.new('Nib deformation','ARMATURE');modifier.object=rig
    obj['variant']='all';obj['bone']=bone;obj['fur_cards']=card_count;obj['fur_guides']=len(guides)
    obj['fur_design']='Provisional curved masked clumps; independent fine opaque accents; no simulation'
    return obj,{'cards':card_count,'triangles':sum(len(p.vertices)-2 for p in mesh.polygons),
                'vertices':len(vertices),'material':material.name,'bone':bone,
                'status':'Actual created geometry still requires zero-area/UV/normal and rendered validation'}
