"""Prepared flexible prosthetic attachment on the actual closed skin boundary.

The outer row shares the retained skin's exact coordinates, morph deltas and
weights. The inner row belongs to Jaw. No artificial closing of the mouth or
masking of the preserved Natural is used.
"""
import bpy
import numpy as np


def copy_driver(source, target_key):
    if source is None:
        return
    curve = target_key.driver_add('value')
    driver = curve.driver
    driver.type = source.driver.type
    driver.expression = source.driver.expression
    driver.use_self = source.driver.use_self
    for original in source.driver.variables:
        variable = driver.variables.new()
        variable.name, variable.type = original.name, original.type
        for a, b in zip(original.targets, variable.targets):
            for attr in ['id_type', 'id', 'bone_target', 'data_path', 'transform_type',
                         'transform_space', 'rotation_mode']:
                if hasattr(a, attr) and hasattr(b, attr):
                    try:
                        setattr(b, attr, getattr(a, attr))
                    except (AttributeError, TypeError):
                        # Some target properties are read-only for this variable type.
                        pass


def closed_loop(edges):
    neighbors = {}
    for a, b in edges:
        neighbors.setdefault(a, []).append(b)
        neighbors.setdefault(b, []).append(a)
    if not neighbors or any(len(v) != 2 for v in neighbors.values()):
        raise RuntimeError('Prosthetic attachment requires a closed degree-two boundary')
    first = min(neighbors)
    loop = [first]
    previous, current = first, neighbors[first][0]
    while current != first:
        if current in loop:
            raise RuntimeError('Attachment has more than one closed component')
        loop.append(current)
        choices = neighbors[current]
        previous, current = current, choices[0] if choices[0] != previous else choices[1]
    if len(loop) != len(neighbors):
        raise RuntimeError('Unvisited attachment component')
    return np.asarray(loop, int)


def build(head, rig, removed_faces, interface_edges, material):
    ids = closed_loop(interface_edges)
    matrix = np.asarray(head.matrix_world, float)
    basis = np.asarray([p.co[:] for p in head.data.shape_keys.key_blocks['Basis'].data], float)
    points = basis@matrix[:3, :3].T+matrix[:3, 3]
    normals = np.asarray([v.normal[:] for v in head.data.vertices], float)@np.linalg.inv(matrix[:3, :3])
    normals /= np.maximum(np.linalg.norm(normals, axis=1), 1e-12)[:, None]
    toward = np.zeros_like(points)
    counts = np.zeros(len(points))
    for polygon, removed in zip(head.data.polygons, removed_faces):
        if not removed:
            continue
        center = points[list(polygon.vertices)].mean(0)
        for i in polygon.vertices:
            toward[i] += center-points[i]
            counts[i] += 1
    direction = toward[ids]
    lengths = np.linalg.norm(direction, axis=1)
    if np.any(lengths < 1e-8):
        raise RuntimeError('Attachment lacks an adjacent replaced surface')
    direction /= lengths[:, None]
    rows = 7
    vertices = []
    weights = []
    original_weights = [{head.vertex_groups[g.group].name: float(g.weight)
                         for g in head.data.vertices[int(i)].groups} for i in ids]
    for row in range(rows):
        t = row/(rows-1)
        smooth = t*t*(3-2*t)
        # Small returned folds supply compliance. Outer contact stays exact.
        offset = direction*(.014*t)-normals[ids]*(.0025*smooth)
        offset += normals[ids]*(.0007*np.sin(4*np.pi*t)*np.sin(np.pi*t))
        vertices.extend(points[ids]+offset)
        for source in original_weights:
            w = {name: value*(1-smooth) for name, value in source.items()}
            w['Jaw'] = w.get('Jaw', 0)+smooth
            weights.append(w)
    n = len(ids)
    faces = [(row*n+i, row*n+(i+1)%n, (row+1)*n+(i+1)%n, (row+1)*n+i)
             for row in range(rows-1) for i in range(n)]
    mesh = bpy.data.meshes.new('Continuous mechanical cheek attachment')
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    mesh.materials.append(material)
    for polygon in mesh.polygons:
        polygon.use_smooth = True
    uv = mesh.uv_layers.new(name='UVMap')
    for polygon in mesh.polygons:
        row = polygon.index//n
        col = polygon.index % n
        for loop_index, value in zip(polygon.loop_indices,
                                     [(col/n, row/(rows-1)), ((col+1)/n, row/(rows-1)),
                                      ((col+1)/n, (row+1)/(rows-1)), (col/n, (row+1)/(rows-1))]):
            uv.data[loop_index].uv = value
    obj = bpy.data.objects.new('IronJaw fitted flexible cheek cuff', mesh)
    bpy.context.collection.objects.link(obj)
    obj['module'] = 'IronJaw_Attachment'
    for name in sorted({name for w in weights for name in w}):
        group = obj.vertex_groups.new(name=name)
        for i, w in enumerate(weights):
            if w.get(name, 0) > 0:
                group.add([i], w[name], 'REPLACE')
    obj.shape_key_add(name='Basis', from_mix=False)
    base = np.asarray(vertices, float)
    source_drivers = head.data.shape_keys.animation_data.drivers if head.data.shape_keys.animation_data else []
    for key in head.data.shape_keys.key_blocks:
        if key.name == 'Basis':
            continue
        values = np.asarray([p.co[:] for p in key.data], float)
        delta = (values-basis)@matrix[:3, :3].T
        generated = base.copy()
        for row in range(rows):
            t = row/(rows-1)
            generated[row*n:(row+1)*n] += delta[ids]*(1-t*t*(3-2*t))
        target = obj.shape_key_add(name=key.name, from_mix=False)
        target.data.foreach_set('co', generated.astype(np.float32).ravel())
        target.slider_min, target.slider_max = key.slider_min, key.slider_max
        driver = next((d for d in source_drivers if d.data_path == key.path_from_id('value')), None)
        copy_driver(driver, target)
    mod = obj.modifiers.new('Krag facial skeleton', 'ARMATURE')
    mod.object = rig
    if not np.array_equal(base[:n], points[ids]):
        raise RuntimeError('Mechanical cuff outer contact moved')
    return obj, {'boundaryVertexCount': n, 'rows': rows, 'vertices': len(vertices),
                 'outerCoordinatesExact': True, 'outerMorphDeltasExact': True,
                 'outerWeightsCopied': True, 'innerWeights': 'Jaw=1',
                 'proposedWidthMeters': .014, 'actualPosedClearanceVerified': False}
