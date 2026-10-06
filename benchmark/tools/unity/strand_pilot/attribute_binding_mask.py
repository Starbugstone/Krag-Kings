"""Compare actual imported Unity mask with raw FBX eligibility by geometry.

Requires the captured import buffers and color-alpha readback. No Unity process,
GPU inference or source mutation is involved.
"""
from pathlib import Path
from collections import Counter
import sys,json,hashlib
import numpy as np
from scipy.spatial import cKDTree

ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/'benchmark/tools/nib/native_groom_wip'))
from check_binding_mask import read
from validate_triangulated_payload import geometry,polygon_vertices

def main():
    pilot=ROOT/'benchmark/local/unity-strand-hair-pilot'
    source=ROOT/'benchmark/art/nib/groom-study/native-filtered-target-v1/triangulated/Nib_Natural.fbx'
    points_path=pilot/'character-import-v3/mesh-0-source-positions.bin'
    index_path=pilot/'character-import-v3/mesh-0-indices.bin'
    alpha_path=pilot/'character-render-v1/imported-color-alpha.bin'
    output=pilot/'character-render-v1/binding-mask-attribution.json'
    if output.exists():raise RuntimeError('Preserve earlier binding-mask attribution')
    color,p=read(source);q=np.fromfile(points_path,dtype='<f4').reshape(-1,3)
    j=np.fromfile(index_path,dtype='<i4').reshape(-1,3);alpha=np.fromfile(alpha_path,dtype='<f4')
    if len(alpha)!=len(q) or np.any((alpha!=0)&(alpha!=1)):raise RuntimeError('Invalid imported mask')
    manifest=json.loads((source.parent/'manifest.json').read_text())
    world=manifest['variants'][0]['sourceRestBoundsMeters'];offset=np.asarray(world['min'])-p.min(0)
    if np.max(np.abs(p.max(0)+offset-np.asarray(world['max'])))>2e-7:raise RuntimeError('Unexpected source mesh coordinate offset')
    p=p+offset;unique,source_ids=np.unique(p,axis=0,return_inverse=True)
    distance,import_ids=cKDTree(unique).query(q,workers=1)
    if distance.max()>2e-6:raise RuntimeError('Imported point mapping exceeds validated tolerance')
    # Coincident source vertices can belong to different regions. Membership
    # must agree at corners/triangles too, not merely nearest-point labels.
    allowed=np.zeros((len(unique),2),bool);allowed[source_ids,color[:,3].astype(int)]=True
    if not np.all(allowed[import_ids,alpha.astype(int)]):raise RuntimeError('Imported mask value is absent at authored point')
    mesh=next(g for g in geometry(source) if g['props'][2]=='Mesh');idx=polygon_vertices(mesh).reshape(-1,3)
    a_mask=np.all(color[idx,3]==1,axis=1);b_mask=np.all(alpha[j]==1,axis=1)
    def triangles(indices,ids,positions,eligible):
        selected=indices[eligible]
        area=np.linalg.norm(np.cross(positions[selected[:,1]]-positions[selected[:,0]],positions[selected[:,2]]-positions[selected[:,0]]),axis=1)
        keys=np.sort(ids[selected[area>0]],axis=1).astype('<i8')
        packed=np.ascontiguousarray(keys).view(np.dtype((np.void,24))).ravel()
        return Counter(x.tobytes() for x in packed)
    expected=triangles(idx,source_ids,p,a_mask);actual=triangles(j,import_ids,q,b_mask)
    if expected!=actual:raise RuntimeError('Eligible nondegenerate triangle multiset differs')
    result={'status':'Actual Unity binding mask identity verified against raw FBX geometry','sourceEligiblePoints':int(sum(color[:,3]==1)),
            'importedEligiblePoints':int(sum(alpha==1)),'sourceEligibleTriangles':int(sum(a_mask)),'importedEligibleTriangles':int(sum(b_mask)),
            'maximumMappedPointErrorMeters':float(distance.max()),'nondegenerateEligibleTriangleMultisetEqual':True,
            'sourceSha256':hashlib.sha256(source.read_bytes()).hexdigest(),'importedAlphaSha256':hashlib.sha256(alpha_path.read_bytes()).hexdigest(),
            'importedPositionsSha256':hashlib.sha256(points_path.read_bytes()).hexdigest(),'importedIndicesSha256':hashlib.sha256(index_path.read_bytes()).hexdigest(),
            'animatedAttachmentVerified':False}
    output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
