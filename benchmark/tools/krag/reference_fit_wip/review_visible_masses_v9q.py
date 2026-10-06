"""Matched neutral anatomy and full-range oral proof of the saved fit."""
from pathlib import Path
import argparse
import sys
import json
import hashlib
import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[4]
ART = ROOT/'benchmark/art/krag'
parser = argparse.ArgumentParser()
parser.add_argument('--view', choices=['FrontClay', 'RightClay', 'FrontMaterial', 'OpenFront', 'OpenRight'], required=True)
args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
report = json.loads((ART/'visible-mass-fit-v9q.json').read_text())
source = ROOT/report['source']['path']
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
assert sha(source) == report['source']['sha256']
bpy.ops.wm.open_mainfile(filepath=str(source))
scene = bpy.context.scene
rig = bpy.data.objects['Krag_Rig']
for track in rig.animation_data.nla_tracks:
    track.mute = True
if args.view.startswith('Open'):
    rig.animation_data.action = bpy.data.actions['FacePerformance']
    scene.frame_set(146)
else:
    rig.animation_data.action = None
    for bone in rig.pose.bones:
        bone.matrix_basis = Matrix.Identity(4)
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and obj.data.shape_keys:
            if obj.data.shape_keys.animation_data:
                obj.data.shape_keys.animation_data.action = None
                for driver in obj.data.shape_keys.animation_data.drivers:
                    driver.mute = True
            for key in obj.data.shape_keys.key_blocks:
                key.value = 0
contract = json.loads((ROOT/'benchmark/local/candidates/krag-v9h-source/krag_asset_contract.json').read_text())
for obj in bpy.data.objects:
    if obj.type == 'MESH' and 'module' in obj:
        obj.hide_viewport = obj.hide_render = obj['module'] in contract['variants']['Krag_Natural']['off']
camera = scene.camera
if args.view in ('RightClay', 'OpenRight'):
    camera.location = Vector((-4, -.045, 1.91))
    target = Vector((0, -.04, 1.87))
    camera.rotation_euler = (target-camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera.data.ortho_scale = .46 if args.view == 'RightClay' else .55
elif args.view == 'OpenFront':
    camera.location = Vector((1.1, -4, 2.05))
    target = Vector((0, -.02, 1.9))
    camera.rotation_euler = (target-camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera.data.ortho_scale = .53
else:
    metadata = json.loads((ART/'landmarks-v9nc/Krag_TrueFront.meta.json').read_text())
    camera.matrix_world = Matrix(metadata['cameraWorld'])
    camera.data.ortho_scale = metadata['orthoScaleMeters']
camera.data.type = 'ORTHO'
if args.view.endswith('Clay'):
    clay = bpy.data.materials.new('Krag_MassFitReview_Clay')
    clay.use_nodes = True
    bs = clay.node_tree.nodes['Principled BSDF']
    bs.inputs['Base Color'].default_value = (.28, .28, .28, 1)
    bs.inputs['Roughness'].default_value = .75
    for layer in scene.view_layers:
        layer.material_override = clay
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 16
scene.render.resolution_x = scene.render.resolution_y = 1000
scene.render.resolution_percentage = 100
for light in bpy.data.lights:
    light.color = (1, 1, 1)
if scene.world and scene.world.use_nodes:
    scene.world.node_tree.nodes['Background'].inputs[0].default_value = (.30, .30, .30, 1)
bpy.context.view_layer.update()
image = ART/'renders'/('Krag_v9q_'+args.view+'.png')
if image.exists():
    raise RuntimeError('Preserve actual previous candidate view')
scene.render.filepath = str(image)
bpy.ops.render.render(write_still=True)
meta = {'source': report['source'], 'view': args.view, 'cameraMatrixWorld': [list(row) for row in camera.matrix_world],
        'orthographicScale': camera.data.ortho_scale,
        'action': 'FacePerformance' if args.view.startswith('Open') else None,
        'frame': 146 if args.view.startswith('Open') else None,
        'imageSha256': sha(image), 'toolSha256': sha(Path(__file__)),
        'artisticAcceptance': False, 'engineEvidence': False}
image.with_suffix('.meta.json').write_text(json.dumps(meta, indent=2)+'\n', newline='\n')
assert sha(source) == report['source']['sha256']
print('KRAG_VISIBLE_MASS_FIT_REVIEW_COMPLETE '+args.view, flush=True)
