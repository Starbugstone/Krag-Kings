"""Lightweight left-hand control study, not an extracted native posed mesh.

Uses the preserved left FINGER_CHAINS from create_nib.py; v5 hand fitting only
changed right joint ordering. Root owns retarget changes and actual pose proof.
"""
import hashlib,json,math,os,sys
from pathlib import Path
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
import numpy as np

ROOT=Path(__file__).resolve().parents[4]
SOURCE=ROOT/'benchmark/art/animation/nib-human-motion-v5/Nib_HumanMotion_Study_v5.blend'
EXPECTED='b82786d632424fd93b798b1a347aab29e568585ee700ce57b0ab435ee76a10da'
def rotate(axis,angle,vector):
    axis=axis/np.linalg.norm(axis);a=math.radians(angle)
    return vector*math.cos(a)+np.cross(axis,vector)*math.sin(a)+axis*(axis@vector)*(1-math.cos(a))
rows=[]
for j,(name,angles) in enumerate([('Index',[18,28,12]),('Middle',[22,32,15]),('Ring',[24,35,16]),('Little',[26,38,18])]):
    fx=.227+(j-1.5)*.012;zz=.563-(.008 if j in [0,3] else 0)
    p=np.asarray([(fx,-.046,zz+.01),(fx+.004,-.049,zz-.011),(fx+.003,-.060,zz-.028),(fx,-.070,zz-.032)])
    row={'digit':name,'restChainMeters':p.tolist(),'runControlAnglesDegrees':[a*1.3 for a in angles],'variants':{}}
    for label in ['existingSegmentAxes','commonKnucklePlane']:
        q=p[0].copy();total=0.
        for segment,angle in enumerate(angles):
            direction=p[segment+1]-p[segment]
            axis=np.cross(direction,[0,-1,0]) if label=='existingSegmentAxes' else np.asarray([-1.,0,0])
            total+=angle*1.3;q+=rotate(axis,total,direction)
        row['variants'][label]={'tipMinusMcpMeters':(q-p[0]).tolist(),'tipMeters':q.tolist()}
    rows.append(row)
report={'status':'Analytical control reconstruction from preserved rest-chain source, not actual saved-mesh pose validation',
    'inspectedNativeSource':str(SOURCE),'expectedNativeSourceSha256':EXPECTED,
    'actualImagesInspected':['benchmark/local/animation/nib-human-motion-v5-review/Run/side/0000.png','benchmark/local/animation/nib-human-motion-v5-review/Run/front/0000.png'],
    'rows':rows,'finding':'Per-segment axes change with authored lateral rest offsets, adding8.6–10.1mm unintended lateral drift; common knuckle-row plane removes it analytically.',
    'proposedNextPoseAnglesDegrees':{'Index':[40,55,20],'Middle':[40,50,20]},
    'proposalStatus':'Unvalidated starting pose; Ring/Little need smaller changes and thumb requires separate restrained opposition. Check actual contact before acceptance.',
    'sharedChanged':False,'rootMotionScriptChanged':False,
    'codeSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
output=ROOT/'benchmark/art/nib/motion-study/free-hand-control-study-v5.json'
output.write_text(json.dumps(report,indent=2)+'\n',newline='\n')
print(json.dumps({'output':str(output),'digits':len(rows)}))
