"""Coordinated whole-face and oral-volume candidate; actual review is mandatory."""
import os
os.environ.setdefault('OMP_NUM_THREADS', '2')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '2')
from pathlib import Path
import sys, json, hashlib
import numpy as np
import bpy
from mathutils import Matrix
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[3]
ART = ROOT/'benchmark/art/krag'
for folder in (HERE, HERE.parent/'ironjaw_wip', HERE.parent/'landmark_wip', HERE.parent/'v9n_wip',
               ROOT/'benchmark/tools/animation/krag_hand_rebuild'):
    sys.path.insert(0, str(folder))
from replacement_surface import coordinates, signature
from landmark_relief import Relief
from macro_envelope_v9nb import surface_report
from profile_and_lip import membership
from whole_face_v9v import WholeFace
from oral_fit_v9va import fit_volume, lip_residual
from morph_drivers import contract as driver_contract

sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
SOURCE = ART/'Krag_ContinuousMandible_v9u_WIP.blend'
EXPECTED = '7c6d88870a8ac46112708147bce98f44b3516387a462b7536ccb117bf0883f19'
OUTPUT = ART/'Krag_WholeFaceOral_v9va_WIP.blend'
if sha(SOURCE) != EXPECTED or OUTPUT.exists():
    raise RuntimeError('Source pin mismatch or actual output already exists')
prepared = json.loads((ART/'oral-volume-study/prepared-whole-face-v9va.json').read_text())
for entry in prepared['pins']:
    if sha(ROOT/entry['path']) != entry['sha256']:
        raise RuntimeError('Prepared recipe changed: '+entry['path'])
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
rig = bpy.data.objects['Krag_Rig']
modules = {o.get('module'): o for o in bpy.data.objects if o.type == 'MESH' and o.get('module')}
head, face, oral = [modules[n] for n in ('Head', 'Face', 'MouthInterior')]
affected = {head, face, oral}


def preserved():
    digest = hashlib.sha256()
    for obj in sorted((o for o in bpy.data.objects if o.type == 'MESH'), key=lambda o: o.name):
        mesh = obj.data
        digest.update(obj.name.encode())
        digest.update(np.asarray(obj.matrix_world, float).tobytes())
        if obj not in affected:
            digest.update(json.dumps(signature(mesh), sort_keys=True).encode())
        digest.update(json.dumps([list(p.vertices) for p in mesh.polygons]).encode())
        digest.update(np.asarray([p.material_index for p in mesh.polygons], np.int32).tobytes())
        for uv in mesh.uv_layers:
            digest.update(uv.name.encode())
            digest.update(np.asarray([entry.uv[:] for entry in uv.data], np.float32).tobytes())
        digest.update(json.dumps([[(g.group, g.weight) for g in vertex.groups] for vertex in mesh.vertices]).encode())
        if mesh.shape_keys:
            digest.update(json.dumps(driver_contract(mesh.shape_keys), sort_keys=True).encode())
    for bone in rig.data.bones:
        digest.update(bone.name.encode())
        digest.update(np.asarray(bone.matrix_local, float).tobytes())
    for action in sorted(bpy.data.actions, key=lambda a: a.name):
        digest.update(action.name.encode())
        for layer in action.layers:
            for strip in layer.strips:
                for slot in action.slots:
                    bag = strip.channelbag(slot)
                    if not bag:
                        continue
                    for curve in bag.fcurves:
                        digest.update(curve.data_path.encode()); digest.update(str(curve.array_index).encode())
                        for key in curve.keyframe_points:
                            digest.update(np.asarray(key.co, float).tobytes())
                            digest.update(np.asarray(key.handle_left, float).tobytes())
                            digest.update(np.asarray(key.handle_right, float).tobytes())
                            digest.update(key.interpolation.encode())
    return digest.hexdigest()


before = preserved()
rig.animation_data.action = None
for bone in rig.pose.bones:
    bone.matrix_basis = Matrix.Identity(4)
bpy.context.view_layer.update()
hp = coordinates(head.data, 'Basis').astype(float)
edges = np.asarray([edge.vertices[:] for edge in head.data.edges], int)
optical = Relief(); held = optical.head_support == 0
head.data.calc_loop_triangles()
triangles = np.asarray([t.vertices[:] for t in head.data.loop_triangles])
preflight = json.loads((ART/'oral-volume-study/whole-face-v9v-preflight.json').read_text())
if hashlib.sha256(hp.astype(np.float32).tobytes()).hexdigest() != preflight['sourceCoordinateReconstructionSha256']:
    raise RuntimeError('Actual saved neutral Head differs from the lightweight reconstruction')
tissue = WholeFace(hp, edges, membership(head.data), triangles, held)
after = tissue.head(hp)
if not np.array_equal(after[held], hp[held]):
    raise RuntimeError('Mandibular fit changed the actual ocular loops')
head.data.calc_loop_triangles()
surface = surface_report(hp, after, np.asarray([triangle.vertices[:] for triangle in head.data.loop_triangles]))
maximum_morph_delta_error = 0.
for key in head.data.shape_keys.key_blocks:
    points = coordinates(head.data, key.name).astype(float)
    revised = tissue.head(points)
    if not np.array_equal(revised[tissue.held], points[tissue.held]):
        raise RuntimeError('Mandibular fit changed protected points in '+key.name)
    rounded = revised.astype(np.float32).astype(float)
    expected_delta = points-hp
    actual_delta = rounded-after.astype(np.float32).astype(float)
    maximum_morph_delta_error = max(maximum_morph_delta_error, float(np.linalg.norm(actual_delta-expected_delta, axis=1).max()))
    if maximum_morph_delta_error > .0000003:
        raise RuntimeError('Existing relative expression delta changed beyond float32 rounding')
    key.data.foreach_set('co', rounded.astype(np.float32).ravel())
head.data.vertices.foreach_set('co', after.astype(np.float32).ravel()); head.data.update()
print('KRAG_WHOLE_FACE_V9VA_NEUTRAL_COMPLETE', flush=True)
oral_volume = fit_volume(head, face, oral)
opening = lip_residual(head, rig, held)
print('KRAG_WHOLE_FACE_V9VA_ORAL_COMPLETE', flush=True)
for obj in affected:
    if obj.data.has_custom_normals:
        obj.data.normals_split_custom_set([(0., 0., 0.)]*len(obj.data.loops)); obj.data.update()
if preserved() != before:
    raise RuntimeError('Mandibular authoring changed unrelated coordinates, bind/actions, UV/topology or corrective drivers')
expected_shapes = {obj['module']: signature(obj.data) for obj in affected}
expected_weights = [[(group.group, group.weight) for group in vertex.groups] for vertex in head.data.vertices]
for name in ('build_whole_face_v9va.py', 'whole_face_v9v.py', 'oral_fit_v9va.py', 'paired_lip_curve.py'):
    block = bpy.data.texts.new('WholeFaceV9va/'+name); block.write((HERE/name).read_text())
rig.animation_data.action = bpy.data.actions['Idle']; bpy.context.scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT), compress=True)
bpy.ops.wm.open_mainfile(filepath=str(OUTPUT))
rig = bpy.data.objects['Krag_Rig']
modules = {o.get('module'): o for o in bpy.data.objects if o.type == 'MESH' and o.get('module')}
head, face, oral = [modules[n] for n in ('Head', 'Face', 'MouthInterior')]
affected = {head, face, oral}
if preserved() != before or any(signature(o.data) != expected_shapes[o['module']] for o in affected):
    raise RuntimeError('Saved/reopened source failed its exact preservation contract')
if expected_weights != [[(group.group, group.weight) for group in vertex.groups] for vertex in head.data.vertices]:
    raise RuntimeError('Saved mandibular weights changed')
if sha(SOURCE) != EXPECTED:
    raise RuntimeError('Input source changed')
result = {'status': 'Actual coordinated facial planes and provisional oral volume; all visual gates remain open',
          'artisticAcceptance': False, 'sharedPromotion': False,
          'input': {'path': SOURCE.relative_to(ROOT).as_posix(), 'sha256': EXPECTED},
          'source': {'path': OUTPUT.relative_to(ROOT).as_posix(), 'sha256': sha(OUTPUT)},
          'neutralSurface': surface, 'wholeFace': tissue.report, 'oralVolume': oral_volume, 'pairedLipOpening': opening,
          'relativeExpressionDeltaMaximumRoundingErrorMeters': maximum_morph_delta_error,
          'retainedTissueWeightsFullJawRange': True, 'savedReopenedChecksPassed': True,
          'preservationContractSha256': before, 'recipePins': prepared['pins'],
          'motionLineage': 'Preserved pre-v4 v9u actions; not the frozen coherent68 engine candidate',
          'pending': ['Actual neutral/profile/full open mouth', 'Dental/lip/canine contact', 'Concept likeness', 'Verified v4 merge before any engine promotion']}
(ART/'whole-face-v9va.json').write_text(json.dumps(result, indent=2)+'\n', newline='\n')
print('KRAG_WHOLE_FACE_V9VA_SOURCE_COMPLETE', flush=True)
