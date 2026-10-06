"""Actual merged-source body poses; clay motion evidence, not material approval."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE.parents[1]/'animation'))
from export_contract import select_action

parser = argparse.ArgumentParser()
parser.add_argument('--source', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
receipt = json.loads(args.source.with_suffix('.json').read_text())
if sha(args.source) != receipt['output']['sha256']:
    raise RuntimeError('Merged source differs from its actual save/reopen receipt')
if args.output.exists():
    raise RuntimeError('Preserve prior actual movement captures')
args.output.mkdir(parents=True)
bpy.ops.wm.open_mainfile(filepath=str(args.source), load_ui=False)
rig = bpy.data.objects['Krag_Rig']
for track in rig.animation_data.nla_tracks:
    track.mute = True
contract = json.loads((ROOT/'benchmark/shared/characters/krag/krag_asset_contract.json').read_text())
hidden = contract['variants']['Krag_Natural']['off']
for obj in bpy.data.objects:
    if obj.type == 'MESH' and obj.get('module'):
        obj.hide_render = obj.hide_viewport = obj['module'] in hidden and obj['module'] != 'Weapon_R'
scene = bpy.context.scene
scene.render.engine = 'BLENDER_WORKBENCH'
scene.render.resolution_x, scene.render.resolution_y = 640, 720
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.film_transparent = False
scene.render.use_compositing = scene.render.use_sequencer = False
shading = scene.display.shading
shading.light = 'STUDIO'
shading.color_type = 'SINGLE'
shading.single_color = (.54, .54, .54)
# The matched v4 shadow-off diagnostic proved the long floor strips were a
# Workbench shadow artifact. Do not reintroduce them as apparent mesh damage.
shading.show_shadows = False
shading.show_cavity = True
shading.cavity_type = 'BOTH'
shading.background_type = 'WORLD'
scene.world.color = (.065, .065, .065)
scene.display.render_aa = '8'
camera = scene.camera
camera.data.type = 'ORTHO'
camera.data.ortho_scale = 2.65
target = Vector((0, 0, 1.11))
report = {'source': receipt['output'], 'recipeSha256': sha(Path(__file__)),
          'renderer': 'Workbench clay, shadows disabled', 'materialAcceptance': False,
          'artisticAcceptance': False, 'views': []}
for clip in ['Walk', 'Run', 'Idle']:
    action = bpy.data.actions[clip]
    select_action(bpy, rig, action)
    first, last = action.frame_range
    for view, offset in [('front', Vector((0, -6, .1))), ('side', Vector((6, 0, .1)))]:
        camera.location = target+offset
        camera.rotation_euler = (target-camera.location).to_track_quat('-Z', 'Y').to_euler()
        for index, phase in enumerate([0, .25, .5, .75]):
            frame = first+(last-first)*phase
            scene.frame_set(int(frame), subframe=frame-int(frame))
            path = args.output/(clip+'-'+view+'-'+str(index)+'.png')
            scene.render.filepath = str(path)
            bpy.ops.render.render(write_still=True)
            report['views'].append({'clip': clip, 'phase': phase, 'frame': frame,
                                    'view': view, 'path': path.relative_to(ROOT).as_posix(),
                                    'sha256': sha(path)})
if sha(args.source) != receipt['output']['sha256']:
    raise RuntimeError('Review mutated the merged source')
(args.output/'review.json').write_text(json.dumps(report, indent=2)+'\n', newline='\n')
print('KRAG_MERGED_BODY_REVIEW_COMPLETE', flush=True)
