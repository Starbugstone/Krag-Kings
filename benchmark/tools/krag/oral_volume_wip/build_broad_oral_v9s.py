"""Actual coherent oral/profile candidate; visual gates remain decisive."""
import os
os.environ.setdefault('OMP_NUM_THREADS', '2')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '2')
from pathlib import Path
import sys
import json
import hashlib
import numpy as np
import bpy
from mathutils import Matrix
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
ART = ROOT/'benchmark/art/krag'
for folder in (HERE, HERE.parent/'ironjaw_wip', HERE.parent/'landmark_wip', HERE.parent/'v9n_wip', HERE.parent/'reference_fit_wip'):
    sys.path.insert(0, str(folder))
from replacement_surface import coordinates, signature
from landmark_relief import Relief
from macro_envelope_v9nb import surface_report
from profile_and_lip import membership
from rest_profile_v9r import OralProfile
from posed_lip_corrective_v9s import apply as fit_open_lip
from broad_oral_v9s import BroadOral, weight_support
from stout_canines import apply as fit_canines
from commissure_support import refine as refine_commissures

SOURCE = ART/'Krag_ProfileOral_v9r_WIP.blend'
EXPECTED = 'c27cecdc6e8709a42f472906db4595aaa6554c3e2897a994fdf19de767e1ceab'
OUTPUT = ART/'Krag_BroadOral_v9s_WIP.blend'
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
assert sha(SOURCE) == EXPECTED
if OUTPUT.exists():
    raise RuntimeError('Preserve prior actual source evidence')
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
rig = bpy.data.objects['Krag_Rig']
modules = {o.get('module'): o for o in bpy.data.objects if o.type == 'MESH' and o.get('module')}
head, face, oral = [modules[n] for n in ('Head', 'Face', 'MouthInterior')]
affected = {head}


def preserved():
    digest = hashlib.sha256()
    for obj in sorted((o for o in bpy.data.objects if o.type == 'MESH'), key=lambda o: o.name):
        if obj in affected:
            continue
        digest.update(obj.name.encode())
        digest.update(json.dumps(signature(obj.data), sort_keys=True).encode())
    for bone in rig.data.bones:
        digest.update(bone.name.encode())
        digest.update(np.asarray(bone.matrix_local, float).tobytes())
    for action in sorted(bpy.data.actions, key=lambda a: a.name):
        digest.update(action.name.encode())
        for layer in action.layers:
            for strip in layer.strips:
                for slot in action.slots:
                    bag = strip.channelbag(slot)
                    if not bag:
                        continue
                    for curve in bag.fcurves:
                        digest.update(curve.data_path.encode())
                        digest.update(str(curve.array_index).encode())
                        for key in curve.keyframe_points:
                            digest.update(np.asarray(key.co, float).tobytes())
                            digest.update(np.asarray(key.handle_left, float).tobytes())
                            digest.update(np.asarray(key.handle_right, float).tobytes())
                            digest.update(key.interpolation.encode())
    return digest.hexdigest()


before = preserved()
rig.animation_data.action = None
for bone in rig.pose.bones:
    bone.matrix_basis = Matrix.Identity(4)
bpy.context.view_layer.update()
for obj in affected:
    if not np.allclose(np.asarray(obj.matrix_world), np.eye(4), atol=1e-7):
        raise RuntimeError('Expected source face/oral mesh coordinates in rig metres')
hp = coordinates(head.data, 'Basis').astype(float)
edges = np.asarray([edge.vertices[:] for edge in head.data.edges], int)
optical = Relief()
profile = BroadOral(hp, edges, membership(head.data), optical.head_support == 0)
head_after = profile.head(hp)
held = optical.head_support == 0
if not np.array_equal(head_after[held], hp[held]):
    raise RuntimeError('Broad oral fit moved real optical return/contact vertices')
head.data.calc_loop_triangles()
metrics = surface_report(hp, head_after, np.asarray([t.vertices[:] for t in head.data.loop_triangles]))
for key in head.data.shape_keys.key_blocks:
    points = coordinates(head.data, key.name).astype(float)
    revised = profile.head(points)
    if not np.array_equal(revised[held],points[held]):
        raise RuntimeError('Broad oral fit moved optical points in shape '+key.name)
    key.data.foreach_set('co', revised.astype(np.float32).ravel())
head.data.vertices.foreach_set('co', head_after.astype(np.float32).ravel())
head.data.update()
# Refit the actual mandibular tissue support, not just a single open-pose
# outline. Transfer only Head/Jaw weights; retain every Neck influence.
groups = {name:head.vertex_groups[name] for name in ('Head','Jaw','Neck')}
weights = np.zeros((len(hp),3));lookup={groups[n].index:i for i,n in enumerate(groups)}
for vertex in head.data.vertices:
    for item in vertex.groups:
        if item.group not in lookup:raise RuntimeError('Unexpected Head skin group')
        weights[vertex.index,lookup[item.group]]=item.weight
new_jaw, support = weight_support(head_after, edges, membership(head.data), weights[:,1])
new_head = weights[:,0]+weights[:,1]-new_jaw
if new_head.min() < -1e-7:raise RuntimeError('Mandibular support overlaps fixed Neck weights')
new_head=np.maximum(new_head,0)
for i in np.flatnonzero(abs(new_jaw-weights[:,1])>1e-9):
    groups['Jaw'].add([int(i)],float(new_jaw[i]),'REPLACE')
    groups['Head'].add([int(i)],float(new_head[i]),'REPLACE')
print('KRAG_V9S_BROAD_ORAL_AND_SUPPORT_COMPLETE',flush=True)
lip=fit_open_lip(head,rig)
print('KRAG_V9S_POSED_LIP_RESIDUAL_COMPLETE',flush=True)
for obj in affected:
    if obj.data.has_custom_normals:
        obj.data.normals_split_custom_set([(0., 0., 0.)]*len(obj.data.loops))
        obj.data.update()
if preserved() != before:
    raise RuntimeError('Oral authoring changed unrelated geometry, bind or action data')
expected_shapes = {obj['module']: signature(obj.data) for obj in affected}
files = [Path(__file__), HERE/'broad_oral_v9s.py', HERE/'posed_lip_corrective_v9s.py', HERE/'profile_and_lip.py']
for path in files:
    block = bpy.data.texts.new('BroadOralV9s/'+path.name); block.write(path.read_text())
rig.animation_data.action = bpy.data.actions['Idle']; bpy.context.scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT), compress=True)
bpy.ops.wm.open_mainfile(filepath=str(OUTPUT))
rig = bpy.data.objects['Krag_Rig']
modules = {o.get('module'): o for o in bpy.data.objects if o.type == 'MESH' and o.get('module')}
head, face, oral = [modules[n] for n in ('Head', 'Face', 'MouthInterior')]
affected = {head}
if preserved() != before or any(signature(o.data) != expected_shapes[o['module']] for o in affected):
    raise RuntimeError('Actual saved/reopened source failed coordinate/bind/action preservation')
assert sha(SOURCE) == EXPECTED
result = {'status':'Actual broad oral-envelope source; closed/open views still required',
          'artisticAcceptance':False,'sharedPromotion':False,
          'input':{'path':SOURCE.relative_to(ROOT).as_posix(),'sha256':EXPECTED},
          'source':{'path':OUTPUT.relative_to(ROOT).as_posix(),'sha256':sha(OUTPUT)},
          'externalConstraint':'Concept front lip/interocular interval; provisional dental arch does not set mouth width',
          'neutralWidthMeters':float(profile.target_width), 'restSurface':metrics,
          'monotoneLateralJacobianLowerBound':float(1-.8*profile.amplitude),
          'heldOpticalVerticesExact':int(held.sum()),'mandibularSupport':support,'posedLowerLip':lip,
          'dentalGumTongueCaninePayloadsExact':True,
          'motionLineage':'Preserved pre-v4 actions from v9r; separate verified body merge required',
          'allExistingBindActionsUnrelatedMeshesPreserved':before,
          'savedReopenedChecksPassed':True,
          'recipeHashes':{p.name:sha(p)for p in files},
          'pending':['Actual closed/open lip and canine/dental fit','Concept likeness and IronJaw compatibility']}
(ART/'broad-oral-v9s.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n')
print('KRAG_BROAD_ORAL_V9S_SOURCE_COMPLETE',flush=True)
