"""Read-only actual-boot contact audit of a saved animation study."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import bpy
sys.path.insert(0, str(Path(__file__).parent))
import sole_geometry

parser = argparse.ArgumentParser()
parser.add_argument('--source', type=Path, required=True)
parser.add_argument('--species', choices=['Krag','Nib'], required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
if args.output.exists(): raise RuntimeError('Preserve previous contact audit')
sha = lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source_sha = sha(args.source)
bpy.ops.wm.open_mainfile(filepath=str(args.source))
rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and 'Pelvis' in o.data.bones)
clouds, records = sole_geometry.capture(rig, args.species)
report = {'source':str(args.source), 'sourceSha256':source_sha, 'soleClouds':records,
          'recipeSha256':sha(Path(__file__)), 'helperSha256':sha(Path(sole_geometry.__file__)),
          'sourceModified':False, 'artisticAcceptance':False, 'clips':{}}
for obj in bpy.data.objects:
    if obj.type == 'MESH':obj.hide_viewport = True
for clip in ['Walk', 'Run', 'Idle']:
    rig.animation_data.action = bpy.data.actions[clip]
    a,b = (int(x) for x in rig.animation_data.action.frame_range)
    samples=[]
    for frame in range(a,b+1):
        bpy.context.scene.frame_set(frame)
        samples.append({'frame':frame,'actualBootMinimumZ':{side:sole_geometry.minimum(rig,clouds,side) for side in ['L','R']}})
    report['clips'][clip] = {'samples':samples,'minimumZ':min(v for s in samples for v in s['actualBootMinimumZ'].values())}
if sha(args.source) != source_sha:raise AssertionError('Audit changed source')
args.output.parent.mkdir(parents=True,exist_ok=True)
args.output.write_text(json.dumps(report,indent=2)+'\n')
print('KRAG_KINGS_SOLE_AUDIT_COMPLETE',flush=True)
