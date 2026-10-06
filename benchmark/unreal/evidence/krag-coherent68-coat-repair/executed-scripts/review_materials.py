"""Matched read-only views of the authored and saved portable Krag materials."""
import argparse
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(Path(__file__).parents[1] / 'nib_candidate'))
from run_stage import sha, local, verify
sys.path.insert(0, str(ROOT / 'benchmark/tools/animation'))
from export_contract import select_action


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--side', choices=['source', 'baked'], required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    plan = json.loads(args.plan.read_text())
    verify(plan['pins'])
    source = local(plan['source'] if args.side == 'source' else plan['pbrSource'])
    output = local(plan['outputRoot']) / ('review-' + args.side)
    if output.exists():
        raise RuntimeError('Preserve earlier material comparison')
    bpy.ops.wm.open_mainfile(filepath=str(source))
    rig = bpy.data.objects['Krag_Rig']
    selection = json.loads(local(plan['selectionContract']).read_text())
    modules = {o['module']: o for o in bpy.data.objects if o.type == 'MESH' and 'module' in o}
    if set(modules) != set(selection['modules']) or set(rig.data.bones.keys()) != set(selection['bones']):
        raise RuntimeError('Review source inventory differs')
    for name, obj in modules.items():
        obj.hide_render = name in selection['variants']['Krag_Natural']['off'] and name != 'Weapon_R'
        obj.hide_set(False)
    select_action(bpy, rig, bpy.data.actions['Idle'])
    for track in rig.animation_data.nla_tracks:
        track.mute = True
    scene = bpy.context.scene
    scene.frame_set(1)
    bpy.context.view_layer.update()
    camera = scene.camera
    if camera is None:
        raise RuntimeError('Saved source camera is missing')
    # Both files inherit the same studio. Change only its color for the paired
    # diagnostic; all light energies, placements, color-management and geometry
    # remain the same. This is material-transfer evidence, not final lighting.
    lights = []
    for obj in scene.objects:
        if obj.type == 'LIGHT':
            obj.data.color = (1, 1, 1)
            lights.append({'name': obj.name, 'type': obj.data.type,
                           'energy': obj.data.energy,
                           'matrixWorld': [list(row) for row in obj.matrix_world]})
    if not lights or not scene.world or not scene.world.use_nodes:
        raise RuntimeError('Expected saved studio illumination')
    background = scene.world.node_tree.nodes.get('Background')
    if background is None:
        raise RuntimeError('Saved studio background node is missing')
    background.inputs[0].default_value = (.30, .30, .30, 1)
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 24
    scene.render.resolution_x = scene.render.resolution_y = 1000
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    camera.data.type = 'ORTHO'
    eye_center = (rig.matrix_world @ rig.pose.bones['Eye_L'].head +
                  rig.matrix_world @ rig.pose.bones['Eye_R'].head) * .5
    views = [
        ('Front', Vector((0, -6, 1.3)), Vector((0, 0, 1.06)), 2.38),
        ('Head', Vector((1.1, -4, 2.05)), Vector((0, -.02, 1.9)), .53),
        ('Eyes', eye_center + Vector((.15, -3, .05)), eye_center, .36),
    ]
    if 'reviewViews' in plan:
        requested = plan['reviewViews']
        if not requested or len(set(requested)) != len(requested) or set(requested) - {v[0] for v in views}:
            raise RuntimeError('Unknown or duplicate matched review views')
        views = [v for v in views if v[0] in requested]
    output.mkdir(parents=True)
    records = []
    for name, position, target, scale in views:
        camera.location = position
        camera.rotation_euler = (target - position).to_track_quat('-Z', 'Y').to_euler()
        camera.data.ortho_scale = scale
        scene.render.filepath = str(output / (name + '.png'))
        bpy.ops.render.render(write_still=True)
        path = Path(scene.render.filepath)
        records.append({'view': name, 'path': path.relative_to(ROOT).as_posix(),
                        'sha256': sha(path), 'cameraPosition': list(position),
                        'cameraTarget': list(target), 'orthographicScaleMeters': scale})
    verify(plan['pins'])
    result = {'side': args.side, 'sourceSha256': sha(source),
              'planSha256': sha(args.plan), 'images': records, 'clip': 'Idle', 'frame': 1,
              'lights': lights, 'engine': 'Cycles CPU', 'samples': 24,
              'viewTransform': scene.view_settings.view_transform,
              'look': scene.view_settings.look, 'exposure': scene.view_settings.exposure,
              'gamma': scene.view_settings.gamma,
              'worldBackgroundColor': list(background.inputs[0].default_value),
              'worldBackgroundStrength': background.inputs[1].default_value,
              'readOnlySource': True, 'artisticAcceptance': False,
              'visualParityInspected': False}
    (output / 'review.json').write_text(json.dumps(result, indent=2) + '\n', newline='\n')
    print('KRAG_COHERENT_MATERIAL_REVIEW_COMPLETE ' + args.side, flush=True)


if __name__ == '__main__':
    main()
