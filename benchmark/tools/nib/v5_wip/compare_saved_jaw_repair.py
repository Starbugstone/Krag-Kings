"""Compare two actual saved-mesh audits; no Blender or asset mutation."""
import hashlib,json
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[4]
ART=ROOT/'benchmark/art/nib/v5-study'
paths={name:ROOT/('benchmark/local/nib-'+name+'-mouth-audit.npz') for name in ['v5e','v5f']}
old=np.load(paths['v5e'],allow_pickle=True);new=np.load(paths['v5f'],allow_pickle=True)
for field in ['source','local','edges','face_sets','face_materials']:
    if not np.array_equal(old[field],new[field]):raise RuntimeError('Repair changed audited '+field)
if not np.array_equal(old['neutral'],new['neutral']):raise RuntimeError('Neutral evaluated surface changed')
edges=old['edges'];source=old['source'];faces=old['faces'];tags=old['face_sets']
upper=np.zeros(len(source),dtype=bool);nose=upper.copy()
for face,tag in zip(faces,tags):
    if tag==33:upper[np.asarray(face,dtype=int)]=True
    if tag==11:nose[np.asarray(face,dtype=int)]=True
length=np.linalg.norm(old['neutral'][edges[:,0]]-old['neutral'][edges[:,1]],axis=1)
mouth=(abs(source[:,0])<.060)&(source[:,1]<-.08)&(source[:,2]>.20)&(source[:,2]<.282)
selected=mouth[edges].all(1)
old_lengths=np.linalg.norm(old['jawOnly'][edges[:,0]]-old['jawOnly'][edges[:,1]],axis=1)
old_ratio=old_lengths/np.maximum(length,1e-12)
old_worst=int(np.flatnonzero(selected)[np.argmax(old_ratio[selected])])
report={'status':'Actual saved source audit comparison; Tongue aperture improvement also separately inspected in native renders; overall art remains unaccepted',
        'sources':{name:json.loads((ART/('native-'+name+'-mouth-audit.json')).read_text())['sourceSha256'] for name in paths},
        'cacheSha256':{name:hashlib.sha256(path.read_bytes()).hexdigest() for name,path in paths.items()},
        'basisTopologyAndNeutralPositionsIdentical':True,'semanticDomains':{},'originalCurtainEdge':{},'repairedWorstRelativeEdge':{},
        'codeSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
for name,mask in [('upperLipCheekSet33',upper),('nasalSet11',nose)]:
    report['semanticDomains'][name]={}
    for label,data in [('v5e',old),('v5f',new)]:
        report['semanticDomains'][name][label]={'vertices':int(mask.sum()),'maximumJawWeight':float(data['jaw_weights'][mask].max()),
            'maximumJawOnlyDisplacementMeters':float(np.linalg.norm(data['jawOnly'][mask]-data['neutral'][mask],axis=1).max())}
    if np.any(new['jaw_weights'][mask]!=0):raise RuntimeError('Repaired upper-face domain still weighted to Jaw')
for label,data in [('v5e',old),('v5f',new)]:
    a,b=edges[old_worst];posed=float(np.linalg.norm(data['jawOnly'][a]-data['jawOnly'][b]))
    report['originalCurtainEdge'][label]={'edge':old_worst,'vertices':[int(a),int(b)],'restLengthMeters':float(length[old_worst]),
        'posedLengthMeters':posed,'stretchRatio':posed/length[old_worst],
        'jawWeights':[float(data['jaw_weights'][a]),float(data['jaw_weights'][b])]}
new_lengths=np.linalg.norm(new['jawOnly'][edges[:,0]]-new['jawOnly'][edges[:,1]],axis=1)
new_ratio=new_lengths/np.maximum(length,1e-12)
worst=int(np.flatnonzero(selected)[np.argmax(new_ratio[selected])]);a,b=edges[worst]
report['repairedWorstRelativeEdge']={'edge':worst,'vertices':[int(a),int(b)],'restLengthMeters':float(length[worst]),
    'posedLengthMeters':float(new_lengths[worst]),'stretchRatio':float(new_ratio[worst]),
    'note':'A very short commissure edge, not the previous large upper-mouth curtain. Actual corner shape still needs refinement.'}
(ART/'native-v5f-jaw-comparison.json').write_text(json.dumps(report,indent=2)+'\n',newline='\n')
print(json.dumps(report,indent=2))
