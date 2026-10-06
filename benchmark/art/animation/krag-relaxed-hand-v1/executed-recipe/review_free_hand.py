"""Actual isolated hand skinning review; never saves or exports the source.

Camera directions follow the hand's original palmar plane, preserving comparable
palm, dorsal and radial views as the body acts. Clay images establish shape and
deformation only. They are not material or engine acceptance evidence.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).parent))
from export_contract import select_action

parser = argparse.ArgumentParser()
parser.add_argument('--source', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--species', choices=['Krag', 'Nib'], required=True)
parser.add_argument('--clips', nargs='+', default=['Idle', 'Walk', 'Run'])
parser.add_argument('--phases', nargs='+', type=float, default=[0., .5])
args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
if any(not 0 <= phase <= 1 for phase in args.phases):
    raise ValueError('Review phases must lie in [0, 1]')
if args.output.exists():
    raise RuntimeError('Preserve previous review output')
args.output.mkdir(parents=True)
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
source_hash = sha(args.source)
bpy.ops.wm.open_mainfile(filepath=str(args.source))
rig = next(obj for obj in bpy.data.objects
           if obj.type == 'ARMATURE' and 'Pelvis' in obj.data.bones)
for track in rig.animation_data.nla_tracks:
    track.mute = True
hand = rig.pose.bones['Hand_L']
digits = [b for b in rig.pose.bones if b.name.endswith('_L') and
          b.name.startswith(('Thumb', 'Index', 'Middle', 'Ring', 'Little', 'Finger'))]
controls = {'Hand_L'} | {bone.name for bone in digits}
visible = []
root = Path(__file__).resolve().parents[2]
hidden_modules = set()
authored_names = None
if args.species == 'Krag':
    contract = json.loads((root/'shared/characters/krag/krag_asset_contract.json').read_text())
    hidden_modules = set(contract['variants']['Krag_Natural']['off'])
else:
    authored_names = {obj.name for obj in bpy.data.collections['Nib_Authored_Components'].all_objects}
for obj in bpy.data.objects:
    if obj.type != 'MESH':
        continue
    groups = {g.index for g in obj.vertex_groups if g.name in controls}
    weighted = sum(any(g.group in groups and g.weight > .1 for g in v.groups)
                   for v in obj.data.vertices)
    # Keep actual hand/glove/wrist pieces; omit whole-body and opposite-side
    # surfaces that would occlude the diagnostic camera through the torso.
    keep = weighted > 0 and weighted / max(1, len(obj.data.vertices)) > .25
    keep = keep and obj.get('variant', 'all') in ['all', 'natural', 'organic']
    if args.species == 'Krag':
        # Krag's organic fingers are part of a dense continuous forearm.
        # A fraction threshold can hide that entire surface while leaving
        # just nails/details. Retain its authored semantic modules explicitly.
        keep = obj.get('module') in ['BioForearm_L', 'HandDetails_L']
        keep = keep and obj.get('module', '') not in hidden_modules
    else:
        keep = keep and obj.name in authored_names
    obj.hide_render = not keep
    obj.hide_viewport = not keep
    if keep:
        visible.append({'name': obj.name, 'vertices': len(obj.data.vertices),
                        'handWeightedVertices': weighted})
if not visible:
    raise RuntimeError('No actual hand geometry found')
scene = bpy.context.scene
scene.render.engine = 'BLENDER_WORKBENCH'
scene.render.resolution_x = 800
scene.render.resolution_y = 800
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
camera.data.clip_start = .001
camera.data.clip_end = 100
camera.data.ortho_scale = .32 if args.species == 'Krag' else .19
report = {'source': str(args.source), 'sourceSha256': source_hash,
          'recipeSha256': sha(Path(__file__)), 'visibleMeshes': visible,
          'renderer': scene.render.engine, 'materialReview': False,
          'surfaceIntersectionProof': False, 'artisticAcceptance': False,
          'sourceModified': False, 'views': []}
for clip in args.clips:
    action = bpy.data.actions[clip]
    select_action(bpy, rig, action)
    first, last = action.frame_range
    for phase in args.phases:
        at = first + phase * (last-first)
        scene.frame_set(int(at), subframe=at-int(at))
        bpy.context.view_layer.update()
        delta = hand.matrix.to_3x3() @ hand.bone.matrix_local.to_3x3().inverted()
        palm = rig.matrix_world.to_3x3() @ delta @ Vector(
            (-1, 0, 0) if args.species == 'Krag' else (0, -1, 0))
        palm.normalize()
        tips = [bone.tail for bone in digits if not bone.children]
        middle = sum(tips, Vector())/len(tips)
        target = rig.matrix_world @ hand.head.lerp(middle, .56)
        up = rig.matrix_world.to_3x3() @ (hand.head-middle)
        up -= palm * up.dot(palm)
        if up.length < 1e-5:
            raise RuntimeError('Degenerate hand camera orientation')
        up.normalize()
        radial = up.cross(palm).normalized()
        for view, outward in [('palm', palm), ('back', -palm), ('edge', radial)]:
            right = up.cross(outward).normalized()
            camera_up = outward.cross(right).normalized()
            camera.matrix_world = Matrix((right, camera_up, outward)).transposed().to_4x4()
            camera.location = target+outward*.75
            output = args.output / f'{clip}_{int(phase*100):02d}_{view}.png'
            scene.render.filepath = str(output)
            bpy.ops.render.render(write_still=True)
            report['views'].append({'clip': clip, 'phase': phase, 'frame': at,
                                    'view': view, 'path': str(output),
                                    'sha256': sha(output), 'target': list(target),
                                    'outward': list(outward)})
if sha(args.source) != source_hash:
    raise AssertionError('Review changed source')
(args.output/'review.json').write_text(json.dumps(report, indent=2)+'\n')
print('KRAG_KINGS_HAND_REVIEW_COMPLETE', flush=True)
