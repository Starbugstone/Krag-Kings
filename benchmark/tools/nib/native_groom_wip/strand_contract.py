"""Portable native strand arrays; Blender positions are metres, never ABC axes."""
import hashlib,json
from pathlib import Path
import numpy as np


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_region(directory, name, positions, radii, counts, roots, colors, source_object, support_object, bone_names):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    counts=np.asarray(counts,dtype='<i4');positions=np.asarray(positions,dtype='<f4');radii=np.asarray(radii,dtype='<f4')
    if counts.sum()!=len(positions)or len(radii)!=len(positions)or positions.shape[1]!=3:raise RuntimeError('Invalid native strand array sizes')
    if not np.isfinite(positions).all()or not np.isfinite(radii).all()or np.any(radii<=0):raise RuntimeError('Invalid native strand values')
    arrays={'positions':positions,'radii':radii,'curveCounts':counts,
            'rootTriangleVertexIndices':np.asarray([r['vertices']for r in roots],dtype='<i4'),
            'rootBarycentrics':np.asarray([r['barycentric']for r in roots],dtype='<f4'),
            'rootUv':np.asarray([r['sourceUv']for r in roots],dtype='<f4'),
            'rootSurfaceUv':np.asarray([r['attachmentUv']for r in roots],dtype='<f4'),
            'colorLinearRgb':np.asarray(colors,dtype='<f4')}
    # Variable-length weights retain every positive source influence. No silent
    # four-weight truncation; consumers may derive their own validated layout.
    offsets=[0];bone_ids=[];weights=[]
    for root in roots:
        for bone,weight in sorted(root['weights'].items()):
            if bone not in bone_names:raise RuntimeError('Unknown root deform bone '+bone)
            bone_ids.append(bone_names.index(bone));weights.append(weight)
        offsets.append(len(weights))
    arrays.update(rootWeightOffsets=np.asarray(offsets,dtype='<i4'),rootBoneIndices=np.asarray(bone_ids,dtype='<i4'),rootBoneWeights=np.asarray(weights,dtype='<f4'))
    files={}
    for key,array in arrays.items():
        path=directory/(name+'.'+key+'.bin');array.tofile(path)
        files[key]={'path':path.name,'sha256':sha(path),'bytes':path.stat().st_size,'dtype':'int32-le'if array.dtype.kind=='i'else'float32-le','shape':list(array.shape)}
        actual=np.fromfile(path,dtype=array.dtype).reshape(array.shape)
        if not np.array_equal(actual,array):raise RuntimeError('Native sidecar binary readback differs '+key)
    return {'name':name,'dataDirectory':'strands','curveCount':len(counts),'pointCount':len(positions),'pointLayout':'curve-major root-to-tip',
            'units':'meters','coordinateSpace':'Blender world / canonical armature rest (verified identity)',
            'axes':{'right':'+X','up':'+Z','characterForward':'-Y','handedness':'right'},
            'radiusSemantics':'radius, not diameter','colorSpace':'linear RGB',
            'sourceSurfaceObject':source_object,'nativeAttachmentSurfaceObject':support_object,
            'rootOffsetMeters':0.,'rootCorrespondence':'original source mesh point indices and Blender rest loop triangulation',
            'maximumRootInfluences':max(len(r['weights'])for r in roots),'files':files}
