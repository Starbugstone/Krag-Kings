"""Lightweight actual-cache semantic replacement plan; not a generated IronJaw."""
from pathlib import Path
import sys,json,hashlib
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];ART=ROOT/'benchmark/art/krag'
sys.path.insert(0,str(HERE));sys.path.insert(0,str(HERE.parent/'landmark_wip'))
from anatomical_exclusion import partition
from landmark_relief import Relief
fit=Relief();cache=np.load(ART/'landmarks-v9nc/actual-neutral-surface.npz')
points=fit.transform_head(cache['Head_world'])
mask,report=partition(points,cache['Head_triangles'],cache['Head_triangle_sets'])
# Interface components are anatomical attachment boundaries, not world-Z cuts.
edges=report['interfaceEdges'];neighbors={}
for a,b in edges:neighbors.setdefault(a,[]).append(b);neighbors.setdefault(b,[]).append(a)
seen=set();components=[]
for first in neighbors:
 if first in seen:continue
 queue=[first];seen.add(first);part=[]
 while queue:
  a=queue.pop();part.append(a)
  for b in neighbors[a]:
   if b not in seen:seen.add(b);queue.append(b)
 components.append({'vertices':len(part),'closedDegreeTwo':all(len(neighbors[i])==2 for i in part),'bounds':[points[part].min(0).tolist(),points[part].max(0).tolist()]})
source=json.loads((ART/'landmark-relief-v9o.json').read_text())['source']
result={'status':'Prepared dense anatomical exclusion from the verified v9o field/cache; no mechanical geometry generated','source':source,'nativeSourceExists':True,'derivedCacheOnly':True,'naturalSourceChanged':False,'artisticAcceptance':False,'partition':report,'interfaceComponents':components,'reference':'krag-kings-design/concept-art/07-crusher-claw-and-metal-jaw-sheet.png','constructionRequirements':['Keep Natural complete; generate alternate head with external mandible and lower oral floor removed.','Preserve upper lip/nose/cheek tissue and fit a closed mechanical lining to actual attachment boundary.','Place two cheek bearings on the actual Jaw rotation axis, not front-facing arbitrary cylinders.','Lower mechanical arch, teeth and chin shield use Jaw weights; fixed bearing carriers use Head.','Retain upper dental arch and tongue; remove replaced lower organic teeth/gums from alternate oral assembly.','Fit short tusks to the mechanical dental sockets; no retained organic chin underneath.','Review closed/open front and side and check all retained surfaces before runtime export.']}
p=ART/'anatomy-study/ironjaw-v9o-dense-prepared.json';p.write_text(json.dumps(result,indent=2)+'\n',newline='\n')
print(json.dumps({'removedTriangles':report['removedFaces'],'retainedUpperFaces':report['retainedUpperLipNoseFaces'],'interfaces':components},indent=2))
