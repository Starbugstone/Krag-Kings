"""Prepare an isolated, recorded mesh-only dependency surface for original TRELLIS.

No trained model or inference is loaded here. Original upstream source is never
edited; optional rendering/text/background-removal imports are made lazy.
"""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[4]
source = ROOT / 'benchmark/local/trellis-original-feasibility/source'
target = ROOT / 'benchmark/local/trellis-original-pilot-v1/source'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
revision = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
assert revision == '442aa1e1afb9014e80681d3bf604e8d728a86ee7'
assert not target.exists(), 'Preserve prior prepared source'
shutil.copytree(source, target, ignore=shutil.ignore_patterns('.git', '__pycache__'))
changes = []
def edit(relative, before, after):
    p = target / relative
    text = p.read_text()
    assert text.count(before) == 1, 'Unexpected upstream source: ' + relative
    old = sha(p)
    p.write_text(text.replace(before, after), newline='\n')
    changes.append({'path': relative, 'upstreamSha256': old, 'preparedSha256': sha(p)})
edit('trellis/__init__.py', (source/'trellis/__init__.py').read_text(),
     '"""Isolated mesh pilot; submodules are loaded only when requested."""\n')
edit('trellis/representations/__init__.py', (source/'trellis/representations/__init__.py').read_text(),
     'from .mesh import MeshExtractResult\n')
edit('trellis/models/structured_latent_vae/__init__.py', (source/'trellis/models/structured_latent_vae/__init__.py').read_text(),
     'from .decoder_mesh import SLatMeshDecoder, ElasticSLatMeshDecoder\n')
edit('trellis/pipelines/__init__.py', 'from .trellis_text_to_3d import TrellisTextTo3DPipeline\n', '')
edit('trellis/pipelines/trellis_image_to_3d.py', 'import rembg\n', '')
edit('trellis/pipelines/trellis_image_to_3d.py', "        else:\n            input = input.convert('RGB')", "        else:\n            import rembg  # Optional: pre-matted local RGBA inputs do not use it.\n            input = input.convert('RGB')")
# These six call sites use only tensor shape matching with None wildcards and
# throw=False. Preserve the assertions, avoiding a large optional Kaolin import.
edit('trellis/representations/mesh/flexicubes/flexicubes.py',
     'from kaolin.utils.testing import check_tensor',
     '''def check_tensor(value, shape, throw=True):
    valid = (torch.is_tensor(value) and value.ndim == len(shape)
             and all(expected is None or actual == expected
                     for actual, expected in zip(value.shape, shape)))
    if not valid and throw:
        raise ValueError("Tensor shape does not match the required shape")
    return valid''')
report = {'status': 'Isolated mesh-only imports prepared; no model/GPU/inference validation',
          'upstreamRevision': revision, 'upstreamChanged': False, 'changes': changes,
          'geometryAlgorithmChanged': False, 'modelWeightsDownloaded': False,
          'inferenceRan': False, 'recipeSha256': sha(Path(__file__))}
(target.parent/'source-preparation.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report))
