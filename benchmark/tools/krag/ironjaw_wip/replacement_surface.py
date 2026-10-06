"""Preserving alternate source surfaces for a true mandibular replacement."""
import hashlib
import numpy as np
import bpy
import bmesh


def coordinates(mesh, key=None):
    data = mesh.shape_keys.key_blocks[key].data if key else mesh.vertices
    values = np.empty(len(data)*3, np.float32)
    data.foreach_get('co', values)
    return values.reshape(-1, 3)


def signature(mesh):
    result = {'BasisMesh': hashlib.sha256(coordinates(mesh).tobytes()).hexdigest()}
    for key in mesh.shape_keys.key_blocks if mesh.shape_keys else []:
        result[key.name] = hashlib.sha256(coordinates(mesh, key.name).tobytes()).hexdigest()
    return result


def alternate(original, remove_faces, module):
    """Delete faces only; original Natural and all retained vertex data stay exact.

    Unused vertices are retained deliberately in the editable study to preserve
    every original shape-key index. Runtime assembly may remove them only with
    an explicit, verified remap once the replacement passes visual review.
    """
    remove_faces = np.asarray(remove_faces, bool)
    if len(remove_faces) != len(original.data.polygons):
        raise RuntimeError('Anatomical exclusion face-count mismatch')
    obj = original.copy()
    obj.data = original.data.copy()
    obj.name = 'Krag '+module
    obj.data.name = module+' retained continuous surface'
    bpy.context.collection.objects.link(obj)
    obj['module'] = module
    before = signature(obj.data)
    before_groups = [(v.index, tuple(sorted((g.group, float(g.weight)) for g in v.groups))) for v in obj.data.vertices]
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.faces.ensure_lookup_table()
    bm.verts.ensure_lookup_table()
    bm.verts.index_update()
    marker = bm.verts.layers.int.new('ironjaw_original_vertex')
    for vertex in bm.verts:
        vertex[marker] = vertex.index+1
    bmesh.ops.delete(bm, geom=[bm.faces[int(i)] for i in np.flatnonzero(remove_faces)], context='FACES_ONLY')
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    actual_ids = np.asarray([entry.value for entry in mesh.attributes['ironjaw_original_vertex'].data])
    if not np.array_equal(actual_ids, np.arange(1, len(actual_ids)+1)):
        raise RuntimeError('Face exclusion changed source vertex indexing')
    if signature(mesh) != before:
        raise RuntimeError('Face exclusion changed a retained shape coordinate')
    after_groups = [(v.index, tuple(sorted((g.group, float(g.weight)) for g in v.groups))) for v in mesh.vertices]
    if before_groups != after_groups:
        raise RuntimeError('Face exclusion changed original skeletal weights')
    if len(mesh.polygons) != len(remove_faces)-int(remove_faces.sum()):
        raise RuntimeError('Unexpected retained face count')
    if mesh.has_custom_normals:
        mesh.normals_split_custom_set([(0., 0., 0.)]*len(mesh.loops))
        mesh.update()
    obj['replacementStudy'] = 'Original coordinates/shape keys/weights retained; excluded anatomical faces are absent'
    return obj, {'removedFaces': int(remove_faces.sum()), 'retainedFaces': len(mesh.polygons),
                 'retainedVertexCount': len(mesh.vertices), 'shapeCoordinateHashes': before,
                 'originalNaturalMutated': False, 'unusedVerticesKeptForEditableIdentity': True}


def rigid_face_mask(obj, bone, materials=None):
    """Select actually weighted anatomy; do not infer a world-space cutoff."""
    group = obj.vertex_groups.get(bone)
    if group is None:
        raise RuntimeError('Missing anatomical bone group '+bone)
    weights = np.zeros(len(obj.data.vertices))
    for vertex in obj.data.vertices:
        weights[vertex.index] = sum(g.weight for g in vertex.groups if g.group == group.index)
    selected = []
    for polygon in obj.data.polygons:
        material = obj.data.materials[polygon.material_index].name
        selected.append(all(weights[i] > .999 for i in polygon.vertices)
                        and (materials is None or material in materials))
    return np.asarray(selected, bool)
