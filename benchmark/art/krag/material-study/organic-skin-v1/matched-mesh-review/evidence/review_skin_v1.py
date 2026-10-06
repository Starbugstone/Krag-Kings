"""Isolated matched skin-material study on the actual current Krag surface.

The generated bitmap is a provisional appearance reference, not measured
albedo or height. Preserve the original source and every deformation payload.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT / 'benchmark/tools/animation'),
               str(ROOT / 'benchmark/tools/nib/restorative_wip')]
from contracts import surface_hash, rig_contract
from export_contract import select_action

p = argparse.ArgumentParser()
p.add_argument('--source', type=Path, required=True)
p.add_argument('--source-sha256', required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args(sys.argv[sys.argv.index('--') + 1:])
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(a.source) == a.source_sha256
assert not a.output.exists(), 'Preserve prior actual review'
a.output.mkdir(parents=True)
bitmap = ROOT / 'benchmark/art/krag/material-study/organic-skin-v1/Krag_Skin_BaseColor_Provisional.png'
assert sha(bitmap) == '346ff0960a02f8b4eb17ba93ff4cb562e238223d758fea64f86169d062f726ea'
bpy.ops.wm.open_mainfile(filepath=str(a.source), load_ui=False)
scene = bpy.context.scene
rig = bpy.data.objects['Krag_Rig']
contract = json.loads((ROOT / 'benchmark/art/krag/coherent68-source-contract.json').read_text())
assert contract['source_blend_sha256'] == a.source_sha256
surfaces = {o.name: surface_hash(o) for o in bpy.data.objects if o.type == 'MESH'}
rig_before = rig_contract(rig)
for track in rig.animation_data.nla_tracks:
    track.mute = True
select_action(bpy, rig, bpy.data.actions['Idle'])
scene.frame_set(1)
for obj in bpy.data.objects:
    if obj.type == 'MESH' and obj.get('module'):
        obj.hide_render = obj.hide_viewport = obj['module'] in contract['variants']['Krag_Natural']['off']
for light in bpy.data.lights:
    light.color = (1, 1, 1)
if scene.world and scene.world.use_nodes:
    scene.world.node_tree.nodes['Background'].inputs[0].default_value = (.3, .3, .3, 1)
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 24
scene.render.resolution_x = scene.render.resolution_y = 1000
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
camera = scene.camera
camera.data.type = 'ORTHO'
report = {'sourceSha256': a.source_sha256, 'bitmapSha256': sha(bitmap),
          'bitmapDimensions': [1254, 1254], 'recipeSha256': sha(Path(__file__)),
          'artisticAcceptance': False, 'sourceModified': False, 'engineIntegrated': False,
          'generatedBitmapIsMeasuredAlbedo': False, 'generatedBitmapUsedAsHeight': False,
          'views': [], 'materialChanges': []}

def render(tag):
    for name, position, target, scale in [
        ('Face', (1.1, -4, 2.05), (0, -.02, 1.9), .53),
        ('Body', (.8, -6, 1.5), (0, 0, 1.3), 1.48)]:
        camera.location = position
        camera.rotation_euler = (Vector(target) - camera.location).to_track_quat('-Z', 'Y').to_euler()
        camera.data.ortho_scale = scale
        output = a.output / (tag + '-' + name + '.png')
        scene.render.filepath = str(output)
        bpy.ops.render.render(write_still=True)
        report['views'].append({'material': tag, 'view': name, 'path': output.name,
                                'sha256': sha(output), 'samples': scene.cycles.samples})

render('Current')
image = bpy.data.images.load(str(bitmap), check_existing=False)
image.colorspace_settings.name = 'sRGB'
assert list(image.size) == [1254, 1254]
for material_name in ['Krag_SandstoneSkin', 'Krag_FacialSkin']:
    material = bpy.data.materials[material_name]
    nodes, links = material.node_tree.nodes, material.node_tree.links
    shader = next(n for n in nodes if n.type == 'BSDF_PRINCIPLED')
    uv = nodes.new('ShaderNodeTexCoord')
    physical = nodes.new('ShaderNodeVectorMath')
    physical.operation = 'SCALE'
    physical.inputs['Scale'].default_value = 6.5 if 'Facial' in material_name else 4.
    links.new(uv.outputs['Object'], physical.inputs[0])
    texture = nodes.new('ShaderNodeTexImage')
    texture.image = image
    texture.projection = 'BOX'
    texture.projection_blend = .32
    texture.extension = 'REPEAT'
    links.new(physical.outputs[0], texture.inputs['Vector'])
    pigment = nodes.new('ShaderNodeMixRGB')
    pigment.name = 'Provisional organic pigment study'
    pigment.blend_type = 'MULTIPLY'
    pigment.inputs[0].default_value = 1
    pigment.inputs[2].default_value = (.88, 1.08, 1.38, 1)
    links.new(texture.outputs['Color'], pigment.inputs[1])
    # The face retains a quieter center and more pigment variation near the
    # scalp. This reads its authored attribute on the actual mesh.
    if 'Facial' in material_name:
        region = nodes.new('ShaderNodeAttribute')
        region.attribute_name = 'Krag_SkinRegion'
        quiet = nodes.new('ShaderNodeMixRGB')
        quiet.inputs[0].default_value = .27
        quiet.inputs[2].default_value = (.38, .22, .105, 1)
        links.new(pigment.outputs[0], quiet.inputs[1])
        mix = nodes.new('ShaderNodeMixRGB')
        links.new(region.outputs['Fac'], mix.inputs[0])
        links.new(quiet.outputs[0], mix.inputs[1])
        links.new(pigment.outputs[0], mix.inputs[2])
        links.new(mix.outputs[0], shader.inputs['Base Color'])
    else:
        links.new(pigment.outputs[0], shader.inputs['Base Color'])
    bump_changes = []
    for node in nodes:
        if node.type == 'BUMP':
            old = node.inputs['Distance'].default_value
            node.inputs['Distance'].default_value = min(old, .00035 if 'Facial' in material_name else .00055)
            node.inputs['Strength'].default_value = min(node.inputs['Strength'].default_value, .3)
            bump_changes.append({'node': node.name, 'beforeMeters': old,
                                 'afterMeters': node.inputs['Distance'].default_value})
    shader.inputs['Subsurface Weight'].default_value = .06
    report['materialChanges'].append({'name': material_name,
        'pigmentScalePerMeter': physical.inputs['Scale'].default_value, 'bumpChanges': bump_changes,
        'subsurfaceWeight': .06, 'roughness': 'Original scanned roughness retained'})
render('OrganicStudy')
assert rig_contract(rig) == rig_before, 'Material review changed rig/action contract'
assert all(surface_hash(bpy.data.objects[name]) == h for name, h in surfaces.items()), 'Mesh payload changed'
assert sha(a.source) == a.source_sha256
(a.output / 'review.json').write_text(json.dumps(report, indent=2) + '\n', newline='\n')
print('KRAG_MATCHED_SKIN_STUDY_COMPLETE', flush=True)
