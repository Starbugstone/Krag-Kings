"""Independent raw FBX regression for the diagnosed body-key/forehead leak.

Geometry, mapped shading/UVs and facial morphs stay unchanged. Only named body
correctives may change, and their corrected extents must match authoring limits.
Run with bundled plain Python/NumPy, without an engine or Blender scene.
"""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
from validate_triangulated_payload import compare,geometry,data,label

def validate(source,target):
    nodes=geometry(target);mesh=next(n for n in nodes if n['props'][2]=='Mesh')
    points=data(mesh,'Vertices').reshape(-1,3)
    shapes={label(n):n for n in nodes if n['props'][2]=='Shape'}
    body={name for name in shapes if name.startswith('Corrective_')}
    if len(body)!=8:raise RuntimeError('Expected all eight authored body correctives')
    result=compare(source,target,expected_changed_morphs=body)
    checked=[]
    for name in sorted(body):
        node=shapes[name];indices=data(node,'Indexes');delta=data(node,'Vertices').reshape(-1,3)
        magnitude=np.linalg.norm(delta,axis=1)
        head=points[indices,2]>1.040
        head_max=float(magnitude[head].max()) if np.any(head) else 0.
        maximum=float(magnitude.max()) if len(magnitude) else 0.
        expected_limit=.00401 if 'HipFlex' in name else .00301
        if head_max>1e-7:raise RuntimeError(f'{name}: corrected body key still changes head by {head_max}m')
        if maximum>expected_limit:raise RuntimeError(f'{name}: {maximum}m exceeds authored {expected_limit}m bound')
        checked.append({'name':name,'maximumDeltaMeters':maximum,'authoredMagnitudeLimitMeters':expected_limit,
                        'headMask':'Basis Z > 1.040 m in confirmed source-local FBX geometry coordinates',
                        'maxHeadDeltaMeters':head_max,'nonzeroHeadVertices':int(np.sum(magnitude[head]>1e-7))})
    result['bodyCorrectiveRegression']=checked
    result['sourceSha256']=hashlib.sha256(source.read_bytes()).hexdigest()
    result['candidateSha256']=hashlib.sha256(target.read_bytes()).hexdigest()
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--source-dir',type=Path,required=True)
    parser.add_argument('--candidate-dir',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();results=[]
    for name in ['Nib_Natural','Nib_GripReplacement','Nib_LegReplacement']:
        results.append(validate(args.source_dir/(name+'.fbx'),args.candidate_dir/(name+'.fbx')))
    args.output.write_text(json.dumps({'passed':True,'variants':results},indent=2)+'\n',newline='\n')
    print('NIB_BODY_MORPH_REGRESSION_PASSED',str(args.output),flush=True)
