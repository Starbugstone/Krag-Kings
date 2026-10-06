"""Small numerical regression for hard-edge corner provenance; no Blender job."""
import argparse
import json
from pathlib import Path
import numpy as np
from triangle_corner_contract import validate


def run():
    # Two quads share vertices 1/2 but have different UVs, materials and normals.
    # Collapsing their normals by vertex would erase this intended hard edge.
    source=np.array([0,1,2,-4, 1,4,5,-3])
    mapping=np.array([0,1,2,0,2,3, 4,5,6,4,6,7])
    vertices=np.where(source<0,-source-1,source)
    target=vertices[mapping].copy();target[2::3]=-target[2::3]-1
    uv=np.array([[0,0],[1,0],[1,1],[0,1],[.2,.1],[.8,.1],[.8,.9],[.2,.9]])
    materials=np.repeat([0,1],4)
    normals=np.repeat([[0.,0.,1.],[1.,0.,0.]],4,axis=0)
    base=dict(source_uv=uv,target_uv=uv[mapping].copy(),source_material=materials,target_material=materials[mapping].copy())
    proof=validate(source,target,mapping,**base)
    expected_normals=normals[mapping]
    shared=np.flatnonzero(vertices[mapping]==1)
    assert len(np.unique(expected_normals[shared],axis=0))==2
    results=[{'case':'two-quads-hard-edge-uv-seam','passed':True,**proof}]
    def reject(name,raw=target,corners=mapping,**overrides):
        try:validate(source,raw,corners,**{**base,**overrides})
        except ValueError as exc:results.append({'case':name,'passed':True,'rejected':str(exc)});return
        raise AssertionError('Corrupt contract was accepted: '+name)
    reversed_map=mapping.copy();reversed_map[[0,1]]=reversed_map[[1,0]]
    reversed_raw=vertices[reversed_map].copy();reversed_raw[2::3]=-reversed_raw[2::3]-1
    reject('changed-winding',reversed_raw,reversed_map,target_uv=uv[reversed_map],target_material=materials[reversed_map])
    crossed=mapping.copy();crossed[1]=4 # Same vertex, different source face.
    reject('cross-face-corner-alias',corners=crossed)
    wrong=mapping.copy();wrong[1]=3
    reject('vertex-identity-change',corners=wrong)
    wrong_uv=base['target_uv'].copy();wrong_uv[0,0]+=.01
    reject('uv-change',target_uv=wrong_uv)
    wrong_mat=base['target_material'].copy();wrong_mat[0]=1
    reject('material-change',target_material=wrong_mat)
    duplicated=mapping.copy();duplicated[3:6]=duplicated[:3]
    dup_raw=vertices[duplicated].copy();dup_raw[2::3]=-dup_raw[2::3]-1
    reject('missing-original-corner',dup_raw,duplicated,target_uv=uv[duplicated],target_material=materials[duplicated])
    return {'passed':True,'scope':'NumPy provenance fixture only; actual Blender/FBX execution remains required','checks':results}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path)
    args=parser.parse_args();result=run()
    if args.output:args.output.write_text(json.dumps(result,indent=2)+'\n',newline='\n')
    print(json.dumps(result,indent=2))
