"""Bounded saved-source oral repair after actual v9h contact attribution.

Preserves body motion and the external neutral face. Broader lower-rim Jaw
transition rounds the aperture; oral floor/roof receive anatomical anchors.
Provisional dental/gum arcs are refitted within the real lip envelope. Actual
neutral/open renders are required; no runtime export occurs here.
"""
from pathlib import Path
import sys, json, hashlib
import numpy as np
import bpy
from mathutils import Matrix

HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE)); import semantic_jaw_v2
ART = ROOT / 'benchmark/art/krag'
SOURCE = ART / 'Krag_Master_v9h_WIP.blend'
OUTPUT = ART / 'Krag_MouthContact_v9i_WIP.blend'
EXPECTED = '5f89b7f1492c46e8ff3a1d9d90bd725ca7353c5474bf93af01a7dd6b2493234e'
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == EXPECTED
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
rig = bpy.data.objects['Krag_Rig']; rig.animation_data.action = None
for pb in rig.pose.bones: pb.matrix_basis = Matrix.Identity(4)
bpy.context.view_layer.update()
modules = {o.get('module'): o for o in bpy.data.objects if o.type == 'MESH' and 'module' in o}
head = modules['Head']; mesh = head.data
raw = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
mesh.attributes['krag_reference_position'].data.foreach_get('vector', raw); raw = raw.reshape(-1, 3)
sets = np.asarray([x.value for x in mesh.attributes['.sculpt_face_set'].data])
faces = [tuple(p.vertices) for p in mesh.polygons]; edges = np.asarray([tuple(e.vertices) for e in mesh.edges])
neck = np.zeros(len(raw)); old_jaw = np.zeros(len(raw))
groups = {name: head.vertex_groups[name] for name in ['Head', 'Jaw', 'Neck']}
for vertex in mesh.vertices:
    for entry in vertex.groups:
        if entry.group == groups['Neck'].index: neck[vertex.index] = entry.weight
        elif entry.group == groups['Jaw'].index: old_jaw[vertex.index] = entry.weight
new_jaw, statistics = semantic_jaw_v2.calculate(raw, faces, sets, edges, neck)
for i, value in enumerate(new_jaw):
    groups['Jaw'].add([i], float(value), 'REPLACE')
    groups['Head'].add([i], float(1 - neck[i] - value), 'REPLACE')
keys = mesh.shape_keys.key_blocks
basis = np.empty(len(raw) * 3, dtype=np.float32); keys['Basis'].data.foreach_get('co', basis); basis = basis.reshape(-1, 3)
old_key = np.empty_like(basis); keys['JawOpen'].data.foreach_get('co', old_key.ravel())
# The existing small chin corrective already had semantic mandibular support.
# Adjust that support only; this is not a recursive mixed-key construction.
ratio = np.zeros(len(raw)); valid = old_jaw > 1e-5
# Do not divide tiny quantized stored deltas into a large new corrective.
# New floor anchors move through the bone; the old small chin corrective is
# only attenuated where the broader corner transition has reduced support.
ratio[valid] = np.minimum(1, new_jaw[valid] / old_jaw[valid])
keys['JawOpen'].data.foreach_set('co', (basis + (old_key - basis) * ratio[:, None]).astype(np.float32).ravel())

def components(obj):
    neighbors = [[] for _ in obj.data.vertices]
    for edge in obj.data.edges:
        a, b = edge.vertices; neighbors[a].append(b); neighbors[b].append(a)
    seen = set(); result = []
    for start in range(len(neighbors)):
        if start in seen: continue
        pending = [start]; seen.add(start); indices = []
        while pending:
            i = pending.pop(); indices.append(i)
            for j in neighbors[i]:
                if j not in seen: seen.add(j); pending.append(j)
        result.append(np.asarray(indices))
    return result

oral = modules['MouthInterior']; oral_mesh = oral.data
oral_base = np.asarray([tuple(v.co) for v in oral_mesh.shape_keys.key_blocks['Basis'].data])
delta = np.zeros_like(oral_base); adjusted = []
ivory = {i for p in oral_mesh.polygons if oral_mesh.materials[p.material_index].name == 'Krag_Ivory' for i in p.vertices}
gum = {i for p in oral_mesh.polygons if oral_mesh.materials[p.material_index].name == 'Krag_OralTissue' for i in p.vertices}
for part, indices in enumerate(components(oral)):
    if int(indices[0]) not in ivory | gum: continue
    upper = bool(oral_base[indices, 2].mean() > 1.822)
    # Dental crowns remain behind closed lips. Central anterior surfaces move
    # toward the actual aperture; posterior molars stay beneath the cheeks.
    fraction = np.clip(1 - (abs(oral_base[indices, 0]) / .082) ** 2, .25, 1)
    delta[indices, 1] = -.017 * fraction
    delta[indices, 2] = -.007 if upper else -.003
    adjusted.append({'part': part, 'upper': upper, 'material': 'ivory' if int(indices[0]) in ivory else 'gum',
                     'vertices': len(indices), 'maximumForwardShiftMeters': float(max(-delta[indices, 1])),
                     'verticalShiftMeters': float(delta[indices[0], 2])})
cached = {key.name: np.asarray([tuple(p.co) for p in key.data]) for key in oral_mesh.shape_keys.key_blocks}
for key in oral_mesh.shape_keys.key_blocks:
    key.data.foreach_set('co', (cached[key.name] + delta).astype(np.float32).ravel())
oral_mesh.vertices.foreach_set('co', (oral_base + delta).astype(np.float32).ravel())
head['krag_semantic_jaw_v2'] = json.dumps(statistics)
rig.animation_data.action = bpy.data.actions['Idle']; bpy.context.scene.frame_set(1)
for path in [Path(__file__), HERE / 'semantic_jaw_v2.py']:
    text = bpy.data.texts.new('v9i_mouth/' + path.name); text.write(path.read_text())
bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT), compress=True)
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == EXPECTED
report = {'status': 'Actual isolated mouth study; neutral/open contact and artistic acceptance pending',
    'source': str(SOURCE.relative_to(ROOT)), 'sourceSha256': EXPECTED,
    'output': str(OUTPUT.relative_to(ROOT)), 'outputSha256': hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
    'jaw': statistics, 'changedJawVertices': int(np.count_nonzero(abs(new_jaw - old_jaw) > 1e-7)),
    'oralPartsAdjusted': adjusted,
    'preserved': ['Body/locomotion actions', 'External neutral face geometry', 'Rig bind', 'Weapon', 'Shared exports'],
    'pending': ['Actual neutral/open review', 'Dental/gum/tusk-root contact after refit', 'Rounded oral aperture and floor clearance']}
(ART / 'mouth-contact-repair-v9i.json').write_text(json.dumps(report, indent=2) + '\n', newline='\n')
print('Isolated Krag mouth repair saved; no acceptance or export', flush=True)
