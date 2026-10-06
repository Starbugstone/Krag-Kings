"""Neutral views of an actual unrigged pilot mesh; never modifies the source GLB."""
import argparse
import hashlib
import json
import math
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[3]
PILOT = ROOT / 'benchmark/local/triposr-reference-v1/pilot-krag-bust-v1'
SOURCE = PILOT / 'Krag_Bust_Reference.glb'
OUTPUT = PILOT / 'neutral-review'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    global PILOT, SOURCE, OUTPUT
    parser = argparse.ArgumentParser()
    parser.add_argument('--pilot-directory', type=Path, default=PILOT)
    parser.add_argument('--upright', action='store_true')
    import sys
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    PILOT = args.pilot_directory.resolve()
    SOURCE = PILOT/'Krag_Bust_Reference.glb'
    OUTPUT = PILOT/'neutral-review'
    receipt = json.loads((PILOT / 'pilot-result.json').read_text(encoding='utf-8'))
    if not receipt['status'].startswith('REFERENCE_GEOMETRY_GENERATED') or sha(SOURCE) != receipt['outputSha256']:
        raise RuntimeError('The actual pilot output does not match its receipt')
    if OUTPUT.exists():
        raise RuntimeError('Preserve the first actual mesh review')
    OUTPUT.mkdir()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(SOURCE))
    objects = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
    if not objects:
        raise RuntimeError('The saved GLB contains no imported mesh')
    if args.upright:
        # Undo Blender's glTF Y-up conversion for this generator's Z-up mesh.
        # This display-only transform is not written into the source GLB.
        rotation = Matrix.Rotation(-math.pi/2, 4, 'X')
        for obj in objects:
            obj.matrix_world = rotation @ obj.matrix_world
        bpy.context.view_layer.update()
    corners = [obj.matrix_world @ Vector(corner) for obj in objects for corner in obj.bound_box]
    lower = Vector([min(point[axis] for point in corners) for axis in range(3)])
    upper = Vector([max(point[axis] for point in corners) for axis in range(3)])
    center = (upper + lower) * .5
    span = max(upper - lower)
    if span <= 0:
        raise RuntimeError('Invalid imported bounds')
    for obj in objects:
        for polygon in obj.data.polygons:
            polygon.use_smooth = True
        for slot in obj.material_slots:
            if slot.material and slot.material.use_nodes:
                for node in slot.material.node_tree.nodes:
                    if node.type == 'BSDF_PRINCIPLED':
                        node.inputs['Metallic'].default_value = 0
                        node.inputs['Roughness'].default_value = .75
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 24
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 640
    scene.render.resolution_y = 640
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.film_transparent = False
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.exposure = 0
    scene.world = bpy.data.worlds.new('Neutral reference world')
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value = (.18, .18, .18, 1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value = .5
    camera_data = bpy.data.cameras.new('Reference camera')
    camera = bpy.data.objects.new('Reference camera', camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera_data.type = 'ORTHO'
    camera_data.ortho_scale = span * 1.30
    camera_data.clip_end = span * 20
    for label, position, power, size in [
        ('Key', (-2.8, -3.2, 4), 550, 3), ('Fill', (3, -1, 2), 260, 3),
        ('Back', (0, 3, 3), 350, 2),
    ]:
        data = bpy.data.lights.new(label, 'AREA')
        data.energy = power * span * span
        data.shape = 'DISK'
        data.size = span * size
        lamp = bpy.data.objects.new(label, data)
        scene.collection.objects.link(lamp)
        lamp.location = center + Vector(position) * span
        lamp.rotation_euler = (center - lamp.location).to_track_quat('-Z', 'Y').to_euler()
    clay = bpy.data.materials.new('Neutral geometry inspection')
    clay.use_nodes = True
    clay.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (.4, .4, .4, 1)
    clay.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = .8
    views = [
        ('AxisMinusY', (0, -3, .15)), ('QuarterMinusYPlusX', (2.1, -2.1, .6)),
        ('AxisPlusX', (3, 0, .15)), ('AxisPlusY', (0, 3, .15)),
        ('AxisMinusX', (-3, 0, .15)), ('AxisPlusZ', (0, -.01, 3)),
    ]
    if args.upright:
        views = [('InputFacingPlusX',(3,0,.12)), ('QuarterPlusXMinusY',(2.3,-1.8,.5)),
                 ('SideMinusY',(0,-3,.12)), ('InferredBackMinusX',(-3,0,.12))]
    images = []
    for mode, selected in [('VertexColor', views), ('Clay', views if args.upright else views[:2])]:
        scene.view_layers[0].material_override = clay if mode == 'Clay' else None
        for label, direction in selected:
            camera.location = center + Vector(direction) * span
            camera.rotation_euler = (center - camera.location).to_track_quat('-Z', 'Y').to_euler()
            path = OUTPUT / f'{mode}_{label}.png'
            scene.render.filepath = str(path)
            bpy.ops.render.render(write_still=True)
            images.append({'path':path.name, 'sha256':sha(path), 'mode':mode,
                           'cameraPosition':list(camera.location), 'axisLabel':label})
    if sha(SOURCE) != receipt['outputSha256']:
        raise RuntimeError('Review changed original pilot output')
    report = {'sourceSha256':sha(SOURCE), 'recipeSha256':sha(__file__),
              'sourceUnchanged':True, 'engineEvidence':False, 'artisticAcceptance':False,
              'orientation':'Axis labels refer to actual Blender GLB import; likeness/front assignment requires inspection.',
              'displayRotationXDegrees':-90 if args.upright else 0,
              'inferredRearIsCanonical':False,
              'render':'Cycles CPU, 24 samples, denoising, neutral white area lights, AgX, smooth display normals',
              'importedBounds':[list(lower), list(upper)], 'images':images}
    (OUTPUT / 'review.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print('TRIPOSR_REFERENCE_MESH_REVIEW_COMPLETE', flush=True)


if __name__ == '__main__':
    main()
