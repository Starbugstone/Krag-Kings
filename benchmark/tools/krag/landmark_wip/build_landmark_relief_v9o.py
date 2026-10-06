"""Isolated named-landmark facial sculpt; actual clay/material review required."""
import os
os.environ.setdefault('OMP_NUM_THREADS', '2')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '2')
from pathlib import Path
import sys, hashlib, json
import bpy
import numpy as np
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
ART = ROOT / 'benchmark/art/krag'
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / 'v9n_wip'))
from landmark_relief import Relief, pick
from macro_envelope_v9nb import surface_report

SOURCE = ART / 'Krag_MacroFace_v9nc_WIP.blend'
EXPECTED = 'f581fff1e1022ac268a69cb9a7b2026c8aa9d8ffa5d4a2d4d974d612706a4299'
OUTPUT = ART / 'Krag_LandmarkRelief_v9o_WIP.blend'
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
assert sha(SOURCE) == EXPECTED
if OUTPUT.exists():
    raise RuntimeError('Refusing to replace actual sculpt evidence')
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
rig = bpy.data.objects['Krag_Rig']
rig.animation_data.action = None
for bone in rig.pose.bones:
    bone.matrix_basis = Matrix.Identity(4)
bpy.context.view_layer.update()
modules = {o.get('module'): o for o in bpy.data.objects if o.type == 'MESH' and o.get('module')}
affected = [modules[name] for name in ('Head', 'Face', 'MouthInterior')]
facial = {bone.name for bone in rig.data.bones if any(parent.name == 'FaceRoot' for parent in bone.parent_recursive)}


def coords(mesh, name='Basis'):
    data = mesh.shape_keys.key_blocks[name].data if mesh.shape_keys else mesh.vertices
    values = np.empty(len(data)*3, np.float32)
    data.foreach_get('co', values)
    return values.reshape(-1, 3).astype(float)


def world(obj, points):
    m = np.asarray(obj.matrix_world, float)
    return points @ m[:3, :3].T+m[:3, 3]


def local(obj, points):
    m = np.asarray(obj.matrix_world.inverted(), float)
    return points @ m[:3, :3].T+m[:3, 3]


def fingerprint():
    h = hashlib.sha256()
    for obj in sorted((obj for obj in modules.values() if obj not in affected), key=lambda o: o.name):
        h.update(obj.name.encode())
        h.update(coords(obj.data).astype(np.float32).tobytes())
        for key in obj.data.shape_keys.key_blocks if obj.data.shape_keys else []:
            h.update(key.name.encode())
            h.update(coords(obj.data, key.name).astype(np.float32).tobytes())
    for bone in rig.data.bones:
        if bone.name not in facial:
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


preserved = fingerprint()
fit = Relief()
head = modules['Head']
head_points = world(head, coords(head.data))
if not np.array_equal(head_points, fit.points):
    raise RuntimeError('Saved source no longer matches actual neutral projection cache')
head_after = fit.transform_head(head_points)
metrics = surface_report(head_points, head_after, fit.triangles)
if metrics['maxDisplacementMeters'] > .035:
    raise RuntimeError('Named anatomical relief exceeds35mm bound')
fixed = fit.head_support == 0
if not np.array_equal(head_points[fixed], head_after[fixed]):
    raise RuntimeError('Fitted lid/contact surfaces moved')
changed = []
for obj in affected:
    mesh = obj.data
    transform = fit.transform_head if obj is head else fit.transform
    prior = world(obj, coords(mesh))
    after = transform(prior)
    if obj is modules['Face']:
        ocular_groups = {obj.vertex_groups[name].index for name in ('Eye_L', 'Eye_R')}
        ocular = [v.index for v in mesh.vertices if any(g.group in ocular_groups and g.weight > .99 for g in v.groups)]
        if not ocular or not np.array_equal(after[ocular], prior[ocular]):
            raise RuntimeError('Rigid fitted ocular surfaces changed')
    mesh.calc_loop_triangles()
    module_metrics = surface_report(prior, after, np.asarray([tri.vertices[:] for tri in mesh.loop_triangles], int))
    for key in mesh.shape_keys.key_blocks if mesh.shape_keys else []:
        values = local(obj, transform(world(obj, coords(mesh, key.name))))
        key.data.foreach_set('co', values.astype(np.float32).ravel())
    mesh.vertices.foreach_set('co', local(obj, after).astype(np.float32).ravel())
    mesh.update()
    if mesh.has_custom_normals:
        mesh.normals_split_custom_set([(0., 0., 0.)]*len(mesh.loops))
        mesh.update()
    changed.append({'module': obj['module'], 'vertices': len(mesh.vertices),
                    'maximumDisplacementMeters': float(np.linalg.norm(after-prior, axis=1).max()),
                    'neutralSurfaceMetrics': module_metrics})

# Move expressive surface-control pivots by the same corresponding surface
# displacement. Keep globe/lid pivots, mandibular hinge, tongue and FaceRoot
# exact; they define preserved contact and whole-mouth articulation.
control_sites = {'BrowInner_L': 'brow_medial_mass_L', 'BrowInner_R': 'brow_medial_mass_R',
                 'BrowOuter_L': 'brow_lateral_mass_L', 'BrowOuter_R': 'brow_lateral_mass_R',
                 'Cheek_L': 'upper_cheek_crest_L', 'Cheek_R': 'upper_cheek_crest_R',
                 'LipUpper': 'upper_lip_center', 'LipLower': 'lower_lip_center',
                 'NoseTip': 'nasal_tip'}
handle_delta = {h['name']: np.asarray(h['target'])-np.asarray(h['source']) for h in fit.handles}
bpy.ops.object.select_all(action='DESELECT')
rig.select_set(True)
bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode='EDIT')
pivot_changes = []
for name, handle in control_sites.items():
    bone = rig.data.edit_bones[name]
    bone.use_connect = False
    delta = handle_delta[handle]
    shift = rig.matrix_world.inverted().to_3x3() @ Vector(delta)
    bone.head += shift
    bone.tail += shift
    pivot_changes.append({'bone': name, 'surfaceHandle': handle, 'translationWorldMeters': delta.tolist()})
bpy.ops.object.mode_set(mode='OBJECT')
bpy.context.view_layer.update()
assert fingerprint() == preserved, 'Unrelated source geometry, body bind or action curves changed'
for path in (Path(__file__), HERE / 'landmark_relief.py'):
    block = bpy.data.texts.new('v9o_landmark_relief/'+path.name)
    block.write(path.read_text())
rig.animation_data.action = bpy.data.actions['Idle']
bpy.context.scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT), compress=True)
assert sha(SOURCE) == EXPECTED
report = {'status': 'Actual named-landmark sculpt; clay/material and expression review required',
          'artisticAcceptance': False, 'sharedPromotion': False,
          'input': {'path': SOURCE.relative_to(ROOT).as_posix(), 'sha256': EXPECTED},
          'source': {'path': OUTPUT.relative_to(ROOT).as_posix(), 'sha256': sha(OUTPUT)},
          'recipeHashes': {path.name: sha(path) for path in (Path(__file__), HERE/'landmark_relief.py')},
          'referenceProjection': 'landmarks-v9nc/projection-review.json',
          'targetDepthsAreAuthoredProposalsNotCalibratedReferenceDimensions': True,
          'handles': fit.handles, 'surface': metrics, 'contact': fit.contact_report,
          'exactFixedOcularVertexCount': int(fixed.sum()), 'changedModules': changed,
          'surfaceControlPivotChanges': pivot_changes,
          'preservedBodyBindActionsEquipmentFingerprint': preserved,
          'pending': ['Actual clay frontal and side likeness', 'Material portrait',
                      'Blink and serious open-mouth contact after sculpt',
                      'Fitted short tusk emergence after facial planes',
                      'Cowl and armor/clothing construction, skin material scale']}
(ART/'landmark-relief-v9o.json').write_text(json.dumps(report, indent=2)+'\n', newline='\n')
print('KRAG_LANDMARK_RELIEF_V9O_SOURCE_COMPLETE', flush=True)
