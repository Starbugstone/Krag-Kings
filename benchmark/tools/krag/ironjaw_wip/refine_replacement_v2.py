"""Prepared correction of the actual v1 casing and missing flexible attachment."""
from pathlib import Path
import sys, hashlib, json, math
import bpy
import numpy as np
from mathutils import Matrix

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
ART = ROOT/'benchmark/art/krag'
sys.path.insert(0, str(HERE))
from mechanical_parts import Parts
from replacement_surface import signature, coordinates
from attachment_cuff import build as build_cuff
from anatomical_exclusion import partition

SOURCE = ART/'Krag_IronJaw_Replacement_v1_WIP.blend'
EXPECTED = '20c48d2e23c112ebca5b855247eca3e3aea630b1c463e8f99d4c4594adb5f031'
OUTPUT = ART/'Krag_IronJaw_Replacement_v2_WIP.blend'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(SOURCE) == EXPECTED
if OUTPUT.exists():
    raise RuntimeError('Preserve actual replacement evidence')
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
rig = bpy.data.objects['Krag_Rig']
rig.animation_data.action = None
for bone in rig.pose.bones:
    bone.matrix_basis = Matrix.Identity(4)
bpy.context.view_layer.update()
originals = [o for o in bpy.data.objects if o.type == 'MESH' and o.get('module')
             and o.get('module') != 'IronJaw_Mechanism']


def preserved():
    h = hashlib.sha256()
    for obj in sorted(originals, key=lambda o: o.name):
        h.update(obj.name.encode())
        h.update(json.dumps(signature(obj.data), sort_keys=True).encode())
        for vertex in obj.data.vertices:
            h.update(np.asarray([(g.group, g.weight) for g in vertex.groups], float).tobytes())
    for bone in rig.data.bones:
        h.update(bone.name.encode())
        h.update(np.asarray(bone.matrix_local, float).tobytes())
    for action in sorted(bpy.data.actions, key=lambda a: a.name):
        h.update(action.name.encode())
        for layer in action.layers:
            for strip in layer.strips:
                for slot in action.slots:
                    bag = strip.channelbag(slot)
                    if bag:
                        for curve in bag.fcurves:
                            h.update(curve.data_path.encode())
                            h.update(str(curve.array_index).encode())
                            for key in curve.keyframe_points:
                                h.update(np.asarray(key.co, float).tobytes())
    return h.hexdigest()


before = preserved()
head = next(o for o in originals if o.get('module') == 'Head')
matrix = np.asarray(head.matrix_world, float)
points = coordinates(head.data, 'Basis').astype(float)@matrix[:3, :3].T+matrix[:3, 3]
sets = np.asarray([v.value for v in head.data.attributes['.sculpt_face_set'].data], int)
faces = [tuple(p.vertices) for p in head.data.polygons]
removed, report = partition(points, faces, sets)
cuff, cuff_report = build_cuff(head, rig, removed, report['interfaceEdges'],
                              bpy.data.materials['Krag_IronJaw_FlexibleLining'])

# Author a real formed U housing rather than retaining an organic lower lip
# under a metal material. Closed walls are added after this coherent rest shape.
old = next(o for o in bpy.data.objects if o.get('component') == 'Continuous fitted mandibular casing')
segments, rows = 48, 5
shape = []
for row in range(rows):
    t = row/(rows-1)
    for i in range(segments+1):
        angle = -.5*math.pi+math.pi*i/segments
        side = math.sin(angle)**2
        top, bottom = 1.801+.032*side, 1.747+.028*side
        x = (.113-.004*t)*math.sin(angle)
        y = -.008-(.176-.013*t)*math.cos(angle)
        z = top*(1-t)+bottom*t
        shape.append((x, y, z))
n = segments+1
shell_faces = [(r*n+i, (r+1)*n+i, (r+1)*n+i+1, r*n+i+1)
               for r in range(rows-1) for i in range(segments)]
# The lower pan is triangulated deliberately, with no overlapping lip folds.
floor_center = len(shape)
shape.append((0, -.061, 1.749))
shell_faces += [((rows-1)*n+i+1, (rows-1)*n+i, floor_center) for i in range(segments)]
shape = np.asarray(shape, float)
parts = Parts(rig)
shell = parts.mesh('Lower formed mandibular casing', shape, shell_faces,
                   bpy.data.materials['Krag_IronJaw_ForgedSteel'])
bpy.data.objects.remove(old, do_unlink=True)
bpy.context.view_layer.objects.active = shell
bpy.ops.object.select_all(action='DESELECT')
shell.select_set(True)
shell.modifiers.remove(shell.modifiers['Krag skeleton'])
solid = shell.modifiers.new('Steel wall and attachment rim', 'SOLIDIFY')
solid.thickness, solid.offset = .0024, 1
bpy.ops.object.modifier_apply(modifier=solid.name)
mod = shell.modifiers.new('Krag skeleton', 'ARMATURE')
mod.object = rig
if preserved() != before:
    raise RuntimeError('Natural/retained anatomy, weights, bind or animation changed')
contract = json.loads((ART/'ironjaw-replacement-v1-contract.json').read_text())
contract['variants']['Krag_Natural']['off'].append('IronJaw_Attachment')
(ART/'ironjaw-replacement-v2-contract.json').write_text(json.dumps(contract, indent=2)+'\n', newline='\n')
for file in (Path(__file__), HERE/'attachment_cuff.py'):
    block = bpy.data.texts.new('IronJawReplacementV2/'+file.name)
    block.write(file.read_text())
rig.animation_data.action = bpy.data.actions['Idle']
bpy.context.scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT), compress=True)
assert sha(SOURCE) == EXPECTED
result = {'status': 'Actual lower casing/flexible attachment study; visual clearance still required',
          'artisticAcceptance': False, 'sharedPromotion': False,
          'input': {'path': SOURCE.relative_to(ROOT).as_posix(), 'sha256': EXPECTED},
          'source': {'path': OUTPUT.relative_to(ROOT).as_posix(), 'sha256': sha(OUTPUT)},
          'preservedNaturalRetainedAnatomyBindActions': before,
          'attachment': cuff_report, 'housingRestBounds': [shape.min(0).tolist(), shape.max(0).tolist()],
          'housingConstruction': 'Authored formed U casing and triangulated lower pan; no recycled organic lip geometry',
          'recipeHashes': {file.name: sha(file) for file in
                          (Path(__file__), HERE/'attachment_cuff.py', HERE/'mechanical_parts.py')},
          'pending': ['Actual open skin/cuff/casing transition', 'Closed crowns and shield clearance',
                      'Natural-mouth attribution/correction remains independent and unresolved']}
(ART/'ironjaw-replacement-v2.json').write_text(json.dumps(result, indent=2)+'\n', newline='\n')
print('KRAG_IRONJAW_REPLACEMENT_V2_SOURCE_COMPLETE', flush=True)
