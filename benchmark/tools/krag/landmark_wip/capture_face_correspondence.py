"""Read-only actual mesh projections for named concept landmark fitting.

The 65-degree comparison view is a labelled camera proposal, not a claim that
the illustrated reference has a calibrated orthographic camera.
"""
from pathlib import Path
import hashlib
import json
import math

import bpy
import numpy as np
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[4]
ART = ROOT / 'benchmark/art/krag'
SOURCE = ART / 'Krag_MacroFace_v9nc_WIP.blend'
EXPECTED = 'f581fff1e1022ac268a69cb9a7b2026c8aa9d8ffa5d4a2d4d974d612706a4299'
OUT = ART / 'landmarks-v9nc'
CONTRACT = ROOT / 'benchmark/local/candidates/krag-v9h-source/krag_asset_contract.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def coordinates(obj):
    data = obj.data.shape_keys.key_blocks['Basis'].data if obj.data.shape_keys else obj.data.vertices
    values = np.empty(len(data) * 3, np.float32)
    data.foreach_get('co', values)
    transform = np.asarray(obj.matrix_world, dtype=float)
    return values.reshape(-1, 3) @ transform[:3, :3].T + transform[:3, 3]


assert sha(SOURCE) == EXPECTED, 'Pinned source changed'
OUT.mkdir(parents=True, exist_ok=True)
if (OUT / 'projection-review.json').exists():
    raise RuntimeError('Refusing to overwrite an actual completed projection capture')
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene = bpy.context.scene
rig = bpy.data.objects['Krag_Rig']
if rig.animation_data:
    rig.animation_data.action = None
    for track in rig.animation_data.nla_tracks:
        track.mute = True
for bone in rig.pose.bones:
    bone.matrix_basis = Matrix.Identity(4)
for obj in bpy.data.objects:
    if obj.type == 'MESH' and obj.data.shape_keys:
        keys = obj.data.shape_keys
        if keys.animation_data:
            keys.animation_data.action = None
            for driver in keys.animation_data.drivers:
                driver.mute = True
        for key in keys.key_blocks:
            key.value = 0
bpy.context.view_layer.update()
off = json.loads(CONTRACT.read_text())['variants']['Krag_Natural']['off']
for obj in bpy.data.objects:
    if obj.type == 'MESH' and 'module' in obj:
        obj.hide_render = obj['module'] in off

cache = {}
modules = {}
for name in ('Head', 'Face', 'MouthInterior'):
    obj = next(o for o in bpy.data.objects if o.get('module') == name)
    mesh = obj.data
    points = coordinates(obj)
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    evaluated_mesh = evaluated.to_mesh()
    evaluated_values = np.empty(len(evaluated_mesh.vertices) * 3, np.float32)
    evaluated_mesh.vertices.foreach_get('co', evaluated_values)
    transform = np.asarray(evaluated.matrix_world, dtype=float)
    evaluated_world = evaluated_values.reshape(-1, 3) @ transform[:3, :3].T + transform[:3, 3]
    if evaluated_world.shape != points.shape:
        raise RuntimeError('Neutral evaluated topology differs from cached Basis: ' + name)
    neutral_error = float(np.linalg.norm(evaluated_world - points, axis=1).max())
    evaluated.to_mesh_clear()
    if neutral_error > .000002:
        raise RuntimeError('Rendered neutral surface differs from projection cache: ' + name + ' ' + str(neutral_error))
    mesh.calc_loop_triangles()
    cache[name + '_world'] = points
    cache[name + '_triangles'] = np.asarray([tri.vertices[:] for tri in mesh.loop_triangles], np.int32)
    cache[name + '_edges'] = np.asarray([edge.vertices[:] for edge in mesh.edges], np.int32)
    cache[name + '_triangle_materials'] = np.asarray([tri.material_index for tri in mesh.loop_triangles], np.int32)
    attribute = mesh.attributes.get('krag_reference_position')
    if attribute:
        values = np.empty(len(mesh.vertices) * 3, np.float32)
        attribute.data.foreach_get('vector', values)
        cache[name + '_reference'] = values.reshape(-1, 3)
    attribute = mesh.attributes.get('.sculpt_face_set')
    if attribute:
        tags = np.asarray([entry.value for entry in attribute.data], np.int32)
        cache[name + '_triangle_sets'] = tags[np.asarray([tri.polygon_index for tri in mesh.loop_triangles])]
        membership = np.zeros(len(points), np.uint64)
        for polygon, tag in zip(mesh.polygons, tags):
            membership[list(polygon.vertices)] |= np.uint64(1) << np.uint64(tag)
        cache[name + '_membership'] = membership
    groups = list(obj.vertex_groups)
    group_weights = np.zeros((len(points), len(groups)), np.float32)
    for vertex in mesh.vertices:
        for group in vertex.groups:
            group_weights[vertex.index, group.group] = group.weight
    cache[name + '_weights'] = group_weights
    modules[name] = {'object': obj.name, 'vertices': len(points),
                     'triangles': len(mesh.loop_triangles),
                     'evaluatedNeutralMaximumErrorMeters': neutral_error,
                     'weightGroups': [group.name for group in groups],
                     'materials': [material.name for material in mesh.materials]}

bone_data = {bone.name: {'headWorld': list(rig.matrix_world @ bone.head_local),
                        'tailWorld': list(rig.matrix_world @ bone.tail_local),
                        'matrixLocal': [list(row) for row in bone.matrix_local]}
             for bone in rig.data.bones
             if bone.name in ('Head', 'Neck', 'FaceRoot') or any(parent.name == 'FaceRoot' for parent in bone.parent_recursive)}
np.savez_compressed(OUT / 'actual-neutral-surface.npz', **cache)

scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 16
scene.render.resolution_x = 1000
scene.render.resolution_y = 1000
scene.render.resolution_percentage = 100
scene.render.pixel_aspect_x = scene.render.pixel_aspect_y = 1
for light in bpy.data.lights:
    light.color = (1, 1, 1)
if scene.world and scene.world.use_nodes:
    scene.world.node_tree.nodes['Background'].inputs[0].default_value = (.30, .30, .30, 1)

camera = scene.camera
camera.data.type = 'ORTHO'
camera.data.ortho_scale = .390
target = Vector((0, -.03, 1.900))
views = []
for name, yaw in [('TrueFront', 0.0), ('MatchedSide65', 65.0)]:
    angle = math.radians(yaw)
    camera.location = target + Vector((4 * math.sin(angle), -4 * math.cos(angle), 0))
    camera.rotation_euler = (target - camera.location).to_track_quat('-Z', 'Y').to_euler()
    bpy.context.view_layer.update()
    view = camera.matrix_world.inverted()
    projection = camera.calc_matrix_camera(bpy.context.evaluated_depsgraph_get(), x=1000, y=1000, scale_x=1, scale_y=1)
    clip = np.asarray(projection @ view, dtype=float)
    points = cache['Head_world']
    homogeneous = np.column_stack((points, np.ones(len(points)))) @ clip.T
    ndc = homogeneous[:, :3] / homogeneous[:, 3:4]
    pixels = np.column_stack(((ndc[:, 0] + 1) * 500, (1 - ndc[:, 1]) * 500))
    np.save(OUT / (name + '-head-pixels.npy'), pixels)
    image_path = OUT / ('Krag_' + name + '.png')
    scene.render.filepath = str(image_path)
    bpy.ops.render.render(write_still=True)
    assert image_path.exists() and image_path.stat().st_size > 10000
    metadata = {'name': name, 'yawDegreesFromFront': yaw, 'resolution': [1000, 1000],
                'orthoScaleMeters': camera.data.ortho_scale,
                'targetWorld': list(target), 'cameraWorld': [list(row) for row in camera.matrix_world],
                'worldToClip': clip.tolist(), 'pixelOrigin': 'top-left',
                'sourceSha256': EXPECTED, 'imageSha256': sha(image_path),
                'referenceCameraCalibration': 'Unknown; 65-degree side is a comparison proposal',
                'pose': 'All bone basis matrices identity; all shape weights zero; no retained Idle pose',
                'status': 'Actual source projection, artistic acceptance remains failed'}
    image_path.with_suffix('.meta.json').write_text(json.dumps(metadata, indent=2) + '\n', newline='\n')
    views.append(metadata)
    print('PROJECTION_VIEW_SAVED ' + name, flush=True)

assert sha(SOURCE) == EXPECTED, 'Read-only source checksum changed'
report = {'source': SOURCE.relative_to(ROOT).as_posix(), 'sourceSha256': EXPECTED,
          'toolSha256': sha(Path(__file__)), 'sourceSavedOrChanged': False,
          'artisticAcceptance': False, 'modules': modules, 'bones': bone_data,
          'views': views, 'surfaceCacheSha256': sha(OUT / 'actual-neutral-surface.npz'),
          'purpose': 'Named concept landmark and relief fitting on actual coherent topology; no new shape generated'}
(OUT / 'projection-review.json').write_text(json.dumps(report, indent=2) + '\n', newline='\n')
print('KRAG_REFERENCE_PROJECTION_COMPLETE', flush=True)
