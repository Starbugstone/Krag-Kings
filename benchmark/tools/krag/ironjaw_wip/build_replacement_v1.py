"""Isolated semantic mandibular replacement, preserving the complete Natural.

This is a source construction study. Only actual closed/open views can establish
fit; neither generation nor semantic deletion constitutes artistic acceptance.
"""
import os
os.environ.setdefault('OMP_NUM_THREADS', '2')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '2')
from pathlib import Path
import sys, json, hashlib, math
import bpy
import bmesh
import numpy as np
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
ART = ROOT/'benchmark/art/krag'
sys.path.insert(0, str(HERE))
from anatomical_exclusion import partition
from replacement_surface import alternate, coordinates, signature, rigid_face_mask
from mechanical_parts import Parts, material

SOURCE = ART/'Krag_LandmarkRelief_v9o_WIP.blend'
EXPECTED = '93661a93f12ab2510bed8d8746452b14573edc71b61b943c53f1c36db2d1bc86'
OUTPUT = ART/'Krag_IronJaw_Replacement_v1_WIP.blend'
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
if sha(SOURCE) != EXPECTED:
    raise RuntimeError('Natural source hash changed')
if OUTPUT.exists():
    raise RuntimeError('Refusing to replace an actual replacement study')
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
rig = bpy.data.objects['Krag_Rig']
rig.animation_data.action = None
for bone in rig.pose.bones:
    bone.matrix_basis = Matrix.Identity(4)
bpy.context.view_layer.update()
modules = {obj['module']: obj for obj in bpy.data.objects if obj.type == 'MESH' and 'module' in obj}
originals = list(modules.values())


def preserved():
    digest = hashlib.sha256()
    for obj in sorted(originals, key=lambda o: o.name):
        digest.update(obj.name.encode())
        digest.update(json.dumps(signature(obj.data), sort_keys=True).encode())
        digest.update(np.asarray(obj.matrix_world, float).tobytes())
        for polygon in obj.data.polygons:
            digest.update(np.asarray(polygon.vertices, np.int32).tobytes())
            digest.update(str(polygon.material_index).encode())
        for vertex in obj.data.vertices:
            for group in vertex.groups:
                digest.update(np.asarray((vertex.index, group.group, group.weight), np.float64).tobytes())
    for bone in rig.data.bones:
        digest.update(bone.name.encode())
        digest.update(np.asarray(bone.matrix_local, float).tobytes())
    for action in sorted(bpy.data.actions, key=lambda a: a.name):
        digest.update(action.name.encode())
        for layer in action.layers:
            for strip in layer.strips:
                for slot in action.slots:
                    bag = strip.channelbag(slot)
                    if bag:
                        for curve in bag.fcurves:
                            digest.update(curve.data_path.encode())
                            digest.update(str(curve.array_index).encode())
                            for key in curve.keyframe_points:
                                digest.update(np.asarray(key.co, float).tobytes())
    return digest.hexdigest()


before = preserved()
head = modules['Head']
matrix = np.asarray(head.matrix_world, float)
points = coordinates(head.data, 'Basis').astype(float)@matrix[:3, :3].T+matrix[:3, 3]
attribute = head.data.attributes.get('.sculpt_face_set')
if attribute is None or attribute.domain != 'FACE':
    raise RuntimeError('Actual semantic mandibular topology is missing')
sets = np.asarray([item.value for item in attribute.data], int)
faces = [tuple(poly.vertices) for poly in head.data.polygons]
remove, partition_report = partition(points, faces, sets)
alternates, reports = {}, {}
alternates['Head_IronJaw'], reports['Head_IronJaw'] = alternate(head, remove, 'Head_IronJaw')
natural_tusks = rigid_face_mask(modules['Face'], 'Jaw')
if not natural_tusks.any():
    raise RuntimeError('Natural tusk module is not identified')
alternates['Face_IronJaw'], reports['Face_IronJaw'] = alternate(modules['Face'], natural_tusks, 'Face_IronJaw')
lower_oral = rigid_face_mask(modules['MouthInterior'], 'Jaw', ['Krag_DentalEnamel', 'Krag_Gingiva'])
if not lower_oral.any():
    raise RuntimeError('Lower dental/gingival tissue is not identified')
alternates['Mouth_IronJaw'], reports['Mouth_IronJaw'] = alternate(modules['MouthInterior'], lower_oral, 'Mouth_IronJaw')

steel = material('Krag_IronJaw_ForgedSteel', (.055, .061, .059), .82, .58)
teal = material('Krag_IronJaw_WornPaint', (.029, .069, .066), .45, .68)
brass = material('Krag_IronJaw_BearingBronze', (.19, .105, .038), .76, .57)
liner_mat = material('Krag_IronJaw_FlexibleLining', (.022, .015, .012), 0, .67)
enamel = bpy.data.materials['Krag_DentalEnamel']
ivory = bpy.data.materials.get('Krag_TuskEnamel_Source') or bpy.data.materials['Krag_Ivory']
parts = Parts(rig)

# Replace the lower oral lining explicitly. Its boundary, morph support and
# weights remain continuous with the retained upper bag; it is now the fitted
# internal liner of the prosthesis, not organic mandible underneath an overlay.
floor = remove & (sets == 7)
lining, reports['IronJaw_Lining'] = alternate(head, ~floor, 'IronJaw_Lining')
lining.data.materials.clear()
lining.data.materials.append(liner_mat)
for polygon in lining.data.polygons:
    polygon.material_index = 0
alternates['IronJaw_Lining'] = lining

# The metal casing is fitted to the actual removed external mandibular surface.
# It contains no skin material and is rigidly driven by the mandibular hinge.
# The retained Natural remains an independent unmodified object.
external = np.flatnonzero(sets == 24)
vertex_ids = np.unique(np.concatenate([np.asarray(faces[i]) for i in external]))
remap = {int(index): i for i, index in enumerate(vertex_ids)}
shell_points = points[vertex_ids].copy()
shell_faces = [tuple(remap[index] for index in faces[i]) for i in external]
shell = parts.mesh('Continuous fitted mandibular casing', shell_points, shell_faces, steel)
shell['derivedFrom'] = 'Removed external mandible face set24; replacement metal, not retained skin'
bpy.context.view_layer.objects.active = shell
bpy.ops.object.select_all(action='DESELECT')
shell.select_set(True)
# Solidify before skinning; no shape keys on the rigid mechanical casing.
arm = shell.modifiers.get('Krag skeleton')
shell.modifiers.remove(arm)
bm = bmesh.new()
bm.from_mesh(shell.data)
bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
bm.to_mesh(shell.data)
bm.free()
solid = shell.modifiers.new('Steel wall and attachment rim', 'SOLIDIFY')
solid.thickness = .0024
solid.offset = 1
bpy.ops.object.modifier_apply(modifier=solid.name)
arm = shell.modifiers.new('Krag skeleton', 'ARMATURE')
arm.object = rig

# A thick cut shield covers the front casing; asymmetric corner bevels and
# independent side cheek plates reproduce the broad forged concept silhouette.
front = [(-.088, -.189, 1.807), (.088, -.189, 1.807),
         (.101, -.188, 1.784), (.072, -.194, 1.751),
         (-.072, -.194, 1.751), (-.101, -.188, 1.784)]
parts.plate('Broad cut chin shield', front, .007, steel)
parts.rail('Lower forged shield lip', [(-.082, -.195, 1.760), (0, -.202, 1.749),
                                     (.082, -.195, 1.760)], .0043, steel)

# Bearings are coaxial with the real Jaw's local X rotation axis. The original
# prototype's front-facing cylinders are deliberately not reused.
pivot = rig.matrix_world @ rig.data.bones['Jaw'].head_local
axis = (rig.matrix_world.to_3x3() @ rig.data.bones['Jaw'].matrix_local.to_3x3().col[0]).normalized()
bearing_locations = []
for side in (-1, 1):
    center = pivot+axis*(side*.135)
    bearing_locations.append(list(center))
    parts.cylinder('Fixed cheek bearing '+str(side), center-axis*.009, center+axis*.009,
                   .024, brass, 'Head')
    parts.cylinder('Moving concentric hub '+str(side), center+axis*(side*.010),
                   center+axis*(side*.016), .017, steel)
    parts.cylinder('Axle cap '+str(side), center+axis*(side*.016), center+axis*(side*.020),
                   .008, brass, 'Head', 12)
    x = side*.129
    outline = [(x, pivot.y-.012, pivot.z+.005), (x, -.060, 1.862),
               (x, -.143, 1.817), (x, -.153, 1.785),
               (x, -.099, 1.774), (x, -.008, 1.851)]
    parts.plate('Angled cheek linkage '+str(side), outline, .006, steel)
    parts.plate('Inset cheek paint plate '+str(side),
                [(x+side*.004, -.058, 1.850), (x+side*.004, -.128, 1.812),
                 (x+side*.004, -.113, 1.786), (x+side*.004, -.034, 1.843)], .003, teal)
    for y, z in [(-.076, 1.834), (-.111, 1.803)]:
        parts.cylinder('Cheek plate fastener '+str((side, y)),
                       (x+side*.007, y, z), (x+side*.010, y, z), .0038, brass, vertices=12)
    for xabs in (.055, .081):
        parts.cylinder('Shield rivet '+str((side, xabs)), (side*xabs, -.198, 1.780),
                       (side*xabs, -.202, 1.780), .0037, brass, vertices=16)

# A U-shaped lower dental tray, replaceable broad crowns and short tapering
# tusks. These are provisional concept-consistent internals, pending real fit.
arch = []
for i in range(41):
    angle = -math.pi*.5+math.pi*i/40
    arch.append((.085*math.sin(angle), -.098-.077*math.cos(angle), 1.807))
parts.rail('Lower dental socket rail', arch, .0053, steel, sides=16)
for i, angle in enumerate([-.99, -.76, -.43, -.15, .15, .43, .76, .99]):
    x, y = .077*math.sin(angle), -.101-.076*math.cos(angle)
    height = .014 if abs(angle) < .5 else .011
    crown = parts.box('Replaceable dental crown '+str(i), (x, y, 1.811+height*.5),
                      (.017 if abs(angle)<.5 else .014, .013, height), enamel, bevel=.0025)
    # Orient each tooth around the actual arch without moving its grip/socket.
    crown.rotation_euler.z = -angle*.55
for side in (-1, 1):
    root = (side*.071, -.143, 1.810)
    parts.cylinder('Tusk socket '+str(side), root, (side*.071, -.145, 1.819), .010, brass)
    parts.tusk('Short exposed tusk '+str(side), root, (side*.076, -.173, 1.828),
               (side*.068, -.178, 1.850), ivory)

# Exact anatomy exclusion is measurable; visual/intersection acceptance remains
# open until both neutral and maximum opening have actually been inspected.
assert preserved() == before, 'Natural geometry, weights, rig or action curves changed'
contract = json.loads((ROOT/'benchmark/local/candidates/krag-v9h-source/krag_asset_contract.json').read_text())
natural_off = set(contract['variants']['Krag_Natural']['off'])
new_modules = set(alternates) | {'IronJaw_Mechanism'}
iron_off = natural_off | {'Head', 'Face', 'MouthInterior', 'BionicJaw_Iron'}
contract['variants']['Krag_Natural']['off'] = sorted(natural_off | new_modules)
contract['variants']['Krag_IronJaw_Replacement'] = {'off': sorted(iron_off)}
contract_path = ART/'ironjaw-replacement-v1-contract.json'
contract_path.write_text(json.dumps(contract, indent=2)+'\n', newline='\n')
for obj in bpy.data.objects:
    if obj.type == 'MESH' and 'module' in obj:
        obj.hide_render = obj.hide_viewport = obj['module'] in iron_off
for file in (Path(__file__), HERE/'mechanical_parts.py', HERE/'replacement_surface.py', HERE/'anatomical_exclusion.py'):
    block = bpy.data.texts.new('IronJawReplacementV1/'+file.name)
    block.write(file.read_text())
rig.animation_data.action = bpy.data.actions['Idle']
bpy.context.scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT), compress=True)
assert sha(SOURCE) == EXPECTED
report = {'status': 'Actual semantic mechanical replacement source; visual clearance unreviewed',
          'artisticAcceptance': False, 'sharedPromotion': False,
          'input': {'path': SOURCE.relative_to(ROOT).as_posix(), 'sha256': EXPECTED},
          'source': {'path': OUTPUT.relative_to(ROOT).as_posix(), 'sha256': sha(OUTPUT)},
          'reference': 'krag-kings-design/concept-art/07-crusher-claw-and-metal-jaw-sheet.png',
          'naturalGeometryWeightsBindActionsFingerprint': before,
          'naturalSourceFileUnchanged': True, 'partition': partition_report,
          'alternates': reports, 'mechanismObjects': len(parts.objects),
          'mechanismVertices': sum(len(obj.data.vertices) for obj in parts.objects),
          'hinge': {'pivotWorld': list(pivot), 'axisWorld': list(axis), 'bearingCenters': bearing_locations},
          'bonesAddedOrMoved': [],
          'recipeHashes': {file.name: sha(file) for file in
                          (Path(__file__), HERE/'mechanical_parts.py', HERE/'replacement_surface.py', HERE/'anatomical_exclusion.py')},
          'pending': ['Actual closed/open front and unobscured side clearance',
                      'Flesh attachment and casing silhouette against concept07',
                      'Natural mouth and buried tusk defects remain separate',
                      'Runtime remap/UV/bake/export after source review']}
(ART/'ironjaw-replacement-v1.json').write_text(json.dumps(report, indent=2)+'\n', newline='\n')
print('KRAG_IRONJAW_REPLACEMENT_V1_SOURCE_COMPLETE', flush=True)
