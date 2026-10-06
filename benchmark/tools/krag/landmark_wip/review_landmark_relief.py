"""Actual anatomy/material views at the measured correspondence cameras."""
from pathlib import Path
import sys, argparse, json, hashlib
import bpy
from mathutils import Matrix

ROOT = Path(__file__).resolve().parents[4]
ART = ROOT/'benchmark/art/krag'
parser = argparse.ArgumentParser()
parser.add_argument('--view', choices=['FrontClay', 'SideClay', 'FrontMaterial'], required=True)
args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
report = json.loads((ART/'landmark-relief-v9o.json').read_text())
source = ROOT/report['source']['path']
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
assert sha(source) == report['source']['sha256']
bpy.ops.wm.open_mainfile(filepath=str(source))
scene = bpy.context.scene
rig = bpy.data.objects['Krag_Rig']
rig.animation_data.action = None
for track in rig.animation_data.nla_tracks:
    track.mute = True
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
        obj.hide_render = obj['module'] in contract['variants']['Krag_Natural']['off']
camera_view = 'MatchedSide65' if args.view == 'SideClay' else 'TrueFront'
camera_meta = json.loads((ART/'landmarks-v9nc'/('Krag_'+camera_view+'.meta.json')).read_text())
scene.camera.matrix_world = Matrix(camera_meta['cameraWorld'])
scene.camera.data.type = 'ORTHO'
scene.camera.data.ortho_scale = camera_meta['orthoScaleMeters']
if args.view.endswith('Clay'):
    clay = bpy.data.materials.new('Krag_AnatomyReview_Clay')
    clay.use_nodes = True
    bs = next(n for n in clay.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
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
image = ART/'renders'/('Krag_v9o_'+args.view+'.png')
if image.exists():
    raise RuntimeError('Refusing to overwrite actual sculpt review')
scene.render.filepath = str(image)
bpy.ops.render.render(write_still=True)
assert image.exists() and image.stat().st_size > 10000
meta = {'source': report['source'], 'view': args.view, 'camera': camera_meta,
        'pose': 'Neutral rest, all bone bases identity and shape values zero',
        'imageSha256': sha(image), 'toolSha256': sha(Path(__file__)),
        'artisticAcceptance': False, 'status': 'Actual source mesh review, not engine evidence'}
image.with_suffix('.meta.json').write_text(json.dumps(meta, indent=2)+'\n', newline='\n')
assert sha(source) == report['source']['sha256']
print('KRAG_LANDMARK_RELIEF_REVIEW_COMPLETE '+args.view, flush=True)
