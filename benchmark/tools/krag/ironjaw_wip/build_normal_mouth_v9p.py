"""Measured lip/arch relationship repair at the unchanged full jaw range."""
from pathlib import Path
import sys, hashlib, json
import numpy as np
import bpy
from mathutils import Matrix

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
ART = ROOT/'benchmark/art/krag'
sys.path.insert(0, str(HERE))
from anatomical_exclusion import _distance
from replacement_surface import coordinates, signature
from attachment_cuff import copy_driver
from natural_tusk_rotation import apply as fit_tusks
SOURCE = ART/'Krag_LandmarkRelief_v9o_WIP.blend'
EXPECTED = '93661a93f12ab2510bed8d8746452b14573edc71b61b943c53f1c36db2d1bc86'
OUTPUT = ART/'Krag_NormalMouth_v9p_WIP.blend'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(SOURCE) == EXPECTED
if OUTPUT.exists():
    raise RuntimeError('Preserve actual earlier mouth evidence')
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
rig = bpy.data.objects['Krag_Rig']
rig.animation_data.action = None
for bone in rig.pose.bones:
    bone.matrix_basis = Matrix.Identity(4)
bpy.context.view_layer.update()
modules = {o.get('module'): o for o in bpy.data.objects if o.type == 'MESH' and o.get('module')}
head, face, oral = [modules[name] for name in ['Head', 'Face', 'MouthInterior']]


def preserved():
    h = hashlib.sha256()
    for obj in sorted(modules.values(), key=lambda o: o.name):
        if obj in [head, face, oral]:
            continue
        h.update(obj.name.encode())
        h.update(json.dumps(signature(obj.data), sort_keys=True).encode())
    for bone in rig.data.bones:
        h.update(bone.name.encode())
        h.update(np.asarray(bone.matrix_local, float).tobytes())
    for action in sorted(bpy.data.actions, key=lambda a: a.name):
        h.update(action.name.encode())
        for layer in action.layers:
            for strip in layer.strips:
                for slot in action.slots:
                    bag = strip.channelbag(slot)
                    if bag:
                        for curve in bag.fcurves:
                            h.update(curve.data_path.encode())
                            h.update(str(curve.array_index).encode())
                            for key in curve.keyframe_points:
                                h.update(np.asarray(key.co, float).tobytes())
    return h.hexdigest()


before = preserved()
head_before = signature(head.data)
oral_before = signature(oral.data)
if not np.allclose(np.asarray(head.matrix_world), np.eye(4), atol=1e-7):
    raise RuntimeError('Expected established world-space head data')
basis = coordinates(head.data, 'Basis').astype(float)
old_delta = coordinates(head.data, 'JawOpen').astype(float)-basis
sets = np.asarray([item.value for item in head.data.attributes['.sculpt_face_set'].data], int)
tags = np.zeros(len(basis), np.uint64)
for polygon, tag in zip(head.data.polygons, sets):
    tags[list(polygon.vertices)] |= np.uint64(1) << np.uint64(tag)
member = lambda tag: (tags & (np.uint64(1) << np.uint64(tag))) != 0
upper = member(33) & member(7)
lower = member(24) & member(7)
corners = upper & lower
if corners.sum() != 2:
    raise RuntimeError('True two-corner oral topology absent')
edges = np.asarray([edge.vertices[:] for edge in head.data.edges], int)
allowed = np.ones(len(basis), bool)
du, dl, dc = [_distance(basis, edges, seeds, allowed) for seeds in [upper, lower, corners]]
fade = np.clip(dc/.014, 0, 1)
fade = fade*fade*(3-2*fade)
total = np.maximum(du+dl, 1e-12)
up = np.exp(-(du/.026)**2)*(dl/total)**2*fade
lo = np.exp(-(dl/.035)**2)*(du/total)**2*fade
new_delta = old_delta*(1-np.maximum(up, lo))[:, None]
new_delta[:, 2] += .006*up-.0018*lo
new_delta[:, 1] += .0015*up-.0008*lo
change = new_delta-old_delta
if np.linalg.norm(change, axis=1).max() > .020:
    raise RuntimeError('Lip-only corrective revision exceeds20mm change bound')
head.data.shape_keys.key_blocks['JawOpen'].data.foreach_set('co', (basis+new_delta).astype(np.float32).ravel())
head.data.update()
head_after = signature(head.data)
if any(head_after[name] != value for name, value in head_before.items() if name != 'JawOpen'):
    raise RuntimeError('Lip corrective altered neutral or unrelated head shape coordinates')

# The tongue remains behind the lower dental arch. Only the open-mouth muscular
# shape changes; neutral dental/gum/tongue geometry and all bone bindings stay.
obasis = coordinates(oral.data, 'Basis').astype(float)
tongue_ids = np.unique(np.concatenate([np.asarray(p.vertices) for p in oral.data.polygons
                                     if oral.data.materials[p.material_index].name == 'Krag_OralTongue']))
tongue = obasis[tongue_ids]
t = np.clip((tongue[:, 1].max()-tongue[:, 1])/np.ptp(tongue[:, 1]), 0, 1)
oral_delta = np.zeros_like(obasis)
oral_delta[tongue_ids, 2] = .005*np.sin(np.pi*t)**.7
oral_delta[tongue_ids, 1] = -.002*t
if 'JawOpen' in oral.data.shape_keys.key_blocks:
    raise RuntimeError('Unexpected existing oral JawOpen target; inspect before replacing')
key = oral.shape_key_add(name='JawOpen', from_mix=False)
key.data.foreach_set('co', (obasis+oral_delta).astype(np.float32).ravel())
source_key = head.data.shape_keys.key_blocks['JawOpen']
driver = next(d for d in head.data.shape_keys.animation_data.drivers if d.data_path == source_key.path_from_id('value'))
copy_driver(driver, key)
if signature(oral.data)['Basis'] != oral_before['Basis']:
    raise RuntimeError('Tongue corrective changed the neutral bite')

# Actual geometry proved full-size crowns behind the lip and tusks behind the
# muzzle. Keep teeth fixed; rotate each existing tusk rigidly about its fitted
# gingival root instead of enlarging it or making another stretched hook.
tusks = fit_tusks(head, face)
assert preserved() == before, 'Unrelated source, actual bind or action curves changed'
for file in [Path(__file__), HERE/'natural_tusk_rotation.py']:
    block = bpy.data.texts.new('NormalMouthV9p/'+file.name)
    block.write(file.read_text())
rig.animation_data.action = bpy.data.actions['Idle']
bpy.context.scene.frame_set(1)
expected_affected = {name: signature(modules[name].data) for name in ['Head', 'Face', 'MouthInterior']}
bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT), compress=True)
bpy.ops.wm.open_mainfile(filepath=str(OUTPUT))
rig = bpy.data.objects['Krag_Rig']
modules = {o.get('module'): o for o in bpy.data.objects if o.type == 'MESH' and o.get('module')}
head, face, oral = [modules[name] for name in ['Head', 'Face', 'MouthInterior']]
if preserved() != before:
    raise RuntimeError('Saved source changed preserved geometry/bind/actions')
if any(signature(modules[name].data) != values for name, values in expected_affected.items()):
    raise RuntimeError('Saved source did not retain authored lip/tongue/tusk coordinates')
rig.animation_data.action = bpy.data.actions['FacePerformance']
bpy.context.scene.frame_set(146)
bpy.context.view_layer.update()
head_value = head.data.shape_keys.key_blocks['JawOpen'].value
oral_value = oral.data.shape_keys.key_blocks['JawOpen'].value
if head_value < .9 or abs(head_value-oral_value) > 1e-6:
    raise RuntimeError('Reopened tongue control does not match portable JawOpen activation')
assert sha(SOURCE) == EXPECTED
result = {'status': 'Actual full-range lip/tongue/tusk fit source; closed/open review required',
          'artisticAcceptance': False, 'sharedPromotion': False,
          'input': {'path': SOURCE.relative_to(ROOT).as_posix(), 'sha256': EXPECTED},
          'source': {'path': OUTPUT.relative_to(ROOT).as_posix(), 'sha256': sha(OUTPUT)},
          'measuredCause': 'The old lower-rim JawOpen correction shifted it backward10.94mm relative to the rigid lower dental arch; actual dental crowns already12–17mm high.',
          'maximumLipCorrectiveChangeMeters': float(np.linalg.norm(change, axis=1).max()),
          'neutralHeadAndDentalTongueGeometryExact': True,
          'newOralMorph': {'name': 'JawOpen', 'bone': 'Jaw', 'channel': 'rotationMagnitudeDegrees',
                           'start': 0, 'end': 25, 'maxWeight': 1,
                           'maximumDorsumLiftMeters': .005, 'maximumAnteriorShiftMeters': .002},
          'tusks': tusks, 'preservedBodyBindActionsOtherMeshes': before,
          'savedReopenedCoordinateBindActionChecksPassed': True,
          'reopenedFullRangeJawOpenWeights': {'Head': head_value, 'MouthInterior': oral_value},
          'jawRangeReduced': False, 'recipeHashes': {file.name: sha(file) for file in
                         [Path(__file__), HERE/'natural_tusk_rotation.py', HERE/'attachment_cuff.py']},
          'pending': ['Actual closed lip/dental/tusk contact', 'Actual full-range front/right opening and tongue-floor visibility',
                      'Brow/skin/cowl/armor and general final likeness remain unaccepted']}
(ART/'normal-mouth-v9p.json').write_text(json.dumps(result, indent=2)+'\n', newline='\n')
print('KRAG_NORMAL_MOUTH_V9P_SOURCE_COMPLETE', flush=True)
