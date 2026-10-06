"""Broad topology-smoothed face study from the structural v9ma neck source.

Discard the failed v9lb local displacement field, retain its ocular material
recipe, and protect actual orbital rings plus skin/globe contact vertices.
"""
from pathlib import Path
import sys,json,hashlib
import numpy as np
import bpy
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];ART=ROOT/'benchmark/art/krag';NIB=ROOT/'benchmark/tools/nib/v5_wip'
sys.path.insert(0,str(HERE));sys.path.insert(0,str(NIB))
import geodesic_planes,ocular_surface,analyze_orbital_rings
SOURCE=ART/'Krag_NeckScarf_v9ma_WIP.blend';OUTPUT=ART/'Krag_GeodesicFace_v9lc_WIP.blend'
EXPECTED='e16545aff12b8f62bd533541adb7447b34ac245aa2bc0b2f4c4615a1f1715650'
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==EXPECTED
if OUTPUT.exists():raise RuntimeError('Refusing to overwrite an actual face study')
bpy.ops.wm.open_mainfile(filepath=str(SOURCE));rig=bpy.data.objects['Krag_Rig'];rig.animation_data.action=None
for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update();modules={o.get('module'):o for o in bpy.data.objects if o.type=='MESH'and 'module'in o}
head=modules['Head'];mesh=head.data;keys=mesh.shape_keys.key_blocks;n=len(mesh.vertices)
raw=np.empty(n*3,dtype=np.float32);mesh.attributes['krag_reference_position'].data.foreach_get('vector',raw);raw=raw.reshape(-1,3)
points=np.asarray([tuple(v.co)for v in keys['Basis'].data]);faces=[tuple(p.vertices)for p in mesh.polygons]
sets=np.asarray([v.value for v in mesh.attributes['.sculpt_face_set'].data]);edges=np.asarray([tuple(e.vertices)for e in mesh.edges])
width=max(map(len,faces));padded=np.asarray([list(f)+[f[-1]]*(width-len(f))for f in faces],dtype=np.int32)
topology=analyze_orbital_rings.analyze(raw,points,padded,sets,edges)
rings={side:eye['candidateRingVertexIds']for side,eye in topology.items()}
# Supplement ring tracing with the actual fitted ocular surfaces. The nearest
# skin contacts are fixed too; no guessed ellipse defines the protected skin.
face=modules['Face'];to_head=head.matrix_world.inverted()@face.matrix_world
eye_points=np.asarray([tuple(to_head@v.co)for v in face.data.vertices]);contacts=[];contact_report={}
for side in ['L','R']:
    group=face.vertex_groups.get('Eye_'+side)
    if group is None:raise RuntimeError('Missing actual ocular skin group')
    selected=np.zeros(len(eye_points),dtype=bool)
    for vertex in face.data.vertices:selected[vertex.index]=any(w.group==group.index and w.weight>.99 for w in vertex.groups)
    eye_faces=[tuple(p.vertices)for p in face.data.polygons if np.all(selected[list(p.vertices)])]
    if not eye_faces:raise RuntimeError('No actual ocular surface for '+side)
    tree=BVHTree.FromPolygons([Vector(p)for p in eye_points],eye_faces)
    lo=eye_points[selected].min(0)-.006;hi=eye_points[selected].max(0)+.006
    candidates=np.flatnonzero(np.all((points>=lo)&(points<=hi),axis=1));local=[];gaps=[]
    for index in candidates:
        closest,normal,face_index,distance=tree.find_nearest(Vector(points[index]))
        if distance<.003:local.append(int(index));gaps.append(float(distance))
    if not local:raise RuntimeError('Actual globe/head contact band is empty on '+side)
    contacts.extend(local);contact_report[side]={'vertices':len(local),'distanceBandMeters':.003,'maxNearestDistanceMeters':max(gaps),'ringVertices':len(rings[side])}
delta,report=geodesic_planes.refine(raw,points,faces,sets,edges,rings,contacts)
had_custom_normals=bool(mesh.has_custom_normals)
for key in keys:
    prior=np.asarray([tuple(v.co)for v in key.data]);key.data.foreach_set('co',(prior+delta).astype(np.float32).ravel())
mesh.vertices.foreach_set('co',(points+delta).astype(np.float32).ravel());mesh.update()
if had_custom_normals:mesh.normals_split_custom_set([(0.,0.,0.)]*len(mesh.loops));mesh.update()
report['customNormalsBeforeSculpt']=had_custom_normals;report['actualGlobeContactAnchors']=contact_report
eye_report=ocular_surface.apply(face)
for path in [Path(__file__),HERE/'geodesic_planes.py',HERE/'ocular_surface.py',NIB/'analyze_orbital_rings.py']:
    block=bpy.data.texts.new('v9lc_face/'+path.name);block.write(path.read_text())
rig.animation_data.action=bpy.data.actions['Idle'];bpy.context.scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT),compress=True)
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==EXPECTED
result={'status':'Actual broad topology-based face source; profile and full expression review required','artisticAcceptance':False,'sharedPromotion':False,
 'input':{'path':SOURCE.relative_to(ROOT).as_posix(),'sha256':EXPECTED},'source':{'path':OUTPUT.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(OUTPUT.read_bytes()).hexdigest()},
 'planes':report,'eyes':eye_report,'knownUnchangedFailures':['Tight v9ma scarf/side knot','Tusk root/lip emergence','Remaining clothing/armor likeness'],
 'preserved':['Actual repaired Body neck','Body coordinates/rig/actions','Real oral rim/interior','Fitted ocular geometry','Current weapon','Shared exports']}
(ART/'geodesic-face-v9lc.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n')
print('KRAG v9lc source saved; actual profile gate required',flush=True)
