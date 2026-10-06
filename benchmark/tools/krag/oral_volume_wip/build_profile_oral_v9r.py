"""Actual coherent oral/profile candidate; visual gates remain decisive."""
import os
os.environ.setdefault('OMP_NUM_THREADS', '2')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '2')
from pathlib import Path
import sys
import json
import hashlib
import numpy as np
import bpy
from mathutils import Matrix
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
ART = ROOT/'benchmark/art/krag'
for folder in (HERE, HERE.parent/'ironjaw_wip', HERE.parent/'landmark_wip', HERE.parent/'v9n_wip', HERE.parent/'reference_fit_wip'):
    sys.path.insert(0, str(folder))
from replacement_surface import coordinates, signature
from landmark_relief import Relief
from macro_envelope_v9nb import surface_report
from profile_and_lip import membership
from rest_profile_v9r import OralProfile
from posed_lip_corrective import apply as fit_open_lip
from stout_canines import apply as fit_canines
from commissure_support import refine as refine_commissures

SOURCE = ART/'Krag_NormalMouth_v9p_WIP.blend'
EXPECTED = '5be64281307b0d35541fb393311c63fcb95b4f7fdd38c2233249fb6a51d51d72'
OUTPUT = ART/'Krag_ProfileOral_v9r_WIP.blend'
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
assert sha(SOURCE) == EXPECTED
if OUTPUT.exists():
    raise RuntimeError('Preserve prior actual source evidence')
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
rig = bpy.data.objects['Krag_Rig']
modules = {o.get('module'): o for o in bpy.data.objects if o.type == 'MESH' and o.get('module')}
head, face, oral = [modules[n] for n in ('Head', 'Face', 'MouthInterior')]
affected = {head, face, oral}


def preserved():
    digest = hashlib.sha256()
    for obj in sorted((o for o in bpy.data.objects if o.type == 'MESH'), key=lambda o: o.name):
        if obj in affected:
            continue
        digest.update(obj.name.encode())
        digest.update(json.dumps(signature(obj.data), sort_keys=True).encode())
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
                        digest.update(curve.data_path.encode())
                        digest.update(str(curve.array_index).encode())
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
for obj in affected:
    if not np.allclose(np.asarray(obj.matrix_world), np.eye(4), atol=1e-7):
        raise RuntimeError('Expected source face/oral mesh coordinates in rig metres')
hp = coordinates(head.data, 'Basis').astype(float)
edges = np.asarray([edge.vertices[:] for edge in head.data.edges], int)
optical = Relief()
profile = OralProfile(hp, edges, membership(head.data), optical.eyes, optical.radii+.001,
                      optical.head_support == 0)
head_after = profile.head(hp)
held = optical.head_support == 0
if not np.array_equal(head_after[held], hp[held]):
    raise RuntimeError('Rest-profile fit moved held optical return/contact vertices')
head.data.calc_loop_triangles()
metrics = surface_report(hp, head_after, np.asarray([t.vertices[:] for t in head.data.loop_triangles]))
for key in head.data.shape_keys.key_blocks:
    points = coordinates(head.data, key.name).astype(float)
    revised = profile.head(points)
    key.data.foreach_set('co', revised.astype(np.float32).ravel())
head.data.vertices.foreach_set('co', head_after.astype(np.float32).ravel())
head.data.update()
for key in oral.data.shape_keys.key_blocks:
    points = coordinates(oral.data, key.name).astype(float)
    key.data.foreach_set('co', (points+profile.oral_translation).astype(np.float32).ravel())
oral.data.vertices.foreach_set('co', coordinates(oral.data, 'Basis').ravel())
oral.data.update()
# Keep the rigid optical assembly exact. Move only the existing Jaw-owned
# crown components with their arch before replacing their rejected hook form.
jaw_index = face.vertex_groups['Jaw'].index
crown_ids = [v.index for v in face.data.vertices if any(g.group == jaw_index and g.weight > .999 for g in v.groups)]
for key in face.data.shape_keys.key_blocks:
    points = coordinates(face.data, key.name).astype(float)
    points[crown_ids] += profile.oral_translation
    key.data.foreach_set('co', points.astype(np.float32).ravel())
face.data.vertices.foreach_set('co', coordinates(face.data, 'Basis').ravel())
face.data.update()
print('KRAG_V9R_COHERENT_REST_PROFILE_COMPLETE', flush=True)
crowns = fit_canines(head, face, oral)
print('KRAG_V9R_TRUE_RIM_CANINES_COMPLETE', flush=True)
# Retain the proven finite-slope corner support from the rejected neutral
# reference fit without inheriting that fit's compressed orbital geometry.
commissures = refine_commissures(head.data, head, head_after)
lip = fit_open_lip(head, rig)
print('KRAG_V9R_POSED_LIP_RESIDUAL_COMPLETE', flush=True)
for obj in affected:
    if obj.data.has_custom_normals:
        obj.data.normals_split_custom_set([(0., 0., 0.)]*len(obj.data.loops))
        obj.data.update()
if preserved() != before:
    raise RuntimeError('Oral authoring changed unrelated geometry, bind or action data')
expected_shapes = {obj['module']: signature(obj.data) for obj in affected}
files = [Path(__file__), HERE/'profile_and_lip.py', HERE/'rest_profile_v9r.py',
         HERE/'posed_lip_corrective.py', HERE/'stout_canines.py',
         HERE.parent/'reference_fit_wip/commissure_support.py']
for path in files:
    block = bpy.data.texts.new('ProfileOralV9r/'+path.name); block.write(path.read_text())
rig.animation_data.action = bpy.data.actions['Idle']; bpy.context.scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT), compress=True)
bpy.ops.wm.open_mainfile(filepath=str(OUTPUT))
rig = bpy.data.objects['Krag_Rig']
modules = {o.get('module'): o for o in bpy.data.objects if o.type == 'MESH' and o.get('module')}
head, face, oral = [modules[n] for n in ('Head', 'Face', 'MouthInterior')]
affected = {head, face, oral}
if preserved() != before or any(signature(o.data) != expected_shapes[o['module']] for o in affected):
    raise RuntimeError('Actual saved/reopened source failed coordinate/bind/action preservation')
assert sha(SOURCE) == EXPECTED
result = {'status': 'Actual coherent mouth/profile candidate; closed/open source views required',
          'artisticAcceptance': False, 'sharedPromotion': False,
          'input': {'path': SOURCE.relative_to(ROOT).as_posix(), 'sha256': EXPECTED},
          'source': {'path': OUTPUT.relative_to(ROOT).as_posix(), 'sha256': sha(OUTPUT)},
          'branchReason': 'Rejected v9qa orbital compression is not retained; start from exact preserved v9p',
          'restProfile': metrics, 'oralTranslationMeters': profile.oral_translation.tolist(),
          'heldOpticalVerticesExact': int(held.sum()), 'canines': crowns, 'posedLowerLip': lip,
          'commissureSupport': commissures,
          'motionLineage': 'Preserved pre-v4 actions from v9p/v9o; separate verified v4 merge is required before engine export',
          'allExistingBindActionsUnrelatedMeshesPreserved': before,
          'savedReopenedChecksPassed': True,
          'recipeHashes': {p.name: sha(p) for p in files},
          'pending': ['Actual normal lip/corner opening and dental/tusk emergence',
                      'Frontal/profile concept likeness and mandibular mass',
                      'Materials/cowl/armor and IronJaw compatibility remain unaccepted']}
(ART/'profile-oral-v9r.json').write_text(json.dumps(result, indent=2)+'\n', newline='\n')
print('KRAG_PROFILE_ORAL_V9R_SOURCE_COMPLETE', flush=True)
