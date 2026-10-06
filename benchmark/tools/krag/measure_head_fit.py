"""Read-only numerical cage-fit diagnostics; does not open Blender or alter assets."""
from pathlib import Path
import numpy as np,ast,json,hashlib,argparse
parser=argparse.ArgumentParser();parser.add_argument('--version',default='v9c');parser.add_argument('--reference-head-scale',action='store_true');options=parser.parse_args()
root=Path(__file__).resolve().parents[3]
script=Path(__file__).with_name('krag_head_v9.py')
ast_root=ast.parse(script.read_text());function=next(n for n in ast_root.body if isinstance(n,ast.FunctionDef) and n.name=='fit');namespace={'np':np};exec(compile(ast.Module(body=[function],type_ignores=[]),str(script),'exec'),namespace)
source=root/'benchmark/art/krag/anatomy-study/GEO-head_animation_realistic.npz'
data=np.load(source);v=data['vertices'];fit=namespace['fit'];t=fit(v);t[:,0]*=.93;t[:,1]*=.94;t[:,2]=2.107+(t[:,2]-2.107)*.85
if options.reference_head_scale:
 from krag_proportions_v9f import transform
 t=transform(t)
regions={}
for title,mask in [('cranium',(v[:,2]>.32)&(v[:,2]<.4)),('jaw',(v[:,2]>.175)&(v[:,2]<.22)),('head_without_neck',v[:,2]>.168)]:
 q=t[mask];regions[title]={'minimumMeters':q.min(0).tolist(),'maximumMeters':q.max(0).tolist(),'sizeMeters':np.ptp(q,axis=0).tolist()}
eyes=fit([[.0358764,-.1153812,.3100375],[-.0358764,-.1153812,.3100375]]);eyes*=np.array((.93,.94,.85));eyes[:,2]+=.15*2.107
if options.reference_head_scale:eyes=transform(eyes)
result={'status':'Code-only fitted control-cage measurement; not an actual Blender render or accepted proportion','fitScriptSha256':hashlib.sha256(script.read_bytes()).hexdigest(),'sourceDataSha256':hashlib.sha256(source.read_bytes()).hexdigest(),'regions':regions,'expectedFittedEyeCentersMeters':eyes.tolist()}
if options.reference_head_scale:
 from krag_proportions_v9f import specification
 result['wholeAssemblyProportion']=specification()
 result['proportionHelperSha256']=hashlib.sha256(Path(__file__).with_name('krag_proportions_v9f.py').read_bytes()).hexdigest()
from anatomy_warp_study import warp
body=warp(np.load(source.with_name('GEO-body_male_realistic.npz'))['vertices'])
shoulders=body[(body[:,2]>1.53)&(body[:,2]<1.74)]
shoulder_width=float(np.ptp(shoulders[:,0]))
result['anatomicalShoulderBandWidthMeters']=shoulder_width
result['headToShoulderWidthRatio']=regions['cranium']['sizeMeters'][0]/shoulder_width
landmarks={}
for label,point in {'nasalTip':(0,-.162,.270),'upperLip':(0,-.122,.239),'lowerLip':(0,-.126,.222),'chin':(0,-.116,.180),'brow_L':(.037,-.109,.334),'cheek_L':(.057,-.095,.281)}.items():
 index=int(np.argmin(np.linalg.norm(v-np.asarray(point),axis=1)))
 landmarks[label]={'sourceVertex':index,'sourceMeters':v[index].tolist(),'fittedMeters':t[index].tolist()}
result['profileLandmarks']=landmarks
out=root/('benchmark/art/krag/anatomy-study/head-fit-'+options.version+'-measurements.json');out.write_text(json.dumps(result,indent=2)+'\n',newline='\n');print(json.dumps(result,indent=2))
