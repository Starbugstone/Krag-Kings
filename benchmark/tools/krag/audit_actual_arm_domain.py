"""Read-only saved Krag Shoot attribution; no mesh/weight/action repair.

Reconstruct the retained source-cage indexing and subdivide its point fields.
Require that the saved editable cage reproduces the actual arm surface before
using those fields to distinguish fit/weight disagreement from pose or morphs.
"""
from pathlib import Path
import hashlib, json
import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
ART = ROOT / 'benchmark/art/krag'
SOURCE = ART / 'Krag_MacroFace_v9na_WIP.blend'
EXPECTED = 'c9aec7f6678553a37dd48287a60a7df308e7b5620fd98af4d1026acc10d3d9b9'
LIBRARY = ROOT / 'benchmark/art/reference-anatomy/blender-studio-human-base-meshes/source/human-base-meshes-bundle-v1.4.1/human_base_meshes_bundle.blend'
LIBRARY_SHA = '3c121505651140ceb4d69fd1d8923f7788ffadd81672f5be14845a5f2c75c137'
OUT = ART / 'anatomy-study/actual-arm-domain-Shoot-v9na.json'
CACHE = ROOT / 'benchmark/local/krag-arm-domain-Shoot-v9na.npz'
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
if sha(SOURCE) != EXPECTED or sha(LIBRARY) != LIBRARY_SHA:
    raise RuntimeError('Pinned source/reference changed')
if OUT.exists() or CACHE.exists():
    raise RuntimeError('Preserve prior saved-pose audit')
bpy.ops.wm.open_mainfile(filepath=str(SOURCE), load_ui=False)
rig = bpy.data.objects['Krag_Rig']
body = next(o for o in bpy.data.objects if o.type == 'MESH' and o.get('module') == 'Body')
cage = bpy.data.objects['EDITABLE Krag anatomical control cage']
for obj in bpy.data.objects:
    if obj.type == 'MESH':
        obj.hide_set(obj != body)

# Obtain semantic topology from the retained licensed reference itself.
with bpy.data.libraries.load(str(LIBRARY), link=False) as (available, loaded):
    loaded.objects = ['GEO-body_male_realistic']
reference = loaded.objects[0]
raw = np.asarray([v.co[:] for v in reference.data.vertices], float)
keep = (raw[:, 2] < 1.445) & ((raw[:, 2] > .945) | ((abs(raw[:, 0]) > .240) & (raw[:, 2] > .70)))
source_faces = [list(p.vertices) for p in reference.data.polygons if all(keep[i] for i in p.vertices)]
used = sorted({i for face in source_faces for i in face})
remap = {old: new for new, old in enumerate(used)}
polygons = [[remap[i] for i in face] for face in source_faces]
if len(cage.data.vertices) != len(used) or polygons != [list(p.vertices) for p in cage.data.polygons]:
    raise RuntimeError('Saved editable cage no longer has the recorded original topology/indexing')
raw = raw[used]

# This temporary clone is never saved and never modifies the actual character.
probe = cage.copy()
probe.data = cage.data.copy()
probe.name = 'READ_ONLY Krag arm-domain probe'
bpy.context.collection.objects.link(probe)
probe.hide_set(False)
probe.hide_render = True
probe.modifiers.clear()
reference_attr = probe.data.attributes.new('Audit_SourcePoint', 'FLOAT_VECTOR', 'POINT')
reference_attr.data.foreach_set('vector', raw.astype(np.float32).ravel())
fit = np.clip((abs(raw[:, 0]) - (.145 + .035 * np.clip((raw[:, 2] - 1.20) / .15, 0, 1))) / .065, 0, 1)
fit = fit * fit * (3 - 2 * fit)
fit_attr = probe.data.attributes.new('Audit_FitArm', 'FLOAT', 'POINT')
fit_attr.data.foreach_set('value', fit.astype(np.float32))
sub = probe.modifiers.new('Same saved cage subdivision', 'SUBSURF')
sub.levels = 3
sub.render_levels = 3
bpy.context.view_layer.objects.active = probe
probe.select_set(True)
bpy.ops.object.modifier_apply(modifier=sub.name)
if len(probe.data.vertices) != len(body.data.vertices):
    raise RuntimeError('Subdivided source-cage indexing does not match actual Body')
source_points = np.asarray([v.vector[:] for v in probe.data.attributes['Audit_SourcePoint'].data], float)
fit_domain = np.asarray([v.value for v in probe.data.attributes['Audit_FitArm'].data], float)
skin_domain = np.asarray([v.value for v in body.data.attributes['Krag_ArmDomain_v2'].data], float)
basis = np.asarray([v.co[:] for v in body.data.shape_keys.key_blocks['Basis'].data], float)
reconstructed = np.asarray([v.co[:] for v in probe.data.vertices], float)
arm_region = (abs(source_points[:, 0]) > .16) & (source_points[:, 2] > 1.04) & (source_points[:, 2] < 1.37)
correspondence_error = np.linalg.norm(reconstructed[arm_region] - basis[arm_region], axis=1)
if correspondence_error.max() > 2e-6:
    raise RuntimeError('Saved cage does not reproduce actual arm surface; do not infer point-field correspondence: ' + str(correspondence_error.max()))
bpy.data.objects.remove(probe, do_unlink=True)
bpy.data.objects.remove(reference, do_unlink=True)

for track in rig.animation_data.nla_tracks:
    track.mute = True
rig.animation_data.action = bpy.data.actions['Shoot']
start, end = map(float, rig.animation_data.action.frame_range)
frame = start + .40 * (end - start)
bpy.context.scene.frame_set(int(frame), subframe=frame % 1)
bpy.context.view_layer.update()
if not np.allclose(np.asarray(body.matrix_world), np.eye(4), atol=1e-8) or not np.allclose(np.asarray(rig.matrix_world), np.eye(4), atol=1e-8):
    raise RuntimeError('Unexpected Body/rig object frame')
names = [g.name for g in body.vertex_groups]
weights = np.zeros((len(basis), len(names)))
for vertex in body.data.vertices:
    for group in vertex.groups:
        weights[vertex.index, group.group] = group.weight
matrices = {name: np.asarray(rig.pose.bones[name].matrix @ rig.data.bones[name].matrix_local.inverted(), float) for name in names}
mixed = basis.copy()
values = {}
for key in body.data.shape_keys.key_blocks:
    if key.name == 'Basis':
        continue
    values[key.name] = float(key.value)
    mixed += key.value * (np.asarray([v.co[:] for v in key.data], float) - basis)

def lbs(points):
    result = np.zeros_like(points)
    homogeneous = np.column_stack((points, np.ones(len(points))))
    for index, name in enumerate(names):
        result += (homogeneous @ matrices[name].T)[:, :3] * weights[:, index, None]
    return result

skin_only, predicted = lbs(basis), lbs(mixed)
evaluated = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
mesh = evaluated.to_mesh()
actual = np.asarray([v.co[:] for v in mesh.vertices], float)
evaluated.to_mesh_clear()
if actual.shape != predicted.shape:
    raise RuntimeError('Actual native Body topology changed')
lbs_error = np.linalg.norm(actual - predicted, axis=1)
if lbs_error.max() > 2e-6:
    raise RuntimeError('Explicit LBS does not reproduce actual native Body')
candidates = np.flatnonzero(arm_region & (fit_domain > .75) & (skin_domain < .25))
np.savez_compressed(CACHE, rest=basis, source_points=source_points, fit_domain=fit_domain, skin_domain=skin_domain,
                    posed=actual, skin_only=skin_only, weights=weights, group_names=np.asarray(names), candidate_ids=candidates)
rows = [{'vertex': int(i), 'sourcePoint': source_points[i].tolist(), 'restPoint': basis[i].tolist(),
         'actualShootPoint': actual[i].tolist(), 'fitArmBlend': float(fit_domain[i]), 'skinArmDomain': float(skin_domain[i]),
         'weights': {name: float(weights[i, j]) for j, name in enumerate(names) if weights[i, j] > 1e-6}}
        for i in sorted(candidates, key=lambda i: float(skin_domain[i] - fit_domain[i]))[:24]]
report = {'status': 'Actual read-only saved-source Shoot attribution; no anatomy repair or art acceptance',
          'source': SOURCE.relative_to(ROOT).as_posix(), 'sourceSha256': EXPECTED,
          'referenceSha256': LIBRARY_SHA, 'action': 'Shoot', 'normalizedTime': .40, 'frame': frame,
          'savedCageVsActualArmMaximumErrorMeters': float(correspondence_error.max()),
          'explicitLbsVsNativeMaximumErrorMeters': float(lbs_error.max()), 'bodyMorphValues': values,
          'bodyMorphPosedMaximumDeltaMeters': float(np.linalg.norm(predicted - skin_only, axis=1).max()),
          'candidateCount': len(candidates), 'worstFitVsSkinRows': rows,
          'cache': CACHE.relative_to(ROOT).as_posix(), 'cacheSha256': sha(CACHE),
          'toolSha256': sha(Path(__file__)), 'sourceUnchanged': sha(SOURCE) == EXPECTED, 'sharedChanged': False}
if not report['sourceUnchanged']:
    raise RuntimeError('Read-only audit changed source')
OUT.write_text(json.dumps(report, indent=2) + '\n', newline='\n')
print('KRAG_ACTUAL_ARM_DOMAIN_AUDIT_COMPLETE', flush=True)
