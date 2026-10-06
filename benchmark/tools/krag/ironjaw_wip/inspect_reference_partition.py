"""Light read-only semantic partition of retained source cage; no Blender."""
from pathlib import Path
import json,hashlib
import numpy as np
from anatomical_exclusion import partition
ROOT=Path(__file__).resolve().parents[4]
source=ROOT/'benchmark/art/krag/anatomy-study/GEO-head_animation_realistic.npz'
attribute_source=ROOT/'benchmark/art/nib/v5-study/head-topology-attributes.json'
npz=np.load(source,allow_pickle=True);attributes=json.loads(attribute_source.read_text())
sets=next(a['values']for a in attributes['attributes']if a['name']=='.sculpt_face_set')
mask,report=partition(npz['vertices'],npz['polygons'],sets)
report['input']={'path':source.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'note':'Original control cage; not actual v9j dense mesh or generated IronJaw'}
report['attributeInput']={'path':attribute_source.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(attribute_source.read_bytes()).hexdigest()}
report['removedFaceIndices']=np.flatnonzero(mask).tolist()
( ROOT/'benchmark/art/krag/anatomy-study/ironjaw-semantic-partition-readiness.json').write_text(json.dumps(report,indent=2)+'\n',newline='\n')
print(json.dumps({k:report[k]for k in ['removedFaces','removedExternalMandibleFaces','removedOralFloorFaces','retainedUpperLipNoseFaces']}))
