"""Read-only original-cage semantic seed audit; not posed-source proof."""
from pathlib import Path
import json,hashlib
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
original=ROOT/'benchmark/art/krag/anatomy-study/GEO-body_male_realistic.npz'
semantic=ROOT/'benchmark/local/nib-axilla-actual-shoot-v2.npz'
a=np.load(original,allow_pickle=True);b=np.load(semantic,allow_pickle=True)
p=np.asarray(a['vertices']);q=np.asarray(b['reference_points'])
if p.shape!=q.shape or not np.array_equal(p,q):raise RuntimeError('Sibling audited reference is not the exact preserved original cage')
faces=b['reference_faces'];sets=b['reference_face_sets'];upper=np.zeros(len(p),bool);thorax=np.zeros(len(p),bool)
for face,tag in zip(faces,sets):
    if tag in [20,21]:upper[np.asarray(face,dtype=int)]=True
    if tag==1:thorax[np.asarray(face,dtype=int)]=True
x=np.abs(p[:,0]);z=p[:,2]
keep=(z<1.445)&((z>.945)|((x>.240)&(z>.70)))
torso=(x<.115)|((z<1.245)&(x<.207))|((z>1.445)&(x<.145))
cutoff=.145+.035*np.clip((z-1.20)/.15,0,1);fit=np.clip((x-cutoff)/.065,0,1);fit=fit*fit*(3-2*fit)
wrong=keep&upper&~thorax&torso&(fit>.5);ids=np.flatnonzero(wrong)
report={'status':'Read-only exact original-cage semantic audit; no saved Krag pose/deformation claim','originalCageSha256':hashlib.sha256(original.read_bytes()).hexdigest(),'auditedSemanticCacheSha256':hashlib.sha256(semantic.read_bytes()).hexdigest(),'referenceVerticesExact':True,
 'criterion':'Retained vertices belonging to upper-arm sets20/21 and not thorax1, hard-pinned as torso by current seed formula, but moved mostly by arm branch of current Krag geometry warp',
 'mismatchedOriginalCageVertices':len(ids),'geometryArmBlendRange':([float(fit[ids].min()),float(fit[ids].max())]if len(ids)else[]),
 'sample':[{'sourceVertex':int(i),'originalPosition':p[i].tolist(),'geometryArmBlend':float(fit[i]),'skinDomainTorsoSeed':True}for i in ids[:24]],
 'next':'Inspect these actual Krag posed vertices and use one semantic shoulder-interface field for both source fitting and skinning if confirmed. Do not copy a species-specific Nib warp or modify source without actual review.'}
(ROOT/'benchmark/art/krag/anatomy-study/original-arm-seed-semantic-audit.json').write_text(json.dumps(report,indent=2)+'\n',newline='\n')
print(json.dumps({'mismatchedOriginalCageVertices':len(ids),'geometryArmBlendRange':report['geometryArmBlendRange']},indent=2))
