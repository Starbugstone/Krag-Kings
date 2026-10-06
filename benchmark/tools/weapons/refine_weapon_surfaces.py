"""Isolated material-only study of the regular Krag prop; never promotes assets.

Real mesh cavity/curvature response must later be baked on a unique mesh atlas.
The ordinary one-metre material-tile bake cannot preserve these fields.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

p = argparse.ArgumentParser()
p.add_argument('--source', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args(sys.argv[sys.argv.index('--') + 1:])
if a.output.exists():
    raise RuntimeError('Preserve existing studies; choose a fresh output directory')
a.output.mkdir(parents=True)
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
source_hash = sha(a.source)
bpy.ops.wm.open_mainfile(filepath=str(a.source))
bpy.context.view_layer.update()


def mesh_fingerprint(obj):
    payload = {
        'vertices': [list(v.co) for v in obj.data.vertices],
        'faces': [list(f.vertices) for f in obj.data.polygons],
        'materials': [f.material_index for f in obj.data.polygons],
        'uv': [list(v.uv) for v in obj.data.uv_layers.active.data],
        'world': [list(row) for row in obj.matrix_world],
    }
    return hashlib.sha256(json.dumps(payload, separators=(',', ':')).encode()).hexdigest()


meshes = [o for o in bpy.data.objects if o.type == 'MESH']
before = {o.name: mesh_fingerprint(o) for o in meshes}
changed = []
for mat in bpy.data.materials:
    if mat.name not in ['Weapon_BlackenedSteel', 'Weapon_WornSteelEdges',
                        'Weapon_AgedBrass', 'Weapon_WeatheredTeal', 'Weapon_DarkCopper']:
        continue
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bs = nodes.get('Principled BSDF')
    original = {}
    for name in ['Base Color', 'Roughness', 'Metallic', 'Normal']:
        socket = bs.inputs[name]
        original[name] = socket.links[0].from_socket if socket.is_linked else socket.default_value

    def connect(value, socket):
        if hasattr(value, 'is_output'):
            links.new(value, socket)
        else:
            if socket.type == 'RGBA' and isinstance(value, (int, float)):
                value = (value, value, value, 1)
            socket.default_value = value

    def math_node(op, first, second=None):
        n = nodes.new('ShaderNodeMath'); n.operation = op
        connect(first, n.inputs[0])
        if second is not None:
            connect(second, n.inputs[1])
        return n.outputs[0]

    def blend(factor, first, second, label):
        n = nodes.new('ShaderNodeMixRGB'); n.label = label
        connect(factor, n.inputs[0]); connect(first, n.inputs[1]); connect(second, n.inputs[2])
        return n.outputs[0]

    def ramp(value, low, high):
        n = nodes.new('ShaderNodeMapRange'); n.clamp = True
        n.inputs['From Min'].default_value = low
        n.inputs['From Max'].default_value = high
        links.new(value, n.inputs['Value'])
        return n.outputs['Result']

    tc = nodes.new('ShaderNodeTexCoord')
    variation = nodes.new('ShaderNodeTexNoise')
    variation.inputs['Scale'].default_value = 67
    variation.inputs['Detail'].default_value = 4
    links.new(tc.outputs['Object'], variation.inputs['Vector'])
    geometry = nodes.new('ShaderNodeNewGeometry')
    exposed = math_node('MULTIPLY', ramp(geometry.outputs['Pointiness'], .497, .535),
                        ramp(variation.outputs['Fac'], .30, .72))
    ao = nodes.new('ShaderNodeAmbientOcclusion')
    ao.label = '16 mm seam dirt on isolated prop; requires actual mesh atlas bake'
    ao.inputs['Distance'].default_value = .016
    ao.only_local = False; ao.samples = 16
    cavity = math_node('MULTIPLY', math_node('SUBTRACT', 1, ao.outputs['AO']), .78)
    direction = nodes.new('ShaderNodeVectorMath'); direction.operation = 'MULTIPLY'
    direction.inputs[1].default_value = (3500, 90, 500)
    links.new(tc.outputs['Object'], direction.inputs[0])
    scratch = nodes.new('ShaderNodeTexNoise'); scratch.inputs['Scale'].default_value = 1
    scratch.inputs['Detail'].default_value = 2
    links.new(direction.outputs['Vector'], scratch.inputs['Vector'])
    scratch_mask = math_node('MULTIPLY', ramp(scratch.outputs['Fac'], .70, .79),
                             ramp(variation.outputs['Fac'], .37, .70))
    wear = math_node('MAXIMUM', exposed, math_node('MULTIPLY', scratch_mask, .42))
    warm_metal = mat.name in ['Weapon_AgedBrass', 'Weapon_DarkCopper']
    edge_color = (.26, .16, .055, 1) if warm_metal else (.19, .19, .17, 1)
    base = blend(wear, original['Base Color'], edge_color, 'Broken exposed edge and fine abrasion')
    base = blend(cavity, base, (.024, .015, .008, 1), 'Dirt retained within actual seams')
    links.new(base, bs.inputs['Base Color'])
    # A rough, irregular surface with small polished wear, never a uniform
    # chrome response. Pigment remains dielectric except at exposed metal.
    broad_rough = math_node('ADD', math_node('MULTIPLY', variation.outputs['Fac'], .30), .40)
    rough = blend(wear, broad_rough, (.34, .34, .34, 1), 'Abrasion roughness')
    rough = blend(cavity, rough, (.88, .88, .88, 1), 'Packed dirt roughness')
    links.new(rough, bs.inputs['Roughness'])
    metal = blend(wear, original['Metallic'], (.85, .85, .85, 1), 'Exposed metal')
    metal = blend(cavity, metal, (.03, .03, .03, 1), 'Dielectric dirt')
    links.new(metal, bs.inputs['Metallic'])
    bump = nodes.new('ShaderNodeBump')
    bump.inputs['Distance'].default_value = .000045
    bump.inputs['Strength'].default_value = .25
    links.new(scratch_mask, bump.inputs['Height'])
    connect(original['Normal'], bump.inputs['Normal'])
    links.new(bump.outputs['Normal'], bs.inputs['Normal'])
    mat['requiresActualMeshAtlas'] = 'Geometry.Pointiness and local AO; do not tile-bake'
    changed.append(mat.name)

after = {o.name: mesh_fingerprint(o) for o in meshes}
if before != after:
    raise AssertionError('Material-only study changed geometry, UVs or transforms')
scene = bpy.context.scene
scene.cycles.samples = 40
scene.render.threads_mode = 'FIXED'; scene.render.threads = 4
source = a.output / 'Krag_Regular_Weapon_SurfaceStudy_v3.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(source), compress=True)
report = {'status': 'Actual isolated material study; visual review pending',
          'source': str(a.source), 'sourceSha256': source_hash,
          'output': str(source), 'outputSha256': sha(source),
          'recipeSha256': sha(Path(__file__)), 'changedMaterials': changed,
          'preservedMeshComponents': len(before), 'meshFingerprints': before,
          'requiresActualMeshAtlas': True, 'sharedAssetsChanged': False,
          'engineExported': False, 'artisticAcceptance': False, 'views': []}
for name, pos, target, scale in [
        ('ThreeQuarter', (.9, -1.25, .64), (0, -.23, .08), .86),
        ('Side', (1.4, -.19, .26), (0, -.22, .085), .85)]:
    camera = scene.camera
    camera.location = pos
    camera.rotation_euler = (Vector(target)-camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera.data.ortho_scale = scale
    output = a.output / ('Krag_Weapon_' + name + '.png')
    scene.render.filepath = str(output)
    bpy.ops.render.render(write_still=True)
    report['views'].append({'path': str(output), 'sha256': sha(output)})
if sha(a.source) != source_hash:
    raise AssertionError('Input prop source changed')
(a.output / 'study.json').write_text(json.dumps(report, indent=2)+'\n')
print('KRAG_WEAPON_SURFACE_STUDY_COMPLETE', flush=True)
