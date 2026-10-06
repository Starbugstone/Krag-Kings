"""Lightweight diagnostic of the frozen v5e Jaw field on original cage points.

This does not evaluate Blender, subdivision, modifiers or a saved pose. It
records the inherited coordinate-field defect separately from the actual
failed Tongue render. No source asset is changed.
"""
import hashlib, json
from pathlib import Path
import numpy as np
from fit_head_v5e import fit_head, oral_translation

ROOT=Path(__file__).resolve().parents[4]
SOURCE=ROOT/'benchmark/art/krag/anatomy-study/GEO-head_animation_realistic.npz'
OUTPUT=ROOT/'benchmark/art/nib/v5-study/native-v5e-raw-jaw-field.json'

def smooth(a,b,x):
    t=np.clip((x-a)/(b-a),0,1)
    return t*t*(3-2*t)

def frozen_jaw(points):
    x,y,z=points.T
    shift=oral_translation()
    oldz=z-shift[2];oldy=y-shift[1]
    result=(1-smooth(1.104,1.135,oldz))*np.clip((-oldy+.004)/.043,0,1)
    special=(abs(x)<.05)&(oldy<-.05)&(oldz>1.102)&(oldz<1.119)
    seam=1.110+.0015*(x/.045)**3
    result[special]=1-smooth(seam[special]-.0012,seam[special]+.0012,oldz[special])
    return result,special

archive=np.load(SOURCE,allow_pickle=True)
source=archive['vertices'].astype(np.float64)
faces=[list(map(int,face)) for face in archive['polygons']]
fitted=fit_head(source)
weights,special=frozen_jaw(fitted)
x,y,z=source.T
# Coordinate regions are explicit diagnostic probes, not semantic topology IDs.
regions={
    'nasalTip':(abs(x)<.026)&(y<-.14)&(z>.259)&(z<.282),
    'philtrumUpperMuzzle':(abs(x)<.035)&(y<-.11)&(z>.242)&(z<=.259),
    'upperLipProbe':(abs(x)<.037)&(y<-.117)&(z>.234)&(z<=.242),
    'lowerLipProbe':(abs(x)<.037)&(y<-.117)&(z>.223)&(z<=.234),
    'chinProbe':(abs(x)<.037)&(y<-.08)&(z>.18)&(z<=.215),
}
report={'status':'Raw source-cage field diagnostic only; saved evaluated mouth topology and pose still require the prepared Blender audit',
        'referenceSha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        'codeSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'oralTranslationMeters':oral_translation().tolist(),
        'coordinateConvention':'Fitted mesh-local metres, before common HEAD_DROP; reproduces frozen v5e authoring field',
        'regions':{},'largestMouthWeightEdges':[]}
for name,mask in regions.items():
    ids=np.flatnonzero(mask)
    report['regions'][name]={'vertices':len(ids),'weightMin':float(weights[ids].min()) if len(ids) else None,
        'weightMax':float(weights[ids].max()) if len(ids) else None,
        'weightMean':float(weights[ids].mean()) if len(ids) else None,
        'samples':[{'vertex':int(i),'source':source[i].tolist(),'fitted':fitted[i].tolist(),
                    'jawWeight':float(weights[i]),'specialBranch':bool(special[i])} for i in ids]}
edges=set()
for face in faces:
    for a,b in zip(face,face[1:]+face[:1]):edges.add(tuple(sorted((a,b))))
mouth=(abs(x)<.060)&(y<-.08)&(z>.205)&(z<.270)
ranked=[]
for a,b in edges:
    if not(mouth[a] and mouth[b]):continue
    length=float(np.linalg.norm(fitted[a]-fitted[b]))
    delta=float(abs(weights[a]-weights[b]))
    ranked.append((delta/max(length,1e-12),delta,length,a,b))
for gradient,delta,length,a,b in sorted(ranked,reverse=True)[:24]:
    report['largestMouthWeightEdges'].append({'vertices':[a,b],'lengthMeters':length,
        'weightDifference':delta,'weightGradientPerMeter':gradient,
        'source':[source[a].tolist(),source[b].tolist()],
        'jawWeights':[float(weights[a]),float(weights[b])],
        'differentFieldBranches':bool(special[a]!=special[b])})
OUTPUT.write_text(json.dumps(report,indent=2)+'\n',newline='\n')
print(json.dumps({name:{k:v for k,v in row.items() if k!='samples'} for name,row in report['regions'].items()},indent=2))
