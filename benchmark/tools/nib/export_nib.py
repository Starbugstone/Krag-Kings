"""Consolidate editable Nib source into three efficient, self-contained FBX variants."""
import bpy,bmesh,json,shutil,hashlib,sys,argparse,os
import numpy as np
from mathutils import Matrix
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];ART=ROOT/'benchmark/art/nib';OUT=ROOT/'benchmark/shared/characters/nib'
parser=argparse.ArgumentParser()
parser.add_argument('--source',type=Path,default=ART/'Nib_Master.blend')
parser.add_argument('--out',type=Path,default=OUT)
parser.add_argument('--baseline-dir',type=Path,default=OUT,help='Matching reference FBXs for point-domain normal preservation; new topology needs its own isolated reference export')
parser.add_argument('--texture-dir',type=Path,help='Explicit baked PBR directory for a new source; otherwise use baseline-dir/textures')
parser.add_argument('--card-texture-dir',type=Path,help='Actual original groom atlas directory; masked maps are copied without rebaking or losing coverage alpha')
parser.add_argument('--source-report',type=Path,default=ART/'source-report.json')
parser.add_argument('--triangulate',action='store_true',help='Export a temporary triangulated mesh while retaining source vertices and shape keys')
parser.add_argument('--preserve-baseline-morphs',action='store_true',help='Historical exact-payload conversion only; never use when correcting morphs')
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
SOURCE=args.source;SHARED_OUT=OUT;BASELINE_OUT=args.baseline_dir;OUT=args.out
OUT.mkdir(parents=True,exist_ok=True)
candidate=OUT.resolve()!=SHARED_OUT.resolve()
if candidate:
    if SOURCE.resolve()==(ART/'Nib_Master.blend').resolve():raise RuntimeError('Candidate export requires an explicit derivative source')
    texture_source=args.texture_dir or BASELINE_OUT/'textures'
    if texture_source.resolve()!=(OUT/'textures').resolve():shutil.copytree(texture_source,OUT/'textures',dirs_exist_ok=True)
legacy=ART/'versions/pre-v4-shared';legacy.mkdir(parents=True,exist_ok=True)
for filename in ([] if candidate else ['asset_manifest.json','manifest.json','Nib_Natural.fbx','Nib_GripReplacement.fbx','Nib_LegReplacement.fbx']):
    old=OUT/filename
    if old.exists() and not (legacy/filename).exists():shutil.copy2(old,legacy/filename)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
rig=bpy.data.objects['Nib_Rig'];scene=bpy.context.scene
rig.animation_data_create();rig.animation_data.action=None
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
scene.frame_set(1);bpy.context.view_layer.update()
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
manifest['source']=os.path.relpath(SOURCE,OUT).replace('\\','/')
manifest['sourceSha256']=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
if 'v5_reference_provenance' in scene:
    manifest['adaptedTopologyProvenance']=json.loads(scene['v5_reference_provenance'])
sys.path.insert(0,str(Path(__file__).parent.parent/'animation'))
import export_contract
manifest['locomotion'],manifest['sourceAnimationContract']=export_contract.prepare(bpy,json.loads(scene['locomotion_contract']))
manifest['facialPerformance']={name:{'authoredInBodyClip':True} for name in ['Idle','Walk','Run','Melee','Shoot','Hit']}
source_report=json.loads(args.source_report.read_text())
reported_source=(source_report.get('candidateSha256') or source_report.get('outputSha256') or source_report.get('sourceSha256'))
if reported_source!=manifest['sourceSha256']:raise RuntimeError('Saved source/report hash mismatch')
if candidate:
    if source_report.get('candidateSha256') and 'trianglesByVariant' in source_report and 'method' in source_report:
        manifest['detailedMasterSha256']=source_report['sourceSha256']
        manifest['runtimeReductionReport']=os.path.relpath(args.source_report,OUT).replace('\\','/')
    else:
        manifest['authoredSourceReport']=os.path.relpath(args.source_report,OUT).replace('\\','/')
        if source_report.get('candidateSha256') and source_report.get('sourceSha256'):
            manifest['authoredInputSourceSha256']=source_report['sourceSha256']
manifest['fur']={key:source_report.get(key) for key in ['furRepresentation','furStrands','furTriangles','cinematic']}
manifest['mouthAnatomyStatus']='Provisional interior and expressions for review; dark-blue tongue canonical.'
if args.triangulate:
    manifest['geometryExport']={'triangulated':True,'method':'Disposable assembly triangulation; validated baseline vertex-domain normal layer preserved, corrected target morphs retained unless explicitly requested otherwise','sourceVertexOrderUnchanged':True,'mappedNormalMaxVectorError':0,'pointAndMorphPayloadsByteIdentical':args.preserve_baseline_morphs}
    manifest['geometryExport']['referenceDirectory']=os.path.relpath(BASELINE_OUT,OUT).replace('\\','/')
manifest['shapeUnion']={'creation':'from_mix=False','copiedDriversClearedBeforeCreation':True,'copiedWeightsZeroedBeforeCreation':True,'bodyCorrectivesOnFacialVerticesChecked':True}
card_entries=json.loads(scene.get('nib_groom_material_contract','[]'))
card_contract={entry['name']:entry for entry in card_entries}
if len(card_contract)!=len(card_entries):raise RuntimeError('Duplicate groom material contract')
used_materials={m.name:m for o in sources if o.type=='MESH' for m in o.data.materials if m}
unused_cards=set(card_contract)-set(used_materials)
if unused_cards:raise RuntimeError('Groom contract has no authored surface assignments: '+str(sorted(unused_cards)))
for name,m in sorted(used_materials.items()):
    if not name.startswith('Nib_'):raise RuntimeError('Uncontracted authored Nib material '+name)
    if name in card_contract:
        entry=dict(card_contract[name])
        if (entry.get('alphaMode')!='MASK' or entry.get('alphaSource')!='baseColor.a'
            or not 0<float(entry.get('alphaClipThreshold',0))<1
            or entry.get('doubleSided') is not True or entry.get('doubleSidedNormalMode')!='Flip'
            or entry.get('normalConvention')!='OpenGL +Y'):
            raise RuntimeError('Incomplete portable groom material contract '+name)
        for channel in ['baseColor','normal','roughness','metallic']:
            relative=Path(entry[channel])
            if relative.is_absolute() or len(relative.parts)!=2 or relative.parts[0]!='textures':
                raise RuntimeError('Groom map must be a local textures/ file '+str(relative))
            destination=OUT/relative
            if args.card_texture_dir:
                atlas=args.card_texture_dir/relative.name
                if not atlas.is_file():raise RuntimeError('Missing original groom atlas '+str(atlas))
                destination.parent.mkdir(parents=True,exist_ok=True)
                if atlas.resolve()!=destination.resolve():shutil.copy2(atlas,destination)
            if not destination.is_file():raise RuntimeError('Missing exported groom texture '+str(destination))
            manifest.setdefault('groomTextureHashes',{})[entry[channel]]=hashlib.sha256(destination.read_bytes()).hexdigest()
    else:
        if m.get('portableAlphaMode')=='MASK':raise RuntimeError('Masked material missing scene contract '+name)
        entry={'name':name,'baseColor':'textures/'+name+'_BaseColor.png','normal':'textures/'+name+'_Normal.png','roughness':'textures/'+name+'_Roughness.png','metallic':'textures/'+name+'_Metallic.png'}
    manifest['materials'].append(entry)
for a in bpy.data.actions:
    if a.name in ['Idle','Walk','Run','Melee','Shoot','Hit','FacePerformance']:
        manifest['clips'].append({'name':a.name,'startFrame':int(a.frame_range[0]),'endFrame':int(a.frame_range[1]),'fps':30})
for variant,label in [('natural','Natural'),('grip','GripReplacement'),('leg','LegReplacement')]:
    bpy.ops.object.select_all(action='DESELECT');copies=[]
    for src in sources:
        if src.type!='MESH' or not visible(src,variant):continue
        o=src.copy();o.data=src.data.copy();scene.collection.objects.link(o);o.hide_set(False);o.hide_render=False;o.select_set(True);copies.append(o)
        o.data.uv_layers.active.name='UVMap'
    card_count=sum(int(o.get('fur_cards',0)) for o in copies)
    strand_triangles=sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in copies if o.get('fur_strands'))
    card_triangles=sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in copies if o.get('fur_cards'))
    variant_fur={'representation':('skinned masked cards with opaque fiber accents' if card_count else 'skinned opaque strands'),
                 'simulation':False,'cards':card_count,'strands':sum(int(o.get('fur_strands',0)) for o in copies),
                 'triangles':strand_triangles+card_triangles,'cardTriangles':card_triangles,'strandTriangles':strand_triangles}
    if candidate and variant=='natural':manifest['fur']={**variant_fur,'cinematic':False,'scope':'Tagged card and strand batches; untagged legacy fine edge/brow/chin tubes are additional geometry in total counts.'}
    # The active head owns the union of shape names; missing shapes on other
    # components are joined as their Basis, preserving both face and body targets.
    active=next(o for o in copies if o.get('bone')=='FaceSurface')
    names=sorted({key.name for o in copies if o.data.shape_keys for key in o.data.shape_keys.key_blocks if key.name!='Basis'})
    for obj in copies:
        if obj.data.shape_keys:
            obj.data.shape_keys.animation_data_clear()
            for key in obj.data.shape_keys.key_blocks:key.value=0
    # Missing union keys must equal Basis. from_mix=True can capture copied live
    # facial drivers recursively, contaminating body correctives with brow deltas.
    for name in names:
        if name not in active.data.shape_keys.key_blocks:active.shape_key_add(name=name,from_mix=False)
    face_marker='NibExportFacialRegion'
    for obj in copies:
        if obj.get('bone') not in ['FaceSurface','FaceSurfaceFuzz']:continue
        attribute=obj.data.attributes.get(face_marker) or obj.data.attributes.new(face_marker,'FLOAT','POINT')
        attribute.data.foreach_set('value',np.ones(len(obj.data.vertices),dtype=np.float32))
    bpy.context.view_layer.objects.active=active;bpy.ops.object.join();mesh=active;mesh.name='Nib_'+label+'_Mesh'
    if not mesh.data.shape_keys:raise RuntimeError('Morphs lost while consolidating '+label)
    basis=np.empty(len(mesh.data.vertices)*3,dtype=np.float32);mesh.data.shape_keys.key_blocks['Basis'].data.foreach_get('co',basis)
    marker=mesh.data.attributes.get(face_marker)
    if marker is None:raise RuntimeError('Joined facial-region regression marker was lost')
    marked=np.empty(len(mesh.data.vertices),dtype=np.float32);marker.data.foreach_get('value',marked);facial=marked>.5
    if not np.any(facial):raise RuntimeError('No joined facial vertices for body-corrective regression')
    isolation={}
    for key in mesh.data.shape_keys.key_blocks:
        if not key.name.startswith('Corrective_'):continue
        values=np.empty_like(basis);key.data.foreach_get('co',values)
        magnitude=float(np.linalg.norm((values-basis).reshape((-1,3))[facial],axis=1).max())
        isolation[key.name]=magnitude
        if magnitude>1e-7:raise RuntimeError(f'{label}: body morph {key.name} contaminates facial vertices by {magnitude}m')
    mesh.data.attributes.remove(marker)
    manifest.setdefault('shapeUnionValidation',[]).append({'variant':label,'facialVertices':int(facial.sum()),'maxFacialDeltaPerBodyTargetMeters':isolation})
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
    if max_influences>(8 if candidate else 4):raise RuntimeError(f'{label}: unsupported bone influence count {max_influences}')
    if empty or badsum:raise RuntimeError(f'{label}: unweighted={empty}, invalid sums={badsum}')
    if args.triangulate:
        # FBX's built-in BMesh conversion perturbs a few near-zero shape deltas.
        # Triangulate this disposable assembly explicitly, then restore every
        # cached key coordinate before export. No vertex may move or reorder.
        vertex_normals=np.zeros((len(mesh.data.vertices),3),dtype=np.float32)
        for loop,normal in zip(mesh.data.loops,mesh.data.corner_normals):
            vertex_normals[loop.vertex_index]=normal.vector
        if any((np.asarray(normal.vector)-vertex_normals[loop.vertex_index]).dot(np.asarray(normal.vector)-vertex_normals[loop.vertex_index])>1e-12 for loop,normal in zip(mesh.data.loops,mesh.data.corner_normals)):
            raise RuntimeError('Nib source split normals need explicit corner transfer')
        cached_keys={}
        for key in mesh.data.shape_keys.key_blocks:
            values=np.empty(len(mesh.data.vertices)*3,dtype=np.float32);key.data.foreach_get('co',values)
            cached_keys[key.name]=values
        original_positions=np.empty(len(mesh.data.vertices)*3,dtype=np.float32);mesh.data.vertices.foreach_get('co',original_positions)
        bm=bmesh.new();bm.from_mesh(mesh.data)
        bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.to_mesh(mesh.data);bm.free()
        resulting_positions=np.empty(len(mesh.data.vertices)*3,dtype=np.float32);mesh.data.vertices.foreach_get('co',resulting_positions)
        if not np.array_equal(original_positions,resulting_positions):raise RuntimeError('Triangulation moved/reordered Basis vertices')
        for key in mesh.data.shape_keys.key_blocks:key.data.foreach_set('co',cached_keys[key.name])
        mesh.data.normals_split_custom_set_from_vertices(vertex_normals.tolist())
        if any(len(p.vertices)!=3 for p in mesh.data.polygons):raise RuntimeError('Explicit triangulation left nontriangular faces')
    rig.hide_set(False);rig.select_set(True);bpy.context.view_layer.objects.active=rig
    fbx='Nib_'+label+'.fbx'
    bpy.ops.export_scene.fbx(filepath=str(OUT/fbx),use_selection=True,object_types={'ARMATURE','MESH'},global_scale=1,apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',axis_forward='-Z',axis_up='Y',add_leaf_bones=False,use_armature_deform_only=False,bake_anim=True,bake_anim_use_all_actions=True,bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_simplify_factor=0,path_mode='RELATIVE',embed_textures=False,mesh_smooth_type='FACE',use_mesh_modifiers=False,use_triangles=False)
    if args.triangulate:
        # Preserve the already validated point-domain shading and shape arrays.
        # The helper refuses any changed vertex coordinates/order, shape list or
        # non-point normal mapping, and verifies every other serialized property.
        if not candidate:raise RuntimeError('Pretriangulation must first be exported to an isolated candidate')
        sys.path.insert(0,str(Path(__file__).parent/'v5_wip'))
        from preserve_fbx_point_payloads import preserve
        preservation=preserve(BASELINE_OUT/fbx,OUT/fbx,Path(bpy.utils.system_resource('SCRIPTS'))/'addons_core',preserve_morphs=args.preserve_baseline_morphs)
        manifest.setdefault('pointPayloadPreservation',[]).append(preservation)
    manifest['variants'].append({'name':'Nib_'+label,'fbx':fbx,'label':{'Natural':'Natural','GripReplacement':'Grip replacement','LegReplacement':'Leg replacement'}[label],'species':'Nib','sourceRestBoundsMeters':bounds,'fur':variant_fur,'deformation':deformation,'morphs':present,'triangles':triangles,'vertices':len(mesh.data.vertices),'preTriangulated':args.triangulate,'skinnedMeshCount':1,'materialSlots':len(mesh.data.materials),'weightedVertices':len(mesh.data.vertices),'maxInfluences':max(len(v.groups) for v in mesh.data.vertices),'bionics':[] if variant=='natural' else [{'region':'left forearm/hand' if variant=='grip' else 'right lower leg/foot','function':'restoration only','upgrade':False}]})
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
    name=clip['name'];scene.name=name;export_contract.select_action(bpy,rig,bpy.data.actions[name])
    scene.frame_start=clip['startFrame'];scene.frame_end=clip['endFrame'];scene.frame_set(scene.frame_start)
    path=animation_dir/(name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'ARMATURE','MESH'},use_mesh_modifiers=False,global_scale=1,apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',axis_forward='-Z',axis_up='Y',add_leaf_bones=False,use_armature_deform_only=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_simplify_factor=0,path_mode='RELATIVE',embed_textures=False)
    clip['fbx']='animations/'+name+'.fbx';manifest['animations'][name]=clip['fbx']
for filename in ['manifest.json','asset_manifest.json']:
    (OUT/filename).write_text(json.dumps(manifest,indent=2),newline='\n')
(OUT/'facial-rig.json').write_text(json.dumps(manifest['deformation'],indent=2),newline='\n')
# Archive only the redundant texture-copy directories generated by the superseded
# first exporter; all variants now share the explicit textures/ manifest paths.
for label in ([] if candidate else ['Natural','GripReplacement','LegReplacement']):
    stale=OUT/('Nib_'+label+'.fbm')
    if stale.exists():
        destination=legacy/stale.name
        if destination.exists():destination=legacy/(stale.name+'-additional')
        shutil.move(str(stale),str(destination))
print('NIB_EXPORT_VALIDATED '+json.dumps(manifest),flush=True)
