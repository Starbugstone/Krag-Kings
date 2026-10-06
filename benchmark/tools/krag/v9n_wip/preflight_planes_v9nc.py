"""Lightweight field continuity sweep; not an actual saved mesh/likeness check."""
from pathlib import Path
import json, hashlib
import numpy as np
from macro_envelope_v9nb import Envelope as PriorEnvelope
from anatomical_planes_v9nc import Envelope

ROOT = Path(__file__).resolve().parents[4]
ART = ROOT / 'benchmark/art/krag'
data = json.loads((ART / 'macro-face-v9nb.json').read_text())['landmarksWorld']
prior = PriorEnvelope(data['eyes'], data['eyeRadii'], data['lowerOralRimMean'], data['nasalFrontMean'])
eyes = prior.transform(np.asarray(data['eyes']))
# Mean of a nonlinear transformation need not equal transformed mean. These
# are explicitly a preparation envelope; the native source measures again.
lip = prior.transform([data['lowerOralRimMean']])[0]
nose = prior.transform([data['nasalFrontMean']])[0]
radii = np.asarray(data['eyeRadii'])
grid = np.stack(np.meshgrid(np.linspace(-.17, .17, 43), np.linspace(-.29, .015, 43),
                           np.linspace(lip[2]-.105, eyes[:, 2].mean()+.145, 43), indexing='ij'), axis=-1).reshape(-1, 3)
cases = []
for surface_offset in [-.012, 0., .012]:
    for radius_offset in [-.004, 0., .004]:
        planes = {'brow': -.175+surface_offset, 'cheek': -.155+surface_offset, 'chin': -.202+surface_offset}
        field = Envelope(eyes, radii+radius_offset, lip, nose, measured_planes=planes)
        row = {'surrogatePlaneDepthsY': planes, 'eyeRadiusOffsetMeters': radius_offset}
        try:
            row['jacobian'] = field.jacobian_report(grid)
            row['maximumDisplacementMeters'] = float(np.linalg.norm(field.delta(grid), axis=1).max())
            row['passes'] = row['maximumDisplacementMeters'] < .035
        except RuntimeError as exc:
            row['passes'] = False
            row['failure'] = str(exc)
        cases.append(row)
report = {'status': 'Numerical support-domain sweep only; actual landmarks/geometry and rendered identity remain unvalidated',
          'allCasesPass': all(c['passes'] for c in cases), 'samplesPerCase': len(grid),
          'landmarkBasis': 'Approximate current means through the known v9nb field; source job independently measures actual mesh planes',
          'cases': cases, 'helperSha256': hashlib.sha256(Path(__file__).with_name('anatomical_planes_v9nc.py').read_bytes()).hexdigest()}
(ART / 'v9nc-planes-math-preflight.json').write_text(json.dumps(report, indent=2)+'\n', newline='\n')
print(json.dumps({'allCasesPass': report['allCasesPass'], 'samplesPerCase': len(grid), 'cases': cases}, indent=2))
if not report['allCasesPass']:
    raise SystemExit(2)
