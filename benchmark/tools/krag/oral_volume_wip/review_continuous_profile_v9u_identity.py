"""Actual replacement clearance views with an unobscured right-side camera."""
from pathlib import Path
import argparse, json, hashlib, sys
import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[4]
ART = ROOT/'benchmark/art/krag'
parser = argparse.ArgumentParser()
parser.add_argument('--view', choices=['NeutralFront', 'NeutralThreeQuarter', 'OpenFront'], required=True)
args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
source = ART/'Krag_ContinuousMandible_v9u_WIP.blend'
receipt = json.loads((ART/'continuous-profile-v9u.json').read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(source) == receipt['source']['sha256']
bpy.ops.wm.open_mainfile(filepath=str(source))
contract = json.loads((ROOT/'benchmark/local/candidates/krag-v9h-source/krag_asset_contract.json').read_text())
off = contract['variants']['Krag_Natural']['off']
for obj in bpy.data.objects:
    if obj.type == 'MESH' and 'module' in obj:
        obj.hide_viewport = obj.hide_render = obj['module'] in off
scene = bpy.context.scene
rig = bpy.data.objects['Krag_Rig']
if args.view.startswith('Open'):
    rig.animation_data.action = bpy.data.actions['FacePerformance']
    scene.frame_set(146)
else:
    rig.animation_data.action = None
    for bone in rig.pose.bones:
        bone.matrix_basis = Matrix.Identity(4)
bpy.context.view_layer.update()
for light in bpy.data.lights:
    light.color = (1, 1, 1)
if scene.world and scene.world.use_nodes:
    scene.world.node_tree.nodes['Background'].inputs[0].default_value = (.30, .30, .30, 1)
camera = scene.camera
target = Vector((0, -.02, 1.9))
camera.location = Vector((-3, -3, 2.03)) if args.view == 'NeutralThreeQuarter' else Vector((0, -4, 1.92))
camera.rotation_euler = (target-camera.location).to_track_quat('-Z', 'Y').to_euler()
camera.data.type = 'ORTHO'
camera.data.ortho_scale = .53
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 16
scene.render.resolution_x = 1000
scene.render.resolution_y = 1000
scene.render.resolution_percentage = 100
image = ART/'renders'/('Krag_ContinuousMandible_v9u_Identity_'+args.view+'.png')
if image.exists():
    raise RuntimeError('Preserve actual previous review image')
scene.render.filepath = str(image)
bpy.ops.render.render(write_still=True)
image.with_suffix('.meta.json').write_text(json.dumps({
    'source': source.relative_to(ROOT).as_posix(), 'sourceSha256': sha(source),
    'scriptSha256': sha(Path(__file__)), 'imageSha256': sha(image),
    'view': args.view, 'camera': list(camera.location), 'target': list(target),
    'orthographicScale': camera.data.ortho_scale,
    'action': 'FacePerformance' if args.view.startswith('Open') else None,
    'frame': 146 if args.view.startswith('Open') else None,
    'renderer': 'Cycles CPU', 'samples': 16, 'artisticAcceptance': False,
    'status': 'Actual replacement-source view; clearance and likeness require inspection'
}, indent=2)+'\n', newline='\n')
print('KRAG_V9U_IDENTITY_REVIEW_COMPLETE '+args.view, flush=True)
