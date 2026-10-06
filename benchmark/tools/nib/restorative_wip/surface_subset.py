"""Prepared exact index-mapped surface partition, without bmesh shape mixing.

Retains only points used by selected original faces. UV corners, materials,
named morph coordinates and skin weights are copied with explicit index maps.
Only POINT float/vector/int fields are expected for the authored Body/fuzz.
"""
import bpy
import numpy as np


def subset(source, keep_faces, name, collection):
    old = source.data
    keep = np.asarray(keep_faces, bool)
    if keep.shape != (len(old.polygons),) or not keep.any() or keep.all():
        raise RuntimeError('Require a nonempty strict subset: '+source.name)
    if old.has_custom_normals:
        raise RuntimeError('Explicit split-normal transport required before subset')
    faces = [p for p in old.polygons if keep[p.index]]
    used = np.asarray(sorted({v for p in faces for v in p.vertices}), np.int32)
    lookup = np.full(len(old.vertices), -1, np.int32)
    lookup[used] = np.arange(len(used))
    loops = np.asarray([i for p in faces for i in p.loop_indices], np.int32)
    values = np.asarray([v.co[:] for v in old.vertices], np.float32)
    mesh = bpy.data.meshes.new(name+' surface')
    mesh.from_pydata(values[used], [], [[int(lookup[v]) for v in p.vertices] for p in faces])
    mesh.update()
    obj = source.copy()
    obj.data = mesh
    obj.name = name
    collection.objects.link(obj)
    # Object.copy preserves the group table, but fresh mesh points have no data.
    obj.vertex_groups.clear()
    groups = [obj.vertex_groups.new(name=g.name) for g in source.vertex_groups]
    for i, original in enumerate(used):
        for assignment in old.vertices[int(original)].groups:
            groups[assignment.group].add([i], assignment.weight, 'REPLACE')
    for mat in old.materials:
        mesh.materials.append(mat)
    for new_face, old_face in zip(mesh.polygons, faces):
        new_face.material_index = old_face.material_index
        new_face.use_smooth = old_face.use_smooth
    for uv in old.uv_layers:
        layer = mesh.uv_layers.new(name=uv.name)
        coords = np.asarray([entry.uv[:] for entry in uv.data], np.float32)[loops]
        layer.data.foreach_set('uv', coords.ravel())
    if old.uv_layers.active:
        mesh.uv_layers.active = mesh.uv_layers[old.uv_layers.active.name]
    for attribute in old.attributes:
        if attribute.name.startswith('.') or attribute.name in ['position']:
            continue
        if attribute.domain != 'POINT':
            continue  # UVs and material indices were explicitly handled above.
        fields = {'FLOAT': ('value', np.float32), 'FLOAT_VECTOR': ('vector', np.float32),
                  'INT': ('value', np.int32)}
        if attribute.data_type not in fields:
            raise RuntimeError('Uncovered point field: '+attribute.name)
        field, dtype = fields[attribute.data_type]
        vals = np.asarray([getattr(v, field) for v in attribute.data], dtype)[used]
        layer = mesh.attributes.new(attribute.name, attribute.data_type, 'POINT')
        layer.data.foreach_set(field, vals.ravel())
    if old.shape_keys:
        for original in old.shape_keys.key_blocks:
            key = obj.shape_key_add(name=original.name, from_mix=False)
            coords = np.asarray([v.co[:] for v in original.data], np.float32)[used]
            key.data.foreach_set('co', coords.ravel())
            key.slider_min = original.slider_min
            key.slider_max = original.slider_max
            key.interpolation = original.interpolation
            key.vertex_group = original.vertex_group
            key.value = 0
        for original in old.shape_keys.key_blocks:
            obj.data.shape_keys.key_blocks[original.name].relative_key = obj.data.shape_keys.key_blocks[original.relative_key.name]
        obj.data.shape_keys.use_relative = old.shape_keys.use_relative
    mesh.update()
    # Verify actual RNA payloads, not merely the assignment arrays.
    for original, key in zip(old.shape_keys.key_blocks if old.shape_keys else [],
                             mesh.shape_keys.key_blocks if mesh.shape_keys else []):
        expected = np.asarray([v.co[:] for v in original.data], np.float32)[used]
        actual = np.asarray([v.co[:] for v in key.data], np.float32)
        if not np.array_equal(expected, actual):
            raise RuntimeError('Partition moved morph points '+key.name)
    for layer in mesh.uv_layers:
        expected = np.asarray([v.uv[:] for v in old.uv_layers[layer.name].data], np.float32)[loops]
        if not np.array_equal(expected, np.asarray([v.uv[:] for v in layer.data], np.float32)):
            raise RuntimeError('Partition moved UV corners')
    for i, original in enumerate(used):
        expected = [(g.group, g.weight) for g in old.vertices[int(original)].groups]
        actual = [(g.group, g.weight) for g in mesh.vertices[i].groups]
        if expected != actual:
            raise RuntimeError('Partition changed skin assignments')
    return obj, {'sourceVertices': len(old.vertices), 'vertices': len(mesh.vertices),
                 'sourceFaces': len(old.polygons), 'faces': len(mesh.polygons),
                 'removedFaces': int((~keep).sum()), 'pointMap': used.tolist(),
                 'originalFaceMap': [p.index for p in faces],
                 'morphCoordinatesExact': True, 'uvCornersExact': True,
                 'skinAssignmentsExact': True}
