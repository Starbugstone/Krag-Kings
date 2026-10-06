"""Read-only diagnostic wrapper around the frozen failed v9k generation.

Expected to exit2 at its unchanged 30mm gate; records exact target/correction
coordinates without saving a blend or changing the limit.
"""
from pathlib import Path
import runpy,json,hashlib,sys
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
source=HERE/'build_mouth_pose_fit.py'
try:runpy.run_path(str(source),run_name='__main__')
except RuntimeError as exception:
    frame=exception.__traceback__
    state=None
    while frame:
        if Path(frame.tb_frame.f_code.co_filename)==source:state=frame.tb_frame.f_globals
        frame=frame.tb_next
    if state is None or 'local'not in state:raise
    magnitude=np.linalg.norm(state['local'],axis=1);worst=np.argsort(magnitude)[-12:][::-1]
    out=ROOT/'benchmark/art/krag/anatomy-study/mouth-pose-fit-v9k-failure.json'
    d={'status':'Actual failed canonical fit; no saved source or render','failure':str(exception),'recipeSha256':hashlib.sha256(source.read_bytes()).hexdigest(),
       'maxStoredCorrectionMeters':float(magnitude.max()),'maximumSkinConditionNumber':float(np.linalg.cond(state['skin']).max()),
       'jawOpenWeight':state['weight'],'depthMeters':state['depth'],'targetBottomZ':state['target_bottom'],'evaluatedLowerIncisorTipCenter':state['tip_center'].tolist(),
       'evaluatedLowerToothFrontY':state['tooth_front'],'corners':[state['posed'][state['left']].tolist(),state['posed'][state['right']].tolist()],
       'worst':[{'vertex':int(i),'source':state['raw'][i].tolist(),'current':state['posed'][i].tolist(),'target':state['target'][i].tolist(),'propagatedDelta':state['value'][i].tolist(),'storedDelta':state['local'][i].tolist(),'lowerRim':bool(state['lr'][i])}for i in worst]}
    out.write_text(json.dumps(d,indent=2)+'\n',newline='\n')
    np.savez_compressed(out.with_suffix('.npz'),raw=state['raw'],posed=state['posed'],target=state['target'],rim=state['lr'],value=state['value'],local=state['local'])
    print(json.dumps({k:d[k]for k in ['failure','maxStoredCorrectionMeters','maximumSkinConditionNumber','depthMeters','targetBottomZ','evaluatedLowerIncisorTipCenter','corners']},indent=2),flush=True)
    raise
