"""Offline numerical preview of a proposed adult face field, never a render."""
import argparse
import hashlib
import json
import os
from pathlib import Path
os.environ['OPENBLAS_NUM_THREADS'] = '1'
import numpy as np
from adult_face_field import propose

ROOT = Path(__file__).resolve().parents[4]
parser = argparse.ArgumentParser()
parser.add_argument('--output-dir', type=Path, required=True)
args = parser.parse_args()
if args.output_dir.exists():
    raise RuntimeError('Preserve previous numerical face study')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
geometry_path = ROOT/'benchmark/local/nib-v5i-orbital-geometry.npz'
cache_path = ROOT/'benchmark/art/nib/identity-study/orbital-identity-v2.npz'
proposal_path = cache_path.with_name('orbital-identity-v2-numerical.json')
proposal = json.loads(proposal_path.read_text())
if sha(geometry_path) != proposal['inputGeometrySha256'] or sha(cache_path) != proposal['proposalCacheSha256']:
    raise RuntimeError('Actual orbital construction input changed')
geometry = np.load(geometry_path)
cache = np.load(cache_path)
basis = cache['neutral'].astype(np.float32).astype(np.float64)
faces = geometry['faces']; edges = geometry['edges']
delta, report = propose(geometry['source'], basis, faces, geometry['faceSets'], edges)
target = basis+delta
triangles = np.vstack((faces[:, [0, 1, 2]], faces[:, [0, 2, 3]]))

def normals(points):
    q = points[triangles]
    return np.cross(q[:, 1]-q[:, 0], q[:, 2]-q[:, 0])

before = normals(basis); after = normals(target)
before_area = np.linalg.norm(before, axis=1); after_area = np.linalg.norm(after, axis=1)
normal_dot = np.sum(before*after, axis=1)/np.maximum(before_area*after_area, 1e-25)
introduced = int(np.sum((before_area > 1e-14) & (after_area <= 1e-14)))
inverted = int(np.sum(normal_dot < 0))
report.update({
    'status': 'Offline numerical proposal; no Blender source, posed check or actual render',
    'actualOrbitalSourceSha256': '09da9c1eb51eabd0402fc1ed52b3d4b07f53a5a74150810796a2b04169d8c88e',
    'geometryCacheSha256': sha(geometry_path), 'neutralCacheSha256': sha(cache_path),
    'proposalReportSha256': sha(proposal_path),
    'neutralMetrics': {'introducedDegenerates': introduced, 'trianglesRotatedOver90': inverted,
        'minimumAreaRatio': float((after_area/np.maximum(before_area, 1e-25)).min()),
        'normalRotationP99Degrees': float(np.degrees(np.arccos(np.clip(np.quantile(normal_dot, .01), -1, 1)))),
        'normalRotationMaximumDegrees': float(np.degrees(np.arccos(np.clip(normal_dot.min(), -1, 1))))},
    'hardStructuralFailure': bool(introduced or inverted or report['edgeDisplacementGradientMaximum'] > .75),
    'artisticAcceptance': False, 'sharedChanged': False,
    'codeSha256': {p.name: sha(p) for p in [Path(__file__), Path(__file__).with_name('adult_face_field.py')]}})
args.output_dir.mkdir(parents=True)
output = args.output_dir/'proposal.npz'
np.savez_compressed(output, expectedBasis=basis.astype(np.float32), delta=delta, target=target)
report['proposalCacheSha256'] = sha(output)
(args.output_dir/'numerical.json').write_text(json.dumps(report, indent=2)+'\n', newline='\n')
print(json.dumps(report['neutralMetrics'], indent=2))
print('maximumDeltaMeters', report['maximumDisplacementMeters'], 'gradient', report['edgeDisplacementGradientMaximum'])
if report['hardStructuralFailure']:
    raise RuntimeError('Prepared field fails the stated numerical gate; keep diagnostic evidence')
print('NIB_ADULT_FACE_NUMERICAL_PROPOSAL_COMPLETE')
