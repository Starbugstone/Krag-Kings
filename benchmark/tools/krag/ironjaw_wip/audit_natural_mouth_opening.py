"""Read-only decomposition of the actual natural mouth, without reducing acting."""
from pathlib import Path
import json, sys, hashlib
import numpy as np
import bpy
from mathutils import Matrix

ROOT = Path(__file__).resolve().parents[4]
ART = ROOT/'benchmark/art/krag'
SOURCE = ART/'Krag_LandmarkRelief_v9o_WIP.blend'
EXPECTED = '93661a93f12ab2510bed8d8746452b14573edc71b61b943c53f1c36db2d1bc86'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(SOURCE) == EXPECTED
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
rig = bpy.data.objects['Krag_Rig']
modules = {obj.get('module'): obj for obj in bpy.data.objects if obj.type == 'MESH' and obj.get('module')}
head = modules['Head']
rig.animation_data.action = bpy.data.actions['FacePerformance']
bpy.context.scene.frame_set(146)
bpy.context.view_layer.update()


def coords(data):
    values = np.empty(len(data)*3, np.float32)
    data.foreach_get('co', values)
    return values.reshape(-1, 3).astype(float)


def world(obj, values):
    matrix = np.asarray(obj.matrix_world, float)
    return values@matrix[:3, :3].T+matrix[:3, 3]


def skin(obj, values):
    original = world(obj, values)
    transformed = np.zeros_like(original)
    total = np.zeros(len(original))
    for group in obj.vertex_groups:
        if group.name not in rig.pose.bones:
            continue
        weights = np.zeros(len(original))
        for vertex in obj.data.vertices:
            weights[vertex.index] = sum(g.weight for g in vertex.groups if g.group == group.index)
        if not np.any(weights):
            continue
        matrix = np.asarray(rig.matrix_world @ rig.pose.bones[group.name].matrix @
                            rig.data.bones[group.name].matrix_local.inverted() @ rig.matrix_world.inverted(), float)
        moved = original@matrix[:3, :3].T+matrix[:3, 3]
        transformed += moved*weights[:, None]
        total += weights
    if np.max(abs(total-1)) > 1e-5:
        raise RuntimeError('Non-normalized source weights prevent exact LBS attribution')
    return transformed


keys = head.data.shape_keys.key_blocks
basis = coords(keys['Basis'].data)
jaw_delta = coords(keys['JawOpen'].data)-basis
active = {key.name: float(key.value) for key in keys if key.value != 0}
combined = basis.copy()
for name, value in active.items():
    combined += (coords(keys[name].data)-basis)*value
deps = bpy.context.evaluated_depsgraph_get()
evaluated = head.evaluated_get(deps)
actual = world(evaluated, coords(evaluated.data.vertices))
predicted = skin(head, combined)
error = np.linalg.norm(actual-predicted, axis=1)
if error.max() > .000003:
    raise RuntimeError('Analytical LBS does not reproduce actual source: '+str(error.max()))
points = world(head, basis)
tags = np.zeros(len(points), np.uint64)
sets = np.asarray([item.value for item in head.data.attributes['.sculpt_face_set'].data], int)
for polygon, tag in zip(head.data.polygons, sets):
    tags[list(polygon.vertices)] |= np.uint64(1) << np.uint64(tag)
member = lambda tag: (tags & (np.uint64(1) << np.uint64(tag))) != 0
upper = member(33) & member(7)
lower = member(24) & member(7)
corners = upper & lower
if corners.sum() != 2:
    raise RuntimeError('Expected true two-corner oral loop')
center = abs(points[:, 0]) < .018
if min(np.count_nonzero(upper & center), np.count_nonzero(lower & center)) < 3:
    raise RuntimeError('Missing central upper/lower oral-margin samples')


def rim(values):
    up, lo = values[upper & center], values[lower & center]
    return {'upperCenter': up.mean(0).tolist(), 'lowerCenter': lo.mean(0).tolist(),
            'verticalOpeningMeters': float(up[:, 2].mean()-lo[:, 2].mean()),
            'upperSamples': len(up), 'lowerSamples': len(lo)}


cases = {
    'neutralBasis': points,
    'skeletonOnly': skin(head, basis),
    'jawOpenMorphOnly': world(head, basis+jaw_delta*keys['JawOpen'].value),
    'skeletonPlusJawOpen': skin(head, basis+jaw_delta*keys['JawOpen'].value),
    'actualAllExpressions': actual,
}
oral = modules['MouthInterior']
oeval = oral.evaluated_get(deps)
opoints = world(oeval, coords(oeval.data.vertices))
oral_groups = {}
for name in ['Head', 'Jaw', 'Tongue_01', 'Tongue_02']:
    group = oral.vertex_groups.get(name)
    if group is None:
        raise RuntimeError('Missing oral skeletal group '+name)
    ids = [v.index for v in oral.data.vertices if any(g.group == group.index and g.weight > .5 for g in v.groups)]
    oral_groups[name] = {'majorityWeightedVertices': len(ids),
                         'posedBounds': [opoints[ids].min(0).tolist(), opoints[ids].max(0).tolist()] if ids else None}
materials = {}
for index, mat in enumerate(oral.data.materials):
    ids = sorted({i for p in oral.data.polygons if p.material_index == index for i in p.vertices})
    materials[mat.name] = {'vertices': len(ids), 'posedBounds': [opoints[ids].min(0).tolist(), opoints[ids].max(0).tolist()]}
report = {
    'status': 'Actual read-only natural-mouth decomposition; no expression range changed',
    'sourceSha256': EXPECTED, 'sourceChanged': False, 'clip': 'FacePerformance', 'frame': 146,
    'jawPoseEulerDegrees': list(np.degrees(rig.pose.bones['Jaw'].rotation_euler)),
    'jawOpenValue': float(keys['JawOpen'].value), 'activeHeadMorphs': active,
    'actualLbsReproductionMaxErrorMeters': float(error.max()),
    'centralOralRims': {name: rim(values) for name, values in cases.items()},
    'jawOpenDelta': {'maximumMeters': float(np.linalg.norm(jaw_delta, axis=1).max()),
                     'upperRimMaximumMeters': float(np.linalg.norm(jaw_delta[upper], axis=1).max()),
                     'lowerRimMaximumMeters': float(np.linalg.norm(jaw_delta[lower], axis=1).max())},
    'oralWeightDomains': oral_groups, 'oralMaterials': materials,
    'oralBoneChains': {name: {'parent': rig.data.bones[name].parent.name if rig.data.bones[name].parent else None,
                             'head': list(rig.data.bones[name].head_local),
                             'tail': list(rig.data.bones[name].tail_local),
                             'poseEulerDegrees': list(np.degrees(rig.pose.bones[name].rotation_euler))}
                      for name in ['Head', 'Jaw', 'Tongue_01', 'Tongue_02']},
    'artisticAcceptance': False,
}
output = ART/'anatomy-study/natural-mouth-opening-v9o-attribution.json'
output.write_text(json.dumps(report, indent=2)+'\n', newline='\n')
assert sha(SOURCE) == EXPECTED
print('KRAG_NATURAL_MOUTH_OPENING_ATTRIBUTION_COMPLETE', flush=True)
