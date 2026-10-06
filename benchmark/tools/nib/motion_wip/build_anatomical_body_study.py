"""Isolated v5i anatomical-body/twist study. Never writes shared runtime files.

Reference shoulders/elbows remain connected. Existing head, hands, facial
targets, ears and actions are preserved. Root must retarget fresh body clips
onto the extended skeleton before any runtime export is considered.
"""
import hashlib,json,sys,random,math
from pathlib import Path
import bpy
import numpy as np
from mathutils import Matrix,Vector

HERE=Path(__file__).parent;ROOT=HERE.parents[3]
sys.path[:0]=[str(HERE),str(HERE.parent),str(ROOT/'benchmark/tools/krag')]
from anatomical_body_fit import crop,warp,weights
from forearm_twist import install,split_existing_weights
import krag_skin_domains
from nib_animation import body_correctives
from runtime_reduction import attach_portable_drivers

ART=ROOT/'benchmark/art/nib/motion-study'
SOURCE=ROOT/'benchmark/art/nib/Nib_Master_v5i_OrbitalClosure_WIP.blend'
EXPECTED='f103eb11e67c412a55753e3a21de491d79ac69f3db1247d3cc2d250995e0b40b'
TARGET=ROOT/'benchmark/art/nib/Nib_AnatomicalBodyStudy_v1.blend'
OUT=ART/'anatomical-body-v1.json'
LIBRARY=ROOT/'benchmark/art/reference-anatomy/blender-studio-human-base-meshes/source/human-base-meshes-bundle-v1.4.1/human_base_meshes_bundle.blend'
LIBRARY_SHA='3c121505651140ceb4d69fd1d8923f7788ffadd81672f5be14845a5f2c75c137'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if sha(SOURCE)!=EXPECTED or sha(LIBRARY)!=LIBRARY_SHA:raise RuntimeError('Pinned source/library changed')
if TARGET.exists() or OUT.exists():raise RuntimeError('Preserve existing anatomical study output')
bpy.ops.wm.open_mainfile(filepath=str(SOURCE),load_ui=False)
scene=bpy.context.scene;rig=bpy.data.objects['Nib_Rig'];collection=bpy.data.collections['Nib_Authored_Components']
rig.animation_data.action=None
for track in rig.animation_data.nla_tracks:track.mute=True
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
scene.frame_set(1);bpy.context.view_layer.update()

def digest(value):return hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest()
def geometry():
    result={}
    for obj in collection.objects:
        if obj.type!='MESH':continue
        result[obj.name]={'vertices':digest(np.asarray([v.co[:] for v in obj.data.vertices],dtype=np.float32)),
            'polygons':digest(np.asarray([i for p in obj.data.polygons for i in p.vertices],dtype=np.int32)),
            'matrix':digest(np.asarray(obj.matrix_world,dtype=np.float64)),
            'uv':{uv.name:digest(np.asarray([v.uv[:] for v in uv.data],dtype=np.float32)) for uv in obj.data.uv_layers},
            'materials':[m.name for m in obj.data.materials],
            'keys':{k.name:digest(np.asarray([v.co[:] for v in k.data],dtype=np.float32)) for k in obj.data.shape_keys.key_blocks} if obj.data.shape_keys else {}}
    return result

before=geometry()
report={'status':'Isolated anatomical construction and twist candidate; source/posed/engine review required',
    'source':str(SOURCE),'sourceSha256':EXPECTED,'library':str(LIBRARY),'librarySha256':LIBRARY_SHA,
    'license':'Blender Studio Human Base Meshes 1.4.1 CC0; original README/provenance preserved',
    'referenceObject':'GEO-body_male_realistic','sharedChanged':False,'artisticAcceptance':False,
    'scope':'Natural torso/arms plus twist extension; retained restorative body is not a newly accepted variant'}
report['skeleton']=install(rig)

archive=bpy.data.collections.new('Nib anatomical study preserved input surfaces')
scene.collection.children.link(archive);archive.hide_render=True;archive.hide_viewport=True
old_body=bpy.data.objects['Continuous Nib anatomy organic']
old_fuzz=bpy.data.objects['Fine skin fuzz organic']
skin=old_body.data.materials[0];fuzz_material=old_fuzz.data.materials[0]
replaced={old_body.name,old_fuzz.name}
for obj in [old_body,old_fuzz]:
    collection.objects.unlink(obj);archive.objects.link(obj);obj.hide_render=True;obj.hide_set(True)
    obj.name='PRESERVED INPUT '+obj.name

with bpy.data.libraries.load(str(LIBRARY),link=False) as (available,loaded):
    if 'GEO-body_male_realistic' not in available.objects:raise RuntimeError('Missing licensed body cage')
    loaded.objects=['GEO-body_male_realistic']
reference=loaded.objects[0];original=reference.data
raw=np.asarray([v.co[:] for v in original.vertices],dtype=np.float64)
source_faces=[tuple(p.vertices) for p in original.polygons]
used,faces=crop(raw,source_faces);source_points=raw[used];points=warp(source_points)
domain,statistics=krag_skin_domains.solve(source_points,faces)
if not statistics['converged']:raise RuntimeError('Source anatomical domain failed to converge')
mesh=bpy.data.meshes.new('Nib connected licensed thorax shoulder elbow cage')
mesh.from_pydata(points,[],faces);mesh.update();mesh.materials.append(skin)
for p in mesh.polygons:p.use_smooth=True
source_attribute=mesh.attributes.new('Nib_BodyReferencePosition','FLOAT_VECTOR','POINT')
source_attribute.data.foreach_set('vector',source_points.astype(np.float32).ravel())
domain_attribute=mesh.attributes.new('Nib_ArmDomain','FLOAT','POINT')
domain_attribute.data.foreach_set('value',domain.astype(np.float32))
if original.uv_layers:
    lookup={face:i for i,face in enumerate(source_faces)};uv=mesh.uv_layers.new(name='UVMap')
    old_uv=original.uv_layers[0]
    for face in mesh.polygons:
        original_polygon=original.polygons[lookup[tuple(int(used[i]) for i in face.vertices)]]
        for dest,src in zip(face.loop_indices,original_polygon.loop_indices):uv.data[dest].uv=old_uv.data[src].uv
else:raise RuntimeError('Reference body unexpectedly has no UV map')
obj=bpy.data.objects.new('Continuous Nib anatomy organic',mesh);collection.objects.link(obj)
obj['bone']='BodyAnatomy';obj['variant']='organic';obj['anatomical_source']='Blender Studio CC0 body_male_realistic'
obj['study_status']='Unaccepted Nib-proportioned continuous anatomical cage; no human head or hand replacement'
control=obj.copy();control.data=mesh.copy();control.name='EDITABLE Nib continuous body control cage'
archive.objects.link(control);control.hide_render=True;control.hide_set(True)
bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
sub=obj.modifiers.new('Continuous anatomical surface','SUBSURF');sub.levels=2;sub.render_levels=2
bpy.ops.object.modifier_apply(modifier=sub.name)
points=np.asarray([v.co[:] for v in obj.data.vertices],dtype=np.float64)
field=np.empty(len(points),dtype=np.float32);obj.data.attributes['Nib_ArmDomain'].data.foreach_get('value',field)
bones={name:[tuple(rig.data.bones[name].head_local),tuple(rig.data.bones[name].tail_local)]
       for side in ['L','R'] for name in ['UpperArm_'+side,'LowerArm_'+side]}
skin_weights=weights(points,field,bones)
for name,values in skin_weights.items():
    group=obj.vertex_groups.new(name=name)
    for i,value in enumerate(values):
        if value>1e-8:group.add([i],float(value),'REPLACE')
obj.parent=rig;obj.matrix_world=Matrix.Identity(4)
modifier=obj.modifiers.new('Portable linear skinning','ARMATURE');modifier.object=rig;modifier.use_deform_preserve_volume=False
body_correctives([obj]);contract=json.loads(scene['deformation_contract']);attach_portable_drivers(obj,rig,contract)

# Deterministic fine fuzz uses area-weighted real surface roots and inherits
# their skin and every body corrective. The confirmed visible skin remains.
obj.data.calc_loop_triangles();triangles=np.asarray([t.vertices[:] for t in obj.data.loop_triangles],dtype=np.int32)
center=points[triangles].mean(axis=1);candidates=(abs(center[:,0])>.126)|(center[:,2]>.979)
triangle_ids=np.nonzero(candidates)[0];triangles=triangles[triangle_ids]
surface=points[triangles];cross=np.cross(surface[:,1]-surface[:,0],surface[:,2]-surface[:,0]);areas=np.linalg.norm(cross,axis=1)
valid=areas>1e-12;triangles=triangles[valid];cross=cross[valid];areas=areas[valid]
rng=np.random.default_rng(417731);selected=rng.choice(len(triangles),2300,p=areas/areas.sum())
root_triangles=triangles[selected];uv_random=rng.random((2300,2));u=np.sqrt(uv_random[:,0]);bary=np.column_stack((1-u,u*(1-uv_random[:,1]),u*uv_random[:,1]))
root=np.sum(points[root_triangles]*bary[:,:,None],axis=1)
normals=cross[selected]/np.linalg.norm(cross[selected],axis=1)[:,None]
vertices=[];fur_faces=[];root_ids=[]
for i,(p,n) in enumerate(zip(root,normals)):
    direction=Vector(n)+Vector((0,0,-.30));direction.normalize()
    axis=direction.cross(Vector((0,1,0)))
    if axis.length<1e-5:axis=direction.cross(Vector((1,0,0)))
    axis.normalize();other=direction.cross(axis).normalized();radius=float(rng.uniform(.000025,.000055));length=float(rng.uniform(.001,.0025));start=len(vertices)
    for ring in range(2):
        c=Vector(p)+Vector(n)*.00005+direction*(length*ring)
        for k in range(3):
            angle=k*math.tau/3;r=radius if ring==0 else .000002
            vertices.append(tuple(c+(axis*math.cos(angle)+other*math.sin(angle))*r));root_ids.append(i)
    for k in range(3):fur_faces.append((start+k,start+(k+1)%3,start+3+(k+1)%3,start+3+k))
fur_mesh=bpy.data.meshes.new('Nib anatomical surface fine fuzz');fur_mesh.from_pydata(vertices,[],fur_faces);fur_mesh.update();fur_mesh.materials.append(fuzz_material)
fuzz=bpy.data.objects.new('Fine skin fuzz organic',fur_mesh);collection.objects.link(fuzz)
fuzz['bone']='BodyAnatomy';fuzz['variant']='organic';fuzz['fur_strands']=2300
fuzz['fur_design']='Fine visible-skin fuzz, area-weighted anatomical surface roots, no simulation'
uv=fur_mesh.uv_layers.new(name='UVMap')
for loop in fur_mesh.loops:uv.data[loop.index].uv=((loop.vertex_index%3)/3,(loop.vertex_index%6)//3)
for polygon in fur_mesh.polygons:polygon.use_smooth=True
root_ids=np.asarray(root_ids)
for name,values in skin_weights.items():
    root_weight=np.sum(values[root_triangles]*bary,axis=1);group=fuzz.vertex_groups.new(name=name)
    for i,value in enumerate(root_weight[root_ids]):
        if value>1e-8:group.add([i],float(value),'REPLACE')
fuzz.shape_key_add(name='Basis',from_mix=False)
basis=np.asarray([v.co[:] for v in obj.data.shape_keys.key_blocks['Basis'].data])
for key in obj.data.shape_keys.key_blocks:
    if key.name=='Basis':continue
    delta=np.asarray([v.co[:] for v in key.data])-basis
    root_delta=np.sum(delta[root_triangles]*bary[:,:,None],axis=1)
    new=fuzz.shape_key_add(name=key.name,from_mix=False)
    new.data.foreach_set('co',(np.asarray(vertices)+root_delta[root_ids]).astype(np.float32).ravel())
fuzz.parent=rig;fuzz.matrix_world=Matrix.Identity(4)
mod=fuzz.modifiers.new('Portable linear surface fuzz','ARMATURE');mod.object=rig;mod.use_deform_preserve_volume=False
attach_portable_drivers(fuzz,rig,contract)

# Soft forearm wraps need the same axial field. Rigid prosthetic modules remain
# outside this Natural-only shape study and require a separate mechanical fit.
report['retainedSoftForearmWeights']=[]
for part in collection.objects:
    if part.type!='MESH' or part in [obj,fuzz]:continue
    if part.name.startswith('Forearm desert wrap '):report['retainedSoftForearmWeights'].append(split_existing_weights(part,rig))
after=geometry()
for name,item in before.items():
    if name not in replaced and after.get(name)!=item:raise RuntimeError('Anatomical body changed unrelated geometry: '+name)
report['preserved']={'unrelatedGeometryUVMaterialsMorphsAndMatrices':len(before)-len(replaced),
    'originalGlobalBoneBind':True,'faceAndEarGeometry':True,'allOriginalAnimationCurves':True,
    'newTwistAnimationAuthored':False,'rigRequiresRootRetarget':True}
report['cage']={'vertices':len(used),'faces':len(faces),'domain':statistics}
report['anatomicalSurface']={'vertices':len(obj.data.vertices),'triangles':sum(len(p.vertices)-2 for p in obj.data.polygons),
    'boundsMin':points.min(axis=0).tolist(),'boundsMax':points.max(axis=0).tolist(),
    'maximumInfluences':int(np.count_nonzero(np.stack(list(skin_weights.values()),axis=1)>1e-7,axis=1).max()),
    'bodyCorrectives':[k.name for k in obj.data.shape_keys.key_blocks if k.name!='Basis'],'fineFuzzStrands':2300}
report['authoringCode']={name:sha(HERE/name) for name in ['build_anatomical_body_study.py','anatomical_body_fit.py','forearm_twist.py']}
report['reusedDomainCodeSha256']=sha(Path(krag_skin_domains.__file__))
for filename in report['authoringCode']:
    text=bpy.data.texts.new('Nib anatomical study '+filename);text.write((HERE/filename).read_text())
bpy.data.objects.remove(reference,do_unlink=True)
if original.users==0:bpy.data.meshes.remove(original)
rig.animation_data.action=bpy.data.actions['Idle'];scene.frame_set(1)
scene['source_version']='Anatomical body v1 on v5i face/ears; new half-twist rig awaiting fresh captured body clips'
bpy.ops.wm.save_as_mainfile(filepath=str(TARGET),compress=True)
if sha(SOURCE)!=EXPECTED:raise RuntimeError('Anatomical generation changed input source')
report['output']=str(TARGET);report['outputSha256']=sha(TARGET);ART.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(report,indent=2)+'\n',newline='\n')
print('NIB_ANATOMICAL_BODY_STUDY_SAVED',flush=True)
