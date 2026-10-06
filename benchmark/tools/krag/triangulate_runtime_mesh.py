"""Triangulate a disposable export assembly without altering its point data.

Original loop normals travel through temporary corner attributes, which also
handles actual split normals. All shape coordinates are restored after BMesh
conversion because Blender otherwise perturbs some near-zero sparse deltas.
"""
import bmesh
import numpy as np


def triangulate(mesh,remove_zero_area=False):
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
    bmesh.ops.triangulate(bm,faces=list(bm.faces))
    removed=0
    if remove_zero_area:
        bm.verts.ensure_lookup_table();bm.verts.index_update()
        faces=list(bm.faces)
        indices=np.asarray([[v.index for v in face.verts] for face in faces],dtype=np.int32)
        coordinates=np.asarray([tuple(v.co) for v in bm.verts],dtype=np.float64)
        a,b,c=(coordinates[indices[:,i]] for i in range(3))
        zero=np.all(np.cross(b-a,c-a)==0.0,axis=1)
        invalid=[face for face,is_zero in zip(faces,zero) if is_zero];removed=len(invalid)
        # No welding, thresholds or vertex deletion: only exact zero-area faces.
        # Existing point identity and every nondegenerate UV corner are retained.
        if invalid:bmesh.ops.delete(bm,geom=invalid,context='FACES_ONLY')
    bm.to_mesh(mesh);bm.free()
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
            'exactZeroAreaFacesRemoved':removed,
            'vertexIndicesPreserved':True,'basisCoordinatesUnchanged':True,
            'normals':'Original corner normals transported through temporary corner attributes'}
