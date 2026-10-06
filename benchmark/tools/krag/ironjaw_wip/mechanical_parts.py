"""Editable forged-jaw geometry; dimensions in world metres, no rig mutation."""
import math
import bpy
from mathutils import Vector


class Parts:
    def __init__(self, rig):
        self.rig = rig
        self.objects = []

    def finish(self, obj, name, material, bone, bevel=0):
        obj.name = 'IronJaw ' + name
        obj['module'] = 'IronJaw_Mechanism'
        obj['component'] = name
        if material:
            obj.data.materials.clear()
            obj.data.materials.append(material)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
        if bevel:
            mod = obj.modifiers.new('Forged edge radii', 'BEVEL')
            mod.width = bevel
            mod.segments = 3
            bpy.ops.object.modifier_apply(modifier=mod.name)
        for polygon in obj.data.polygons:
            polygon.use_smooth = True
        group = obj.vertex_groups.new(name=bone)
        group.add(list(range(len(obj.data.vertices))), 1., 'REPLACE')
        mod = obj.modifiers.new('Krag skeleton', 'ARMATURE')
        mod.object = self.rig
        self.objects.append(obj)
        return obj

    def mesh(self, name, points, faces, material, bone='Jaw', bevel=0):
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(points, [], faces)
        mesh.update()
        obj = bpy.data.objects.new(name, mesh)
        bpy.context.collection.objects.link(obj)
        return self.finish(obj, name, material, bone, bevel)

    def cylinder(self, name, start, end, radius, material, bone='Jaw', vertices=48):
        a, b = Vector(start), Vector(end)
        bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius,
                                           depth=(b-a).length, location=(a+b)*.5)
        obj = bpy.context.object
        obj.rotation_euler = (b-a).to_track_quat('Z', 'Y').to_euler()
        return self.finish(obj, name, material, bone, .0008)

    def box(self, name, center, dimensions, material, bone='Jaw', bevel=.001):
        bpy.ops.mesh.primitive_cube_add(size=1, location=center)
        obj = bpy.context.object
        obj.dimensions = dimensions
        return self.finish(obj, name, material, bone, bevel)

    def rail(self, name, points, radius, material, bone='Jaw', sides=12):
        verts = []
        for i, raw in enumerate(points):
            p = Vector(raw)
            tangent = Vector(points[min(len(points)-1, i+1)])-Vector(points[max(0, i-1)])
            tangent.normalize()
            side = tangent.cross(Vector((0, 0, 1)))
            if side.length < .1:
                side = tangent.cross(Vector((0, 1, 0)))
            side.normalize()
            up = tangent.cross(side).normalized()
            for j in range(sides):
                angle = 2*math.pi*j/sides
                verts.append(p+radius*(math.cos(angle)*side+math.sin(angle)*up))
        faces = []
        for i in range(len(points)-1):
            for j in range(sides):
                faces.append((i*sides+j, i*sides+(j+1)%sides,
                              (i+1)*sides+(j+1)%sides, (i+1)*sides+j))
        faces += [tuple(reversed(range(sides))),
                  tuple((len(points)-1)*sides+j for j in range(sides))]
        return self.mesh(name, verts, faces, material, bone)

    def plate(self, name, outline, depth, material, bone='Jaw'):
        # Outline lies in a shaped XY/Z plane; extrusion follows its plane normal.
        pts = [Vector(point) for point in outline]
        normal = (pts[1]-pts[0]).cross(pts[2]-pts[0]).normalized()
        n = len(pts)
        verts = [p+normal*depth*.5 for p in pts]+[p-normal*depth*.5 for p in pts]
        faces = [tuple(range(n)), tuple(reversed(range(n, n*2)))]
        faces += [(i, (i+1)%n, (i+1)%n+n, i+n) for i in range(n)]
        return self.mesh(name, verts, faces, material, bone, .0014)

    def tusk(self, name, root, bend, tip, material):
        a, b, c = Vector(root), Vector(bend), Vector(tip)
        points, sides, rings = [], 20, 17
        for i in range(rings):
            t = i/(rings-1)
            center = (1-t)**2*a+2*(1-t)*t*b+t*t*c
            tangent = (2*(1-t)*(b-a)+2*t*(c-b)).normalized()
            side = tangent.cross(Vector((1, 0, 0))).normalized()
            other = tangent.cross(side).normalized()
            radius = .0085*(1-t)**.7+.00015
            for j in range(sides):
                angle = 2*math.pi*j/sides
                points.append(center+radius*(math.cos(angle)*side+math.sin(angle)*other))
        faces = []
        for i in range(rings-1):
            for j in range(sides):
                faces.append((i*sides+j, i*sides+(j+1)%sides,
                              (i+1)*sides+(j+1)%sides, (i+1)*sides+j))
        faces += [tuple(reversed(range(sides))), tuple((rings-1)*sides+j for j in range(sides))]
        return self.mesh(name, points, faces, material)


def material(name, color, metallic, roughness):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bs = next(node for node in nodes if node.type == 'BSDF_PRINCIPLED')
    bs.inputs['Base Color'].default_value = (*color, 1)
    bs.inputs['Metallic'].default_value = metallic
    bs.inputs['Roughness'].default_value = roughness
    # Fine pitting, not millimetre-scale normal noise or arbitrary paint blotches.
    noise = nodes.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value = 460
    noise.inputs['Detail'].default_value = 2
    tex = nodes.new('ShaderNodeTexCoord')
    links.new(tex.outputs['Object'], noise.inputs['Vector'])
    bump = nodes.new('ShaderNodeBump')
    bump.inputs['Distance'].default_value = .000055
    bump.inputs['Strength'].default_value = .22
    links.new(noise.outputs['Fac'], bump.inputs['Height'])
    links.new(bump.outputs['Normal'], bs.inputs['Normal'])
    return mat
