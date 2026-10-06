"""Lightweight route attribution on actual saved body triangles; no Blender."""
import argparse,ast,hashlib,json,os
from pathlib import Path
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
import numpy as np
p=argparse.ArgumentParser();p.add_argument('--cache',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();data=json.loads(a.cache.read_text())
points=np.asarray(data['vertices'],float);tris=np.asarray([(f[0],f[i],f[i+1]) for f in data['polygons'] for i in range(1,len(f)-1)],int);xyz=points[tris];e1=xyz[:,1]-xyz[:,0];e2=xyz[:,2]-xyz[:,0];normals=np.cross(e1,e2);normals/=np.maximum(np.linalg.norm(normals,axis=1)[:,None],1e-30)
# Reuse the exact prepared centreline interpolation, without importing bpy.
source=Path(__file__).with_name('shoulder_straps.py');tree=ast.parse(source.read_text());function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='smooth_curve');env={'np':np};exec(compile(ast.Module(body=[function],type_ignores=[]),str(source),'exec'),env);smooth=env['smooth_curve']
seed=np.asarray([(-.060,-.073,.880),(-.073,-.060,.933),(-.080,-.020,.978),(-.080,.012,.997),(-.079,.050,.950),(-.055,.067,.893),(-.017,.074,.816),(.052,.067,.729)])
directions=np.asarray([(0,-1,.10),(0,-1,.4),(0,-.65,.8),(0,0,1),(0,1,.45),(0,1,.1),(0,1,0),(0,1,0)],float);raw=smooth(seed);direction=smooth(directions);direction/=np.linalg.norm(direction,axis=1)[:,None]
rows=[];centers=[]
for i,(p,d) in enumerate(zip(raw,direction)):
 origin=p+d*.24;axis=-d;h=np.cross(np.broadcast_to(axis,e2.shape),e2);det=np.einsum('ij,ij->i',e1,h);ok=abs(det)>1e-12;inverse=np.where(ok,1/np.where(ok,det,1),0);s=origin-xyz[:,0];u=inverse*np.einsum('ij,ij->i',s,h);q=np.cross(s,e1);v=inverse*np.einsum('j,ij->i',axis,q);t=inverse*np.einsum('ij,ij->i',e2,q);ok&=(u>=0)&(v>=0)&(u+v<=1)&(t>=0)&(t<=.48);t[~ok]=np.inf;tri=int(t.argmin())
 if not np.isfinite(t[tri]):raise RuntimeError('No body support at row'+str(i))
 hit=origin+axis*t[tri];normal=normals[tri];center=hit+normal*.0115;centers.append(center);rows.append({'row':i,'triangle':tri,'skinPoint':hit.tolist(),'normal':normal.tolist(),'center':center.tolist(),'supportNormalFacing':float(normal@d)})
centers=np.asarray(centers);segments=np.diff(centers,axis=0);length=np.linalg.norm(segments,axis=1);bend=np.degrees(np.arccos(np.clip(np.einsum('ij,ij->i',segments[:-1],segments[1:])/(length[:-1]*length[1:]),-1,1)));order=np.argsort(bend)[-8:][::-1]
report={'status':'Actual body-only ray route attribution; settled-shirt support not present in this cache','source':data['source'],'sourceSha256':data['sourceSha256'],'cacheSha256':hashlib.sha256(a.cache.read_bytes()).hexdigest(),'preparedRecipeSha256':hashlib.sha256(source.read_bytes()).hexdigest(),'maximumBodyOnlyBendDegrees':float(bend.max()),'worstKinks':[{'middleRow':int(i+1),'angleDegrees':float(bend[i]),'incomingLengthMeters':float(length[i]),'outgoingLengthMeters':float(length[i+1]),'previous':rows[i],'current':rows[i+1],'next':rows[i+2]} for i in order],'allRows':rows,'sharedChanged':False,'sourceSaved':False}
a.output.write_text(json.dumps(report,indent=2)+'\n',newline='\n');print(json.dumps({'maximumBodyOnlyBendDegrees':float(bend.max()),'worstRows':[int(i+1) for i in order]}))
