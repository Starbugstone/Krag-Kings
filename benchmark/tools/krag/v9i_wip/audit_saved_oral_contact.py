"""Prepared read-only v9h dental/lining attribution in neutral and mouth-open poses.

Reports which actual evaluated head faces hide sampled provisional tooth/gum
surfaces. It does not alter the source or infer artistic acceptance.
"""
from pathlib import Path
import json, hashlib
import numpy as np
import bpy
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[4]
ART = ROOT / 'benchmark/art/krag'
SOURCE = ART / 'Krag_Master_v9h_WIP.blend'
EXPECTED = '5f89b7f1492c46e8ff3a1d9d90bd725ca7353c5474bf93af01a7dd6b2493234e'
before = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
if before != EXPECTED:
    raise RuntimeError('Pinned v9h source changed')
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
rig = bpy.data.objects['Krag_Rig']
modules = {o.get('module'): o for o in bpy.data.objects if o.type == 'MESH' and 'module' in o}
head, oral = modules['Head'], modules['MouthInterior']
scene = bpy.context.scene
camera_position = Vector((1.1, -4, 2.05))

def components(mesh):
    neighbors = [[] for _ in mesh.vertices]
    for e in mesh.edges:
        a, b = e.vertices; neighbors[a].append(b); neighbors[b].append(a)
    seen = set(); result = []
    material_for_vertex = {}
    for p in mesh.polygons:
        for i in p.vertices:
            material_for_vertex.setdefault(i, set()).add(p.material_index)
    for start in range(len(mesh.vertices)):
        if start in seen:
            continue
        stack = [start]; seen.add(start); group = []
        while stack:
            i = stack.pop(); group.append(i)
            for j in neighbors[i]:
                if j not in seen:
                    seen.add(j); stack.append(j)
        materials = sorted({m for i in group for m in material_for_vertex.get(i, ())})
        result.append((np.asarray(group), [mesh.materials[m].name for m in materials]))
    return result

parts = components(oral.data)
report = {'status': 'Actual saved-source posed occlusion attribution; no repair or artistic acceptance',
          'source': str(SOURCE.relative_to(ROOT)), 'sourceSha256': before,
          'camera': list(camera_position), 'poses': {}}
for name, frame in [('Neutral', None), ('OpenMouth', 146)]:
    if frame is None:
        rig.animation_data.action = None
        for bone in rig.pose.bones:
            bone.matrix_basis = Matrix.Identity(4)
    else:
        rig.animation_data.action = bpy.data.actions['FacePerformance']; scene.frame_set(frame)
    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()
    h, m = head.evaluated_get(deps), oral.evaluated_get(deps)
    hv = [h.matrix_world @ v.co for v in h.data.vertices]
    head_tree = BVHTree.FromPolygons(hv, [tuple(p.vertices) for p in h.data.polygons])
    face_sets = h.data.attributes.get('.sculpt_face_set')
    result = []
    for number, (indices, materials) in enumerate(parts):
        if len(m.data.vertices) != len(oral.data.vertices):
            raise RuntimeError('Evaluated oral topology changed')
        coords = np.asarray([tuple(m.matrix_world @ m.data.vertices[int(i)].co) for i in indices])
        # Sample actual surface vertices across each connected component.
        selected = np.linspace(0, len(indices) - 1, min(160, len(indices)), dtype=int)
        hidden = 0; hits = {}; gaps = []
        for local in selected:
            point = Vector(coords[local]); ray = point - camera_position
            length = ray.length; ray.normalize()
            hit, normal, face, distance = head_tree.ray_cast(camera_position, ray, length - .0001)
            if hit is None:
                continue
            hidden += 1; gaps.append(length - distance)
            polygon = h.data.polygons[face]
            material = h.data.materials[polygon.material_index].name
            tag = int(face_sets.data[face].value) if face_sets else None
            label = material + '/sourceFaceSet=' + str(tag)
            hits[label] = hits.get(label, 0) + 1
        result.append({'component': number, 'materials': materials, 'vertices': len(indices),
                       'boundsMeters': [coords.min(0).tolist(), coords.max(0).tolist()],
                       'sampledVertices': len(selected), 'hiddenByHead': hidden,
                       'firstHeadSurfaceHits': hits, 'largestCameraOcclusionGapMeters': max(gaps, default=0)})
    report['poses'][name] = result
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != before:
    raise RuntimeError('Read-only source changed')
(ART / 'anatomy-study/mouth-posed-contact-v9h.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8', newline='\n')
print('Read-only actual oral contact attribution saved', flush=True)
