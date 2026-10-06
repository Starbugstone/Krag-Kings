"""Lightweight proposal check on v5f's actual saved audit cache; not a render."""
import hashlib,json
from pathlib import Path
import numpy as np
from face_planes_v5g import plane_delta,MouthContact

ROOT=Path(__file__).resolve().parents[4]
CACHE=ROOT/'benchmark/local/nib-v5f-mouth-audit.npz'
archive=np.load(CACHE,allow_pickle=True)
source=archive['source'];basis=archive['local']
delta,fields=plane_delta(source,basis)
solver=MouthContact(source,archive['faces'],archive['face_sets'],archive['edges'])
rejected_contact,contact=solver.close(basis+delta)
result=basis+delta
contact['applied']=False
contact['status']='Rejected lip-curve contact: introduces 43 >90 degree triangle rotations; selected proposal uses only the independent shape field'
triangles=[];triangle_sets=[]
for face,tag in zip(archive['faces'],archive['face_sets']):
    for i in range(1,len(face)-1):triangles.append([face[0],face[i],face[i+1]]);triangle_sets.append(int(tag))
triangles=np.asarray(triangles,dtype=np.int32);triangle_sets=np.asarray(triangle_sets)
def surface(points):
    p=points[triangles]
    normal=np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0]);area=np.linalg.norm(normal,axis=1)
    return normal,area
old_normal,old_area=surface(basis);new_normal,new_area=surface(result)
valid=(old_area>1e-12)&(new_area>1e-12)
cosine=np.ones(len(triangles));cosine[valid]=np.sum(old_normal[valid]*new_normal[valid],axis=1)/(old_area[valid]*new_area[valid])
changed_degenerate=(old_area>1e-12)&(new_area<=1e-12)
reversed_faces=valid&(cosine<0)
surface_report={'triangulation':'Read-only polygon fan diagnostic; not an exported topology',
    'triangleCount':len(triangles),'oldDegenerateAtDoubleArea1e12':int((old_area<=1e-12).sum()),
    'newDegenerateAtDoubleArea1e12':int((new_area<=1e-12).sum()),
    'introducedDegenerateCount':int(changed_degenerate.sum()),
    'rotatedOver90DegreesCount':int(reversed_faces.sum()),
    'rotatedOver90ByFaceSet':{str(int(t)):int((reversed_faces&(triangle_sets==t)).sum()) for t in np.unique(triangle_sets[reversed_faces])},
    'maximumNormalRotationDegrees':float(np.degrees(np.arccos(np.clip(cosine[valid].min(),-1,1)))),
    'lowestAreaRatio':float(np.min(new_area[valid]/old_area[valid]))}
if not np.isfinite(result).all():raise RuntimeError('Nonfinite facial-plane proposal')
if contact['rimMaximumAdjustmentMeters']>.004:raise RuntimeError('Contact proposal moves lip rim by more than the bounded4mm')
if surface_report['introducedDegenerateCount'] or surface_report['rotatedOver90DegreesCount']:raise RuntimeError('Selected facial-plane field introduces surface reversal/degeneration')
if fields['lowerNeckMaximumDeltaMeters']!=0:raise RuntimeError('Proposal changes lower neck')
report={'status':'Numerical proposal on actual saved cache; no Blender source, rendered anatomy or acceptance',
        'sourceSha256':'9b3380fd9b44eb2cff299310ae89f95d3faa4600c5653cc6ca06fba6fcf5c90e',
        'cacheSha256':hashlib.sha256(CACHE.read_bytes()).hexdigest(),'fields':fields,'contact':contact,'surface':surface_report,
        'totalMaximumDisplacementMeters':float(np.linalg.norm(result-basis,axis=1).max()),
        'authoringCode':{name:hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                         for name in ['face_planes_v5g.py','measure_v5g_planes.py']}}
np.savez_compressed(ROOT/'benchmark/local/nib-v5g-plane-proposal.npz',source=source,basis=basis,proposed=result)
(ROOT/'benchmark/art/nib/v5-study/native-v5g-plane-proposal.json').write_text(json.dumps(report,indent=2)+'\n',newline='\n')
print(json.dumps(report,indent=2))
