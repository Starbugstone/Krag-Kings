"""Prepared isolated semantic axilla repair on an explicitly pinned coherent source.

The same original-topology field controls fit and skin. Retains all rig/actions,
clothing, hands, head, ear cards and materials. Source and output must differ.
Reopens its save to verify retention; actual raised-arm views remain mandatory.
"""
import argparse,hashlib,json,sys,math
from pathlib import Path
import bpy,numpy as np
from mathutils import Matrix,Vector
from bpy_extras.anim_utils import action_get_channelbag_for_slot
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sys.path[:0]=[str(HERE),str(HERE.parent),str(ROOT/'benchmark/tools/krag')]
from anatomical_body_fit import crop,weights
from anatomical_domain_v2 import solve,warp
from nib_animation import body_correctives
from runtime_reduction import attach_portable_drivers
parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,required=True);parser.add_argument('--source-sha256',required=True);parser.add_argument('--output-dir',type=Path,required=True)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:]);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if sha(args.source)!=args.source_sha256:raise RuntimeError('Pinned coherent source changed')
TARGET=args.output_dir/'Nib_Coherent_SemanticBody_v2.blend';REPORT=args.output_dir/'source.json'
if TARGET.exists() or REPORT.exists():raise RuntimeError('Preserve previous semantic body source')
if not args.output_dir.resolve().is_relative_to((ROOT/'benchmark/art/nib').resolve()):raise RuntimeError('Owned isolated art output required')
args.output_dir.mkdir(parents=True,exist_ok=True);bpy.ops.wm.open_mainfile(filepath=str(args.source),load_ui=False)
scene=bpy.context.scene;rig=bpy.data.objects['Nib_Rig'];collection=bpy.data.collections['Nib_Authored_Components']
CANONICAL=['Idle','Walk','Run','Melee','Shoot','Hit','FacePerformance']
if any(name not in bpy.data.actions for name in CANONICAL):raise RuntimeError('Source lacks saved canonical actions')
for name in CANONICAL:bpy.data.actions[name].use_fake_user=True

def rig_contract():
    original=rig.animation_data.action;actions={}
    for action in bpy.data.actions:
        rig.animation_data.action=action;bag=action_get_channelbag_for_slot(action,rig.animation_data.action_slot)
        if bag is None:continue
        rows=[(c.data_path,c.array_index,c.extrapolation,[(tuple(k.co),tuple(k.handle_left),tuple(k.handle_right),k.interpolation,k.handle_left_type,k.handle_right_type,k.easing,k.amplitude,k.back,k.period) for k in c.keyframe_points]) for c in bag.fcurves]
        actions[action.name]=hashlib.sha256(json.dumps({'frameRange':list(action.frame_range),'curves':sorted(rows)},separators=(',',':')).encode()).hexdigest()
    rig.animation_data.action=original
    return {'world':[list(r) for r in rig.matrix_world],'bones':{b.name:{'matrix':[list(r) for r in b.matrix_local],'parent':b.parent.name if b.parent else None,'connected':b.use_connect,'rotationMode':rig.pose.bones[b.name].rotation_mode} for b in rig.data.bones},'actions':actions}

def surface_hash(obj):
    h=hashlib.sha256();m=obj.data;v=np.empty(len(m.vertices)*3,np.float32);m.vertices.foreach_get('co',v);h.update(v.tobytes())
    for key in m.shape_keys.key_blocks if m.shape_keys else []:key.data.foreach_get('co',v);h.update(key.name.encode());h.update(v.tobytes())
    for uv in m.uv_layers:
        values=np.empty(len(uv.data)*2,np.float32);uv.data.foreach_get('uv',values);h.update(uv.name.encode());h.update(values.tobytes())
    payload={'faces':[(list(p.vertices),p.material_index) for p in m.polygons],'groups':[g.name for g in obj.vertex_groups],'weights':[[(g.group,g.weight) for g in v.groups] for v in m.vertices],'materials':[m.name if m else None for m in m.materials],'basis':[list(r) for r in obj.matrix_basis],'parentInverse':[list(r) for r in obj.matrix_parent_inverse],'parent':obj.parent.name if obj.parent else None,'parentType':obj.parent_type,'parentBone':obj.parent_bone}
    h.update(json.dumps(payload,separators=(',',':')).encode());return h.hexdigest()

before_rig=rig_contract();rig.animation_data.action=None
for track in rig.animation_data.nla_tracks:track.mute=True
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
scene.frame_set(1);bpy.context.view_layer.update()
body=bpy.data.objects['Continuous Nib anatomy organic'];fuzz=bpy.data.objects['Fine skin fuzz organic']
retained={o.name:surface_hash(o) for o in bpy.data.objects if o.type=='MESH' and o not in [body,fuzz]}
if body.data.has_custom_normals:raise RuntimeError('Body has custom normals; explicit preservation/refit must be authored first')
LIBRARY=ROOT/'benchmark/art/reference-anatomy/blender-studio-human-base-meshes/source/human-base-meshes-bundle-v1.4.1/human_base_meshes_bundle.blend'
if sha(LIBRARY)!='3c121505651140ceb4d69fd1d8923f7788ffadd81672f5be14845a5f2c75c137':raise RuntimeError('Licensed reference changed')
with bpy.data.libraries.load(str(LIBRARY),link=False) as (available,loaded):loaded.objects=['GEO-body_male_realistic']
reference=loaded.objects[0];raw=np.asarray([v.co[:] for v in reference.data.vertices],float);original=[list(p.vertices) for p in reference.data.polygons];attr=reference.data.attributes.get('.sculpt_face_set')
if attr is None:raise RuntimeError('Original anatomical face sets missing')
sets=np.asarray([v.value for v in attr.data],int);used,faces=crop(raw,original);lookup={tuple(f):i for i,f in enumerate(original)};face_ids=np.asarray([lookup[tuple(int(used[i]) for i in f)] for f in faces]);source=raw[used];domain,domain_report=solve(source,faces,sets[face_ids]);points=warp(source,domain)
# Identical original crop/order and Catmull-Clark construction retain point
# identity. The only changed source component is the coherent anatomical fit.
mesh=bpy.data.meshes.new('Nib semantic shoulder control cage');mesh.from_pydata(points,[],faces);mesh.update()
a=mesh.attributes.new('Nib_BodyReferencePosition','FLOAT_VECTOR','POINT');a.data.foreach_set('vector',source.astype(np.float32).ravel())
a=mesh.attributes.new('Nib_ArmDomain','FLOAT','POINT');a.data.foreach_set('value',domain.astype(np.float32))
cage=bpy.data.objects.new('EDITABLE Nib semantic shoulder control cage v2',mesh);scene.collection.objects.link(cage)
control=cage.copy();control.data=mesh.copy();control.name='EDITABLE Nib semantic shoulder domain cage v2';scene.collection.objects.link(control);control.hide_render=True;control.hide_set(True)
bpy.ops.object.select_all(action='DESELECT');cage.select_set(True);bpy.context.view_layer.objects.active=cage;modifier=cage.modifiers.new('Same anatomical subdivision','SUBSURF');modifier.levels=2;modifier.render_levels=2;bpy.ops.object.modifier_apply(modifier=modifier.name)
old=np.asarray([v.co[:] for v in body.data.shape_keys.key_blocks['Basis'].data],float);new=np.asarray([v.co[:] for v in cage.data.vertices],float)
if new.shape!=old.shape or [tuple(p.vertices) for p in cage.data.polygons]!=[tuple(p.vertices) for p in body.data.polygons]:raise RuntimeError('Semantic regeneration changed surface topology/order')
old_reference=np.asarray([v.vector[:] for v in body.data.attributes['Nib_BodyReferencePosition'].data],float);new_reference=np.asarray([v.vector[:] for v in cage.data.attributes['Nib_BodyReferencePosition'].data],float)
reference_error=float(np.linalg.norm(old_reference-new_reference,axis=1).max())
if reference_error>1e-7:raise RuntimeError('Semantic body point correspondence changed')
field=np.asarray([v.value for v in cage.data.attributes['Nib_ArmDomain'].data],float)
delta=new-old
if np.linalg.norm(delta,axis=1).max()>.020:raise RuntimeError('Native fit exceeds measured bounded cage change')
body.data.calc_loop_triangles();triangles=np.asarray([t.vertices[:] for t in body.data.loop_triangles],int)
old_faces=old[triangles];new_faces=new[triangles];old_cross=np.cross(old_faces[:,1]-old_faces[:,0],old_faces[:,2]-old_faces[:,0]);new_cross=np.cross(new_faces[:,1]-new_faces[:,0],new_faces[:,2]-new_faces[:,0]);area=np.linalg.norm(new_cross,axis=1);old_area=np.linalg.norm(old_cross,axis=1);normal_dot=np.sum(old_cross*new_cross,axis=1)/np.maximum(area*old_area,1e-20)
if np.any(area<=1e-12) or np.any(normal_dot<=0):raise RuntimeError('Semantic native fit degenerates/inverts surface')
old_keys={key.name for key in body.data.shape_keys.key_blocks};body.data.shape_keys.animation_data_clear()
for key in list(body.data.shape_keys.key_blocks):
    if key.name.startswith('Corrective_'):body.shape_key_remove(key)
    else:
        values=np.asarray([v.co[:] for v in key.data],float)+delta;key.data.foreach_set('co',values.astype(np.float32).ravel())
body.data.vertices.foreach_set('co',new.astype(np.float32).ravel());body.data.attributes['Nib_ArmDomain'].data.foreach_set('value',field.astype(np.float32));body.data.update()
bones={n:[tuple(rig.data.bones[n].head_local),tuple(rig.data.bones[n].tail_local)] for side in ['L','R'] for n in ['UpperArm_'+side,'LowerArm_'+side]};skin=weights(new,field,bones)
def assign(obj,values):
    obj.vertex_groups.clear()
    for name,array in values.items():
        group=obj.vertex_groups.new(name=name)
        for i,value in enumerate(array):
            if value>1e-8:group.add([i],float(value),'REPLACE')
assign(body,skin);body_correctives([body]);contract=json.loads(scene['deformation_contract']);attach_portable_drivers(body,rig,contract)
if {key.name for key in body.data.shape_keys.key_blocks}!=old_keys:raise RuntimeError('Body corrective target set changed')
# Recreate the original deterministic surface correspondence; verify before
# moving fine fuzz, then recompute its roots/normal flow/weights/correctives.
center=old[triangles].mean(1);eligible=(abs(center[:,0])>.126)|(center[:,2]>.979);root_triangles=triangles[eligible];q=old[root_triangles];cross=np.cross(q[:,1]-q[:,0],q[:,2]-q[:,0]);areas=np.linalg.norm(cross,axis=1);valid=areas>1e-12;root_triangles=root_triangles[valid];cross=cross[valid];areas=areas[valid]
rng=np.random.default_rng(417731);chosen=rng.choice(len(root_triangles),2300,p=areas/areas.sum());root_triangles=root_triangles[chosen];random_uv=rng.random((2300,2));u=np.sqrt(random_uv[:,0]);bary=np.column_stack((1-u,u*(1-random_uv[:,1]),u*random_uv[:,1]));radii_lengths=[(float(rng.uniform(.000025,.000055)),float(rng.uniform(.001,.0025))) for _ in range(2300)]
def make_fuzz(surface):
    q=surface[root_triangles];root=np.sum(q*bary[:,:,None],1);normal=np.cross(q[:,1]-q[:,0],q[:,2]-q[:,0]);normal/=np.linalg.norm(normal,axis=1)[:,None];vertices=[]
    for i,(p,n) in enumerate(zip(root,normal)):
        direction=Vector(n)+Vector((0,0,-.30));direction.normalize();axis=direction.cross(Vector((0,1,0)))
        if axis.length<1e-5:axis=direction.cross(Vector((1,0,0)))
        axis.normalize();other=direction.cross(axis).normalized();radius,length=radii_lengths[i]
        for ring in range(2):
            c=Vector(p)+Vector(n)*.00005+direction*(length*ring)
            for k in range(3):
                angle=k*math.tau/3;r=radius if ring==0 else .000002;vertices.append(tuple(c+(axis*math.cos(angle)+other*math.sin(angle))*r))
    return np.asarray(vertices,float)
old_fuzz=np.asarray([v.co[:] for v in fuzz.data.shape_keys.key_blocks['Basis'].data],float);rebuilt=make_fuzz(old)
if old_fuzz.shape!=rebuilt.shape:raise RuntimeError('Body fuzz no longer has the original deterministic construction')
fuzz_error=float(np.linalg.norm(rebuilt-old_fuzz,axis=1).max())
if fuzz_error>2e-7:raise RuntimeError('Original fine-fuzz correspondence did not reproduce saved geometry: '+str(fuzz_error))
new_fuzz=make_fuzz(new);fuzz.data.shape_keys.animation_data_clear();fuzz.data.vertices.foreach_set('co',new_fuzz.astype(np.float32).ravel());root_ids=np.repeat(np.arange(2300),6)
for key in fuzz.data.shape_keys.key_blocks:
    if key.name=='Basis':values=new_fuzz
    else:
        body_key=body.data.shape_keys.key_blocks.get(key.name)
        if body_key is None:raise RuntimeError('Fine fuzz target lacks matching Body target')
        morph=np.asarray([v.co[:] for v in body_key.data],float)-new;root_delta=np.sum(morph[root_triangles]*bary[:,:,None],1);values=new_fuzz+root_delta[root_ids]
    key.data.foreach_set('co',values.astype(np.float32).ravel())
fuzz.data.update();assign(fuzz,{name:np.sum(values[root_triangles]*bary,1)[root_ids] for name,values in skin.items()});attach_portable_drivers(fuzz,rig,contract)
# Dispose only temporary loaded/evaluated objects; retain the new editable cage.
for obj in [cage,reference]:
    data=obj.data;bpy.data.objects.remove(obj,do_unlink=True)
    if data.users==0:bpy.data.meshes.remove(data)
for name,digest in retained.items():
    if surface_hash(bpy.data.objects[name])!=digest:raise RuntimeError('Body repair changed unrelated mesh '+name)
if rig_contract()!=before_rig:raise RuntimeError('Body repair changed rig/action contract')
body_hash=surface_hash(body);fuzz_hash=surface_hash(fuzz);rig.animation_data.action=bpy.data.actions['Idle'];scene.frame_set(1)
scene['nib_semantic_body_repair']=json.dumps({'sourceSha256':args.source_sha256,'field':'original face-set arm/thorax geodesic shared by fitting and skinning','anatomicalFaceSets':[11,12,20,21],'artisticAcceptance':False})
scene['source_version']='Coherent Nib semantic Natural body v2; inherited face, ear, groom and clothing failures retained'
for name in ['repair_semantic_body.py','anatomical_domain_v2.py']:
    block=bpy.data.texts.new('Nib semantic body v2 '+name);block.write((HERE/name).read_text())
bpy.ops.wm.save_as_mainfile(filepath=str(TARGET),compress=True)
# Actual saved-data readback prevents in-memory-only action retention claims.
bpy.ops.wm.open_mainfile(filepath=str(TARGET),load_ui=False);rig=bpy.data.objects['Nib_Rig'];scene=bpy.context.scene
if any(name not in bpy.data.actions for name in CANONICAL):raise RuntimeError('Saved semantic source lost a canonical action')
if rig_contract()!=before_rig:raise RuntimeError('Saved semantic source rig/actions differ')
for name,digest in retained.items():
    if surface_hash(bpy.data.objects[name])!=digest:raise RuntimeError('Saved unrelated mesh differs '+name)
if surface_hash(bpy.data.objects['Continuous Nib anatomy organic'])!=body_hash or surface_hash(bpy.data.objects['Fine skin fuzz organic'])!=fuzz_hash:raise RuntimeError('Saved Body/fuzz payload differs')
if sha(args.source)!=args.source_sha256:raise RuntimeError('Input source changed')
report={'status':'Actual isolated semantic body source; raised-arm/cloth/engine review required','source':str(args.source),'sourceSha256':args.source_sha256,'candidate':str(TARGET),'candidateSha256':sha(TARGET),'field':domain_report,'surfaceVertices':len(new),'triangles':len(triangles),'maximumFitChangeMeters':float(np.linalg.norm(delta,axis=1).max()),'minimumAreaRatio':float((area/old_area).min()),'minimumNormalDotWithOld':float(normal_dot.min()),'originalPointCorrespondenceMaxErrorMeters':reference_error,'originalFineFuzzReconstructionMaxErrorMeters':fuzz_error,'fuzzRoots':2300,'maximumInfluences':int(np.count_nonzero(np.stack(list(skin.values()),1)>1e-8,axis=1).max()),'preservedRig':before_rig,'retainedMeshHashes':retained,'retainedMeshCount':len(retained),'bodyPayloadSha256':body_hash,'fuzzPayloadSha256':fuzz_hash,'savedSourceReopened':True,'savedCanonicalActionsPresent':CANONICAL,'preRenderGate':{'passed':False,'status':'Inherited face/cloth/groom failures remain explicit; diagnostic body review only'},'artisticAcceptance':False,'sharedChanged':False,'variantScope':'Natural connected Body only; legacy restorative Grip body still requires coherent partition','codeSha256':{p.name:sha(p) for p in [Path(__file__),HERE/'anatomical_domain_v2.py',HERE/'anatomical_body_fit.py',HERE.parent/'nib_animation.py']},'pending':['Actual Shoot/raised-arm silhouette and pose deformation','Shirt/bib/strap clearance after bounded Body fit','Natural gait and arm travel','Restorative Body partition and actual variant checks']}
REPORT.write_text(json.dumps(report,indent=2)+'\n',newline='\n');print('NIB_SEMANTIC_BODY_SOURCE_SAVED_AND_REOPENED',flush=True)
