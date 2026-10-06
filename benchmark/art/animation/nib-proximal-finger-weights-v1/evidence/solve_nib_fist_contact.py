"""Read-only NumPy hand-space skin evaluation against actual native audit."""
import json,math,ast,sys
from pathlib import Path
import numpy as np
root=Path(r'D:\Dev\Krag-Kings\benchmark');sys.path.insert(0,str(root/'tools/animation'));import hand_skin_domains as domains
r=json.loads((root/'local/nib-fist-v3-native-audit.json').read_text());native=np.asarray(r['actualSkinInRestHandFrame']);points=np.asarray(r['restSkin']);bones=json.loads((root/'local/nib-actual-hand-fit-v2.json').read_text())['bones'];axis=np.asarray(r['axis']);axis/=np.linalg.norm(axis)
module=ast.parse((root/'tools/nib/v5_wip/nib_hand_v5.py').read_text());chains=next(ast.literal_eval(n.value) for n in module.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SOURCE_CHAINS' for t in n.targets))
def rot(axis,angle):
 axis=axis/np.linalg.norm(axis);x,y,z=axis;C=np.array([[0,-z,y],[z,0,-x],[-y,x,0]]);return np.eye(3)+math.sin(angle)*C+(1-math.cos(angle))*(C@C)
def frames(angles,thumb=(18,25),opposition=32):
 transforms={'Hand_L':(np.eye(3),np.zeros(3))};ends={}
 for digit,values in angles.items():
  first=bones[digit+'1_L'];reference=np.asarray(first['tail'])-first['head'];reference-=axis*reference.dot(axis);reference/=np.linalg.norm(reference);total=0;posed_head=np.asarray(first['head']);previous=None
  for i,angle in enumerate(values,1):
   bone=bones[digit+str(i)+'_L'];head=np.asarray(bone['head']);tail=np.asarray(bone['tail']);direction=tail-head;direction-=axis*direction.dot(axis);direction/=np.linalg.norm(direction);bind=math.atan2(axis@np.cross(reference,direction),reference@direction);total+=angle;R=rot(axis,math.radians(total)-bind)
   if previous is not None:
    prevbone,prevR,prevposed=previous;posed_head=prevposed+prevR@(head-prevbone)
   transforms[digit+str(i)+'_L']=(R,posed_head-R@head);previous=(head,R,posed_head);ends[digit+str(i)+'_L']=(posed_head,posed_head+R@(tail-head))
 total=0;previous=None
 for i,angle in enumerate(thumb,1):
  name='Thumb'+str(i)+'_L';head=np.asarray(bones[name]['head']);tail=np.asarray(bones[name]['tail']);total+=angle;R=rot(axis,math.radians(total))@rot(np.array([0,-1,0]),math.radians(opposition));posed_head=head if previous is None else previous[2]+previous[1]@(head-previous[0]);transforms[name]=(R,posed_head-R@head);previous=(head,R,posed_head);ends[name]=(posed_head,posed_head+R@(tail-head))
 return transforms,ends
def evaluate(weights,angles):
 transform,ends=frames(angles);result=np.zeros_like(points)
 for name in transform:
  ids=[];values=[]
  for i,row in enumerate(weights):
   value=row.get(name,0)
   if value>1e-9:ids.append(i);values.append(value)
  ids=np.asarray(ids,int);v=np.asarray(values);R,t=transform[name];result[ids]+=(points[ids]@R.T+t)*v[:,None]
 return result,ends
old=[dict(v) for v in r['weights']];angles={n:(82,98,55) for n in domains.DIGITS if n!='Thumb'}
actual,ends=evaluate(old,angles);error=np.linalg.norm(actual-native,axis=1);print('LBS vs native max mm',error.max()*1000,'mean',error.mean()*1000)
raw=np.column_stack([.008+(.227-points[:,0])/.43,(-.043-points[:,1])/.43,(points[:,2]-.610)/.43]);field,fr=domains.solve(raw,r['polygons'],True,chains);names,wt,wr=domains.weights(raw,field,chains,joint_half_width=.008);weights=[{names[j]:float(v) for j,v in enumerate(row) if v>1e-8} for row in wt]
palm_mask=(wt[:,0]>.95)&(points[:,2]<.603)&(points[:,1]<-.047);palm=points[palm_mask];print('palmar skin samples',len(palm))
# Closest surface on the fingertip cap to fixed palmar samples. These are
# unsigned distances and do not establish collision-free contact.
rows={}
for finger in angles:
 tail=np.asarray(bones[finger+'3_L']['tail']);own=wt[:,names.index(finger+'3_L')]>.8;cap=own&(np.linalg.norm(points-tail,axis=1)<.007)
 print(finger,'tip cap',cap.sum())
 results=[]
 for dip in [40,55,65,75,85,90]:
  spec=angles.copy();spec[finger]=(82,98,dip);posed,_=evaluate(weights,spec);d=np.linalg.norm(posed[cap,None,:]-palm[None,:,:],axis=2);results.append({'DIP':dip,'minimumDistanceMm':float(d.min()*1000),'meanClosestMm':float(d.min(axis=1).mean()*1000)})
 rows[finger]=results
print(json.dumps(rows,indent=2));(root/'local/nib-fist-contact-preflight.json').write_text(json.dumps({'nativeSkinMaxErrorMeters':float(error.max()),'palmSampleCount':len(palm),'unsignedTipDistances':rows,'status':'Numerical diagnostic only; not source mutation or collision proof'},indent=2)+'\n')
