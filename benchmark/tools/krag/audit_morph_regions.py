"""Read actual FBX sparse morph extents without loading an editor or changing it."""
from pathlib import Path
import argparse, hashlib, json, sys
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'benchmark/tools/nib/v5_wip'))
from validate_triangulated_payload import geometry, data, label

def inspect(path):
    nodes=geometry(path)
    meshes=[n for n in nodes if n['props'][2]=='Mesh']
    if len(meshes)!=1:raise ValueError('Expected one assembled mesh')
    points=data(meshes[0],'Vertices').reshape(-1,3)
    shapes=[]
    for node in nodes:
        if node['props'][2]!='Shape':continue
        ids=data(node,'Indexes');delta=data(node,'Vertices').reshape(-1,3)
        if len(ids)!=len(delta) or np.any(ids<0) or np.any(ids>=len(points)):
            raise ValueError('Invalid sparse morph indexing: '+label(node))
        if not np.isfinite(delta).all():raise ValueError('Non-finite morph: '+label(node))
        length=np.linalg.norm(delta,axis=1)
        significant=length>1e-6
        affected=points[ids[significant]]
        worst=int(np.argmax(length)) if len(length) else None
        above=points[ids,2]>1.9
        shapes.append({'name':label(node),'sparseVertices':len(ids),
            'verticesAboveOneMicrometre':int(significant.sum()),
            'maximumDeltaMeters':float(length.max()) if len(length) else 0,
            'affectedRestBoundsMeters':{'minimum':affected.min(0).tolist(),'maximum':affected.max(0).tolist()} if len(affected) else None,
            'maximumDeltaAbove1_9Meters':float(length[above].max()) if above.any() else 0,
            'worstVertex':int(ids[worst]) if worst is not None else None,
            'worstRestPositionMeters':points[ids[worst]].tolist() if worst is not None else None,
            'worstDeltaMeters':delta[worst].tolist() if worst is not None else None})
    return {'file':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'scope':'Actual sparse FBX morph deltas and their neutral positions; no engine pose or artistic acceptance claim',
        'vertices':len(points),'shapes':shapes}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('files',nargs='+',type=Path);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    results=[inspect(p) for p in args.files]
    args.output.write_text(json.dumps(results,indent=2)+'\n',newline='\n')
    for result in results:
        print(result['file'])
        for shape in result['shapes']:
            if 'Corrective_' in shape['name']:
                print(shape['name'],'max',shape['maximumDeltaMeters'],'above1.9',shape['maximumDeltaAbove1_9Meters'])
