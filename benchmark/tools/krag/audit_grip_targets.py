"""Numerical reach audit for prepared anatomical grip targets; no Blender launch."""
import ast,hashlib,json
from pathlib import Path
import numpy as np
from anatomy_warp_study import warp

folder=Path(__file__).parent;root=folder.parents[2]
tree=ast.parse((folder/'krag_anatomy.py').read_text())
function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='hand_landmarks')
namespace={'np':np,'warp':warp};exec(compile(ast.Module(body=[function],type_ignores=[]),'hand_landmarks','exec'),namespace)
points=namespace['hand_landmarks']('R');knuckles=np.asarray([points['Finger_'+str(j)][0] for j in range(4)])
row=knuckles[-1]-knuckles[0];row[2]=0;row/=np.linalg.norm(row);normal=np.array([-row[1],row[0],0])
center=knuckles.mean(0)+normal*.055+[0,0,.008];samples=[]
for name,chain in points.items():
    chain=np.asarray(chain);a,b=np.linalg.norm(np.diff(chain,axis=0),axis=1)
    if name=='Thumb':target=center+normal*.050+row*.025+[0,0,.038]
    else:target=center+row*np.dot(chain[0]-center,row)+normal*.053+[0,0,-.005]
    distance=np.linalg.norm(target-chain[0]);margin=float(min(distance-abs(a-b),a+b-distance))
    if margin<=1e-5:raise AssertionError('Unreachable '+name)
    samples.append({'chain':name,'root':chain[0].tolist(),'target':target.tolist(),
                    'segmentsMeters':[float(a),float(b)],'distanceMeters':float(distance),'reachMarginMeters':margin})
report={'status':'Prepared target reach only; no generated source or visual grip/contact acceptance',
    'helperSha256':hashlib.sha256((folder/'krag_grip_v2.py').read_bytes()).hexdigest(),
    'knuckleRowSpanMeters':float(np.linalg.norm(knuckles[-1]-knuckles[0])),
    'handleCenterMeters':center.tolist(),'rowAxis':row.tolist(),'palmNormal':normal.tolist(),
    'samples':samples}
out=root/'benchmark/art/krag/anatomy-study/grip-v2-target-measurements.json'
out.write_text(json.dumps(report,indent=2)+'\n',newline='\n');print(json.dumps(report,indent=2))
