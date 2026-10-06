"""Light numerical field check only; no Blender asset or art validation."""
from pathlib import Path
import sys,json,hashlib
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];sys.path.insert(0,str(HERE))
from macro_envelope_v9na import Envelope
cached=ROOT/'benchmark/art/krag/anatomy-study/head-fit-v9f-measurements.json'
eyes=np.asarray(json.loads(cached.read_text())['expectedFittedEyeCentersMeters'])
x=np.unique(np.r_[np.linspace(-.17,.17,39),[-1e-5,0,1e-5]])
y=np.linspace(-.29,.10,41);z=np.linspace(1.695,2.065,43)
points=np.stack(np.meshgrid(x,y,z,indexing='ij'),axis=-1).reshape(-1,3)
results=[]
for radius in [.014,.019,.025]:
    for nose_z in [1.862,1.876,1.890]:
        envelope=Envelope(eyes,[radius,radius],[0,-.1745,1.8197],[0,-.21,nose_z])
        try:metrics=envelope.jacobian_report(points);passed=True
        except RuntimeError as error:metrics={'failure':str(error)};passed=False
        results.append({'radiusMeters':radius,'noseZ':nose_z,'passed':passed,'metrics':metrics})
        print(radius,nose_z,passed,metrics,flush=True)
report={'status':'Numerical support-domain parameter sweep only; no saved source or visual proof','helperSha256':hashlib.sha256((HERE/'macro_envelope_v9na.py').read_bytes()).hexdigest(),
 'cachedEyeLandmarkSource':str(cached.relative_to(ROOT)),'cachedEyeLandmarksAreCodeFitNotCurrentSourceQuery':True,
 'otherLandmarks':'LipZ1.8197 from retained tusk/lip report; nose height and globe radius intentionally bracket plausible current values, not an exact saved-source claim',
 'supportBoundsMeters':[points.min(0).tolist(),points.max(0).tolist()],'pointsPerCase':len(points),'cases':results,'allPass':all(r['passed']for r in results)}
(ROOT/'benchmark/art/krag/v9na-envelope-math-preflight.json').write_text(json.dumps(report,indent=2)+'\n',newline='\n')
if not report['allPass']:raise SystemExit(2)
