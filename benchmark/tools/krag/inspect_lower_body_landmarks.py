"""Read-only retained topology study; no Blender process or generated model."""
from pathlib import Path
import numpy as np,json,hashlib
root=Path(__file__).resolve().parents[3];p=root/'benchmark/art/krag/anatomy-study/GEO-body_male_realistic.npz'
v=np.load(p)['vertices'];result={'source':str(p.relative_to(root)),'sourceSha256':hashlib.sha256(p.read_bytes()).hexdigest(),'status':'Numerical source-cage study only; no accepted Krag lower-body design or generated mesh','vertices':len(v),'bounds':{'minimum':v.min(0).tolist(),'maximum':v.max(0).tolist()},'positiveLegSlices':[]}
for z,band in [(0,.018),(.035,.013),(.070,.014),(.100,.015),(.135,.014),(.18,.015),(.27,.025),(.36,.025),(.45,.022),(.52,.023),(.63,.025),(.73,.025),(.83,.025),(.91,.025)]:
 q=v[(v[:,0]>0)&(v[:,0]<.25)&(abs(v[:,2]-z)<band)]
 result['positiveLegSlices'].append({'z':z,'halfBand':band,'count':len(q),'minimum':q.min(0).tolist() if len(q) else None,'maximum':q.max(0).tolist() if len(q) else None,'median':np.median(q,axis=0).tolist() if len(q) else None})
p=root/'benchmark/art/krag/anatomy-study/lower-body-source-landmarks.json';p.write_text(json.dumps(result,indent=2)+'\n',newline='\n');print(json.dumps(result,indent=2))
