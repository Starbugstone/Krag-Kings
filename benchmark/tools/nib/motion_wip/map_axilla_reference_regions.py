"""Map actual saved Nib mismatch points to the licensed unwarped body surface."""
from pathlib import Path
import json,hashlib,collections
import numpy as np
ROOT=Path(__file__).resolve().parents[4];cache=ROOT/'benchmark/local/nib-axilla-actual-shoot-v2.npz';data=np.load(cache,allow_pickle=True)
points=data['reference_points'];faces=data['reference_faces'];sets=data['reference_face_sets'];tri=[];owners=[]
for i,face in enumerate(faces):
 if points[np.asarray(face,int),2].max()<1.05 or points[np.asarray(face,int),2].min()>1.43:continue
 for j in range(1,len(face)-1):tri.append((face[0],face[j],face[j+1]));owners.append(i)
tri=np.asarray(tri,int);owners=np.asarray(owners,int);xyz=points[tri];a,b,c=xyz[:,0],xyz[:,1],xyz[:,2];cross=np.cross(b-a,c-a);valid=np.linalg.norm(cross,axis=1)>1e-12;xyz=xyz[valid];owners=owners[valid];a,b,c=xyz[:,0],xyz[:,1],xyz[:,2];cross=np.cross(b-a,c-a);normal=cross/np.linalg.norm(cross,axis=1)[:,None];v0=b-a;v1=c-a;d00=np.sum(v0*v0,1);d01=np.sum(v0*v1,1);d11=np.sum(v1*v1,1);den=d00*d11-d01*d01

def nearest(p):
 hit=p-np.sum((p-a)*normal,1)[:,None]*normal;v2=hit-a;d20=np.sum(v2*v0,1);d21=np.sum(v2*v1,1);u=(d11*d20-d01*d21)/den;v=(d00*d21-d01*d20)/den;dist=np.sum((hit-p)**2,1);dist[(u<0)|(v<0)|(u+v>1)]=np.inf
 for x,y in [(a,b),(b,c),(c,a)]:
  delta=y-x;t=np.clip(np.sum((p-x)*delta,1)/np.sum(delta*delta,1),0,1);h=x+t[:,None]*delta;d=np.sum((h-p)**2,1);m=d<dist;dist[m]=d[m]
 i=int(np.argmin(dist));return int(owners[i]),float(np.sqrt(dist[i]))
rows=[]
for i in data['candidate_ids']:
 face,distance=nearest(data['source_points'][i]);rows.append({'vertex':int(i),'referenceFace':face,'referenceFaceSet':int(sets[face]),'sourceSurfaceDistanceMeters':distance,'sourcePosition':data['source_points'][i].tolist()})
report={'status':'Actual source-coordinate correspondence to original semantic surface; set meaning inferred from complete source bounds and connectivity','sourceCacheSha256':hashlib.sha256(cache.read_bytes()).hexdigest(),'points':len(rows),'referenceFaceSetCounts':dict(collections.Counter(r['referenceFaceSet'] for r in rows)),'sourceSurfaceDistanceMaxMeters':max(r['sourceSurfaceDistanceMeters'] for r in rows),'sourceSurfaceDistanceMedianMeters':float(np.median([r['sourceSurfaceDistanceMeters'] for r in rows])),'proposedSemantics':{'1':'thorax','20':'right upper arm/deltoid','21':'left upper arm/deltoid','11':'right forearm','12':'left forearm'},'rows':rows,'codeSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'sourceChanged':False,'sharedChanged':False}
p=ROOT/'benchmark/art/nib/motion-study/axilla-reference-region-mapping-v2.json';p.write_text(json.dumps(report,indent=2)+'\n',newline='\n')
face_path=ROOT/'benchmark/art/nib/motion-study/body-reference-face-sets.json';face_path.write_text(json.dumps({'source':'Blender Studio Human Base Meshes1.4.1 / GEO-body_male_realistic','librarySha256':'3c121505651140ceb4d69fd1d8923f7788ffadd81672f5be14845a5f2c75c137','vertexCount':len(points),'faces':len(faces),'faceSetIds':sets.tolist(),'referenceCacheSha256':hashlib.sha256((ROOT/'benchmark/art/krag/anatomy-study/GEO-body_male_realistic.npz').read_bytes()).hexdigest(),'proposedSemantics':report['proposedSemantics']},indent=2)+'\n',newline='\n')
print(json.dumps({k:v for k,v in report.items() if k!='rows'},indent=2))
