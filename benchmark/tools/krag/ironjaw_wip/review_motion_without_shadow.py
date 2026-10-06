"""One matched frame to distinguish Workbench shadows from source mesh strips."""
from pathlib import Path
import sys, json, hashlib
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT/'benchmark/art/animation/krag-human-motion-v4/Krag_HumanMotion_Study_v4.blend'
EXPECTED = '84822444a021194fc47e0360bfffc875c18687720bb8b8923588e486b9900607'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(SOURCE) == EXPECTED
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
sys.path.insert(0, str(ROOT/'benchmark/tools/animation'))
from export_contract import select_action
rig = bpy.data.objects['Krag_Rig']
hidden = json.loads((ROOT/'benchmark/shared/characters/krag/krag_asset_contract.json').read_text())['variants']['Krag_Natural']['off']
for obj in bpy.data.objects:
    if obj.type == 'MESH' and 'module' in obj:
        obj.hide_render = obj.hide_viewport = obj['module'] in hidden and obj['module'] != 'Weapon_R'
for track in rig.animation_data.nla_tracks:
    track.mute = True
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
camera.location = target+Vector((0, -6, .1))
camera.rotation_euler = (target-camera.location).to_track_quat('-Z', 'Y').to_euler()
select_action(bpy, rig, bpy.data.actions['Walk'])
scene.frame_set(1)
output = ROOT/'benchmark/art/krag/renders/Krag_v4_Walk_front_f1_NoWorkbenchShadows.png'
if output.exists():
    raise RuntimeError('Preserve existing matched diagnostic')
scene.render.filepath = str(output)
bpy.ops.render.render(write_still=True)
assert sha(SOURCE) == EXPECTED
baseline = ROOT/'benchmark/art/animation/krag-human-motion-v4/motion-review/Walk/front/0000.png'
output.with_suffix('.meta.json').write_text(json.dumps({
    'sourceSha256': EXPECTED, 'sourceChanged': False,
    'baseline': baseline.relative_to(ROOT).as_posix(), 'baselineSha256': sha(baseline),
    'imageSha256': sha(output), 'scriptSha256': sha(Path(__file__)),
    'clip': 'Walk', 'frame': 1, 'onlyIntentionalRenderDifference': 'Workbench show_shadows=False',
    'status': 'Actual matched shadow-attribution view; inspect before attributing source defect'
}, indent=2)+'\n', newline='\n')
print('KRAG_V4_SHADOW_ATTRIBUTION_VIEW_COMPLETE', flush=True)
