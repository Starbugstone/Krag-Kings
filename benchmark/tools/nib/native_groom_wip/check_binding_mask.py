"""Read actual raw FBX color-layer eligibility, never infer from authoring success."""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'v5_wip'))
from validate_triangulated_payload import geometry,data,polygon_vertices,mapped


def read(path):
    meshes=[g for g in geometry(path)if g['props'][2]=='Mesh']
    if len(meshes)!=1:raise RuntimeError('Expected one Natural FBX mesh for native binding mask')
    mesh=meshes[0];layers=[x for x in mesh['children']if x['name']=='LayerElementColor']
    layers=[x for x in layers if data(x,'Name')=='KKGroomBindable']
    if len(layers)!=1:raise RuntimeError('Actual FBX lacks exactly one KKGroomBindable color layer')
    indices=polygon_vertices(mesh);corner=mapped(layers[0],'Colors','ColorIndex',4,indices)
    vertices=data(mesh,'Vertices').reshape(-1,3);values=np.zeros((len(vertices),4),float);values[indices]=corner
    if not np.array_equal(values[indices],corner):raise RuntimeError('Binding mask split across a source point')
    if np.any(values[:,:3]!=0)or np.any((values[:,3]!=0)&(values[:,3]!=1)):raise RuntimeError('Binding mask is not exact RGB0/binary alpha')
    return values,vertices


def compare(source,target,source_report):
    a,positions=read(source);b,_=read(target)
    if not np.array_equal(a,b):raise RuntimeError('Triangulation changed binding eligibility')
    eligible=int(np.sum(b[:,3]==1));expected=sum(x['vertices']for x in source_report['addedBindingAttribute']['objects']if x['eligible'])
    if eligible!=expected:raise RuntimeError('FBX binding eligibility count differs from exact skin '+str((eligible,expected)))
    points=positions[b[:,3]==1]
    return {'attribute':'KKGroomBindable','passed':True,'actualFbxLayerVerified':True,'pointValuesByteEqual':True,'eligibleVertices':eligible,
            'ineligibleVertices':int(np.sum(b[:,3]==0)),'eligibleFbxPositionBounds':{'min':points.min(axis=0).tolist(),'max':points.max(axis=0).tolist()},
            'unrealAttributeImportVerified':False,'runtimeBindingVerified':False}
