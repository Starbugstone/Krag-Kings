"""Isolated skinning repair on the actual left hand; preserves shape and rig."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import hand_skin_domains

p = argparse.ArgumentParser()
p.add_argument('--source', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args(sys.argv[sys.argv.index('--')+1:])
if a.output.exists():
    raise RuntimeError('Preserve prior hand skinning study')
a.output.mkdir(parents=True)
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
source_hash = sha(a.source)
bpy.ops.wm.open_mainfile(filepath=str(a.source), load_ui=False)
hand = bpy.data.objects['Nib v5 coherent hand L']
rig = bpy.data.objects['Nib_Rig']
points = np.array([v.co[:] for v in hand.data.vertices])
faces = [list(poly.vertices) for poly in hand.data.polygons]
bind = {b.name: [list(row) for row in b.matrix_local] for b in rig.data.bones}
old_groups = [g.name for g in hand.vertex_groups]
before_weights = [[(old_groups[g.group], g.weight) for g in v.groups] for v in hand.data.vertices]
domains, diagnostic = hand_skin_domains.solve(points, faces)
chains = {}
for name in hand_skin_domains.DIGITS:
    bones = [rig.data.bones[name+str(i)+'_L'] for i in range(1, 3 if name == 'Thumb' else 4)]
    chains[name] = [b.head_local[:] for b in bones]+[bones[-1].tail_local[:]]
names, weights, limits = hand_skin_domains.weights(points, domains, chains)
hand.vertex_groups.clear()
for name in names:
    hand.vertex_groups.new(name=name)
for vertex, row in enumerate(weights):
    for index in np.flatnonzero(row > 1e-8):
        hand.vertex_groups[int(index)].add([vertex], float(row[index]), 'REPLACE')
for index, name in enumerate(hand_skin_domains.DIGITS+['Palm']):
    attribute = hand.data.attributes.new('Nib_HandDomain_'+name, 'FLOAT', 'POINT')
    attribute.data.foreach_set('value', np.asarray(domains[:, index], dtype=np.float32))
if not np.array_equal(points, np.array([v.co[:] for v in hand.data.vertices])):
    raise RuntimeError('Skinning repair changed hand coordinates')
if faces != [list(poly.vertices) for poly in hand.data.polygons]:
    raise RuntimeError('Skinning repair changed topology')
if bind != {b.name: [list(row) for row in b.matrix_local] for b in rig.data.bones}:
    raise RuntimeError('Skinning repair changed skeleton')
output = a.output/'Nib_HandSkinning_Study_v1.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(output), compress=True)
if sha(a.source) != source_hash:
    raise RuntimeError('Input source changed')
report = {'status': 'Actual skinning-only source; native pose/contact review required',
          'source': str(a.source), 'sourceSha256': source_hash,
          'output': str(output), 'outputSha256': sha(output),
          'recipeSha256': sha(Path(__file__)), 'domainRecipeSha256': sha(Path(hand_skin_domains.__file__)),
          'handMesh': hand.name, 'vertices': len(points), 'faces': len(faces),
          'harmonicDomainSolve': diagnostic, 'limits': limits,
          'beforeWeightsSha256': hashlib.sha256(json.dumps(before_weights, separators=(',', ':')).encode()).hexdigest(),
          'afterWeightsSha256': hashlib.sha256(np.asarray(weights, dtype=np.float32).tobytes()).hexdigest(),
          'bindAndCoordinatesPreserved': True, 'actionsChanged': False,
          'unresolved': ['Actual curled hand silhouette/contact', 'Floating old glove rivets',
                         'Right hand weapon contact and skinning need separate review'],
          'sharedAssetsChanged': False, 'engineExported': False, 'artisticAcceptance': False}
(a.output/'skinning-study.json').write_text(json.dumps(report, indent=2)+'\n', newline='\n')
print('NIB_HAND_SKINNING_STUDY_COMPLETE', flush=True)
