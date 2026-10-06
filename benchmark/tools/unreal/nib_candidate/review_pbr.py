"""Run the existing Nib views with identical cameras/settings on pinned inputs."""
import argparse
import hashlib
import json
from pathlib import Path
import runpy
import sys

ROOT=Path(__file__).resolve().parents[4]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
parser=argparse.ArgumentParser()
parser.add_argument('--contract',type=Path,required=True)
parser.add_argument('--side',choices=['source','baked'],required=True)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
contract=json.loads(args.contract.read_text())
for item in contract['pins']:
    if sha(ROOT/item['path'])!=item['sha256']:raise RuntimeError('Review input changed '+item['path'])
# The saved PBR reopen gate must precede visual review, not only a successful bake.
receipt=ROOT/contract['savedPbrSnapshotReceipt']
if not receipt.exists():raise RuntimeError('Saved PBR snapshot has not passed')
for item in json.loads(receipt.read_text())['outputs']:
    if sha(ROOT/item['path'])!=item['sha256']:raise RuntimeError('Saved PBR snapshot output changed')
source=ROOT/contract[args.side]
output=ROOT/contract['outputRoot']/args.side
if output.exists():raise RuntimeError('Preserve earlier comparison renders')
script=ROOT/'benchmark/tools/nib/render_review.py'
sys.argv=[str(script),'--','--source',str(source),'--output-dir',str(output),'Face','Tongue','Front']
runpy.run_path(str(script),run_name='__main__')
for item in contract['pins']:
    if sha(ROOT/item['path'])!=item['sha256']:raise RuntimeError('Read-only review changed input '+item['path'])
images=[{'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p)} for p in sorted(output.glob('*.png'))]
if len(images)!=3:raise RuntimeError('Expected all three matched views')
(output/'review-receipt.json').write_text(json.dumps({'side':args.side,'contractSha256':sha(args.contract),
    'images':images,'artisticAcceptance':False,'visualParityInspected':False,
    'status':'Actual source/baked comparison images; requires inspection'},indent=2)+'\n',newline='\n')
print('NIB_COHERENT_PBR_REVIEW_COMPLETE '+args.side,flush=True)
