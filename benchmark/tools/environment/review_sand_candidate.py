"""Render baseline/candidate dune materials with identical geometry and lighting.

Source review only. These images do not establish engine appearance or speed.
Run in guarded Blender after prepare_sand_candidate.py.
"""
import hashlib
import json
import math
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[3]
CANDIDATE = ROOT / 'benchmark/local/candidates/sand-scan-v1'
OUTPUT = CANDIDATE / 'review'
OUTPUT.mkdir(parents=True, exist_ok=True)
sources = {
    'baseline': ROOT / 'benchmark/art/environment/Dunes.blend',
    'scan_candidate': CANDIDATE / 'Dunes_ScanCandidate.blend',
}
views = {
    'near': ((-2.5, -4.2, 3.4), (0, 0, 1.35)),
    'wide': ((8, -18, 7.5), (0, 8, 1.3)),
}
records = []
for label, source in sources.items():
    bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False)
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 24
    scene.cycles.use_denoising = True
    scene.render.threads_mode = 'FIXED'
    scene.render.threads = 2
    scene.render.resolution_x = 960
    scene.render.resolution_y = 640
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Medium High Contrast'
    scene.view_settings.exposure = 0
    scene.world = bpy.data.worlds.new('Sand review neutral world')
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes.get('Background')
    background.inputs['Color'].default_value = (.55, .65, .8, 1)
    background.inputs['Strength'].default_value = .35
    sun = bpy.data.lights.new('Sand review white sun', 'SUN')
    sun.energy = 3
    sun.angle = math.radians(1.5)
    light = bpy.data.objects.new('Sand review white sun', sun)
    scene.collection.objects.link(light)
    light.rotation_euler = tuple(math.radians(v) for v in (27, -20, -35))
    data = bpy.data.cameras.new('Sand review camera')
    camera = bpy.data.objects.new('Sand review camera', data)
    scene.collection.objects.link(camera)
    data.lens = 42
    data.clip_end = 2000
    scene.camera = camera
    for view, (position, focus) in views.items():
        camera.location = position
        camera.rotation_euler = (Vector(focus) - camera.location).to_track_quat('-Z', 'Y').to_euler()
        target = OUTPUT / (label + '_' + view + '.png')
        scene.render.filepath = str(target)
        bpy.ops.render.render(write_still=True)
        records.append({'material': label, 'view': view, 'source': str(source.relative_to(ROOT)),
                        'sourceSha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                        'image': target.name, 'imageSha256': hashlib.sha256(target.read_bytes()).hexdigest()})
(OUTPUT / 'source-review.json').write_text(json.dumps({
    'status': 'Actual Blender material comparison; visual acceptance and engine review pending',
    'renderer': 'Cycles CPU, 24 samples, 960x640',
    'geometry': 'Unmodified shared dune geometry',
    'lighting': 'Identical neutral white sun with blue ambient fill',
    'images': records,
}, indent=2) + '\n', newline='\n')
print('SAND_MATERIAL_REVIEW_COMPLETE', OUTPUT)
