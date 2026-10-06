from pathlib import Path
import numpy as np,json
root=Path(__file__).resolve().parents[3];base=root/'benchmark/art/krag/anatomy-study'
j=json.loads((base/'library-inventory.json').read_text());objs={x['name']:x for x in j['objects']};headinv=np.linalg.inv(objs['GEO-head_animation_realistic']['matrixWorld'])
for part in ['sclera','iris']:
 name='GEO-head_animation_realistic.'+part+'.L';q=np.load(base/(name+'.npz'));print(name,q.files)
 v=q['vertices'];w=np.c_[v,np.ones(len(v))]@(headinv@np.array(objs[name]['matrixWorld'])).T;center=np.array([.0358764,-.1153812,.3100375]);delta=w[:,:3]-center
 print('bounds',w.min(0),w.max(0),'localbounds',v.min(0),v.max(0));print('front quantile',np.quantile(delta[:,1],[0,.01,.05,.1,.25,.5,.75,.9,1]));print('materials',[(key,np.unique(q[key])) for key in q.files if 'mat' in key.lower()])
