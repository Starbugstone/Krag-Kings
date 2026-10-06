"""Read-only saved-pose audit in the actual hand frame.

Export numerical skin/joint evidence for the failed fist before changing more
angles. No Blender scene, rig or shared content is saved by this script.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Vector

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]
from export_contract import select_action
import pose_refinement

p = argparse.ArgumentParser()
p.add_argument('--source', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args(sys.argv[sys.argv.index('--') + 1:])
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
digest = sha(a.source)
assert not a.output.exists(), 'Preserve prior audit'
a.output.mkdir(parents=True)
bpy.ops.wm.open_mainfile(filepath=str(a.source), load_ui=False)
rig = bpy.data.objects['Krag_Rig']
obj = bpy.data.objects['BioForearm_L']
scene = bpy.context.scene
for track in rig.animation_data.nla_tracks:
    track.mute = True
hand = rig.pose.bones['Hand_L']
across, along, palm = pose_refinement.frame(rig)
basis = np.array([across[:], along[:], palm[:]])
origin = np.array(hand.bone.head_local)
def local(points):
    return (np.asarray(points) - origin) @ basis.T

rest = np.array([v.co[:] for v in obj.data.vertices])
weights = np.zeros((len(rest), len(obj.vertex_groups)))
for vertex in obj.data.vertices:
    for weight in vertex.groups:
        weights[vertex.index, weight.group] = weight.weight
arrays = {'rest': rest, 'restHandCoordinates': local(rest), 'weights': weights}
obj.data.calc_loop_triangles()
arrays['triangles'] = np.array([t.vertices[:] for t in obj.data.loop_triangles])
report = {'sourceSha256': digest, 'source': str(a.source),
          'basisRows': basis.tolist(), 'handOrigin': origin.tolist(),
          'weightGroups': [g.name for g in obj.vertex_groups], 'poses': {},
          'sourceChanged': False, 'artisticAcceptance': False}
digit_names = [f'Finger{s}_{d}_L' for d in range(4) for s in range(1, 4)] + ['Thumb1_L', 'Thumb2_L']
for clip, phase in [('Idle', 0.), ('Run', .5), ('Melee', .5)]:
    action = bpy.data.actions[clip]
    select_action(bpy, rig, action)
    first, last = action.frame_range
    at = first + phase * (last - first)
    scene.frame_set(int(at), subframe=at - int(at))
    bpy.context.view_layer.update()
    delta = hand.matrix @ hand.bone.matrix_local.inverted()
    inverse = delta.inverted()
    rows = {}
    for name in digit_names:
        bone = rig.pose.bones[name]
        h, t = inverse @ bone.head, inverse @ bone.tail
        rows[name] = {'restHead': local([bone.bone.head_local])[0].tolist(),
                      'restTail': local([bone.bone.tail_local])[0].tolist(),
                      'posedHead': local([h])[0].tolist(), 'posedTail': local([t])[0].tolist(),
                      'location': list(bone.location), 'scale': list(bone.scale),
                      'rotationEuler': list(bone.rotation_euler),
                      'restMatrix': [list(row) for row in bone.bone.matrix_local],
                      'poseMatrix': [list(row) for row in bone.matrix]}
    ev = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = ev.to_mesh()
    posed = np.array([tuple(inverse @ v.co) for v in mesh.vertices])
    ev.to_mesh_clear()
    assert len(posed) == len(rest), 'Modifier changed topology'
    arrays[clip + 'SkinHandCoordinates'] = local(posed)
    report['poses'][clip] = {'frame': at, 'bones': rows,
                            'activeMorphs': {k.name: k.value for k in obj.data.shape_keys.key_blocks if k.value}}
np.savez_compressed(a.output / 'skin-evidence.npz', **arrays)
report['skinEvidenceSha256'] = sha(a.output / 'skin-evidence.npz')
report['recipeSha256'] = sha(Path(__file__))
(a.output / 'audit.json').write_text(json.dumps(report, indent=2) + '\n', newline='\n')
assert sha(a.source) == digest
print('KRAG_HAND_POSE_AUDIT_COMPLETE', flush=True)
