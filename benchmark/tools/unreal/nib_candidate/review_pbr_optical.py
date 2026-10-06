"""Matched saved-source/PBR iris view using the actual adult-review camera.

Run only after the saved-PBR snapshot. This is material transfer evidence,
not a new character design or a claim of artistic acceptance.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[4]
sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
parser = argparse.ArgumentParser()
parser.add_argument('--contract', type=Path, required=True)
parser.add_argument('--side', choices=['source', 'baked'], required=True)
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
contract = json.loads(args.contract.read_text())
for item in contract['pins']:
    if sha(ROOT / item['path']) != item['sha256']:
        raise RuntimeError('Frozen optical review input changed: ' + item['path'])
pinned_paths = {item['path'] for item in contract['pins']}
for required in [contract['source'], contract['baked'],
                 Path(__file__).relative_to(ROOT).as_posix(),
                 'benchmark/tools/nib/identity_wip/review_adult_identity.py']:
    if required not in pinned_paths:
        raise RuntimeError('Missing optical source/recipe pin: ' + required)
receipt = ROOT / contract['savedPbrSnapshotReceipt']
if not receipt.is_file():
    raise RuntimeError('Saved PBR snapshot has not passed')
snapshot = json.loads(receipt.read_text())
if snapshot['stage'] != 'snapshot-pbr':
    raise RuntimeError('Wrong completed stage for optical review')
for item in snapshot['outputs']:
    if sha(ROOT / item['path']) != item['sha256']:
        raise RuntimeError('Saved PBR snapshot output changed')
source = ROOT / contract[args.side]
source_sha = sha(source)
output = ROOT / contract['outputRoot'] / (args.side + '-optical')
if output.exists():
    raise RuntimeError('Preserve earlier optical comparison')
output.mkdir(parents=True)
bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False)
scene = bpy.context.scene
rig = bpy.data.objects['Nib_Rig']
for track in rig.animation_data.nla_tracks:
    track.mute = True
for obj in bpy.data.collections['Nib_Authored_Components'].objects:
    show = obj.get('variant', 'all') in ['all', 'natural', 'organic']
    obj.hide_set(not show)
    obj.hide_render = not show
rig.animation_data.action = bpy.data.actions['Idle']
scene.frame_set(1)
bpy.context.view_layer.update()
scene.render.engine = 'CYCLES'
scene.render.threads_mode = 'FIXED'
scene.render.threads = 4
scene.cycles.device = 'CPU'
scene.cycles.samples = 24
scene.cycles.use_denoising = True
scene.render.resolution_x = 1500
scene.render.resolution_y = 900
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.use_sequencer = False
# Exact EyeCloseup definition from the pinned adult native review.
target = (rig.matrix_world @ rig.pose.bones['Eye_L'].head
          + rig.matrix_world @ rig.pose.bones['Eye_R'].head) * .5
camera = scene.camera
camera.data.type = 'ORTHO'
camera.data.ortho_scale = .18
camera.location = target + Vector((.12, -3, .08))
camera.rotation_euler = (target-camera.location).to_track_quat('-Z', 'Y').to_euler()
image = output / 'EyeCloseup.png'
scene.render.filepath = str(image)
bpy.ops.render.render(write_still=True)
for item in contract['pins']:
    if sha(ROOT / item['path']) != item['sha256']:
        raise RuntimeError('Read-only optical review changed input: ' + item['path'])
result = {
    'side': args.side, 'contractSha256': sha(args.contract),
    'source': source.relative_to(ROOT).as_posix(), 'sourceSha256': source_sha,
    'view': 'EyeCloseup', 'action': 'Idle', 'frame': 1,
    'camera': {'type': 'ORTHO', 'scaleMeters': .18, 'position': list(camera.location),
               'target': list(target), 'relativeOffsetMeters': [.12, -3, .08]},
    'render': {'engine': 'Blender Cycles CPU', 'threads': 4, 'samples': 24,
               'width': 1500, 'height': 900, 'denoising': True},
    'image': image.relative_to(ROOT).as_posix(), 'imageSha256': sha(image),
    'visualParityInspected': False, 'artisticAcceptance': False,
    'status': 'Actual matched iris transfer image; inspect source/baked pair before acceptance',
}
(output / 'review-receipt.json').write_text(json.dumps(result, indent=2)+'\n', newline='\n')
print('NIB_COHERENT_PBR_OPTICAL_REVIEW_COMPLETE ' + args.side, flush=True)
