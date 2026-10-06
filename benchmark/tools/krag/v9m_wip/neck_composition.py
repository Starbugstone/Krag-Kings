"""Prepared removal of concealed duplicate Body neck faces inside Head.

Preserves the complete Head neck, Body vertex/shape indices and all rig binds.
This composes overlapping library surfaces; final cinematic seam welding and
actual open-mouth/neck review remain required. Never changes limbs or torso.
"""
import numpy as np
import bpy,bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def remove_concealed_faces(body,head,rig):
    hp=np.asarray([tuple(head.matrix_world@v.co)for v in head.data.shape_keys.key_blocks['Basis'].data])
    tags=head.data.attributes['.sculpt_face_set'];polygons=[tuple(p.vertices)for p,t in zip(head.data.polygons,tags.data)if t.value not in [7,5,6]]
    tree=BVHTree.FromPolygons([Vector(p)for p in hp],polygons)
    points=np.asarray([tuple(body.matrix_world@v.co)for v in body.data.vertices]);neck_group=body.vertex_groups.get('Neck')
    if neck_group is None:raise RuntimeError('Body neck domain absent')
    neck=np.zeros(len(points))
    for v in body.data.vertices:
        for w in v.groups:
            if w.group==neck_group.index:neck[v.index]=w.weight
    joint=rig.data.bones['Neck'];cut_z=(joint.head_local.z+joint.tail_local.z)*.5
    inside=np.zeros(len(points),dtype=bool);signed=np.zeros(len(points))
    for i in np.flatnonzero((neck>.75)&(points[:,2]>cut_z)):
        nearest,normal,index,distance=tree.find_nearest(Vector(points[i]))
        if nearest is None:continue
        signed[i]=float((Vector(points[i])-nearest).dot(normal));inside[i]=signed[i]<-.001
    remove=[]
    for polygon in body.data.polygons:
        ids=np.asarray(polygon.vertices)
        # All corners must be concealed, so the actual exterior torso/nape is
        # never shortened by a guessed horizontal crop through visible skin.
        if np.all(inside[ids]):remove.append(polygon.index)
    if not remove:raise RuntimeError('No concealed duplicate neck region found')
    mesh=body.data;basis=np.asarray([tuple(v.co)for v in mesh.vertices]);keys={k.name:np.asarray([tuple(v.co)for v in k.data])for k in mesh.shape_keys.key_blocks}
    marker=mesh.attributes.new('krag_preserved_vertex_index','INT','POINT');marker_name=marker.name
    marker.data.foreach_set('value',np.arange(len(points),dtype=np.int32))
    before_polygons=len(mesh.polygons);bm=bmesh.new();bm.from_mesh(mesh);bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm,geom=[bm.faces[i]for i in remove],context='FACES_ONLY');bm.to_mesh(mesh);bm.free()
    observed=np.empty(len(mesh.vertices),dtype=np.int32);mesh.attributes[marker_name].data.foreach_get('value',observed)
    if not np.array_equal(observed,np.arange(len(points))):raise RuntimeError('Concealed-face deletion changed Body vertex indices')
    for key in mesh.shape_keys.key_blocks:key.data.foreach_set('co',keys[key.name].astype(np.float32).ravel())
    mesh.vertices.foreach_set('co',basis.astype(np.float32).ravel());mesh.attributes.remove(mesh.attributes[marker_name])
    return {'status':'Prepared concealed-face composition executed; actual open-mouth/neck review required',
            'removedFaces':len(remove),'beforeFaces':before_polygons,'afterFaces':len(mesh.polygons),
            'selection':'All face corners are in the Neck skin domain, above Neck joint midpoint and strictly inside external Head surface',
            'neckJointMidpointZ':float(cut_z),'retainedVertexCount':len(mesh.vertices),'shapeCoordinatesPreserved':True,
            'unchanged':['Limbs','Torso','Head anatomy','Body vertex order','Rig bind'],
            'pending':'Actual visibility/neck seam review; cinematic seam welding is not claimed'}
