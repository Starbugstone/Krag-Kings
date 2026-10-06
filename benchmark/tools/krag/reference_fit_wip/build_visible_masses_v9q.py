"""Actual existing-topology face fit, preserving the authored full-range rig."""
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
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent/'ironjaw_wip'))
sys.path.insert(0, str(HERE.parent/'v9n_wip'))
from fit_visible_masses import MassFit
from commissure_support import refine as refine_commissures
from replacement_surface import coordinates, signature
from macro_envelope_v9nb import surface_report
SOURCE = ART/'Krag_NormalMouth_v9p_WIP.blend'
EXPECTED = '5be64281307b0d35541fb393311c63fcb95b4f7fdd38c2233249fb6a51d51d72'
OUTPUT = ART/'Krag_VisibleMassFit_v9q_WIP.blend'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(SOURCE) == EXPECTED
if OUTPUT.exists():
    raise RuntimeError('Preserve actual previous candidate')
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
rig = bpy.data.objects['Krag_Rig']
rig.animation_data.action = None
for bone in rig.pose.bones:
    bone.matrix_basis = Matrix.Identity(4)
bpy.context.view_layer.update()
modules = {o.get('module'): o for o in bpy.data.objects if o.type == 'MESH' and o.get('module')}
affected = [modules[name] for name in ('Head', 'Face', 'MouthInterior')]


def preserved():
    h = hashlib.sha256()
    for obj in sorted(modules.values(), key=lambda o: o.name):
        if obj in affected:
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
fit = MassFit()
head = modules['Head']
prior_head = coordinates(head.data, 'Basis').astype(float)
if np.max(np.linalg.norm(prior_head-fit.points, axis=1)) > .0000004:
    raise RuntimeError('Actual neutral source differs from pinned cached face')
commissures = refine_commissures(head.data, head, prior_head)
contact = json.loads((ART/'landmarks-v9nc/contact-ring-topology.json').read_text())
contact_ids = np.unique([i for value in contact.values() for i in value['candidateRingVertexIds']])
changed = []
for obj in affected:
    if not np.allclose(np.asarray(obj.matrix_world), np.eye(4), atol=1e-7):
        raise RuntimeError('Face fit expects established world-space source meshes')
    mesh = obj.data
    prior = coordinates(mesh, 'Basis').astype(float)
    transform = fit.head if obj is head else fit.transform
    after = transform(prior)
    if obj is head and not np.array_equal(after[contact_ids], prior[contact_ids]):
        raise RuntimeError('Actual ocular-contact loop moved')
    if obj is modules['Face']:
        groups = {obj.vertex_groups[n].index for n in ('Eye_L', 'Eye_R')}
        ocular = [v.index for v in mesh.vertices if any(g.group in groups and g.weight > .99 for g in v.groups)]
        if not np.array_equal(after[ocular], prior[ocular]):
            raise RuntimeError('Actual fitted ocular surface changed')
    mesh.calc_loop_triangles()
    triangles = np.asarray([t.vertices[:] for t in mesh.loop_triangles], int)
    metrics = surface_report(prior, after, triangles)
    if float(np.linalg.norm(after-prior, axis=1).max()) > .035:
        raise RuntimeError('Visible mass fit exceeds35mm bounded correction')
    for key in mesh.shape_keys.key_blocks:
        points = coordinates(mesh, key.name).astype(float)
        revised = after if key.name == 'Basis' else transform(points)
        key.data.foreach_set('co', revised.astype(np.float32).ravel())
    mesh.vertices.foreach_set('co', after.astype(np.float32).ravel())
    mesh.update()
    if mesh.has_custom_normals:
        mesh.normals_split_custom_set([(0., 0., 0.)]*len(mesh.loops))
        mesh.update()
    changed.append({'module': obj['module'], 'neutralSurface': metrics})
    print('REFERENCE_MASS_MODULE_COMPLETE '+obj['module'], flush=True)
assert preserved() == before, 'Unrelated geometry, any bind or action curves changed'
expected_shapes = {o['module']: signature(o.data) for o in affected}
for file in (Path(__file__), HERE/'fit_visible_masses.py', HERE/'reference_landmarks.py', HERE/'commissure_support.py'):
    block = bpy.data.texts.new('VisibleMassFitV9q/'+file.name)
    block.write(file.read_text())
rig.animation_data.action = bpy.data.actions['Idle']
bpy.context.scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT), compress=True)
bpy.ops.wm.open_mainfile(filepath=str(OUTPUT))
rig = bpy.data.objects['Krag_Rig']
modules = {o.get('module'): o for o in bpy.data.objects if o.type == 'MESH' and o.get('module')}
affected = [modules[name] for name in ('Head', 'Face', 'MouthInterior')]
if preserved() != before or any(signature(o.data) != expected_shapes[o['module']] for o in affected):
    raise RuntimeError('Saved/reopened source did not preserve declared mesh/bind/action contracts')
assert sha(SOURCE) == EXPECTED
result = {'status': 'Actual coherent-topology reference-mass fit; neutral and full-range mouth inspection required',
          'artisticAcceptance': False, 'sharedPromotion': False,
          'input': {'path': SOURCE.relative_to(ROOT).as_posix(), 'sha256': EXPECTED},
          'source': {'path': OUTPUT.relative_to(ROOT).as_posix(), 'sha256': sha(OUTPUT)},
          'referenceSha256': fit.reference['referenceSha256'],
          'referenceUse': 'Inspected near-side visible broad masses only; no GLB topology/noise/eyes/teeth/rear transferred',
          'scaleNormalizedToMeters': fit.scale, 'flowDuration': .85,
          'actualOcularContactVerticesFixed': len(contact_ids), 'ocularGeometryExact': True,
          'commissureSupport': commissures, 'changedModules': changed,
          'allBindActionsUnrelatedMeshesPreserved': before, 'savedReopenedChecksPassed': True,
          'recipeHashes': {file.name: sha(file) for file in (Path(__file__), HERE/'fit_visible_masses.py', HERE/'reference_landmarks.py', HERE/'commissure_support.py')},
          'pending': ['Actual frontal/profile clay concept likeness', 'Full-range lip/chin/corner volume',
                      'Short broad natural tusk crown/root refit; existing hooks remain unaccepted',
                      'Material/cowl/armor construction and mechanical jaw compatibility']}
(ART/'visible-mass-fit-v9q.json').write_text(json.dumps(result, indent=2)+'\n', newline='\n')
print('KRAG_VISIBLE_MASS_FIT_V9Q_SOURCE_COMPLETE', flush=True)
