"""Isolated concept-plane/ocular study on the reviewed mouth candidate.

Runs only after its exact input source exists and matches the source receipt.
No body, animation, bionic or shared asset changes are made here.
"""
from pathlib import Path
import sys,json,hashlib
import numpy as np
import bpy
from mathutils import Matrix
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];ART=ROOT/'benchmark/art/krag'
sys.path.insert(0,str(HERE));import anatomical_planes,ocular_surface
SOURCE=ART/'Krag_NeckScarf_v9ma_WIP.blend';RECEIPT=ART/'neck-scarf-v9ma.json';OUTPUT=ART/'Krag_FacialPlanes_v9lb_WIP.blend'
receipt=json.loads(RECEIPT.read_text());expected=receipt['source']['sha256']
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==expected
if OUTPUT.exists():raise RuntimeError('Refusing to overwrite prior facial study')
bpy.ops.wm.open_mainfile(filepath=str(SOURCE));rig=bpy.data.objects['Krag_Rig'];rig.animation_data.action=None
for p in rig.pose.bones:p.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update();modules={o.get('module'):o for o in bpy.data.objects if o.type=='MESH'and 'module'in o}
head=modules['Head'];mesh=head.data;n=len(mesh.vertices);keys=mesh.shape_keys.key_blocks
raw=np.empty(n*3,dtype=np.float32);mesh.attributes['krag_reference_position'].data.foreach_get('vector',raw);raw=raw.reshape(-1,3)
had_custom_normals=bool(mesh.has_custom_normals)
points=np.asarray([tuple(v.co)for v in keys['Basis'].data]);tags=np.zeros(n,dtype=np.uint64)
for face,tag in zip(mesh.polygons,mesh.attributes['.sculpt_face_set'].data):tags[list(face.vertices)]|=np.uint64(1)<<np.uint64(tag.value)
edges=np.asarray([tuple(e.vertices)for e in mesh.edges]);delta,report=anatomical_planes.refine(raw,points,tags,edges)
for key in keys:
    p=np.asarray([tuple(v.co)for v in key.data]);key.data.foreach_set('co',(p+delta).astype(np.float32).ravel())
mesh.vertices.foreach_set('co',(points+delta).astype(np.float32).ravel())
mesh.update()
if had_custom_normals:
    # Zero custom vectors request geometry-derived smooth loop normals.
    # Old source-space vectors must not mask the newly sculpted planes.
    mesh.normals_split_custom_set([(0.,0.,0.)]*len(mesh.loops))
    mesh.update()
report['customNormalsBeforeSculpt']=had_custom_normals
report['customNormalsResetToGeometry']=had_custom_normals
report['normalSource']='Geometry-derived smooth loop normals after the new sculpt'
oral=(tags&(np.uint64(1)<<np.uint64(7)))!=0
if np.max(np.linalg.norm(delta[oral],axis=1))>1e-9:raise RuntimeError('Oral contact topology moved')
eye_report=ocular_surface.apply(modules['Face'])
head['facial_plane_study']='v9lb: concept-brow/cheek/mandible geometry, aperture/rim protected; actual review required'
for path in [Path(__file__),HERE/'anatomical_planes.py',HERE/'ocular_surface.py',HERE.parent/'krag_iris_material.py']:
    block=bpy.data.texts.new('v9lb_face/'+path.name);block.write(path.read_text())
rig.animation_data.action=bpy.data.actions['Idle'];bpy.context.scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT),compress=True)
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==expected
result={'status':'Generated isolated facial/ocular source; actual likeness and expression review required','artisticAcceptance':False,'sharedPromotion':False,
 'input':{'path':SOURCE.relative_to(ROOT).as_posix(),'sha256':expected},'source':{'path':OUTPUT.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(OUTPUT.read_bytes()).hexdigest()},
 'planes':report,'eyes':eye_report,'preserved':['Mouth interior/real oral rim','Optical geometry','Body anatomy and rig','Actions','Current weapon','Shared exports'],
 'next':['HeadSide first: no pointed brow/chin profile','Neutral portrait and full-body proportion check','Actual Blink/OpenMouth folded-lid and oral contact review','Actual Face UV bake before runtime export']}
(ART/'facial-planes-v9lb.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n')
print('KRAG v9lb facial/ocular source saved; no acceptance or runtime export',flush=True)
