"""Consolidate editable Nib source into three efficient, self-contained FBX variants."""
import bpy,json,shutil,hashlib
import numpy as np
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];ART=ROOT/'benchmark/art/nib';OUT=ROOT/'benchmark/shared/characters/nib'
legacy=ART/'versions/pre-v4-shared';legacy.mkdir(parents=True,exist_ok=True)
for filename in ['asset_manifest.json','manifest.json','Nib_Natural.fbx','Nib_GripReplacement.fbx','Nib_LegReplacement.fbx']:
    old=OUT/filename
    if old.exists() and not (legacy/filename).exists():shutil.copy2(old,legacy/filename)
bpy.ops.wm.open_mainfile(filepath=str(ART/'Nib_Master.blend'))
rig=bpy.data.objects['Nib_Rig'];scene=bpy.context.scene
for required in ['FaceRoot','WeaponMuzzle','WeaponAim']:
    if required not in rig.data.bones:raise RuntimeError('Saved source is missing current required bone '+required)
sources=list(bpy.data.collections['Nib_Authored_Components'].objects)
for source_object in sources:
    source_object.hide_set(True);source_object.hide_render=True
def visible(o,variant):
    tag=o.get('variant','all');region=o.get('bone','')
    if tag=='all':return True
    if tag=='organic':return variant!='grip'
    if tag=='natural':
        if variant=='grip' and (region in ['Arm_L','LowerArm_L','Hand_L'] or (region.endswith('_L') and any(region.startswith(n) for n in ['Finger_','Index','Middle','Ring','Little','Thumb']))):return False
        if variant=='leg' and region in ['Shin_R','Foot_R']:return False
        return True
    return tag==variant
manifest={'source':'../../../art/nib/Nib_Master.blend','sourceSha256':hashlib.sha256((ART/'Nib_Master.blend').read_bytes()).hexdigest(),'referenceImages':['krag-kings-design/concept-art/02-nib-character-sheet.png','krag-kings-design/concept-art/05-jetpack-bionics-sheet.png'],'units':'meters','sourceForward':'-Y','sourceUp':'Z','fbxForward':'-Z','fbxUp':'Y','normalConvention':'OpenGL +Y','boneRollAlignment':'local Z aligned toward world -Y','heightMeters':1.385,'bones':[b.name for b in rig.data.bones],'bindAnkleHeightMeters':.10,'materials':[],'variants':[],'clips':[],'acceptance':'Authored review candidate; likeness and investor acceptance remain unverified.'}
manifest['weapon']={'muzzleBone':'WeaponMuzzle','aimBone':'WeaponAim','fireTimesNormalized':[.46],'forwardDefinition':'normalize(worldPosition(WeaponAim)-worldPosition(WeaponMuzzle))','sourceRestMuzzleMeters':[-.227,-.083,.427],'sourceRestBarrelForward':[0,0,-1]}
manifest['deformation']=json.loads(scene['deformation_contract'])
manifest['locomotion']=json.loads(scene['locomotion_contract'])
manifest['facialPerformance']={name:{'authoredInBodyClip':True} for name in ['Idle','Walk','Run','Melee','Shoot','Hit']}
source_report=json.loads((ART/'source-report.json').read_text())
if source_report['sourceSha256']!=manifest['sourceSha256']:raise RuntimeError('Saved source/report hash mismatch')
manifest['fur']={key:source_report.get(key) for key in ['furRepresentation','furStrands','furTriangles','cinematic']}
manifest['mouthAnatomyStatus']='Provisional interior and expressions for review; dark-blue tongue canonical.'
for m in bpy.data.materials:
    if not m.name.startswith('Nib_'):continue
    manifest['materials'].append({'name':m.name,'baseColor':'textures/'+m.name+'_BaseColor.png','normal':'textures/'+m.name+'_Normal.png','roughness':'textures/'+m.name+'_Roughness.png','metallic':'textures/'+m.name+'_Metallic.png'})
for a in bpy.data.actions:
    if a.name in ['Idle','Walk','Run','Melee','Shoot','Hit','FacePerformance']:
        manifest['clips'].append({'name':a.name,'startFrame':int(a.frame_range[0]),'endFrame':int(a.frame_range[1]),'fps':30})
for variant,label in [('natural','Natural'),('grip','GripReplacement'),('leg','LegReplacement')]:
    bpy.ops.object.select_all(action='DESELECT');copies=[]
    for src in sources:
        if src.type!='MESH' or not visible(src,variant):continue
        o=src.copy();o.data=src.data.copy();scene.collection.objects.link(o);o.hide_set(False);o.hide_render=False;o.select_set(True);copies.append(o)
        o.data.uv_layers.active.name='UVMap'
    variant_fur={'representation':'skinned opaque strands; no simulation','strands':sum(int(o.get('fur_strands',0)) for o in copies),'triangles':sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in copies if o.get('fur_strands'))}
    # The active head owns the union of shape names; missing shapes on other
    # components are joined as their Basis, preserving both face and body targets.
    active=next(o for o in copies if o.get('bone')=='FaceSurface')
    names=sorted({key.name for o in copies if o.data.shape_keys for key in o.data.shape_keys.key_blocks if key.name!='Basis'})
    for name in names:
        if name not in active.data.shape_keys.key_blocks:active.shape_key_add(name=name)
    for obj in copies:
        if obj.data.shape_keys:
            obj.data.shape_keys.animation_data_clear()
            for key in obj.data.shape_keys.key_blocks:key.value=0
    bpy.context.view_layer.objects.active=active;bpy.ops.object.join();mesh=active;mesh.name='Nib_'+label+'_Mesh'
    if not mesh.data.shape_keys:raise RuntimeError('Morphs lost while consolidating '+label)
    basis=np.empty(len(mesh.data.vertices)*3,dtype=np.float32);mesh.data.shape_keys.key_blocks['Basis'].data.foreach_get('co',basis)
    present=[]
    for key in mesh.data.shape_keys.key_blocks:
        if key.name=='Basis':continue
        values=np.empty_like(basis);key.data.foreach_get('co',values)
        if float(np.max(np.abs(values-basis)))>1e-7:present.append(key.name)
    deformation={**manifest['deformation'],'drivers':[rule for rule in manifest['deformation']['drivers'] if rule['morph'] in present],'morphs':present}
    if any(rule['kind']=='facial' and rule['morph'] not in present for rule in manifest['deformation']['drivers']):raise RuntimeError('Missing nonzero facial target in '+label)

    # Joining leaves only the active object's modifier stack; keep one skin modifier.
    mesh.parent=rig
    for mod in list(mesh.modifiers):
        if mod.type!='ARMATURE':mesh.modifiers.remove(mod)
    if not any(m.type=='ARMATURE' for m in mesh.modifiers):mesh.modifiers.new('Nib deformation','ARMATURE').object=rig
    for mod in mesh.modifiers:
        if mod.type=='ARMATURE':mod.object=rig
    # Verify exactly normalized weighted vertices and UV coverage before export.
    empty=sum(1 for v in mesh.data.vertices if not v.groups)
    badsum=sum(1 for v in mesh.data.vertices if abs(sum(g.weight for g in v.groups)-1)>.001)
    triangles=sum(len(p.vertices)-2 for p in mesh.data.polygons)
    max_influences=max(len(v.groups) for v in mesh.data.vertices)
    positions=np.empty(len(mesh.data.vertices)*3,dtype=np.float32);mesh.data.vertices.foreach_get('co',positions);positions=positions.reshape((-1,3))
    transform=np.array(mesh.matrix_world,dtype=np.float64);world=positions@transform[:3,:3].T+transform[:3,3]
    bounds={'min':world.min(axis=0).tolist(),'max':world.max(axis=0).tolist()}
    if variant=='natural':manifest['heightMeters']=bounds['max'][2]-bounds['min'][2]
    if max_influences>4:raise RuntimeError(f'{label}: more than four bone influences')
    if empty or badsum:raise RuntimeError(f'{label}: unweighted={empty}, invalid sums={badsum}')
    rig.hide_set(False);rig.select_set(True);bpy.context.view_layer.objects.active=rig
    fbx='Nib_'+label+'.fbx'
    bpy.ops.export_scene.fbx(filepath=str(OUT/fbx),use_selection=True,object_types={'ARMATURE','MESH'},global_scale=1,apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',axis_forward='-Z',axis_up='Y',add_leaf_bones=False,use_armature_deform_only=False,bake_anim=True,bake_anim_use_all_actions=True,bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_simplify_factor=0,path_mode='RELATIVE',embed_textures=False,mesh_smooth_type='FACE',use_mesh_modifiers=False)
    manifest['variants'].append({'name':'Nib_'+label,'fbx':fbx,'label':{'Natural':'Natural','GripReplacement':'Grip replacement','LegReplacement':'Leg replacement'}[label],'species':'Nib','sourceRestBoundsMeters':bounds,'fur':variant_fur,'deformation':deformation,'morphs':present,'triangles':triangles,'vertices':len(mesh.data.vertices),'skinnedMeshCount':1,'materialSlots':len(mesh.data.materials),'weightedVertices':len(mesh.data.vertices),'maxInfluences':max(len(v.groups) for v in mesh.data.vertices),'bionics':[] if variant=='natural' else [{'region':'left forearm/hand' if variant=='grip' else 'right lower leg/foot','function':'restoration only','upgrade':False}]})
    temporary_mesh=mesh.data
    bpy.data.objects.remove(mesh,do_unlink=True)
    if temporary_mesh.users==0:bpy.data.meshes.remove(temporary_mesh)
    # This fresh process contains only this task's loaded Nib artifact. Purge
    # orphan copies/shape arrays left by joining, while referenced source stays.
    bpy.data.orphans_purge(do_local_ids=True,do_linked_ids=False,do_recursive=True)
# Export explicit single-take skeleton files for Unreal as well as embedded Unity takes.
animation_dir=OUT/'animations';animation_dir.mkdir(exist_ok=True);manifest['animations']={}
# A tiny Root-skinned carrier forces FBX Skin/BindPose data. Rig-only files can
# otherwise reconstruct their reference skeleton from a posed first frame.
carrier_data=bpy.data.meshes.new('Nib animation bind carrier');carrier_data.from_pydata([(0,0,0),(.001,0,0),(0,.001,0)],[],[(0,1,2)]);carrier_data.update()
carrier=bpy.data.objects.new('Nib_AnimationBindCarrier',carrier_data);scene.collection.objects.link(carrier);carrier.parent=rig
carrier.vertex_groups.new(name='Root').add([0,1,2],1.0,'REPLACE');carrier.modifiers.new('Bind pose carrier skin','ARMATURE').object=rig
manifest['animationBindCarrier']={'mesh':'Nib_AnimationBindCarrier','purpose':'Preserve identical FBX rest skeleton; animation import ignores carrier geometry.'}
bpy.ops.object.select_all(action='DESELECT');rig.hide_set(False);rig.select_set(True);carrier.select_set(True);bpy.context.view_layer.objects.active=rig
for clip in manifest['clips']:
    name=clip['name'];scene.name=name;rig.animation_data.action=bpy.data.actions[name]
    scene.frame_start=clip['startFrame'];scene.frame_end=clip['endFrame'];scene.frame_set(scene.frame_start)
    path=animation_dir/(name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'ARMATURE','MESH'},use_mesh_modifiers=False,global_scale=1,apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',axis_forward='-Z',axis_up='Y',add_leaf_bones=False,use_armature_deform_only=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_simplify_factor=0,path_mode='RELATIVE',embed_textures=False)
    clip['fbx']='animations/'+name+'.fbx';manifest['animations'][name]=clip['fbx']
for filename in ['manifest.json','asset_manifest.json']:
    (OUT/filename).write_text(json.dumps(manifest,indent=2))
# Archive only the redundant texture-copy directories generated by the superseded
# first exporter; all variants now share the explicit textures/ manifest paths.
for label in ['Natural','GripReplacement','LegReplacement']:
    stale=OUT/('Nib_'+label+'.fbm')
    if stale.exists():
        destination=legacy/stale.name
        if destination.exists():destination=legacy/(stale.name+'-additional')
        shutil.move(str(stale),str(destination))
print('NIB_EXPORT_VALIDATED '+json.dumps(manifest),flush=True)
