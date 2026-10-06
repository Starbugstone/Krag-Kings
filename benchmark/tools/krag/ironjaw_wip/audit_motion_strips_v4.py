"""Read-only attribution of actual floor-reaching triangles in Krag v4 motion."""
from pathlib import Path
import sys, json, hashlib
import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT/'benchmark/art/animation/krag-human-motion-v4/Krag_HumanMotion_Study_v4.blend'
EXPECTED = '84822444a021194fc47e0360bfffc875c18687720bb8b8923588e486b9900607'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(SOURCE) == EXPECTED
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
sys.path.insert(0, str(ROOT/'benchmark/tools/animation'))
from export_contract import select_action
rig = bpy.data.objects['Krag_Rig']
contract = json.loads((ROOT/'benchmark/shared/characters/krag/krag_asset_contract.json').read_text())
hidden = contract['variants']['Krag_Natural']['off']
for obj in bpy.data.objects:
    if obj.type == 'MESH' and 'module' in obj:
        obj.hide_viewport = obj.hide_render = obj['module'] in hidden and obj['module'] != 'Weapon_R'
for track in rig.animation_data.nla_tracks:
    track.mute = True
objects = [obj for obj in bpy.data.objects if obj.type == 'MESH' and not obj.hide_render]


def points(obj, mesh, basis=False):
    data = mesh.shape_keys.key_blocks[0].data if basis and mesh.shape_keys else mesh.vertices
    out = np.empty(len(data)*3, np.float32)
    data.foreach_get('co', out)
    m = np.asarray(obj.matrix_world, float)
    return out.reshape(-1, 3).astype(float)@m[:3, :3].T+m[:3, 3]


rest = {}
for obj in objects:
    edges = np.empty(len(obj.data.edges)*2, np.int32)
    obj.data.edges.foreach_get('vertices', edges)
    rest[obj.name] = (points(obj, obj.data, True), edges.reshape(-1, 2))
frames = []
select_action(bpy, rig, bpy.data.actions['Walk'])
for frame in (1, 15):
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()
    entries = []
    for obj in objects:
        original, edges = rest[obj.name]
        evaluated = obj.evaluated_get(deps)
        current = points(evaluated, evaluated.data)
        if len(current) != len(original):
            entries.append({'object': obj.name, 'module': obj.get('module'), 'topologyChanged': True})
            continue
        if not len(edges):
            continue
        prior_length = np.linalg.norm(original[edges[:, 0]]-original[edges[:, 1]], axis=1)
        length = np.linalg.norm(current[edges[:, 0]]-current[edges[:, 1]], axis=1)
        growth = length-prior_length
        suspect = np.flatnonzero((growth > .15) & (length > .20))
        if len(suspect):
            samples = []
            for idx in suspect[np.argsort(growth[suspect])[-5:]][::-1]:
                ids = edges[idx]
                samples.append({'vertexIds': ids.tolist(), 'rest': original[ids].tolist(),
                                'posed': current[ids].tolist(), 'restLength': float(prior_length[idx]),
                                'posedLength': float(length[idx]),
                                'weights': [{obj.vertex_groups[g.group].name: float(g.weight)
                                             for g in obj.data.vertices[int(i)].groups} for i in ids]})
            entries.append({'object': obj.name, 'module': obj.get('module'),
                            'suspectEdges': len(suspect), 'maxEdgeGrowthMeters': float(growth.max()),
                            'activeShapes': {key.name: key.value for key in obj.data.shape_keys.key_blocks
                                             if key.value != 0} if obj.data.shape_keys else {},
                            'examples': samples})
    frames.append({'clip': 'Walk', 'frame': frame, 'objects': entries})
assert sha(SOURCE) == EXPECTED
output = ROOT/'benchmark/art/krag/anatomy-study/motion-strips-v4-attribution.json'
hands = {bone.name: {'head': list(bone.head_local), 'tail': list(bone.tail_local),
                    'parent': bone.parent.name if bone.parent else None,
                    'matrixLocal': [list(row) for row in bone.matrix_local]}
         for bone in rig.data.bones
         if bone.name.startswith(('Hand_', 'Finger', 'Thumb'))}
output.write_text(json.dumps({'source': str(SOURCE), 'sourceSha256': EXPECTED,
                             'sourceChanged': False, 'frames': frames,
                             'handRestBones': hands}, indent=2)+'\n', newline='\n')
print('KRAG_V4_STRIP_ATTRIBUTION_COMPLETE', flush=True)
