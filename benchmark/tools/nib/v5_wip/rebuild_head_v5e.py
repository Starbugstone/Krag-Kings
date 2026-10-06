"""Separate v5e muzzle study; preserves saved v5d and all shared outputs.

Uses the explicitly CC0 Blender Studio animation-head topology as a fitted cage.
The authored creature proportions and all new shapes remain review candidates.
Run only in a serialized, memory-guarded Blender process.
"""
import argparse, hashlib, json, math, sys
from pathlib import Path
import bpy, bmesh
import numpy as np
from mathutils import Matrix, Vector

ROOT=Path(__file__).resolve().parents[4]
ART=ROOT/'benchmark/art/nib'
sys.path.insert(0,str(Path(__file__).parent))
sys.path.insert(0,str(Path(__file__).parent.parent))
sys.path.insert(0,str(ROOT/'benchmark/tools/krag'))
from fit_head_v5e import fit_head,nose_mask,oral_translation,shape_receipt
from nib_neck_v5d import cut_and_close,conform_to_body
from nib_face import FACIAL_MORPHS, morph_delta, smoothstep
from runtime_reduction import attach_portable_drivers
from nib_groom_v5 import build_groom, deepen_ears
from nib_cloth_v5 import revise_cloth
from nib_hand_v5 import rebuild_hands
from nib_opaque_eyes import fit_opaque_eye
from nib_ocular_materials import create_ocular_materials
from nib_groom_materials import create_regions
from audit_face_coordinates import facial_snapshot

parser=argparse.ArgumentParser()
parser.add_argument('--source',type=Path,default=ART/'Nib_Runtime_Optimized_v4b_MorphRepair.blend')
parser.add_argument('--cinematic',action='store_true')
parser.add_argument('--hands',action='store_true')
parser.add_argument('--revision',required=True,choices=['v5e'],help='Explicit isolated revision; older job recipes require their recorded source revision')
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
SOURCE=args.source
TARGET=ART/('Nib_Cinematic_'+args.revision+'_WIP.blend' if args.cinematic else 'Nib_Master_'+args.revision+'_WIP.blend')
REPORT=ART/'v5-study'/('native-head-'+('cinematic-' if args.cinematic else '')+args.revision+'.json')
LIBRARY=ROOT/'benchmark/art/reference-anatomy/blender-studio-human-base-meshes/source/human-base-meshes-bundle-v1.4.1/human_base_meshes_bundle.blend'
HEAD_DROP=-.032
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source_hash=sha(SOURCE)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE),load_ui=False)
scene=bpy.context.scene;rig=bpy.data.objects['Nib_Rig']
collection=bpy.data.collections['Nib_Authored_Components']
rig.animation_data.action=None
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
scene.frame_set(1)
deformation=json.loads(scene['deformation_contract'])
report={'status':'Work in progress: native geometry review required','artisticAcceptance':False,
        'source':str(SOURCE),'sourceSha256':source_hash,'referenceLibrarySha256':sha(LIBRARY),
        'referenceLicense':'CC0 per Blender Studio bundle README; retained in original reference directory.',
        'borrowedTopology':'GEO-head_animation_realistic and its matching eye topology; original sculpt and proportions adapted to the Nib concept.',
        'changes':[]}
report['authoringCode']={}
for filename in ['rebuild_head_v5e.py','fit_head.py','fit_head_v5d.py','fit_head_v5e.py','nib_neck_v5d.py','nib_groom_v5.py','nib_cloth_v5.py',
                 'nib_hand_v5.py','nib_opaque_eyes.py','nib_ocular_materials.py','nib_groom_materials.py','audit_face_coordinates.py']:
    path=Path(__file__).with_name(filename)
    report['authoringCode'][filename]=sha(path)
    text_name='Nib source '+args.revision+' '+filename
    text=bpy.data.texts.get(text_name) or bpy.data.texts.new(text_name)
    text.clear();text.write(path.read_text())

def discard(obj):
    mesh=obj.data if obj.type=='MESH' else None
    bpy.data.objects.remove(obj,do_unlink=True)
    if mesh is not None and mesh.users==0:bpy.data.meshes.remove(mesh)

def bind(obj,bone='Head'):
    obj.parent=rig;obj.matrix_parent_inverse=Matrix.Identity(4)
    mod=obj.modifiers.new('Nib deformation','ARMATURE');mod.object=rig
    if bone:
        group=obj.vertex_groups.new(name=bone)
        group.add(list(range(len(obj.data.vertices))),1,'REPLACE')
    for polygon in obj.data.polygons:polygon.use_smooth=True
    obj['variant']='all';obj['bone']=bone or 'FaceSurface'

def setmaterial(obj,*names):
    obj.data.materials.clear()
    for name in names:obj.data.materials.append(bpy.data.materials[name])

def apply_subdivision(obj,levels=2):
    bpy.context.view_layer.objects.active=obj
    mod=obj.modifiers.new('Animation surface subdivision','SUBSURF');mod.levels=levels
    bpy.ops.object.modifier_apply(modifier=mod.name)

names=['GEO-head_animation_realistic']
names += ['GEO-head_animation_realistic.'+part+'.'+side for part in ['iris','sclera'] for side in ['L','R']]
with bpy.data.libraries.load(str(LIBRARY),link=False) as (available,requested):
    requested.objects=names
reference={o.name:o for o in requested.objects}
for obj in reference.values():
    for c in list(obj.users_collection):c.objects.unlink(obj)
    collection.objects.link(obj)
# Evaluate the original, intact parent hierarchy before caching source space.
# matrix_world on an unlinked appended object can be stale. The independent
# source-center assertion below is against the audited CC0 library coordinates.
bpy.context.view_layer.update()
def authored_world(obj):
    if obj.parent is None:return obj.matrix_basis.copy()
    return authored_world(obj.parent)@obj.matrix_parent_inverse@obj.matrix_basis
reference_world={name:obj.matrix_world.copy() for name,obj in reference.items()}
head=reference['GEO-head_animation_realistic'];head_matrix=reference_world[head.name].copy()
report['originalReferenceMatrices']={name:[list(row) for row in matrix] for name,matrix in reference_world.items()}
report['referenceEyeLocalCenters']={}
for side,sign in [('L',1),('R',-1)]:
    name='GEO-head_animation_realistic.sclera.'+side
    local=(head_matrix.inverted()@reference_world[name]).translation
    expected=Vector((sign*.0358764,-.1153812,.3100375))
    if (local-expected).length>.00005:raise RuntimeError('Reference eye parent evaluation differs from audited source: '+side+' '+str(tuple(local)))
    report['referenceEyeLocalCenters'][side]=list(local)
source_vertices=np.asarray([tuple(v.co) for v in head.data.vertices],dtype=float)
for name,obj in reference.items():
    obj.modifiers.clear()
    obj.vertex_groups.clear()
    obj.parent=None;obj.matrix_parent_inverse=Matrix.Identity(4)
    obj.matrix_world=reference_world[name]

# Remove the original human auricles, including their hidden posterior roots.
# No additional ears are retained: the existing two fennec auricles remain.
# The read-only audit identified face sets 3 and 4 as the two auricles (200
# vertices each, lateral x about +/-0.071..0.100 m); preserve adjacent skull.
head.name='Nib v5 fitted animation face'
bm=bmesh.new();bm.from_mesh(head.data);bm.verts.ensure_lookup_table()
face_sets=bm.faces.layers.int.get('.sculpt_face_set')
if face_sets is None:raise RuntimeError('Expected audited animation-head face sets')
ears=[face for face in bm.faces if face[face_sets] in {3,4}]
if not ears:raise RuntimeError('Audited original ear face sets are absent')
bmesh.ops.delete(bm,geom=ears,context='FACES_ONLY')
# A vertex-delete cutoff left a jagged, visibly open ring in the real profile.
# Bisect and close the actual lower neck before conforming it to retained skin.
report['neckBoundary']=cut_and_close(bm)
bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
# Repair the two lateral openings while retaining the source's facial loops.
boundaries=[edge for edge in bm.edges if edge.is_boundary]
components=[];remaining=set(boundaries)
while remaining:
    initial=remaining.pop();group={initial};frontier=[initial]
    while frontier:
        edge=frontier.pop()
        for vertex in edge.verts:
            for adjacent in vertex.link_edges:
                if adjacent in remaining:remaining.remove(adjacent);group.add(adjacent);frontier.append(adjacent)
    components.append(list(group))
repaired=0
for edges in components:
    verts={v for edge in edges for v in edge.verts};center=sum((v.co for v in verts),Vector())/len(verts)
    if abs(center.x)<.05 or not .20<center.z<.38:continue
    faces=bmesh.ops.holes_fill(bm,edges=edges,sides=0)['faces']
    bmesh.ops.triangulate(bm,faces=faces)
    repaired+=1
if repaired!=2:raise RuntimeError(f'Expected exactly two human-ear removal patches, found {repaired}')
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(head.data);bm.free()

original=np.asarray([tuple(v.co) for v in head.data.vertices],dtype=float)
source_attribute=head.data.attributes.new('nib_source_position','FLOAT_VECTOR','POINT')
source_attribute.data.foreach_set('vector',original.astype(np.float32).ravel())
fitted=fit_head(original)
report['shapeCorrection']=shape_receipt(original)
neck_weights,report['neckSurfaceFit']=conform_to_body(original,fitted,collection,HEAD_DROP)
neck_attribute=head.data.attributes.new('NibNeckBlend','FLOAT','POINT')
neck_attribute.data.foreach_set('value',neck_weights.astype(np.float32))
mouth_shift=Vector(oral_translation())
head.data.vertices.foreach_set('co',fitted.astype(np.float32).ravel())
head.matrix_world=Matrix.Translation((0,0,HEAD_DROP))
setmaterial(head,'Nib_Skin','Nib_EarInner','Nib_MouthInterior')
face_material=bpy.data.materials['Nib_Skin'].copy();face_material.name='Nib_v5_FacialSkin'
head.data.materials[0]=face_material
mask=head.data.attributes.new('NibNoseMask','FLOAT','POINT')
mask.data.foreach_set('value',nose_mask(original).astype(np.float32))
nodes=face_material.node_tree.nodes;links=face_material.node_tree.links
principled=next(node for node in nodes if node.type=='BSDF_PRINCIPLED')
base=principled.inputs['Base Color'];old_link=base.links[0].from_socket if base.links else None
attribute=nodes.new('ShaderNodeAttribute');attribute.attribute_name='NibNoseMask'
mix=nodes.new('ShaderNodeMixRGB');mix.blend_type='MIX';mix.inputs[2].default_value=(.115,.062,.044,1)
if old_link:links.new(old_link,mix.inputs[1])
else:mix.inputs[1].default_value=base.default_value
links.new(attribute.outputs['Fac'],mix.inputs[0]);links.new(mix.outputs[0],base)
for polygon in head.data.polygons:
    center=original[list(polygon.vertices)].mean(0)
    # Audited set7 is the oral region. The old unbounded y test also painted
    # posterior neck faces black, visible as rectangles in the actual profile.
    face_set=head.data.attributes['.sculpt_face_set'].data[polygon.index].value
    if face_set==7 and -.115<center[1]<-.025:polygon.material_index=2
apply_subdivision(head,2)
surface_check=bmesh.new();surface_check.from_mesh(head.data)
boundary_edges=[e for e in surface_check.edges if e.is_boundary]
neck_open=[e for e in boundary_edges if max(v.co.z+HEAD_DROP for v in e.verts)<1.07]
report['neckBoundary']['evaluatedOpenNeckEdges']=len(neck_open)
report['neckBoundary']['allSurfaceBoundaryEdges']=len(boundary_edges)
surface_check.free()
if neck_open:raise RuntimeError('Visible lower-neck boundary is still open after subdivision')
bind(head,None)
headgroup=head.vertex_groups.new(name='Head');jawgroup=head.vertex_groups.new(name='Jaw');neckgroup=head.vertex_groups.new(name='Neck')
for v in head.data.vertices:
    x,y,z=v.co
    oldz=z-mouth_shift.z;oldy=y-mouth_shift.y
    jaw=(1-smoothstep(1.104,1.135,oldz))*max(0,min(1,(-oldy+.004)/.043))
    # The source mouth has separate upper/lower interior loops. A narrow seam
    # preserves lip closure during smiles; Jaw opens the lower lip and chin.
    if abs(x)<.05 and oldy<-.05 and 1.102<oldz<1.119:
        seam=1.110+.0015*(x/.045)**3
        jaw=1-smoothstep(seam-.0012,seam+.0012,oldz)
    neck=max(0,min(1,head.data.attributes['NibNeckBlend'].data[v.index].value))
    jaw*=1-neck;head_weight=max(0,1-jaw-neck)
    if head_weight>0:headgroup.add([v.index],head_weight,'REPLACE')
    if jaw>0:jawgroup.add([v.index],jaw,'REPLACE')
    if neck>0:neckgroup.add([v.index],neck,'REPLACE')
head.shape_key_add(name='Basis',from_mix=False)
for name in FACIAL_MORPHS:
    key=head.shape_key_add(name=name,from_mix=False)
    for vertex in head.data.vertices:
        sample=vertex.co.copy()
        if name.startswith(('Smile','Frown','CheekTension')) or name in ['JawOpen','LipPress']:
            sample-=mouth_shift
        delta=morph_delta(name,sample)
        # Orbital loops receive an explicit continuous closing motion. The
        # exact eyeball collision/closure is assessed in the Blink review.
        if name.startswith('Blink'):
            side=1 if name.endswith('_L') else -1
            x,y,z=vertex.co
            cx=side*.039
            envelope=math.exp(-((x-cx)/.025)**6-((z-1.165)/.020)**4)
            if y<-.03 and abs(x-cx)<.030:
                line=1.165+side*.10*(x-cx)
                delta.z=(line-z)*envelope
                delta.y=-.0018*envelope
        key.data[vertex.index].co=vertex.co+delta
attach_portable_drivers(head,rig,deformation)
report['changes'].append({'part':'Face','vertices':len(head.data.vertices),'triangles':sum(len(p.vertices)-2 for p in head.data.polygons),'removedHumanEarPatches':repaired})

# Replace floating discs with the topology that was fitted to the source lids.
# Applying the identical regional warp to eyes and lids preserves their relation.
fitted_eye_centers={}
report['opaqueEyeProjection']={}
ocular_materials,report['ocularMaterials']=create_ocular_materials()
for side in ['L','R']:
    source_matrices={part:head_matrix.inverted()@reference_world['GEO-head_animation_realistic.'+part+'.'+side] for part in ['sclera','iris']}
    report['opaqueEyeProjection'][side]=fit_opaque_eye(
        reference['GEO-head_animation_realistic.sclera.'+side],
        reference['GEO-head_animation_realistic.iris.'+side],
        source_matrices['sclera'],source_matrices['iris'],fit_head,HEAD_DROP,apply_subdivision)
    for part in ['sclera','iris']:
        obj=reference['GEO-head_animation_realistic.'+part+'.'+side]
        source_transform=source_matrices[part]
        if part=='sclera':
            center=np.asarray([tuple(source_transform.translation)])
            fitted_eye_centers[side]=Vector(fit_head(center)[0])+Vector((0,0,HEAD_DROP))
        obj.name='Nib v5 fitted '+part+' '+side
        obj.data.materials.clear();obj.data.materials.append(ocular_materials[part])
        bind(obj,'Eye_'+side)
        eye_points=np.asarray([tuple(obj.matrix_world@v.co) for v in obj.data.vertices])
        head_points=np.asarray([tuple(head.matrix_world@v.co) for v in head.data.vertices])
        if np.any(eye_points.min(axis=0)<head_points.min(axis=0)-.012) or np.any(eye_points.max(axis=0)>head_points.max(axis=0)+.012):
            raise RuntimeError('Fitted eye is detached from the facial volume: '+obj.name)
        report['changes'].append({'part':obj.name,'vertices':len(obj.data.vertices),
                                  'worldBoundsMin':eye_points.min(axis=0).tolist(),'worldBoundsMax':eye_points.max(axis=0).tolist()})

# Refit deforming facial pivots and the complete existing provisional interior
# together. Control-only facial translations remain portable scalar channels.
oral_shift=mouth_shift.copy()
oral_prefixes=('Provisional recessed oral cavity','Upper provisional gum ridge','Lower provisional gum ridge',
               'Upper provisional tooth','Lower provisional tooth','Canonical dark blue Nib tongue')
for obj in collection.objects:
    if obj.name.startswith(oral_prefixes):obj.location+=oral_shift
bpy.ops.object.select_all(action='DESELECT');rig.hide_set(False);rig.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.ops.object.mode_set(mode='EDIT')
for side,center in fitted_eye_centers.items():
    bone=rig.data.edit_bones['Eye_'+side];direction=bone.tail-bone.head
    bone.head=center;bone.tail=center+direction
for name in ['Jaw','TongueBase','TongueTip','LipUpper','LipLower','MouthCorner_L','MouthCorner_R']:
    bone=rig.data.edit_bones[name];bone.head+=oral_shift;bone.tail+=oral_shift
bpy.ops.object.mode_set(mode='OBJECT')
report['fittedEyeCentersMeters']={side:list(point) for side,point in fitted_eye_centers.items()}
report['provisionalOralShiftMeters']=list(oral_shift)
report['oralFitNote']='Retained oral meshes and Jaw/Tongue/lip pivots move by the measured old-to-new fitted seam landmark delta only. Existing HEAD_DROP is not repeated. Actual closure/interior/pose review is required.'

old_names=['Nib facial surface with eyelid and lip loops','Recessed eyeball ',
           'Amber iris ','Nib vertical pupil ','Wet eye glint ','Small triangular Nib nose',
           'Inset nostril','Fine eyebrow hair ','Fine chin fur']
for obj in list(collection.objects):
    if obj is head or obj in reference.values():continue
    if any(obj.name.startswith(prefix) for prefix in old_names):discard(obj)
    elif obj.name.startswith('Fine skin fuzz') and obj.get('bone')=='FaceSurface':discard(obj)

for obj in list(collection.objects):
    if obj.name.startswith(('Swept fine head and cheek coat','Soft inner auricle hair','Fine auricle fur')):
        discard(obj)
report['deepenedAuricleParts']=deepen_ears(collection)
groom_materials,report['groomColorRegions']=create_regions(collection)
groom=build_groom(head,collection,rig,groom_materials,args.cinematic)
for obj in groom:
    if obj.data.shape_keys:attach_portable_drivers(obj,rig,deformation)
report['cloth']=revise_cloth(collection,rig)
if args.hands:report['hands']=rebuild_hands(LIBRARY,collection,rig,discard)
report['groom']={'cinematic':args.cinematic,'guideCount':sum(int(o.get('fur_guides',0)) for o in groom),
                 'strands':sum(int(o.get('fur_strands',0)) for o in groom),
                 'triangles':sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in groom),
                 'representation':'Opaque skinned tapered strands; no simulation; identical deterministic guide field between densities.',
                 'mainStrandRadiusRangeMeters':[.000035,.000080],
                 'retainedEarCoordinatesIncludeHeadDrop':True,'goggleAvoidance':'Measured lens world centers/back bounds',
                 'groups':[{'name':o.name,'strands':int(o.get('fur_strands',0)),
                            'triangles':sum(len(p.vertices)-2 for p in o.data.polygons),
                            'materials':[m.name for m in o.data.materials]} for o in groom]}
rig.animation_data.action=None
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
scene.frame_set(1)
report['neutralCoordinates']=facial_snapshot(scene,rig,head)
rig.animation_data.action=bpy.data.actions['Idle'];scene.frame_set(1)
report['idleCoordinates']=facial_snapshot(scene,rig,head)
blockers=[pose+': '+issue for pose in ['neutralCoordinates','idleCoordinates']
          for issue in report[pose]['neutralStructuralBlockersIfClosedMouthExpected']]
report['preRenderGate']={'passed':not blockers,'blockingIssues':blockers,
                        'scope':'Sampled neutral frontal/oblique oral occlusion and visible iris; requires actual visual review too'}
scene['source_version']=args.revision+' rounded nose-leading muzzle proposal; v5d orbital/closed-neck fit retained; unaccepted'
scene['v5_reference_provenance']=json.dumps({key:report[key] for key in ['referenceLibrarySha256','referenceLicense','borrowedTopology']})
bpy.ops.wm.save_as_mainfile(filepath=str(TARGET),compress=True)
assert sha(SOURCE)==source_hash,'Pinned input was modified'
report['candidateSha256']=sha(TARGET)
report['pending']=['Inspect Side/Back ear patch silhouette','Eye and eyelid collisions/neutral mouth fit','Review scalp/ear clumps and morph-following fine facial fuzz','Review coherent hands and corrected right-hand ordering/grip' if args.hands else 'Generate and review coherent hand replacement','Review compressed scarf loops, back and action cloth fit','Final portable PBR/morph export and both-engine checks']
REPORT.write_text(json.dumps(report,indent=2),newline='\n')
print('NIB_V5_HEAD_STUDY_SAVED',str(TARGET),flush=True)
