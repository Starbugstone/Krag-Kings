"""Light numerical field check only; no Blender asset or art validation."""
from pathlib import Path
import sys,json,hashlib
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];sys.path.insert(0,str(HERE))
from macro_envelope_v9nb import Envelope
cached=ROOT/'benchmark/art/krag/macro-face-v9na.json'
actual=json.loads(cached.read_text())['landmarksWorld'];eyes=np.asarray(actual['eyes'])
x=np.unique(np.r_[np.linspace(-.17,.17,39),[-1e-5,0,1e-5]])
y=np.linspace(-.29,.10,41);z=np.linspace(1.695,2.065,43)
points=np.stack(np.meshgrid(x,y,z,indexing='ij'),axis=-1).reshape(-1,3)
results=[]
for radius in [float(np.mean(actual['eyeRadii']))-.005,float(np.mean(actual['eyeRadii'])),float(np.mean(actual['eyeRadii']))+.005]:
    for nose_z in [actual['nasalFrontMean'][2]-.014,actual['nasalFrontMean'][2],actual['nasalFrontMean'][2]+.014]:
        envelope=Envelope(eyes,[radius,radius],actual['lowerOralRimMean'],[actual['nasalFrontMean'][0],actual['nasalFrontMean'][1],nose_z])
        try:metrics=envelope.jacobian_report(points);passed=True
        except RuntimeError as error:metrics={'failure':str(error)};passed=False
        results.append({'radiusMeters':radius,'noseZ':nose_z,'passed':passed,'metrics':metrics})
        print(radius,nose_z,passed,metrics,flush=True)
report={'status':'Numerical support-domain parameter sweep only; no saved source or visual proof','helperSha256':hashlib.sha256((HERE/'macro_envelope_v9nb.py').read_bytes()).hexdigest(),
 'cachedEyeLandmarkSource':str(cached.relative_to(ROOT)),'cachedLandmarksMeasuredFromExactInputSource':True,
 'otherLandmarks':'Measured input-source eyes/lip/nose plus a globe-radius +/-5mm and nose-height +/-14mm robustness sweep; not visual validation',
 'supportBoundsMeters':[points.min(0).tolist(),points.max(0).tolist()],'pointsPerCase':len(points),'cases':results,'allPass':all(r['passed']for r in results)}
(ROOT/'benchmark/art/krag/v9nb-envelope-math-preflight.json').write_text(json.dumps(report,indent=2)+'\n',newline='\n')
if not report['allPass']:raise SystemExit(2)
