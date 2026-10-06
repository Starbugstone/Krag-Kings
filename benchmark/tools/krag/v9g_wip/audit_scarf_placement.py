"""Read-only collar-envelope diagnostic, run with Blender under serial guard.

Loads the actual saved v9f anatomy. It never changes or saves that source.
Reports which anatomical triangle supplied each radial/nearest support sample,
including interpolated source arm-domain membership, before any simulation.
"""
from pathlib import Path
import sys,json,hashlib,collections
import bpy,numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sys.path.insert(0,str(HERE));import scarf_cloth
source=ROOT/'benchmark/art/krag/Krag_Master_v9f_WIP.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
original_sha=hashlib.sha256(source.read_bytes()).hexdigest()
refs=[bpy.data.objects['EDITABLE Krag anatomical control cage'],bpy.data.objects['EDITABLE Krag continuous facial cage']]
# Both saved cages are already in final proportion space; do NOT apply H twice.
colliders=[scarf_cloth.collider_copy(o,head=False) for o in refs]
surfaces=[]
for o in colliders:
 v=np.asarray([tuple(o.matrix_world@p.co) for p in o.data.vertices])
 p=[tuple(p.vertices) for p in o.data.polygons]
 arm=o.data.attributes.get('Krag_ArmDomain_v2')
 domain=np.asarray([d.value for d in arm.data]) if arm else None
 surfaces.append((o,v,p,domain,BVHTree.FromPolygons([Vector(x) for x in v],p)))
points,faces,pins=scarf_cloth.initial_sheet();samples=[];counts=collections.Counter()
for i,p in enumerate(points):
 origin=Vector((0,.019,p[2]));direction=Vector(p)-origin;radius=direction.length;direction.normalize()
 hits=[]
 for o,v,polys,domain,tree in surfaces:
  hit,normal,index,distance=tree.ray_cast(origin,direction,.5)
  if hit is None:continue
  face=polys[index];armmean=float(np.mean(domain[list(face)])) if domain is not None else None
  hits.append({'collider':o.name,'distanceMeters':float(distance),'requiredRadiusMeters':float(distance+.009),'hitMeters':list(hit),'normal':list(normal),'triangleOrPolygon':int(index),'armDomainMean':armmean,'anatomicalZone':'head/neck' if domain is None else ('arm/shoulder' if armmean>.5 else 'torso/neck'),'supportVerticesMeters':v[list(face)].tolist()})
 required=max([radius]+[h['requiredRadiusMeters'] for h in hits]);winner=max(hits,key=lambda h:h['requiredRadiusMeters']) if hits else None
 if winner:counts[winner['anatomicalZone']]+=1
 samples.append({'vertex':i,'stripU':i//29/176,'widthV':i%29/28,'initialMeters':p.tolist(),'initialRadiusMeters':float(radius),'requiredRadiusMeters':float(required),'radialAdjustmentMeters':float(required-radius),'pinWeight':float(pins[i]),'support':winner,'allHits':hits})
worst=sorted(samples,key=lambda r:r['radialAdjustmentMeters'],reverse=True)
over=[s for s in samples if s['requiredRadiusMeters']>.32]
report={'status':'Read-only actual-cage support diagnostic; no new scarf source or simulation','source':str(source.relative_to(ROOT)),'sourceSha256':original_sha,'scriptSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'samples':len(samples),'colliderZoneCounts':dict(counts),'radiusOverCapCount':len(over),'maximumRequiredRadiusMeters':max(s['requiredRadiusMeters'] for s in samples),'maximumRadialAdjustmentMeters':max(s['radialAdjustmentMeters'] for s in samples),'worst80':worst[:80],'overCapFirst40':over[:40],'angleHeightBins':[]}
for iz in range(7):
 z0=1.50+iz*.06
 for ia in range(8):
  chosen=[s for s in samples if z0<=s['initialMeters'][2]<z0+.06 and ia<=((np.arctan2(s['initialMeters'][1]-.019,s['initialMeters'][0])+np.pi)/(2*np.pi)*8)<ia+1]
  if chosen:report['angleHeightBins'].append({'zRangeMeters':[z0,z0+.06],'angleOctant':ia,'count':len(chosen),'maxRequiredRadiusMeters':max(s['requiredRadiusMeters'] for s in chosen),'maxRadialAdjustmentMeters':max(s['radialAdjustmentMeters'] for s in chosen),'supportZones':dict(collections.Counter(s['support']['anatomicalZone'] for s in chosen if s['support']))})
out=ROOT/'benchmark/art/krag/v9g-scarf-placement-audit.json';out.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
assert hashlib.sha256(source.read_bytes()).hexdigest()==original_sha
print(json.dumps({k:report[k] for k in ['samples','colliderZoneCounts','radiusOverCapCount','maximumRequiredRadiusMeters','maximumRadialAdjustmentMeters']},indent=2),flush=True)
