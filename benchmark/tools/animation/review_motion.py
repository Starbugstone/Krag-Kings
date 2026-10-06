"""Render real deformed source meshes for inexpensive whole-cycle inspection.

Workbench clay views are motion evidence, not final material/lighting evidence.
The source and exported assets are never saved or modified.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector

parser = argparse.ArgumentParser()
parser.add_argument('--source', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--species', choices=['Krag', 'Nib'], required=True)
parser.add_argument('--poses-only', action='store_true')
args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
if args.output.exists(): raise RuntimeError('Preserve previous review output')
args.output.mkdir(parents=True)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
source_sha = sha(args.source)
bpy.ops.wm.open_mainfile(filepath=str(args.source))
root = Path(__file__).resolve().parents[2]
if args.species == 'Krag':
    contract = json.loads((root/'shared/characters/krag/krag_asset_contract.json').read_text())
    hidden = contract['variants']['Krag_Natural']['off']
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and 'module' in obj:
            obj.hide_render = obj['module'] in hidden and obj['module'] != 'Weapon_R'
            obj.hide_viewport = obj.hide_render
else:
    for obj in bpy.data.collections['Nib_Authored_Components'].objects:
        visible = obj.get('variant', 'all') in ['all', 'natural', 'organic']
        obj.hide_render = not visible
        obj.hide_viewport = not visible
rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and 'Pelvis' in o.data.bones)
for track in rig.animation_data.nla_tracks: track.mute = True
scene = bpy.context.scene
scene.render.engine = 'BLENDER_WORKBENCH'
scene.render.resolution_x = 640
scene.render.resolution_y = 720
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.film_transparent = False
scene.render.use_compositing = False
scene.render.use_sequencer = False
shading = scene.display.shading
shading.light = 'STUDIO'
shading.color_type = 'SINGLE'
shading.single_color = (.54, .54, .54)
shading.show_shadows = True
shading.show_cavity = True
shading.cavity_type = 'BOTH'
shading.background_type = 'WORLD'
scene.world.color = (.065, .065, .065)
scene.display.render_aa = '8'
camera = scene.camera
camera.data.type = 'ORTHO'
camera.data.ortho_scale = 2.65 if args.species == 'Krag' else 1.85
target = Vector((0, 0, 1.11 if args.species == 'Krag' else .73))
report = {'source': str(args.source), 'sourceSha256': source_sha,
          'recipeSha256': sha(Path(__file__)), 'renderer': scene.render.engine,
          'materialReview': False, 'artisticAcceptance': False, 'clips': {}}
for clip in ['Walk', 'Run', 'Idle']:
    action = bpy.data.actions[clip]
    rig.animation_data.action = action
    first, last = (int(v) for v in action.frame_range)
    frames = ([round(first+(last-first)*p) for p in [0, .25, .5, .75]] if args.poses_only
              else list(range(first, last, 3 if clip == 'Idle' else 1)))
    views = {}
    for view, offset in [('front', Vector((0, -6, .1))), ('side', Vector((6, 0, .1)))]:
        camera.location = target+offset
        camera.rotation_euler = (target-camera.location).to_track_quat('-Z', 'Y').to_euler()
        folder = args.output/clip/view; folder.mkdir(parents=True)
        images = []
        for index, frame in enumerate(frames):
            scene.frame_set(frame)
            path = folder/('%04d.png' % index)
            scene.render.filepath = str(path)
            bpy.ops.render.render(write_still=True)
            images.append({'frame': frame, 'file': str(path), 'sha256': sha(path)})
        views[view] = images
    report['clips'][clip] = {'frameRange': [first, last], 'sampleRate': 10 if clip == 'Idle' else 30,
                            'views': views}
if sha(args.source) != source_sha: raise AssertionError('Review changed source')
(args.output/'review.json').write_text(json.dumps(report, indent=2)+'\n')
print('KRAG_KINGS_MOTION_REVIEW_COMPLETE', flush=True)
