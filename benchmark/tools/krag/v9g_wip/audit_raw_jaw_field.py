"""Lightweight source-domain classification audit; no Blender or pose claim."""
from pathlib import Path
import json,hashlib,numpy as np
ROOT=Path(__file__).resolve().parents[4]
geometry=ROOT/'benchmark/art/krag/anatomy-study/GEO-head_animation_realistic.npz'
attributes=ROOT/'benchmark/art/nib/v5-study/head-topology-attributes.json'
data=np.load(geometry,allow_pickle=True);raw=data['vertices'];faces=data['polygons']
info=json.loads(attributes.read_text());sets=np.asarray(next(a['values'] for a in info['attributes'] if a['name']=='.sculpt_face_set'))
assert info['object']=='GEO-head_animation_realistic' and len(sets)==len(faces)
tags=np.zeros(len(raw),dtype=np.uint64)
for face,tag in zip(faces,sets):tags[np.asarray(face,dtype=int)]|=np.uint64(1)<<np.uint64(tag)
member=lambda tag:(tags&(np.uint64(1)<<np.uint64(tag)))!=0
w=np.clip((.239-raw[:,2])/.011,0,1);w=w*w*(3-2*w)
depth=np.clip((.055-raw[:,1])/.075,0,1);depth=depth*depth*(3-2*depth);w*=depth;w[raw[:,2]<.168]=0
regions={'upperLipRim':member(33)&member(7),'lowerLipRim':member(24)&member(7),'nose':member(11),'upperFaceAndCheek':member(33),'lowerJaw':member(24),'oralBag':member(7)}
report={'status':'Raw control-cage classification of current Krag Jaw formula; not actual dense saved-weight or posed verification','sourceGeometrySha256':hashlib.sha256(geometry.read_bytes()).hexdigest(),'sourceAttributeSha256':hashlib.sha256(attributes.read_bytes()).hexdigest(),'fieldRecipe':'krag_face.face_weights: raw-Z smooth((.239-z)/.011) times depth, with neck exception z<.168','regions':{}}
for name,mask in regions.items():
 report['regions'][name]={'vertices':int(mask.sum()),'positiveJawVertices':int((w[mask]>1e-6).sum()),'maxJawWeight':float(w[mask].max()),'meanJawWeight':float(w[mask].mean()),'sourceBounds':[raw[mask].min(0).tolist(),raw[mask].max(0).tolist()]}
out=ROOT/'benchmark/art/krag/anatomy-study/jaw-source-domain-audit-v9f.json';out.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n');print(json.dumps(report['regions'],indent=2))
