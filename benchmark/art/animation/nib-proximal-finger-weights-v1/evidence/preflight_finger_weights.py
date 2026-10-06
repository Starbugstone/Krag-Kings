import ast,json,sys
from pathlib import Path
import numpy as np
root=Path(r'D:\Dev\Krag-Kings\benchmark');sys.path.insert(0,str(root/'tools/animation'));import hand_skin_domains as h
module=ast.parse((root/'tools/nib/v5_wip/nib_hand_v5.py').read_text());chains=next(ast.literal_eval(n.value) for n in module.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SOURCE_CHAINS' for t in n.targets))
r=json.loads((root/'local/nib-actual-hand-fit-v2.json').read_text());pts=np.asarray(r['vertices']);raw=np.column_stack([.008+(.227-pts[:,0])/.43,(-.043-pts[:,1])/.43,(pts[:,2]-.610)/.43]);domains,report=h.solve(raw,r['polygons'],True,chains);names,weights,wr=h.weights(raw,domains,chains,joint_half_width=.008);result={}
for digit in h.DIGITS:
 a,b=np.asarray(chains[digit][:2]);v=b-a;length=np.linalg.norm(v);t=(raw-a)@v/(length*length);d=np.linalg.norm(raw-a-t[:,None]*v,axis=1);mask=(t>.35)&(t<.65)&(d<.008/.43);own=[i for i,n in enumerate(names) if n.startswith(digit)];result[digit]={'vertices':int(mask.sum()),'newHandWeightRange':[float(weights[mask,0].min()),float(weights[mask,0].max())],'newOwnDigitWeightMean':float(weights[mask][:,own].sum(axis=1).mean())}
(root/'local/nib-proximal-finger-weights-preflight.json').write_text(json.dumps({'domain':report,'weights':wr,'proximalRows':result,'status':'Numerical proposal only, no native source generated'},indent=2)+'\n');print(json.dumps(result));print(report)
