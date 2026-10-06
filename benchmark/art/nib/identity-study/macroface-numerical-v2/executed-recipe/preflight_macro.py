"""Numerical exact-shape topology/closure preflight, before native generation."""
import argparse,hashlib,json,os
os.environ['OPENBLAS_NUM_THREADS']='1'
from pathlib import Path
import numpy as np
from macro_field import prepare,transform,jacobian
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
parser=argparse.ArgumentParser();parser.add_argument('--output-dir',type=Path,required=True);args=parser.parse_args()
if args.output_dir.exists():raise RuntimeError('Preserve previous numerical candidate')
cache_path=ROOT/'benchmark/local/nib-regional-macroface-cache.json';cache=json.loads(cache_path.read_text());old_path=ROOT/'benchmark/local/nib-v5i-orbital-geometry.npz';geometry=np.load(old_path)
if cache['sourceSha256']!='ed53df0741441724ea84b09af8124132a1be6f33c1d02a31b9b377ddb53c8903':raise RuntimeError('Wrong source')
raw=np.asarray(cache['attributes']['nib_source_position']['values']);faces=np.asarray(cache['polygons'],int);basis=np.asarray(cache['shapeKeys']['Basis']['coordinates'],float)
if not np.array_equal(raw,geometry['source'])or not np.array_equal(faces,geometry['faces']):raise RuntimeError('Reference anatomy topology changed')
keys={k:np.asarray(v['coordinates'],float)for k,v in cache['shapeKeys'].items()};params=prepare(raw,basis,{side:geometry['eyeCenter_'+side]for side in ['L','R']})
transformed={k:transform(v,params)for k,v in keys.items()};tri=np.vstack([faces[:,[0,1,2]],faces[:,[0,2,3]]]);edges=geometry['edges']
def metrics(old,new):
 def normals(p):
  q=p[tri];return np.cross(q[:,1]-q[:,0],q[:,2]-q[:,0])
 a=normals(old);b=normals(new);aa=np.linalg.norm(a,axis=1);bb=np.linalg.norm(b,axis=1);active=aa>1e-14
 d=np.linalg.norm(new-old,axis=1);return {'maximumMoveMeters':float(d.max()),'introducedDegenerates':int(np.sum(active&(bb<=1e-14))),'trianglesTurnedBeyond90FromSameOriginalShape':int(np.sum((np.sum(a*b,axis=1)<0)&active)),'minimumAreaRatio':float((bb[active]/aa[active]).min()),'maximumEdgeStretch':float((np.linalg.norm(new[edges[:,1]]-new[edges[:,0]],axis=1)/np.maximum(np.linalg.norm(old[edges[:,1]]-old[edges[:,0]],axis=1),1e-15)).max())}
shape_metrics={k:metrics(keys[k],v)for k,v in transformed.items()};sample=np.unique(np.r_[np.arange(0,len(basis),7),[c['vertex']for c in params['controls']]])
J=jacobian(basis[sample],params);det=np.linalg.det(J);eig=np.linalg.svd(J,compute_uv=False)
optical={}
for side in ['L','R']:
 e=next(e for e in params['ocular']if e['side']==side);c=np.asarray(e['center']);A=np.asarray(e['matrix']);t=np.asarray(e['translation']);parts={}
 for part in ['sclera','iris']:
  q=geometry[part+'_'+side];actual=transform(q,params);expected=(q-c)@A.T+c+t
  parts[part]={'vertices':len(q),'maximumNonSimilarityErrorMeters':float(np.linalg.norm(actual-expected,axis=1).max()),'scale':1.12}
 optical[side]=parts
# Compare the engine's linear morph sum with the transformed original combined
# pose. Both sides are independent support; nonlinear cross-talk is measured.
combined={}
for label,names in [('Blink',['Blink_L','Blink_R']),('Squint',['Squint_L','Squint_R']),('Playful',['Smile_L','Smile_R','JawOpen','TongueOut'])]:
 old=basis.copy();new=transformed['Basis'].copy()
 for name in names:
  if name in keys:old+=keys[name]-basis;new+=transformed[name]-transformed['Basis']
 exact=transform(old,params);combined[label]={'maximumMorphSuperpositionErrorMeters':float(np.linalg.norm(new-exact,axis=1).max()),**metrics(old,new)}
# Closure is checked by the same audited pairs, preserving their exact support
# through the coherent volume. Do not infer self-collision absence from normals.
orb=json.loads((ROOT/'benchmark/art/nib/identity-study/orbital-identity-v2-numerical.json').read_text());closure={}
for side in ['L','R']:
 e=orb['closure']['eyes'][side];upper=np.asarray(e['upperArc']);lower=np.asarray(e['lowerArc']);old=keys['Blink_'+side];new=transformed['Blink_'+side]
 # Nearest opposite rim point: report max/p95 separation, not a new pairing.
 dist=np.linalg.norm(old[upper,None]-old[lower][None],axis=2);pair=lower[np.argmin(dist,axis=1)];old_d=np.linalg.norm(old[upper]-old[pair],axis=1);new_d=np.linalg.norm(new[upper]-new[pair],axis=1)
 closure[side]={'upperRimVertices':len(upper),'baselineMaximumNearestOppositeRimMeters':float(old_d.max()),'candidateMaximumSamePairMeters':float(new_d.max()),'baselineP95Meters':float(np.quantile(old_d,.95)),'candidateP95Meters':float(np.quantile(new_d,.95))}
fail=[]
if params['maximumControlResidualMeters']>.00025:fail.append('Broad control interpolation residual exceeds0.25mm')
if det.min()<=.10:fail.append('Volume-field Jacobian determinant <=0.10')
if eig.min()<=.25:fail.append('Volume field collapses a local direction below25%')
for name,m in shape_metrics.items():
 if m['introducedDegenerates']or m['trianglesTurnedBeyond90FromSameOriginalShape']:fail.append('New topology fold/degenerate in '+name)
for side,parts in optical.items():
 for part,m in parts.items():
  if m['maximumNonSimilarityErrorMeters']>1e-6:fail.append('Optical assembly leaves exact similarity domain '+part+side)
for name,m in combined.items():
 if m['maximumMorphSuperpositionErrorMeters']>.00025:fail.append('Morph-combination nonlinear error exceeds0.25mm '+name)
report={'status':'Actual numerical proposal only; no native source/render','sourceSha256':cache['sourceSha256'],'cacheSha256':sha(cache_path),'ocularCacheSha256':sha(old_path),'params':params,'shapes':shape_metrics,'jacobian':{'samples':len(sample),'minimumDeterminant':float(det.min()),'maximumDeterminant':float(det.max()),'minimumSingularValue':float(eig.min())},'optical':optical,'combined':combined,'closure':closure,'blockingIssues':fail,'hardStructuralFailure':bool(fail),'artisticAcceptance':False,'sharedChanged':False,'codeSha256':{p.name:sha(p)for p in [Path(__file__),HERE/'macro_field.py']},'pending':['Actual native same-source geometry/shape checks','Refit Eye rest axes/centers by exact ocular similarity; explicit migration report','Actual neutral/profile and Blink/Tongue evaluated LBS; oral collision check','Camera-matched broad identity and materials/groom after shape']}
args.output_dir.mkdir(parents=True);np.savez_compressed(args.output_dir/'proposal.npz',expectedBasis=basis,**{'expected_'+k:v for k,v in keys.items()},**{'target_'+k:v for k,v in transformed.items()});report['proposalSha256']=sha(args.output_dir/'proposal.npz');(args.output_dir/'numerical.json').write_text(json.dumps(report,indent=2)+'\n',newline='\n');print(json.dumps({k:report[k]for k in ['jacobian','optical','closure','blockingIssues']},indent=2))
if fail:raise RuntimeError('Macroface numerical gate failed; preserve this candidate')
print('NIB_MACROFACE_NUMERICAL_PREFLIGHT_COMPLETE')
