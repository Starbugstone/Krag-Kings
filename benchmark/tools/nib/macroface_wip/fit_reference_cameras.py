"""Read-only weak-perspective landmark/camera proposal; no Blender mutation.

Use the exact actual saved face and the audited visible ocular rim IDs.
Reference illustrations are oblique/stylized: retain residuals and uncertainty.
"""
import argparse,hashlib,json,os
os.environ['OPENBLAS_NUM_THREADS']='1'
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
parser=argparse.ArgumentParser();parser.add_argument('--output-dir',type=Path,required=True);args=parser.parse_args()
if args.output_dir.exists():raise RuntimeError('Preserve previous camera fit')
cache_path=ROOT/'benchmark/local/nib-regional-macroface-cache.json';cache=json.loads(cache_path.read_text())
if cache['sourceSha256']!='ed53df0741441724ea84b09af8124132a1be6f33c1d02a31b9b377ddb53c8903':raise RuntimeError('Wrong actual source cache')
p=np.asarray(cache['shapeKeys']['Basis']['coordinates'],float);raw=np.asarray(cache['attributes']['nib_source_position']['values'])
orb_path=ROOT/'benchmark/art/nib/identity-study/orbital-identity-v2-numerical.json';orb=json.loads(orb_path.read_text());reference_path=HERE/'reference_landmarks.json';reference=json.loads(reference_path.read_text())
if sha(ROOT/reference['image'])!=reference['imageSha256']:raise RuntimeError('Reference changed')
features={}
for side in ['R','L']:
 arc=np.asarray(orb['closure']['eyes'][side]['upperArc']);a,b=int(arc[0]),int(arc[-1]);outer,inner=(a,b)if side=='R'else(b,a)
 for label,index in [('outer',outer),('inner',inner)]:features[label+'_'+side]={'vertex':index,'point':p[index].tolist(),'selection':'Audited visible orbital-margin canthus'}
def pick(name,target):
 index=int(np.argmin(np.linalg.norm(raw-np.asarray(target),axis=1)));features[name]={'vertex':index,'point':p[index].tolist(),'sourcePoint':raw[index].tolist(),'sourceTarget':target,'selection':'Nearest audited source anatomical landmark; actual exterior interpretation still reviewed'}
for side,sign in [('R',-1),('L',1)]:
 pick('brow_'+side,[sign*.040,-.130,.342])
 pick('cheek_'+side,[sign*.075,-.10,.275])
 pick('mouth_'+side,[sign*.038,-.136,.235])
pick('lip_center',[0,-.149,.237]);pick('chin',[0,-.1367,.200])
mask=np.asarray(cache['attributes']['NibNoseMask']['values']);ids=np.flatnonzero(mask>.8);index=int(ids[np.argmin(p[ids,1])]);features['nose_tip']={'vertex':index,'point':p[index].tolist(),'selection':'Foremost actual nose-mask exterior point'}

def projection(yaw,pitch):
 y,t=np.radians([yaw,pitch]);u=np.array([np.cos(y),np.sin(y),0]);d=np.array([-np.sin(y),np.cos(y),0]);v=-np.array([0,0,np.cos(t)])-np.sin(t)*d
 return np.array([u,v])

def fit(view):
 names=[n for n in view['points']if n in features];source=np.array([features[n]['point']for n in names]);target=np.array([view['points'][n]for n in names],float)
 weights=np.array([2. if n.startswith(('outer','inner'))else .7 if n.startswith(('brow','cheek'))else 1. for n in names]);weights/=weights.sum()
 target_center=weights@target;v=target-target_center;best=None
 for yaw in np.arange(*[view['yawDegreesRange'][0],view['yawDegreesRange'][1]+.1],1.):
  for pitch in np.arange(view['pitchDegreesRange'][0],view['pitchDegreesRange'][1]+.1,1.):
   proj=projection(yaw,pitch);base=source@proj.T;center=weights@base;u=base-center
   # Full 2D similarity fits head roll while retaining one isotropic scale.
   cov=(u*weights[:,None]).T@v;U,S,Vt=np.linalg.svd(cov);R=U@Vt
   if np.linalg.det(R)<0:continue
   scale=float(S.sum()/np.sum(weights[:,None]*u*u));offset=target_center-scale*(center@R);A=scale*R.T@proj;pred=source@A.T+offset
   error=np.linalg.norm(pred-target,axis=1);cost=float(weights@(error*error))
   if best is None or cost<best['weightedSquaredErrorPixels']:
    best={'yawDegrees':float(yaw),'pitchDegrees':float(pitch),'rollDegrees':float(np.degrees(np.arctan2(R[0,1],R[0,0]))),'scalePixelsPerMeter':scale,'matrixPixelsPerMeter':A.tolist(),'offsetPixels':offset.tolist(),'weightedSquaredErrorPixels':cost,'rmsPixels':float(np.sqrt(cost)),'manualUncertaintyPixels':view['uncertaintyPixels'],'landmarks':{n:{'reference':target[i].tolist(),'projected':pred[i].tolist(),'residualPixels':float(error[i])}for i,n in enumerate(names)}}
 return best
cameras={name:fit(v)for name,v in reference['views'].items()}
# Triangulate the same visible landmark from independent fitted camera rows.
# This is an evidence-driven proposal, not an automatically accepted sculpt.
targets={}
for name,feature in features.items():
 rows=[];values=[]
 for view,camera in cameras.items():
  if name not in reference['views'][view]['points']:continue
  weight=1/reference['views'][view]['uncertaintyPixels'];rows.extend(weight*np.array(camera['matrixPixelsPerMeter']));values.extend(weight*(np.array(reference['views'][view]['points'][name])-camera['offsetPixels']))
 point=np.asarray(feature['point']);A=np.asarray(rows);b=np.asarray(values)
 # 8mm prior uncertainty regularizes depth where the illustrations disagree.
 strength=1/.008;M=np.vstack([A,np.eye(3)*strength]);rhs=np.r_[b,point*strength];target=np.linalg.lstsq(M,rhs,rcond=None)[0]
 targets[name]={'source':point.tolist(),'proposed':target.tolist(),'deltaMeters':(target-point).tolist(),'distanceMeters':float(np.linalg.norm(target-point)),'views':len(rows)//2}
report={'status':'Actual numerical camera fit/landmark target proposal; no native geometry generated','sourceCacheSha256':sha(cache_path),'sourceSha256':cache['sourceSha256'],'referenceSha256':sha(reference_path),'ocularReportSha256':sha(orb_path),'coordinateSpace':'Saved Head-local metres; fitted weak-perspective image coordinates','features':features,'cameras':cameras,'landmarkTargets':targets,'cautions':reference['cautions'],'artisticAcceptance':False,'sharedChanged':False,'codeSha256':sha(Path(__file__))}
args.output_dir.mkdir(parents=True);(args.output_dir/'camera-fit.json').write_text(json.dumps(report,indent=2)+'\n',newline='\n');print(json.dumps({'cameras':{k:{x:v[x]for x in ['yawDegrees','pitchDegrees','rollDegrees','rmsPixels']}for k,v in cameras.items()},'targets':{k:v['deltaMeters']for k,v in targets.items()}},indent=2))
