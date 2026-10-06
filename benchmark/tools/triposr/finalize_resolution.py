"""Finalize the existing completed pip report after an explicit UTF-8 reader fix."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
from resolve_environment import OUTPUT, ROOT, emit_inventory, sha

parser=argparse.ArgumentParser()
parser.add_argument('--resolution-sha256',required=True)
args=parser.parse_args()
if os.name!='nt' or sys.version_info[:2]!=(3,10):
    raise RuntimeError('Use the original Windows interpreter')
report=OUTPUT/'resolution.json'
if sha(report)!=args.resolution_sha256:
    raise RuntimeError('Existing pip resolution is not the diagnosed report')
if (OUTPUT/'dependency-license-inventory.json').exists():
    raise RuntimeError('Preserve an existing finalized inventory')
local=(OUTPUT/'requirements-local.in').read_text(encoding='utf-8')
requirements=ROOT/'benchmark/tools/triposr/windows-reference.in'
# The sole intentional local substitution is the already-hashed Torch wheel.
expected=[]
for line in requirements.read_text(encoding='utf-8').splitlines():
    if line.startswith('torch @ '):
        path=ROOT/'benchmark/local/triposr-downloads-v1/torch-2.5.1+cu121-cp310-cp310-win_amd64.whl'
        line='torch @ '+path.as_uri()
    expected.append(line)
if local!='\n'.join(expected)+'\n':
    raise RuntimeError('Resolution input changed after the actual pip run')
emit_inventory(report,requirements)
(OUTPUT/'evidence/resolution-finalization.json').write_text(json.dumps({
    'status':'Existing completed report finalized; original process failure retained',
    'reportSha256':sha(report),'finalizerSha256':sha(__file__),
    'executedResolverSha256':sha(OUTPUT/'evidence/resolver-executed-v1.py'),
    'inventorySha256':sha(OUTPUT/'dependency-license-inventory.json'),
    'resolutionRerun':False,'runtimeDependenciesInstalled':False
},indent=2)+'\n')
print('TRIPOSR_RESOLUTION_FINALIZED',flush=True)
