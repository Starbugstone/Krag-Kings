"""Triangulate a disposable export assembly without altering its point data.

Original loop normals travel through temporary corner attributes, which also
handles actual split normals. All shape coordinates are restored after BMesh
conversion because Blender otherwise perturbs some near-zero sparse deltas.
"""
import bmesh
import numpy as np


def triangulate(mesh):
    count=len(mesh.vertices)
    basis=np.empty(count*3,dtype=np.float32);mesh.vertices.foreach_get('co',basis)
    keys={}
    if mesh.shape_keys:
        for key in mesh.shape_keys.key_blocks:
            values=np.empty(count*3,dtype=np.float32);key.data.foreach_get('co',values)
            keys[key.name]=values
    ids=mesh.attributes.new('krag_export_vertex_id','INT','POINT')
    ids.data.foreach_set('value',np.arange(count,dtype=np.int32))
    normal_data=np.empty(len(mesh.loops)*3,dtype=np.float32)
    mesh.corner_normals.foreach_get('vector',normal_data)
    normal_data=normal_data.reshape(-1,3)
    names=[]
    for axis in range(3):
        name='krag_export_corner_normal_'+str(axis);names.append(name)
        attribute=mesh.attributes.new(name,'FLOAT','CORNER')
        attribute.data.foreach_set('value',np.ascontiguousarray(normal_data[:,axis]))
    bm=bmesh.new();bm.from_mesh(mesh)
    bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    if len(mesh.vertices)!=count:raise RuntimeError('Triangulation changed vertex count')
    actual_ids=np.empty(count,dtype=np.int32)
    mesh.attributes['krag_export_vertex_id'].data.foreach_get('value',actual_ids)
    if not np.array_equal(actual_ids,np.arange(count,dtype=np.int32)):
        raise RuntimeError('Triangulation reordered indexed vertices')
    current=np.empty_like(basis);mesh.vertices.foreach_get('co',current)
    if not np.array_equal(basis,current):raise RuntimeError('Triangulation changed Basis coordinates')
    if mesh.shape_keys:
        for key in mesh.shape_keys.key_blocks:key.data.foreach_set('co',keys[key.name])
    normals=np.empty((len(mesh.loops),3),dtype=np.float32)
    for axis,name in enumerate(names):
        values=np.empty(len(mesh.loops),dtype=np.float32)
        mesh.attributes[name].data.foreach_get('value',values);normals[:,axis]=values
    mesh.normals_split_custom_set(normals.tolist())
    for name in names+['krag_export_vertex_id']:mesh.attributes.remove(mesh.attributes[name])
    if any(len(poly.vertices)!=3 for poly in mesh.polygons):
        raise RuntimeError('Nontriangular face survived triangulation')
    return {'vertices':count,'triangles':len(mesh.polygons),'restoredShapeCoordinates':len(keys),
            'vertexIndicesPreserved':True,'basisCoordinatesUnchanged':True,
            'normals':'Original corner normals transported through temporary corner attributes'}
