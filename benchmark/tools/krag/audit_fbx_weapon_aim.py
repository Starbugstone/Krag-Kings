"""Read-only FBX marker/curve evaluation for the Blender-exported rig contract.

No editor is launched. Supports XYZ bone rotations with zero transform pivots;
rejects unsupported transforms rather than guessing their interpretation.
"""
import argparse,json,hashlib,math,struct,zlib
from pathlib import Path
import numpy as np
TICKS=46186158000

def read(path):
 with Path(path).open('rb') as stream:
  header=stream.read(27);assert header.startswith(b'Kaydara FBX Binary')
  version=struct.unpack_from('<I',header,23)[0];size,fmt=(25,'<QQQB') if version>=7500 else (13,'<IIIB')
  def prop():
   kind=stream.read(1);scalar={b'Y':'<h',b'C':'<?',b'I':'<i',b'F':'<f',b'D':'<d',b'L':'<q'}
   if kind in scalar:
    form=scalar[kind];return struct.unpack(form,stream.read(struct.calcsize(form)))[0]
   if kind in (b'S',b'R'):
    raw=stream.read(struct.unpack('<I',stream.read(4))[0]);return raw.decode('utf8','replace') if kind==b'S' else raw
   types={b'f':'<f4',b'd':'<f8',b'i':'<i4',b'l':'<i8',b'b':'u1',b'c':'u1'}
   count,encoding,length=struct.unpack('<III',stream.read(12));raw=stream.read(length)
   if encoding:raw=zlib.decompress(raw)
   values=np.frombuffer(raw,dtype=types[kind]);assert len(values)==count;return values
  def node(parent=''):
   raw=stream.read(size)
   if len(raw)<size:return
   end,count,_,length=struct.unpack(fmt,raw)
   if not end:return
   name=stream.read(length).decode()
   if (not parent and name not in ('Objects','Connections')) or (parent=='Objects' and name not in ('Model','AnimationStack','AnimationLayer','AnimationCurveNode','AnimationCurve')):
    stream.seek(end);return
   values=[prop() for _ in range(count)];children=[]
   while stream.tell()<end-size:
    child=node(name)
    if child:children.append(child)
   stream.seek(end);return {'name':name,'props':values,'children':children}
  roots=[]
  while stream.tell()<Path(path).stat().st_size-size:
   before=stream.tell();item=node()
   if item:roots.append(item)
   if stream.tell()==before+size:break
 objects=next(n['children'] for n in roots if n['name']=='Objects')
 edges=[n['props'] for n in next(n['children'] for n in roots if n['name']=='Connections') if n['name']=='C']
 return {n['props'][0]:n for n in objects},edges

def label(node):return node['props'][1].split('\0')[0]
def children(node,name):return [n for n in node['children'] if n['name']==name]
def properties(node):
 groups=children(node,'Properties70')
 return {n['props'][0]:n['props'][4:] for n in groups[0]['children'] if n['name']=='P'} if groups else {}
def euler(degrees):
 x,y,z=np.radians(degrees);cx,sx=np.cos(x),np.sin(x);cy,sy=np.cos(y),np.sin(y);cz,sz=np.cos(z),np.sin(z)
 return np.array([[cz,-sz,0],[sz,cz,0],[0,0,1]])@np.array([[cy,0,sy],[0,1,0],[-sy,0,cy]])@np.array([[1,0,0],[0,cx,-sx],[0,sx,cx]])

def audit(path):
 objects,edges=read(path);models={i:o for i,o in objects.items() if o['name']=='Model'};names={label(o):i for i,o in models.items()}
 stacks=[i for i,o in objects.items() if o['name']=='AnimationStack' and label(o).endswith('Shoot')]
 if len(stacks)!=1:raise ValueError('Expected one Shoot stack')
 layers={e[1] for e in edges if e[2]==stacks[0] and objects.get(e[1],{}).get('name')=='AnimationLayer'}
 nodes={e[1] for e in edges if e[2] in layers and objects.get(e[1],{}).get('name')=='AnimationCurveNode'}
 channels={}
 for edge in edges:
  if edge[0]!='OP' or edge[1] not in nodes or edge[2] not in models:continue
  model,channel=edge[2],edge[3]
  for row in edges:
   if row[0]!='OP' or row[2]!=edge[1] or objects.get(row[1],{}).get('name')!='AnimationCurve':continue
   curve=objects[row[1]];times=children(curve,'KeyTime')[0]['props'][0]/TICKS;values=children(curve,'KeyValueFloat')[0]['props'][0]
   channels[(model,channel,row[3][-1])]=(times,values)
 parents={e[1]:e[2] for e in edges if e[0]=='OO' and e[1] in models and e[2] in models}
 props={i:properties(o) for i,o in models.items()}
 def matrix(model,time,cache):
  if model in cache:return cache[model]
  p=props[model]
  if p.get('RotationOrder',[0])[0]!=0:raise ValueError('Unsupported rotation order '+label(models[model]))
  for key in ('RotationPivot','RotationOffset','ScalingPivot','ScalingOffset'):
   if np.linalg.norm(p.get(key,[0,0,0]))>1e-9:raise ValueError('Nonzero FBX pivot '+key)
  vectors={}
  for key,default in [('Lcl Translation',[0,0,0]),('Lcl Rotation',[0,0,0]),('Lcl Scaling',[1,1,1])]:
   value=np.asarray(p.get(key,default),dtype=float)
   for j,axis in enumerate('XYZ'):
    curve=channels.get((model,key,axis))
    if curve is not None:value[j]=np.interp(time,*curve)
   vectors[key]=value
  m=np.eye(4);m[:3,:3]=euler(p.get('PreRotation',[0,0,0]))@euler(vectors['Lcl Rotation'])@euler(p.get('PostRotation',[0,0,0])).T@np.diag(vectors['Lcl Scaling']);m[:3,3]=vectors['Lcl Translation']
  if model in parents:m=matrix(parents[model],time,cache)@m
  cache[model]=m;return m
 samples=[]
 start=min(float(curve[0][0]) for curve in channels.values());end=max(float(curve[0][-1]) for curve in channels.values())
 for frame in [1,13,18,19,31]:
  normalized=(frame-1)/30;t=start+normalized*(end-start);cache={};rig=matrix(names['Krag_Rig'],t,cache);inverse=np.linalg.inv(rig)
  muzzle=(inverse@matrix(names['WeaponMuzzle'],t,cache))[:3,3];aim=(inverse@matrix(names['WeaponAim'],t,cache))[:3,3]
  forward=aim-muzzle;forward/=np.linalg.norm(forward)
  samples.append({'frame':frame,'normalizedTime':normalized,'fileTimeSeconds':t,'muzzleInRigSpace':muzzle.tolist(),'forwardInRigSpace':forward.tolist(),'dotCharacterForward':float(-forward[1]),'angleFromCharacterForwardDegrees':float(np.degrees(np.arccos(np.clip(-forward[1],-1,1))))})
 return {'file':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'clipStartFileSeconds':start,'clipEndFileSeconds':end,'method':'XYZ FBX PreRotation * animated LocalRotation * inverse PostRotation; pivot-free hierarchy; marker positions expressed in exported armature space','status':'Raw exported marker/curve measurement; actual editor roundtrip and visual pose remain separate checks','samples':samples}

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('file',type=Path);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();result=audit(args.file);args.output.write_text(json.dumps(result,indent=2)+'\n',newline='\n');print(json.dumps(result,indent=2))
