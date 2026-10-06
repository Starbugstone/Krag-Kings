"""One saved-pose attribution of hidden dental/tongue surfaces and lip skinning."""
from pathlib import Path
import hashlib
import json
import sys
import numpy as np
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
ART = ROOT/'benchmark/art/krag'
SOURCE = ART/'Krag_NormalMouth_v9p_WIP.blend'
EXPECTED = '5be64281307b0d35541fb393311c63fcb95b4f7fdd38c2233249fb6a51d51d72'
sys.path.insert(0, str(HERE.parent/'v9j_wip'))
from dental_arch import components
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(SOURCE) == EXPECTED
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
rig = bpy.data.objects['Krag_Rig']
rig.animation_data.action = bpy.data.actions['FacePerformance']
bpy.context.scene.frame_set(146)
bpy.context.view_layer.update()
modules = {o.get('module'): o for o in bpy.data.objects if o.type == 'MESH' and o.get('module')}
head, oral = [modules[name] for name in ('Head', 'MouthInterior')]


def evaluated(obj):
    actual = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = actual.to_mesh()
    matrix = np.asarray(actual.matrix_world, float)
    points = np.asarray([p.co[:] for p in mesh.vertices])@matrix[:3, :3].T+matrix[:3, 3]
    mesh.calc_loop_triangles()
    triangles = np.asarray([t.vertices[:] for t in mesh.loop_triangles], int)
    polygons = np.asarray([t.polygon_index for t in mesh.loop_triangles], int)
    actual.to_mesh_clear()
    return points, triangles, polygons


hp, ht, hpoly = evaluated(head)
op, ot, opoly = evaluated(oral)
if len(hp) != len(head.data.vertices) or len(op) != len(oral.data.vertices):
    raise RuntimeError('Evaluated topology changed; need explicit source correspondence')
tags = np.asarray([v.value for v in head.data.attributes['.sculpt_face_set'].data], int)
tree = BVHTree.FromPolygons(hp, ht, all_triangles=True)
camera = np.asarray((1.1, -4., 2.05))
hb = np.asarray([p.co[:] for p in head.data.shape_keys.key_blocks['Basis'].data])
ob = np.asarray([p.co[:] for p in oral.data.shape_keys.key_blocks['Basis'].data])
names = [g.name for g in head.vertex_groups]
weights = np.zeros((len(hp), len(names)))
for vertex in head.data.vertices:
    for group in vertex.groups:
        weights[vertex.index, group.group] = group.weight


def visibility(ids):
    counts = {}
    visible = []
    examples = []
    for index in ids:
        point = op[int(index)]
        vector = point-camera
        length = float(np.linalg.norm(vector))
        hit, _, tri, distance = tree.ray_cast(Vector(camera), Vector(vector/length), length-.0001)
        if hit is None:
            visible.append(int(index))
            continue
        polygon = int(hpoly[tri])
        tag = int(tags[polygon])
        label = str(tag)
        counts[label] = counts.get(label, 0)+1
        if len(examples) < 12:
            examples.append({'oralVertex': int(index), 'oralWorld': point.tolist(),
                             'blockingHeadTriangle': int(tri), 'blockingHeadPolygon': polygon,
                             'blockingFaceSet': tag, 'blockerWorld': list(hit),
                             'blockerAheadOfTargetMeters': length-float(distance),
                             'headTriangleJawWeights': weights[ht[tri], names.index('Jaw')].tolist()})
    return {'samples': len(ids), 'visible': len(visible), 'blockedByHeadFaceSet': counts,
            'blockerExamples': examples}


enamel = {v for p in oral.data.polygons if oral.data.materials[p.material_index].name == 'Krag_DentalEnamel' for v in p.vertices}
tooth_report = []
for part in components(oral.data):
    if int(part[0]) not in enamel:
        continue
    first = oral.data.vertices[int(part[0])]
    owner = max(first.groups, key=lambda g: g.weight)
    bone = oral.vertex_groups[owner.group].name
    # Crown incisal end plus front-facing half of its actual source surface.
    z = ob[part, 2]
    incisal = z <= np.quantile(z, .38) if bone == 'Head' else z >= np.quantile(z, .62)
    anterior = ob[part, 1] <= np.quantile(ob[part, 1], .50)
    selected = part[incisal & anterior]
    selected = selected[np.linspace(0, len(selected)-1, min(32, len(selected))).astype(int)]
    tooth_report.append({'bone': bone, 'centerBasis': ob[part].mean(0).tolist(),
                         'boundsPosed': [op[part].min(0).tolist(), op[part].max(0).tolist()],
                         'incisalAnteriorVisibility': visibility(selected)})
tongue = np.unique([v for p in oral.data.polygons if oral.data.materials[p.material_index].name == 'Krag_OralTongue' for v in p.vertices])
selection = tongue[(op[tongue, 2] >= np.quantile(op[tongue, 2], .55)) &
                   (op[tongue, 1] <= np.quantile(op[tongue, 1], .65))]
selection = selection[np.linspace(0, len(selection)-1, min(64, len(selection))).astype(int)]
membership = np.zeros(len(hp), np.uint64)
for poly, tag in zip(head.data.polygons, tags):
    membership[list(poly.vertices)] |= np.uint64(1) << np.uint64(tag)
member = lambda tag: (membership & (np.uint64(1) << np.uint64(tag))) != 0
rim = member(24) & member(7)
jaw = weights[:, names.index('Jaw')]
edges = np.asarray([e.vertices[:] for e in head.data.edges], int)
length = np.linalg.norm(hb[edges[:, 1]]-hb[edges[:, 0]], axis=1)
gradient = abs(jaw[edges[:, 1]]-jaw[edges[:, 0]])/np.maximum(length, 1e-8)
region = member(24) & (hb[:, 1] < -.09) & (hb[:, 2] > 1.73)
selected_edges = np.flatnonzero(region[edges].all(1))
worst = selected_edges[np.argsort(gradient[selected_edges])[-12:]]
cache = ROOT/'benchmark/local/krag-normal-mouth-v9p-posed-cache.npz'
np.savez_compressed(cache, Head_basis=hb, Head_posed=hp, Head_triangles=ht,
                    Head_triangle_sets=tags[hpoly], Head_edges=edges, Head_membership=membership,
                    Head_weights=weights, Mouth_basis=ob, Mouth_posed=op, Mouth_triangles=ot)
assert sha(SOURCE) == EXPECTED
report = {'status': 'Actual saved full-open occlusion and lower-face weight attribution; source unchanged',
          'sourceSha256': EXPECTED, 'action': 'FacePerformance', 'frame': 146,
          'camera': camera.tolist(), 'teeth': tooth_report,
          'tongueDorsumVisibility': visibility(selection),
          'lowerLipJawWeights': {'minimum': float(jaw[rim].min()), 'median': float(np.median(jaw[rim])),
                                'maximum': float(jaw[rim].max()), 'samples': int(rim.sum())},
          'worstLowerFaceWeightEdges': [{'ids': edges[i].tolist(), 'basis': hb[edges[i]].tolist(),
                                         'posed': hp[edges[i]].tolist(), 'jawWeights': jaw[edges[i]].tolist(),
                                         'weightGradientPerMeter': float(gradient[i])} for i in worst],
          'cache': {'path': cache.relative_to(ROOT).as_posix(), 'sha256': sha(cache)},
          'toolSha256': sha(Path(__file__)), 'artisticAcceptance': False}
(ART/'anatomy-study/oral-occlusion-v9p.json').write_text(json.dumps(report, indent=2)+'\n', newline='\n')
print('KRAG_ORAL_OCCLUSION_ATTRIBUTION_COMPLETE', flush=True)
