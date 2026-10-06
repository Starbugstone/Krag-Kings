from pathlib import Path
import json,numpy as np,hashlib
root=Path(__file__).resolve().parents[4];old_path=root/'benchmark/art/nib/groom-study/coherent79-v2-runtime-wide-nap/groom-source.json';new_path=root/'benchmark/art/nib/motion-study/semantic-body-v2/source.json'
a=json.loads(old_path.read_text())['preservedRigAndActions']['bones'];b=json.loads(new_path.read_text())['preservedRig']['bones'];rows=[]
chains={}
for j,n in enumerate(['Index','Middle','Ring','Little']):
 x=.227+(j-1.5)*.012;z=.563-(.008 if j in [0,3] else 0);chains[n]=[(x,-.046,z+.01),(x+.004,-.049,z-.011),(x+.003,-.060,z-.028),(x,-.070,z-.032)]
chains['Thumb']=[(.206,-.042,.594),(.193,-.055,.581),(.190,-.066,.565)]
for name,p in chains.items():
 for i in range(len(p)-1):
  n=name+str(i+1)+'_L';old=np.asarray(a[n]['matrix']);new=np.asarray(b[n]['matrix']);delta=np.asarray(p[i+1])-p[i];length=float(delta@old[:3,1]);head=float(np.linalg.norm(old[:3,3]-p[i]));axis=float(np.linalg.norm(delta-old[:3,1]*length));rows.append({'bone':n,'oldHeadMatchMeters':head,'oldAxisMismatchMeters':axis,'oldSegmentLengthMeters':length,'newHeadShiftMeters':float(np.linalg.norm(new[:3,3]-old[:3,3]))})
  if head>2e-7 or axis>2e-7 or length<=0:raise RuntimeError(str(rows[-1]))
r={'status':'Prepared old mechanical segment vs actual saved rest-frame preflight; no native geometry mutation/posed proof','oldRestReportSha256':hashlib.sha256(old_path.read_bytes()).hexdigest(),'newRestReportSha256':hashlib.sha256(new_path.read_bytes()).hexdigest(),'segments':rows,'all14RestFrameIdentitiesPassed':True,'recipeSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'maxHeadMatchMeters':max(x['oldHeadMatchMeters'] for x in rows),'maxAxisMismatchMeters':max(x['oldAxisMismatchMeters'] for x in rows)}
p=root/'benchmark/art/nib/motion-study/restorative-rest-preflight.json';p.write_text(json.dumps(r,indent=2)+'\n',newline='\n');print(json.dumps({k:v for k,v in r.items() if k!='segments'},indent=2))
