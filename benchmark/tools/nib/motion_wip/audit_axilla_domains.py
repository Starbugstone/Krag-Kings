"""Read-only numerical domain diagnosis on the actual saved Body cache.

This compares the field used to fit anatomy with the field used to skin it.
It does not establish posed attribution by itself or modify any Blender source.
"""
import json,hashlib,collections,sys
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sys.path.insert(0,str(HERE));from forearm_twist import smooth
source=ROOT/'benchmark/local/nib-actual-garment-v2-body-domains.json';d=json.loads(source.read_text())
p=np.asarray(d['vertices']);raw=np.asarray(d['attributes']['Nib_BodyReferencePosition']['values']);domain=np.asarray(d['attributes']['Nib_ArmDomain']['values'])
x=abs(raw[:,0]);threshold=.120+.035*np.clip((raw[:,2]-1.20)/.16,0,1);fit=smooth(threshold,threshold+.09,x)
arm=np.asarray([sum(w for name,w in row if name.startswith(('Clavicle','UpperArm','LowerArm','ForearmTwist','Hand'))) for row in d['weights']])
counts=collections.Counter(tuple(sorted((a,b))) for f in d['polygons'] for a,b in zip(f,f[1:]+f[:1]));adj=collections.defaultdict(set)
for (a,b),n in counts.items():
 if n==1:adj[a].add(b);adj[b].add(a)
remaining=set(adj);boundaries=[]
while remaining:
 i=remaining.pop();stack=[i];ids=[i]
 while stack:
  for j in adj[stack.pop()]:
   if j in remaining:remaining.remove(j);stack.append(j);ids.append(j)
 values=p[ids];boundaries.append({'vertices':len(ids),'bounds':[values.min(0).tolist(),values.max(0).tolist()],'armDomainRange':[float(domain[ids].min()),float(domain[ids].max())]})
# Candidate mismatch is a source-attribution measurement, not an acceptance test.
mask=(fit>.75)&(domain<.25)&(raw[:,2]>1.10)&(raw[:,2]<1.37)
ids=np.flatnonzero(mask);worst=sorted(ids,key=lambda i:float(domain[i]-fit[i]))[:20]
rows=[{'vertex':int(i),'restPosition':p[i].tolist(),'sourceReferencePosition':raw[i].tolist(),'fitArmBlend':float(fit[i]),'skinArmDomain':float(domain[i]),'weights':d['weights'][i]} for i in worst]
report={'status':'Actual saved rest-domain diagnosis; posed LBS isolation still required','sourceSha256':d['sourceSha256'],'cacheSha256':hashlib.sha256(source.read_bytes()).hexdigest(),'auditCodeSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'vertices':len(p),'openBoundaryLoops':sorted(boundaries,key=lambda v:-v['vertices']),'nonManifoldEdgesAboveTwoFaces':sum(n>2 for n in counts.values()),'skinArmWeightVsStoredDomainMaxError':float(np.max(abs(arm-domain))),'fitOver75SkinUnder25UpperArmCandidates':len(ids),'candidateRestBounds':[p[ids].min(0).tolist(),p[ids].max(0).tolist()] if len(ids) else None,'worstCandidates':rows,'inference':'Position-based arm fitting and geodesic arm skinning use different fields. Upper-arm-shaped surface that remains chest-weighted can stay behind during elevation, producing an axillary sheet. This requires posed vertex correspondence before a weight repair is accepted.','boundaryFinding':'Only neck, covered waist and two wrist loops are open; no anatomical axillary cut exists in the retained mesh. Apparent jagged underarm edge is a deformed silhouette, not a missing armpit boundary.','sourceChanged':False,'sharedChanged':False}
out=ROOT/'benchmark/art/nib/motion-study/axilla-rest-domain-audit-v2.json';out.write_text(json.dumps(report,indent=2)+'\n',newline='\n')
print(json.dumps({k:v for k,v in report.items() if k!='worstCandidates'},indent=2));print(json.dumps(rows[:4],indent=2))
