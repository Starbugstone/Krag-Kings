"""Separate native Nib facial-topology study; never overwrites pinned outputs.

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
from fit_head import fit_head
from nib_face import FACIAL_MORPHS, morph_delta, smoothstep
from runtime_reduction import attach_portable_drivers
from nib_groom_v5 import build_groom
from nib_cloth_v5 import revise_cloth
from nib_hand_v5 import rebuild_hands

parser=argparse.ArgumentParser()
parser.add_argument('--source',type=Path,default=ART/'Nib_Runtime_Optimized_v4b.blend')
parser.add_argument('--cinematic',action='store_true')
parser.add_argument('--hands',action='store_true')
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
SOURCE=args.source
TARGET=ART/('Nib_Cinematic_v5_WIP.blend' if args.cinematic else 'Nib_Master_v5_WIP.blend')
REPORT=ART/'v5-study'/('native-head-cinematic-v5.json' if args.cinematic else 'native-head-v5.json')
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
head=reference['GEO-head_animation_realistic'];head_matrix=head.matrix_world.copy()
source_vertices=np.asarray([tuple(v.co) for v in head.data.vertices],dtype=float)
for obj in reference.values():
    for c in list(obj.users_collection):c.objects.unlink(obj)
    collection.objects.link(obj)
    obj.modifiers.clear()
    obj.vertex_groups.clear()

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
# Suppress the human chin and philtrum while keeping cheek/lip continuity.
front=np.clip((-original[:,1]-.015)/.05,0,1)
chin=np.exp(-((original[:,2]-.184)/.026)**2)*front
fitted[:,0]*=1-.10*chin
fitted[:,1]+=.004*chin
# Lower nasal tip becomes the compact, downward triangular feline leather pad.
nose=np.exp(-(original[:,0]/.025)**4-((original[:,2]-.263)/.017)**4)*front
fitted[:,0]*=1-.13*nose*np.clip((.266-original[:,2])/.015,0,1)
head.data.vertices.foreach_set('co',fitted.astype(np.float32).ravel())
head.matrix_world=Matrix.Translation((0,0,HEAD_DROP))
setmaterial(head,'Nib_Skin','Nib_EarInner','Nib_MouthInterior')
for polygon in head.data.polygons:
    center=original[list(polygon.vertices)].mean(0)
    if abs(center[0])<.023 and .247<center[2]<.276 and center[1]<-.137:polygon.material_index=1
    if abs(center[0])<.038 and .222<center[2]<.249 and center[1]>-.088:polygon.material_index=2
apply_subdivision(head,2)
bind(head,None)
headgroup=head.vertex_groups.new(name='Head');jawgroup=head.vertex_groups.new(name='Jaw')
for v in head.data.vertices:
    x,y,z=v.co
    jaw=(1-smoothstep(1.104,1.135,z))*max(0,min(1,(-y+.004)/.043))
    # The source mouth has separate upper/lower interior loops. A narrow seam
    # preserves lip closure during smiles; Jaw opens the lower lip and chin.
    if abs(x)<.05 and y<-.05 and 1.102<z<1.119:
        seam=1.110+.0015*(x/.045)**3
        jaw=1-smoothstep(seam-.0012,seam+.0012,z)
    if jaw<1:headgroup.add([v.index],1-jaw,'REPLACE')
    if jaw>0:jawgroup.add([v.index],jaw,'REPLACE')
head.shape_key_add(name='Basis')
for name in FACIAL_MORPHS:
    key=head.shape_key_add(name=name)
    for vertex in head.data.vertices:
        delta=morph_delta(name,vertex.co)
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
for side in ['L','R']:
    for part in ['sclera','iris']:
        obj=reference['GEO-head_animation_realistic.'+part+'.'+side]
        source_transform=head_matrix.inverted()@obj.matrix_world
        if part=='iris':
            for vertex in obj.data.vertices:
                x,y,z=vertex.co;radius=math.sqrt(x*x+z*z)
                weight=1-smoothstep(.0023,.006,radius)
                vertex.co.x*=1-.55*weight;vertex.co.z*=1+.65*weight
        points=np.asarray([tuple(source_transform@v.co) for v in obj.data.vertices],dtype=float)
        transformed=fit_head(points)
        obj.data.vertices.foreach_set('co',transformed.astype(np.float32).ravel())
        obj.matrix_world=Matrix.Translation((0,0,HEAD_DROP))
        obj.name='Nib v5 fitted '+part+' '+side
        setmaterial(obj,'Nib_Dark' if part=='sclera' else 'Nib_Eye')
        apply_subdivision(obj,1);bind(obj,'Eye_'+side)
        report['changes'].append({'part':obj.name,'vertices':len(obj.data.vertices)})

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
groom=build_groom(head,collection,rig,bpy.data.materials['Nib_Hair'],args.cinematic)
report['cloth']=revise_cloth(collection,rig)
if args.hands:report['hands']=rebuild_hands(LIBRARY,collection,rig,discard)
report['groom']={'cinematic':args.cinematic,'guideCount':sum(int(o.get('fur_guides',0)) for o in groom),
                 'strands':sum(int(o.get('fur_strands',0)) for o in groom),
                 'triangles':sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in groom),
                 'representation':'Opaque skinned tapered strands; no simulation; identical deterministic guide field between densities.'}
rig.animation_data.action=bpy.data.actions['Idle'];scene.frame_set(1)
scene['source_version']='v5 fitted animation-head topology study; unaccepted'
scene['v5_reference_provenance']=json.dumps({key:report[key] for key in ['referenceLibrarySha256','referenceLicense','borrowedTopology']})
bpy.ops.wm.save_as_mainfile(filepath=str(TARGET),compress=True)
assert sha(SOURCE)==source_hash,'Pinned input was modified'
report['candidateSha256']=sha(TARGET)
report['pending']=['Inspect Side/Back ear patch silhouette','Eye and eyelid collisions/neutral mouth fit','Review new scalp-bound groom and reattach fine facial fuzz','Right-hand anatomical ordering and coherent topology','Review compressed scarf loops, back and action cloth fit','Final portable PBR/morph export and both-engine checks']
REPORT.write_text(json.dumps(report,indent=2))
print('NIB_V5_HEAD_STUDY_SAVED',str(TARGET),flush=True)
