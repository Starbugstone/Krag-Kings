"""Actual mandibular tissue/canine candidate, isolated from the engine source."""
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
from posed_lip_corrective_v9s import apply as fit_open_lip
from mandibular_tissue_v9ta import MandibularTissue
from exterior_canines_v9t import apply as fit_canines
from morph_drivers import contract as driver_contract

sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
SOURCE = ART/'Krag_BroadOral_v9s_WIP.blend'
EXPECTED = 'bbe3deadd7d9507a027afc0474206ad8528de8820606539246bc3242ffd171fd'
OUTPUT = ART/'Krag_MandibularTissue_v9ta_WIP.blend'
if sha(SOURCE) != EXPECTED or OUTPUT.exists():
    raise RuntimeError('Source pin mismatch or actual output already exists')
prepared = json.loads((ART/'oral-volume-study/prepared-mandibular-v9ta.json').read_text())
for entry in prepared['pins']:
    if sha(ROOT/entry['path']) != entry['sha256']:
        raise RuntimeError('Prepared recipe changed: '+entry['path'])
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
rig = bpy.data.objects['Krag_Rig']
modules = {o.get('module'): o for o in bpy.data.objects if o.type == 'MESH' and o.get('module')}
head, face, oral = [modules[n] for n in ('Head', 'Face', 'MouthInterior')]
affected = {head, face}


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
        if obj != head:
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
tissue = MandibularTissue(hp, edges, membership(head.data))
after = tissue.head(hp)
if not np.array_equal(after[held], hp[held]):
    raise RuntimeError('Mandibular fit changed the actual ocular loops')
head.data.calc_loop_triangles()
surface = surface_report(hp, after, np.asarray([triangle.vertices[:] for triangle in head.data.loop_triangles]))
for key in head.data.shape_keys.key_blocks:
    points = coordinates(head.data, key.name).astype(float)
    revised = tissue.head(points)
    if not np.array_equal(revised[held | tissue.rim], points[held | tissue.rim]):
        raise RuntimeError('Mandibular fit changed protected points in '+key.name)
    key.data.foreach_set('co', revised.astype(np.float32).ravel())
head.data.vertices.foreach_set('co', after.astype(np.float32).ravel()); head.data.update()
groups = {name: head.vertex_groups[name] for name in ('Head', 'Jaw', 'Neck')}
lookup = {groups[name].index: i for i, name in enumerate(groups)}
weights = np.zeros((len(hp), 3))
for vertex in head.data.vertices:
    for item in vertex.groups:
        if item.group not in lookup:
            raise RuntimeError('Unexpected Head skin group')
        weights[vertex.index, lookup[item.group]] = item.weight
if abs(weights.sum(1)-1).max() > 1e-6:
    raise RuntimeError('Existing Head weights are not normalized')
new_jaw, support = tissue.weights(weights[:, 1], weights[:, 0]+weights[:, 1])
new_head = weights[:, 0]+weights[:, 1]-new_jaw
if new_head.min() < -1e-7:
    raise RuntimeError('Mandibular tissue overlaps retained Neck support')
for i in np.flatnonzero(abs(new_jaw-weights[:, 1]) > 1e-9):
    groups['Jaw'].add([int(i)], float(new_jaw[i]), 'REPLACE')
    groups['Head'].add([int(i)], float(max(0, new_head[i])), 'REPLACE')
print('KRAG_V9TA_TISSUE_COMPLETE', flush=True)
canines = fit_canines(head, face, oral)
lip = fit_open_lip(head, rig)
print('KRAG_V9TA_CANINES_POSED_LIP_COMPLETE', flush=True)
for obj in affected:
    if obj.data.has_custom_normals:
        obj.data.normals_split_custom_set([(0., 0., 0.)]*len(obj.data.loops)); obj.data.update()
if preserved() != before:
    raise RuntimeError('Mandibular authoring changed unrelated coordinates, bind/actions, UV/topology or corrective drivers')
expected_shapes = {obj['module']: signature(obj.data) for obj in affected}
expected_weights = [[(group.group, group.weight) for group in vertex.groups] for vertex in head.data.vertices]
for name in ('build_mandibular_v9ta.py', 'mandibular_tissue_v9ta.py', 'exterior_canines_v9t.py'):
    block = bpy.data.texts.new('MandibularV9ta/'+name); block.write((HERE/name).read_text())
rig.animation_data.action = bpy.data.actions['Idle']; bpy.context.scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT), compress=True)
bpy.ops.wm.open_mainfile(filepath=str(OUTPUT))
rig = bpy.data.objects['Krag_Rig']
modules = {o.get('module'): o for o in bpy.data.objects if o.type == 'MESH' and o.get('module')}
head, face, oral = [modules[n] for n in ('Head', 'Face', 'MouthInterior')]
affected = {head, face}
if preserved() != before or any(signature(o.data) != expected_shapes[o['module']] for o in affected):
    raise RuntimeError('Saved/reopened source failed its exact preservation contract')
if expected_weights != [[(group.group, group.weight) for group in vertex.groups] for vertex in head.data.vertices]:
    raise RuntimeError('Saved mandibular weights changed')
if sha(SOURCE) != EXPECTED:
    raise RuntimeError('Input source changed')
result = {'status': 'Actual mandibular tissue/canine source; neutral and full open views still required',
          'artisticAcceptance': False, 'sharedPromotion': False,
          'input': {'path': SOURCE.relative_to(ROOT).as_posix(), 'sha256': EXPECTED},
          'source': {'path': OUTPUT.relative_to(ROOT).as_posix(), 'sha256': sha(OUTPUT)},
          'neutralSurface': surface, 'mandibularSupport': support, 'exteriorCanines': canines,
          'posedLowerLip': lip, 'savedReopenedChecksPassed': True,
          'preservationContractSha256': before, 'recipePins': prepared['pins'],
          'motionLineage': 'Preserved pre-v4 v9s actions; not the frozen coherent68 engine candidate',
          'pending': ['Actual neutral/profile/full open mouth', 'Dental/lip/canine contact', 'Concept likeness', 'Verified v4 merge before any engine promotion']}
(ART/'mandibular-tissue-v9ta.json').write_text(json.dumps(result, indent=2)+'\n', newline='\n')
print('KRAG_MANDIBULAR_V9TA_SOURCE_COMPLETE', flush=True)
