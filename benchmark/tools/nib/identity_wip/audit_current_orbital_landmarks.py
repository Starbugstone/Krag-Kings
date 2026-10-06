from pathlib import Path
import json,hashlib,numpy as np
root=Path(__file__).resolve().parents[4];p=root/'benchmark/local/nib-v5i-orbital-proposal-rotation.npz';data=np.load(p);points=data['neutral'];r=json.loads((root/'benchmark/art/nib/v5-study/native-v5i-orbital-proposal-rotation.json').read_text())
if hashlib.sha256(p.read_bytes()).hexdigest()!=r['proposalCacheSha256']:
 raise RuntimeError('Actual v5i construction cache changed')
if hashlib.sha256((root/'benchmark/local/nib-v5i-orbital-geometry.npz').read_bytes()).hexdigest()!=r['cacheSha256']:
 raise RuntimeError('Audited ocular cache changed')
geometry=np.load(root/'benchmark/local/nib-v5i-orbital-geometry.npz');records={}
for side in ['L','R']:
 eye=r['eyes'][side];u=points[eye['upperArc']];l=points[eye['lowerArc']];x=np.linspace(max(u[:,0].min(),l[:,0].min()),min(u[:,0].max(),l[:,0].max()),201);zu=np.interp(x,u[:,0],u[:,2]);zl=np.interp(x,l[:,0],l[:,2]);height=zu-zl;width=x[-1]-x[0];iris=geometry['iris_'+side]
 records[side]={'widthMeters':float(width),'maximumVerticalApertureMeters':float(height.max()),'widthToMaximumHeight':float(width/height.max()),'centerVerticalApertureMeters':float(height[len(height)//2]),'irisBounds':[iris.min(0).tolist(),iris.max(0).tolist()],'rimBounds':[points[eye['ring']].min(0).tolist(),points[eye['ring']].max(0).tolist()]}
report={'status':'Read-only numerical landmark audit of the actual v5i neutral proposal used by the coherent face; no new geometry', 'neutralCacheSha256':hashlib.sha256(p.read_bytes()).hexdigest(), 'proposalReportSha256':hashlib.sha256((root/'benchmark/art/nib/v5-study/native-v5i-orbital-proposal-rotation.json').read_bytes()).hexdigest(), 'eyes':records, 'referenceComparison':{'manualPortraitWidthHeightRatio':2.3333333333333335,'measurementSource':'benchmark/art/nib/v5-study/proportions/nib-reference-proportions.json','caution':'2D illustration and mesh-axis projection differ in perspective and expression; this identifies a tendency, not an approved numeric target'},'codeSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'sharedChanged':False}
(root/'benchmark/art/nib/identity-study/current-orbital-landmarks.json').write_text(json.dumps(report,indent=2)+'\n',newline='\n')
print(json.dumps(records,indent=2))
