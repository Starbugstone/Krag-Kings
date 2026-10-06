"""Make a new path-only derivative of the preserved failed portable file."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import bpy

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT/'benchmark/tools/nib/v5_wip/pbr'))
from portable_save import expected_maps, save_and_validate_pbr

def sha(path):
    # Large source/FBX files must not allocate a second full payload just to hash.
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()
parser = argparse.ArgumentParser()
parser.add_argument('--prior-pbr', type=Path, required=True)
parser.add_argument('--out', type=Path, required=True)
args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
if args.out.exists():
    raise RuntimeError('Choose a fresh path-only derivative output')
if not args.out.resolve().is_relative_to((ROOT/'benchmark/local/candidates').resolve()):
    raise RuntimeError('Repair output must remain isolated')
prior = args.prior_pbr/'Nib_Runtime_PBR.blend'
report_path = args.prior_pbr/'pbr-bake-report.json'
report = json.loads(report_path.read_text())
original_hash = sha(prior)
if original_hash != report['candidateSha256']:
    raise RuntimeError('Preserved failed file differs from actual bake report')
expected = expected_maps(report)
args.out.mkdir(parents=True)
textures = args.out/'textures'
textures.mkdir()
for name, entry in expected.items():
    source = args.prior_pbr/'textures'/name
    if sha(source) != entry['sha256']:
        raise RuntimeError('Original baked map changed: ' + name)
    shutil.copy2(source, textures/name)
bpy.ops.wm.open_mainfile(filepath=str(prior))
report['pathOnlyRepair'] = {'originalCandidate': str(prior), 'originalSha256': original_hash,
    'originalReportSha256': sha(report_path), 'textureFilesRebaked': False,
    'mapFilesCopiedByteIdentically': len(expected),
    'reason': 'Original save remapped intended target-relative paths from the old source root',
    'repairRecipeSha256': sha(__file__),
    'saveHelperSha256': sha(ROOT/'benchmark/tools/nib/v5_wip/pbr/portable_save.py'),
    'geometryActionParity': 'Requires separate snapshot against original source before export'}
bpy.context.scene['portable_pbr_bake'] = json.dumps(report)
target = args.out/'Nib_Runtime_PBR.blend'
report['savedPbrImageValidation'] = save_and_validate_pbr(target, report)
if sha(prior) != original_hash:
    raise RuntimeError('Path repair changed preserved failed file')
report['candidate'] = str(target)
report['candidateSha256'] = sha(target)
(args.out/'pbr-bake-report.json').write_text(json.dumps(report, indent=2)+'\n', newline='\n')
print('NIB_PBR_PATH_REPAIR_COMPLETE', flush=True)
