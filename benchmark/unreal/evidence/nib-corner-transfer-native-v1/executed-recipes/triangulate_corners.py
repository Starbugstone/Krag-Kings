"""Triangulate a disposable skinned assembly without collapsing hard edges."""
import numpy as np
from triangle_corner_contract import validate


def _polygon_indices(mesh):
    values = np.empty(len(mesh.loops), dtype=np.int32)
    mesh.loops.foreach_get('vertex_index', values)
    ends = np.fromiter((p.loop_start + p.loop_total - 1 for p in mesh.polygons), dtype=np.int64)
    values[ends] = -values[ends] - 1
    return values


def _uv(mesh):
    values = np.empty(len(mesh.loops) * 2, dtype=np.float32)
    mesh.uv_layers.active.data.foreach_get('uv', values)
    return values.reshape((-1, 2))


def _materials(mesh):
    return np.repeat([p.material_index for p in mesh.polygons], [p.loop_total for p in mesh.polygons])


def triangulate(mesh, output):
    import bmesh
    marker_name = 'NibExportOriginalCorner'
    if mesh.attributes.get(marker_name):
        raise RuntimeError('Disposable corner marker already exists')
    source_indices = _polygon_indices(mesh)
    source_uv = _uv(mesh)
    source_material = _materials(mesh)
    source_normals = np.empty(len(mesh.loops) * 3, dtype=np.float32)
    mesh.corner_normals.foreach_get('vector', source_normals)
    source_normals = source_normals.reshape((-1, 3))
    cached_keys = {}
    for key in mesh.shape_keys.key_blocks:
        values = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
        key.data.foreach_get('co', values)
        cached_keys[key.name] = values
    positions = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
    mesh.vertices.foreach_get('co', positions)
    # BMesh copies original loop CustomData onto each new triangle corner.
    # Validate the entire provenance afterward instead of assuming that copy.
    marker = mesh.attributes.new(marker_name, 'INT', 'CORNER')
    marker.data.foreach_set('value', np.arange(len(mesh.loops), dtype=np.int32))
    bm = bmesh.new()
    try:
        bm.from_mesh(mesh)
        bmesh.ops.triangulate(bm, faces=list(bm.faces))
        bm.to_mesh(mesh)
    finally:
        bm.free()
    resulting = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
    mesh.vertices.foreach_get('co', resulting)
    if not np.array_equal(positions, resulting):
        raise RuntimeError('Triangulation moved/reordered Basis vertices')
    if set(cached_keys) != {key.name for key in mesh.shape_keys.key_blocks}:
        raise RuntimeError('Triangulation changed shape-key inventory')
    for key in mesh.shape_keys.key_blocks:
        key.data.foreach_set('co', cached_keys[key.name])
    marker = mesh.attributes.get(marker_name)
    if marker is None or marker.domain != 'CORNER' or marker.data_type != 'INT':
        raise RuntimeError('Triangulation lost original corner provenance')
    mapping = np.empty(len(mesh.loops), dtype=np.int32)
    marker.data.foreach_get('value', mapping)
    target_indices = _polygon_indices(mesh)
    result = validate(source_indices, target_indices, mapping,
        source_uv=source_uv, target_uv=_uv(mesh),
        source_material=source_material, target_material=_materials(mesh))
    mesh.attributes.remove(marker)
    mesh.normals_split_custom_set(source_normals[mapping].tolist())
    np.savez_compressed(output, sourcePolygonVertexIndex=source_indices,
        targetPolygonVertexIndex=target_indices, targetToSourceCorner=mapping)
    result.update({'basisCoordinatesByteIdentical':True,
        'shapeCoordinatesRestored':len(cached_keys), 'authoredCornerNormalsRetained':True})
    return result
