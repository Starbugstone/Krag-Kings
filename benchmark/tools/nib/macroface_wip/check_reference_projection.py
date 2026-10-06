"""Compare a numerical candidate through unchanged provisional reference cameras.

This does not optimize the field, infer anatomy from an expression, or establish
likeness. Both camera residuals and manually selected landmarks remain uncertain.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from macro_field_candidate import transform

p = argparse.ArgumentParser()
p.add_argument('--camera-report', type=Path, required=True)
p.add_argument('--numerical-report', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
if a.output.exists():
    raise RuntimeError('Preserve earlier projection evidence')
fit = json.loads(a.camera_report.read_text())
report = json.loads(a.numerical_report.read_text())
records = {}
for name, camera in fit['cameras'].items():
    names = list(camera['landmarks'])
    points = np.array([fit['features'][n]['point'] for n in names])
    target = np.array([camera['landmarks'][n]['reference'] for n in names])
    transformed = transform(points, report['params'])
    predicted = transformed @ np.array(camera['matrixPixelsPerMeter']).T + camera['offsetPixels']
    errors = np.linalg.norm(predicted - target, axis=1)
    weights = np.array([2 if n.startswith(('outer', 'inner')) else .7 if n.startswith(('brow', 'cheek')) else 1 for n in names], float)
    weights /= weights.sum()
    records[name] = {
        'beforeRmsPixels': camera['rmsPixels'],
        'afterSameCameraRmsPixels': float(np.sqrt(weights @ (errors * errors))),
        'points': {n: {'before': camera['landmarks'][n]['residualPixels'], 'after': float(errors[i])} for i, n in enumerate(names)},
    }
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
result = {
    'status': 'Numerical projection only; camera fits and authored landmark choices remain provisional',
    'cameraReportSha256': sha(a.camera_report),
    'numericalReportSha256': sha(a.numerical_report),
    'scriptSha256': sha(Path(__file__)),
    'views': records,
    'artisticAcceptance': False,
    'sharedChanged': False,
}
a.output.write_text(json.dumps(result, indent=2) + '\n', newline='\n')
print(json.dumps({n: {k: v for k, v in entry.items() if k != 'points'} for n, entry in records.items()}, indent=2))
