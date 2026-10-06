"""Isolated coherent macro face correction; keep body bind/motion and equipment."""
from pathlib import Path
import sys,json,hashlib
import numpy as np
import bpy
from mathutils import Matrix,Vector
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];ART=ROOT/'benchmark/art/krag'
sys.path.insert(0,str(HERE));from anatomical_planes_v9nc import Envelope,surface_report
SOURCE=ART/'Krag_MacroFace_v9nb_WIP.blend';EXPECTED='82cde1e66b94804e8cfbff47ed2f48ea7a40daad23c0658bfdc509ab59e3f8e7'
OUTPUT=ART/'Krag_MacroFace_v9nc_WIP.blend'
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==EXPECTED
if OUTPUT.exists():raise RuntimeError('Refusing to overwrite an actual macro face study')
bpy.ops.wm.open_mainfile(filepath=str(SOURCE));rig=bpy.data.objects['Krag_Rig'];rig.animation_data.action=None
for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update()
modules={o.get('module'):o for o in bpy.data.objects if o.type=='MESH'and o.get('module')}
affected=[modules[k]for k in ['Head','Face','MouthInterior']];head=modules['Head'];face=modules['Face']
facial={b.name for b in rig.data.bones if b.name=='FaceRoot'or any(p.name=='FaceRoot'for p in b.parent_recursive)}
if not {'Jaw','Eye_L','Eye_R','Tongue_01','Tongue_02'}.issubset(facial):raise RuntimeError('Actual facial subtree does not contain required articulation')

def coords(mesh,key='Basis'):
    data=mesh.shape_keys.key_blocks[key].data if mesh.shape_keys else mesh.vertices
    p=np.empty(len(data)*3,dtype=np.float32);data.foreach_get('co',p);return p.reshape(-1,3).astype(np.float64)

def world(obj,p):
    m=np.asarray(obj.matrix_world,dtype=float);return p@m[:3,:3].T+m[:3,3]

def local(obj,p):
    m=np.asarray(obj.matrix_world.inverted(),dtype=float);return p@m[:3,:3].T+m[:3,3]

def fingerprint():
    h=hashlib.sha256()
    for o in sorted((o for o in modules.values()if o not in affected),key=lambda o:o.name):
        h.update(o.name.encode());h.update(coords(o.data).astype(np.float32).tobytes())
        if o.data.shape_keys:
            for k in o.data.shape_keys.key_blocks:h.update(k.name.encode());h.update(coords(o.data,k.name).astype(np.float32).tobytes())
    for b in rig.data.bones:
        if b.name not in facial:h.update(b.name.encode());h.update(np.asarray(b.matrix_local,dtype=float).tobytes())
    for action in sorted(bpy.data.actions,key=lambda a:a.name):
        h.update(action.name.encode())
        for layer in action.layers:
            for strip in layer.strips:
                for slot in action.slots:
                    bag=strip.channelbag(slot)
                    if bag:
                        for curve in bag.fcurves:
                            h.update(curve.data_path.encode());h.update(str(curve.array_index).encode())
                            for key in curve.keyframe_points:h.update(np.asarray(key.co,dtype=float).tobytes())
    return h.hexdigest()

before=fingerprint();head_points=world(head,coords(head.data));face_points=world(face,coords(face.data))
sets=head.data.attributes['.sculpt_face_set'];membership=np.zeros(len(head_points),dtype=np.uint64)
for p in head.data.polygons:membership[list(p.vertices)]|=np.uint64(1)<<np.uint64(sets.data[p.index].value)
member=lambda s:(membership&(np.uint64(1)<<np.uint64(s)))!=0
rim=member(24)&member(7)
if rim.sum()<30:raise RuntimeError('Actual lower oral rim semantics are missing')
lip=head_points[rim].mean(0)
nose_points=head_points[member(11)];anterior=nose_points[nose_points[:,1]<=np.quantile(nose_points[:,1],.20)];nose=anterior.mean(0)
eye_centers=[];eye_radii=[];eye_vertices=[]
for name in ['Eye_L','Eye_R']:
    center=np.asarray(rig.matrix_world@rig.data.bones[name].head_local,dtype=float);index=face.vertex_groups[name].index
    ids=np.asarray([v.index for v in face.data.vertices if any(g.group==index and g.weight>.99 for g in v.groups)],dtype=int)
    if len(ids)<100:raise RuntimeError('Actual weighted ocular geometry missing for '+name)
    radius=float(np.linalg.norm(face_points[ids]-center,axis=1).max())
    eye_centers.append(center);eye_radii.append(radius);eye_vertices.append(ids)
envelope=Envelope(eye_centers,eye_radii,lip,nose,head_points=head_points)
head_after=envelope.transform(head_points);head.data.calc_loop_triangles();tri=np.asarray([t.vertices[:]for t in head.data.loop_triangles],dtype=int)
metrics=surface_report(head_points,head_after,tri)
if metrics['maxDisplacementMeters']>.035:raise RuntimeError('Macro envelope exceeds35mm source-change bound')
probe=head_points[np.linspace(0,len(head_points)-1,min(6000,len(head_points)),dtype=int)]
metrics.update(envelope.jacobian_report(probe))
eye_error=[]
for center,ids,shift in zip(eye_centers,eye_vertices,envelope.eye_moves):
    error=float(np.linalg.norm(envelope.transform(face_points[ids])-face_points[ids]-shift,axis=1).max());eye_error.append(error)
    if error>1e-6:raise RuntimeError('Coherent ocular neighborhood distorted the actual globe instead of translating it')
changed=[]
for obj in affected:
    mesh=obj.data;basis=world(obj,coords(mesh));after=envelope.transform(basis)
    for key in mesh.shape_keys.key_blocks if mesh.shape_keys else []:
        old=world(obj,coords(mesh,key.name));new=local(obj,envelope.transform(old));key.data.foreach_set('co',new.astype(np.float32).ravel())
    mesh.vertices.foreach_set('co',local(obj,after).astype(np.float32).ravel());mesh.update()
    if mesh.has_custom_normals:mesh.normals_split_custom_set([(0.,0.,0.)]*len(mesh.loops));mesh.update()
    changed.append({'module':obj['module'],'vertices':len(mesh.vertices),'shapeKeys':len(mesh.shape_keys.key_blocks)if mesh.shape_keys else 0,'maximumDisplacementMeters':float(np.linalg.norm(after-basis,axis=1).max())})
# Translate each facial pivot and retain its authored local axis/length. Body
# bones including Head remain exact; no body motion keys are reauthored here.
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig;bpy.ops.object.mode_set(mode='EDIT')
rig_inverse=rig.matrix_world.inverted();pivot_changes=[]
rest={name:(rig.data.edit_bones[name].head.copy(),rig.data.edit_bones[name].tail.copy(),rig.data.edit_bones[name].use_connect)for name in facial}
for name in facial:rig.data.edit_bones[name].use_connect=False
for name in sorted(facial):
    bone=rig.data.edit_bones[name];old_head,old_tail,was_connected=rest[name]
    prior=np.asarray(rig.matrix_world@old_head,dtype=float);delta=envelope.delta(prior)[0]
    shift=rig_inverse.to_3x3()@Vector(delta);bone.head=old_head+shift;bone.tail=old_tail+shift
    pivot_changes.append({'bone':name,'beforeHeadWorld':prior.tolist(),'translationMeters':delta.tolist(),'retainedAxisAndLength':True,'wasConnected':bool(was_connected)})
bpy.ops.object.mode_set(mode='OBJECT');bpy.context.view_layer.update()
assert fingerprint()==before,'Macro face changed body bind/actions or unrelated equipment geometry'
for path in [Path(__file__),HERE/'anatomical_planes_v9nc.py']:
    block=bpy.data.texts.new('v9nc_macro_face/'+path.name);block.write(path.read_text())
rig.animation_data.action=bpy.data.actions['Idle'];bpy.context.scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT),compress=True)
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==EXPECTED
result={'status':'Actual macro facial source; profile/likeness and expression reviews required','artisticAcceptance':False,'sharedPromotion':False,
 'input':{'path':SOURCE.relative_to(ROOT).as_posix(),'sha256':EXPECTED},'source':{'path':OUTPUT.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(OUTPUT.read_bytes()).hexdigest()},
 'inputChoice':'Actual v9nb macro source; broad plane pass without global head scaling, retained buried tusks remain a known fit task',
 'landmarksWorld':{'eyes':np.asarray(eye_centers).tolist(),'eyeRadii':eye_radii,'lowerOralRimMean':lip.tolist(),'nasalFrontMean':nose.tolist()},
 'method':'Measured continuous brow/cheek/mandibular planes, soft nasolabial separation and compact lip shaping; same field moves oral/ocular shapes and facial pivots',
 'neutralHeadMetrics':metrics,'measuredFacialPlanesY':envelope.planes,'planeMeasurementVertexCounts':envelope.measurement_counts,'ocularRigidTranslationMaximumErrorMeters':eye_error,'changedModules':changed,'facialPivotChanges':pivot_changes,
 'preservedBodyBindActionsEquipmentFingerprint':before,'bodyBindAndActionCurvesChanged':False,
 'pending':['Actual profile and portrait concept likeness','Normal opening and lid/gaze contact after moved facial pivots','Short natural tusks refitted only after macro envelope passes','Cowl construction, garments/armor/material realism','Final expression corrective and runtime export verification']}
(ART/'macro-face-v9nc.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n')
print('Krag v9nc macro facial source saved; actual side/portrait/expressions require review',flush=True)
