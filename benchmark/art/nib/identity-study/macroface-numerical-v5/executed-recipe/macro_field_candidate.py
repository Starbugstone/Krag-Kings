"""Broad provisional facial envelope with exact coherent ocular similarities.

Every mesh/shape point is transformed through the same smooth volume field.
No isolated additive Basis delta, abrupt semantic zero or separate nose sphere.
"""
import numpy as np

def smooth(a,b,x):
 t=np.clip((x-a)/(b-a),0,1);return t*t*(3-2*t)
def kernel(r):
 a=np.maximum(0,1-r);return a**4*(4*r+1)

def prepare(raw,basis,eye_centers):
 controls=[]
 def pick(name,target,delta):
  i=int(np.argmin(np.linalg.norm(raw-np.asarray(target),axis=1)))
  controls.append({'name':name,'vertex':i,'source':basis[i].tolist(),'delta':delta,'referenceSourceTarget':target})
 for side,sign in [('R',-1),('L',1)]:
  pick('brow_arch_'+side,[sign*.040,-.130,.342],[sign*.005,-.009,-.001])
  pick('outer_brow_'+side,[sign*.064,-.108,.329],[sign*.003,-.008,.001])
  pick('cheek_peak_'+side,[sign*.075,-.100,.275],[-sign*.006,-.008,.002])
  pick('lower_cheek_'+side,[sign*.065,-.100,.229],[-sign*.008,-.004,.003])
  pick('muzzle_pad_'+side,[sign*.023,-.147,.250],[sign*.002,-.005,.003])
  pick('nasal_ala_'+side,[sign*.019,-.145,.268],[sign*.0005,-.003,.003])
  pick('smile_corner_'+side,[sign*.038,-.136,.235],[sign*.001,-.001,.004 if side=='R'else -.001])
 pick('nasal_dome',[0,-.160,.271],[0,-.002,.005])
 pick('nasal_bridge',[0,-.146,.291],[0,-.003,.003])
 pick('lip_center',[0,-.149,.237],[0,0,.001])
 pick('chin_front',[0,-.1367,.200],[0,-.002,0])
 # Broad volume anchors are outside the facial working envelope. They prevent
 # the finite field from dragging the scalp, rear skull or retained neck join.
 anchors=[]
 for x in [-.12,0,.12]:
  for y in [-.15,-.04,.07]:
   for z in [1.050,1.270]:anchors.append([x,y,z])
 for x in [-.12,.12]:
  for y in [-.15,.07]:
   for z in [1.120,1.200]:anchors.append([x,y,z])
 centers=np.array([c['source']for c in controls]+anchors)
 requested=np.array([c['delta']for c in controls]+[[0,0,0]]*len(anchors))
 ocular=[]
 for side,sign in [('R',-1),('L',1)]:
  angle=np.radians(-sign*10);rotation=np.array([[np.cos(angle),0,np.sin(angle)],[0,1,0],[-np.sin(angle),0,np.cos(angle)]])
  ocular.append({'side':side,'center':eye_centers[side].tolist(),'matrix':(1.12*rotation).tolist(),'translation':[sign*.0015,-.0045,.0028],'innerRadii':[.023,.022,.019],'outerNormalizedRadius':1.7})
 params={'controls':controls,'centers':centers.tolist(),'radiusMeters':.075,'ocular':ocular,'sourceDimensionsProvisional':True}
 eye_delta,eye_weight=ocular_field(centers,params)
 w=global_window(centers)*(1-eye_weight)
 # Camera targets are evidence, not literal per-vertex edits. These authored
 # broad controls express a symmetric anatomical proposal for actual review.
 desired=np.zeros_like(requested);movable=w>.05
 desired[movable]=(requested[movable]-eye_delta[movable])/w[movable,None]
 if not np.all(movable[:len(controls)]):raise RuntimeError('Macro control is buried inside an exact ocular domain')
 K=kernel(np.linalg.norm(centers[:,None]-centers[None,:],axis=2)/params['radiusMeters'])
 params['coefficients']=np.linalg.solve(K+np.eye(len(K))*1e-5,desired).tolist()
 params['controlMatrixCondition']=float(np.linalg.cond(K+np.eye(len(K))*1e-5))
 actual=transform(centers,params)-centers
 params['maximumControlResidualMeters']=float(np.linalg.norm(actual-requested,axis=1).max())
 return params

def global_window(p):
 return smooth(1.077,1.110,p[:,2])*(1-smooth(1.220,1.270,p[:,2]))*(1-smooth(-.035,.010,p[:,1]))

def ocular_field(p,params):
 deltas=[];weights=[]
 for eye in params['ocular']:
  c=np.asarray(eye['center']);q=p-c;r=np.linalg.norm(q/eye['innerRadii'],axis=1)
  w=1-smooth(1,eye['outerNormalizedRadius'],r)
  d=q@np.asarray(eye['matrix']).T+eye['translation']-q
  weights.append(w);deltas.append(d)
 total=np.sum(weights,axis=0);normalizer=np.maximum(total,1)
 delta=sum(d*(w/normalizer)[:,None]for d,w in zip(deltas,weights))
 return delta,np.minimum(total,1)

def transform(points,params):
 points=np.asarray(points,float);result=np.empty_like(points);centers=np.asarray(params['centers']);coeff=np.asarray(params['coefficients'])
 for start in range(0,len(points),16384):
  p=points[start:start+16384];eyed,eyew=ocular_field(p,params)
  radial=kernel(np.linalg.norm(p[:,None]-centers[None,:],axis=2)/params['radiusMeters'])@coeff
  result[start:start+len(p)]=p+eyed+radial*(global_window(p)*(1-eyew))[:,None]
 return result

def jacobian(points,params,step=1e-5):
 p=np.asarray(points,float);columns=[]
 for axis in range(3):
  d=np.zeros(3);d[axis]=step;columns.append((transform(p+d,params)-transform(p-d,params))/(2*step))
 return np.stack(columns,axis=2)
