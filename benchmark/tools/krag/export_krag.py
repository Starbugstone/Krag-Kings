"""Bake portable PBR material tiles, attach them, and export identical animated variants.
No paid materials; provenance for CC0 scanned skin inputs is retained with the source. Source nodes remain in Krag_Master.blend; runtime saved separately.
"""
import bpy, bmesh, json, math, sys, os, shutil
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).parent));import material_cache
from triangulate_runtime_mesh import triangulate as triangulate_assembly
def argument(name,default):return Path(sys.argv[sys.argv.index(name)+1]) if name in sys.argv else default
ROOT=Path(__file__).resolve().parents[3];ART=ROOT/'benchmark/art/krag';BASE_OUT=ROOT/'benchmark/shared/characters/krag';OUT=argument('--output-dir',BASE_OUT);TEX=OUT/'textures';TEX.mkdir(parents=True,exist_ok=True)
stage='export' if '--export-only' in sys.argv or '--animations-only' in sys.argv else 'bake'
triangulate='--triangulate' in sys.argv
source_blend=argument('--source-runtime',ART/'Krag_Runtime.blend') if stage=='export' else argument('--source-master',ART/'Krag_Master.blend')
runtime_destination=argument('--runtime-output',ART/'Krag_Runtime.blend')
texture_source=argument('--texture-source-dir',BASE_OUT/'textures')
bpy.ops.wm.open_mainfile(filepath=str(source_blend))
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=4;scene.render.bake.margin=4
rig=bpy.data.objects['Krag_Rig'];modules={o.get('module'):o for o in bpy.data.objects if o.type=='MESH' and 'module' in o};contract=json.loads(argument('--contract',BASE_OUT/'krag_asset_contract.json').read_text())
sys.path.insert(0,str(Path(__file__).parent.parent/'animation'))
import export_contract
contract['locomotionCycles'],action_export=export_contract.prepare(bpy,contract['locomotionCycles'])
contract['clips']=list(export_contract.CLIPS)
if stage=='export' and OUT!=BASE_OUT:
    (OUT/'facial-rig.json').write_text(json.dumps(contract['deformation'],indent=2),newline='\n')
    for maps in contract['material_maps'].values():
        for filename in maps.values():
            source=texture_source/filename;destination=TEX/filename
            if source.resolve()!=destination.resolve():shutil.copy2(source,destination)
    for image in bpy.data.images:
        if image.filepath and (TEX/Path(bpy.path.abspath(image.filepath)).name).is_file():image.filepath=str(TEX/Path(bpy.path.abspath(image.filepath)).name)

# Muzzle marker bones use two geometric points, avoiding engine-specific axis assumptions.
weapon_contract={'muzzleBone':'WeaponMuzzle','aimBone':'WeaponAim','fireTimesNormalized':[.40,.58]}
if stage=='bake':
    bpy.ops.object.select_all(action='DESELECT');rig.hide_set(False);rig.select_set(True);bpy.context.view_layer.objects.active=rig;bpy.ops.object.mode_set(mode='EDIT')
    for name,head in [('WeaponMuzzle',(-.450,-.048,.567)),('WeaponAim',(-.450,-.048,.467))]:
        bone=rig.data.edit_bones.get(name)
        if bone is None:
            bone=rig.data.edit_bones.new(name);bone.head=head;bone.tail=(head[0],head[1],head[2]-.025)
        bone.parent=rig.data.edit_bones['Hand_R'];bone.use_deform=False
    bpy.ops.object.mode_set(mode='OBJECT');contract['runtime_extra_bones']=['WeaponMuzzle','WeaponAim'];contract['weapon']=weapon_contract

def attach_maps(m,maps):
    nodes=m.node_tree.nodes;links=m.node_tree.links
    nodes.clear();out=nodes.new('ShaderNodeOutputMaterial');bs=nodes.new('ShaderNodeBsdfPrincipled');links.new(bs.outputs[0],out.inputs[0])
    for channel,fn in maps.items():
        im=bpy.data.images.load(str(TEX/fn),check_existing=True);im.colorspace_settings.name='sRGB' if channel=='BaseColor' else 'Non-Color';n=nodes.new('ShaderNodeTexImage');n.image=im;n.extension='REPEAT';n.label=channel
        if channel=='Normal':
            nm=nodes.new('ShaderNodeNormalMap');links.new(n.outputs['Color'],nm.inputs['Color']);links.new(nm.outputs['Normal'],bs.inputs['Normal'])
        else:links.new(n.outputs['Color'],bs.inputs[{'BaseColor':'Base Color','Roughness':'Roughness','Metallic':'Metallic'}[channel]])
    if 'Skin' in m.name:bs.inputs['Subsurface Weight'].default_value=.035

def save_manifest():
    manifest={'materials':[dict(name=n,baseColor='textures/'+m['BaseColor'],normal='textures/'+m['Normal'],roughness='textures/'+m['Roughness'],metallic='textures/'+m['Metallic']) for n,m in material_maps.items()], 'variants':[{'name':n,'fbx':n+'.fbx','label':n.replace('Krag_',''),'deformation':v.get('deformation',contract['deformation'])} for n,v in contract['variants'].items()], 'animations':{n:'animations/'+n+'.fbx' for n in contract['clips']}, 'normalConvention':'OpenGL', 'authoringForward':'-Y','authoringUp':'Z','heightMeters':2.107,'weapon':weapon_contract,'weaponNode':None,'weaponSourceModule':'Weapon_R','weaponGeometryIncluded':True,'weaponDefaultVisible':True,'deformation':contract['deformation'],'locomotion':contract['locomotionCycles'],'status':'Review model, artistic acceptance pending','geometryExport':{'triangulated':triangulate,'method':'Temporary assembly BMesh triangulation with cached shape coordinates and corner normals restored' if triangulate else 'Original polygon topology'}}
    manifest['sourceAnimationContract']=action_export
    if contract.get('runtime_derivative_sha256'):
        manifest['runtimeDerivative']={'sha256':contract['runtime_derivative_sha256'],'status':contract.get('runtime_derivative_status'),'trianglesAllModules':contract.get('runtime_triangles_all_modules')}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),newline='\n')

if stage=='bake':
    visibility={o.name:o.hide_render for o in bpy.data.objects}
    for o in bpy.data.objects:
        if o.type=='MESH':o.hide_render=True
    # Material tile sampled on 1m of physically scaled surface.
    for o in bpy.context.selected_objects:o.select_set(False)
    bpy.ops.mesh.primitive_plane_add(size=1,location=(0,0,0));tile=bpy.context.object;tile.name='Temporary_PBR_bake_tile';tile.rotation_euler=(0,0,0)
    material_maps={};new_cache={};cache_path=argument('--material-cache',ART/'material-cache.json');reuse='--reuse-tiles' in sys.argv
    if reuse and not cache_path.is_file():raise RuntimeError('Verified material cache missing; run the seed job before reusing existing tiles.')
    old_cache=json.loads(cache_path.read_text()).get('materials',{}) if cache_path.is_file() else {}
    source_sha=material_cache.sha(source_blend)
    if 'Krag_SkinRegion' in modules['Head'].data.attributes:
        from bake_face_atlas import bake
        tile.hide_render=True
        material,maps,receipt=bake(modules['Head'],TEX);material_maps[material.name]=maps;attach_maps(material,maps)
        (OUT/'facial-atlas-receipt.json').write_text(json.dumps(receipt,indent=2),newline='\n')
        modules['Head'].hide_render=True;modules['Head'].select_set(False)
        tile.hide_render=False;tile.hide_set(False);tile.select_set(True);bpy.context.view_layer.objects.active=tile
    if 'Face' in modules and 'Krag_IrisCoord' in modules['Face'].data.attributes:
        from bake_face_atlas import bake
        tile.hide_render=True
        material,maps,receipt=bake(modules['Face'],TEX,optical=True);material_maps[material.name]=maps;attach_maps(material,maps)
        (OUT/'optical-atlas-receipt.json').write_text(json.dumps(receipt,indent=2),newline='\n')
        modules['Face'].hide_render=True;modules['Face'].select_set(False)
        tile.hide_render=False;tile.hide_set(False);tile.select_set(True);bpy.context.view_layer.objects.active=tile
    used_materials={material.name for obj in modules.values() for material in obj.data.materials}
    for m in [m for m in bpy.data.materials if m.name in used_materials and m.name not in material_maps]:
        recipe_hash=material_cache.recipe(m);cached=old_cache.get(m.name)
        if reuse and material_cache.valid(cached,recipe_hash,TEX):
            print('REUSE VERIFIED PBR TILES',m.name,flush=True);maps=dict(cached['maps']);material_maps[m.name]=maps;new_cache[m.name]=cached;attach_maps(m,maps);continue
        print('BAKE',m.name,flush=True);tile.data.materials.clear();tile.data.materials.append(m);nodes=m.node_tree.nodes;links=m.node_tree.links;bs=next(n for n in nodes if n.type=='BSDF_PRINCIPLED');out=next(n for n in nodes if n.type=='OUTPUT_MATERIAL');saved=list(out.inputs['Surface'].links)[0].from_socket
        target=nodes.new('ShaderNodeTexImage');nodes.active=target;maps={}
        for channel in ['BaseColor','Normal','Roughness','Metallic']:
            size=(2048 if m.name=='Krag_SandstoneSkin' else 1024) if channel in ['BaseColor','Normal'] else 128
            if m.name in ['Krag_Recess','Krag_Amber','Krag_EyeWhite','Krag_Ivory']:size=256 if channel in ['BaseColor','Normal'] else 32
            im=bpy.data.images.new(m.name+'_'+channel,width=size,height=size,alpha=False);im.colorspace_settings.name='sRGB' if channel=='BaseColor' else 'Non-Color';target.image=im;nodes.active=target
            for n in nodes:n.select=False
            target.select=True
            if channel=='Normal':
                links.new(saved,out.inputs['Surface']);bpy.ops.object.bake(type='NORMAL',normal_space='TANGENT')
            else:
                emit=nodes.new('ShaderNodeEmission');source=bs.inputs[{'BaseColor':'Base Color','Roughness':'Roughness','Metallic':'Metallic'}[channel]]
                if source.is_linked:links.new(source.links[0].from_socket,emit.inputs['Color'])
                else:
                    value=source.default_value;emit.inputs['Color'].default_value=(value,value,value,1) if isinstance(value,(int,float)) else value
                links.new(emit.outputs[0],out.inputs['Surface']);bpy.ops.object.bake(type='EMIT');nodes.remove(emit)
            path=TEX/(m.name+'_'+channel+'.png');im.filepath_raw=str(path);im.file_format='PNG';im.save();maps[channel]=path.name
        links.new(saved,out.inputs['Surface']);nodes.remove(target);material_maps[m.name]=maps
        new_cache[m.name]={'recipeHash':recipe_hash,'maps':maps,'mapHashes':{c:material_cache.sha(TEX/f) for c,f in maps.items()}}
        attach_maps(m,maps)
    bpy.data.objects.remove(tile,do_unlink=True)
    for o in bpy.data.objects:
        if o.name in visibility:o.hide_render=visibility[o.name]
    # Sharply reduce tiny rivet topology only if needed; meshes remain editable at source.
    for g,o in modules.items():
        # Closed surface winding is consistent before reduction/export.
        if not o.data.shape_keys:
            bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free()
        # Retain high-resolution master; collapse near-planar excess voxel tessellation for runtime.
        tris=sum(len(p.vertices)-2 for p in o.data.polygons)
        target=45000 if g=='Head' else 50000 if g=='Body' else 24000 if g.startswith('BioForearm') else 18000 if g.startswith('BioArm') else 14000
        if '--optimize' in sys.argv and tris>target and not o.data.shape_keys:
            bpy.context.view_layer.objects.active=o;o.hide_set(False);dec=o.modifiers.new('Runtime topology reduction','DECIMATE');dec.ratio=target/tris
            while o.modifiers[0]!=dec:bpy.ops.object.modifier_move_up(modifier=dec.name)
            bpy.ops.object.modifier_apply(modifier=dec.name)
        # Tiles represent one square metre. Preserve physical texel density after island packing.
        if o.data.uv_layers and not o.get('runtime_uv_atlas',False):
            o.data.calc_loop_triangles();uv=o.data.uv_layers.active.data;uv_area=0.0
            for tri in o.data.loop_triangles:
                a,b,c=[uv[i].uv for i in tri.loops];ab=b-a;ac=c-a;uv_area+=abs(ab.x*ac.y-ab.y*ac.x)*.5
            surface_area=sum(poly.area for poly in o.data.polygons)
            factor=math.sqrt(surface_area/max(uv_area,1e-10))
            for loop in uv:loop.uv*=factor
            o['runtime_uv_metres_scale']=factor
    for g,o in modules.items():o.hide_render=g in contract['variants']['Krag_Natural']['off'];o.hide_set(o.hide_render)
    rig.animation_data.action=bpy.data.actions['Idle'];scene.frame_set(1)
    contract['material_maps']=material_maps;contract['materials']=list(material_maps);contract['bone_count']=len(rig.data.bones);contract['runtime_triangles_all_modules']=sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in modules.values())
    (OUT/'krag_asset_contract.json').write_text(json.dumps(contract,indent=2),newline='\n')
    cache_path.write_text(json.dumps({'schemaVersion':1,'sourceBlendSha256':source_sha,'materials':new_cache},indent=2),newline='\n')
    contract['source_blend_sha256']=source_sha
    (OUT/'krag_asset_contract.json').write_text(json.dumps(contract,indent=2),newline='\n')
    save_manifest();bpy.ops.wm.save_as_mainfile(filepath=str(runtime_destination),compress=True);bpy.ops.file.make_paths_relative();bpy.ops.wm.save_as_mainfile(filepath=str(runtime_destination),compress=True)
    print('BAKE/SAVE COMPLETE. Run a fresh process with -- --export-only next.',flush=True)
else:
    material_maps=contract['material_maps']
    # Export each character assembly with all seven actions and its visible weapon.
    for name,v in ({} if '--animations-only' in sys.argv else contract['variants']).items():
        bpy.ops.object.select_all(action='DESELECT');rig.hide_set(False)
        copies=[];copy_meshes=[]
        for g,o in modules.items():
            if g in v['off'] and g!='Weapon_R':continue
            dupe=o.copy();dupe.data=o.data.copy();bpy.context.collection.objects.link(dupe);dupe.hide_set(False);dupe.hide_render=False;dupe.select_set(True);copies.append(dupe);copy_meshes.append(dupe.data)
        bpy.context.view_layer.objects.active=copies[0];bpy.ops.object.join();assembly=copies[0];assembly.name=name+'_Mesh'
        # Shared UVMap and unique material slots survive consolidation into one runtime renderer.
        rig.select_set(True);bpy.context.view_layer.objects.active=rig;rig.animation_data.action=bpy.data.actions.get('Idle');scene.frame_set(1)
        present=[]
        if assembly.data.shape_keys:
            import numpy as np
            basis=np.empty(len(assembly.data.vertices)*3,dtype=np.float32);assembly.data.shape_keys.key_blocks['Basis'].data.foreach_get('co',basis)
            for shape in assembly.data.shape_keys.key_blocks:
                if shape.name=='Basis':continue
                coordinates=np.empty_like(basis);shape.data.foreach_get('co',coordinates)
                if np.max(np.abs(coordinates-basis))>1e-6:present.append(shape.name)
        missing_facial={d['morph'] for d in contract['deformation']['drivers'] if d['kind']=='facial'}-set(present)
        if missing_facial:raise RuntimeError('Assembly lost required facial targets: '+str(sorted(missing_facial)))
        v['deformation']={**contract['deformation'],'drivers':[d for d in contract['deformation']['drivers'] if d['morph'] in present],'morphs':present}
        if triangulate:v['triangulation']=triangulate_assembly(assembly.data,remove_zero_area='--remove-zero-area' in sys.argv)
        fp=OUT/(name+'.fbx');print('EXPORT',fp,flush=True)
        bpy.ops.export_scene.fbx(use_triangles=False,filepath=str(fp),use_selection=True,object_types={'MESH','ARMATURE'},axis_forward='-Z',axis_up='Y',apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',add_leaf_bones=False,use_armature_deform_only=False,mesh_smooth_type='FACE',use_mesh_modifiers=False,bake_anim=True,bake_anim_use_all_actions=True,bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_simplify_factor=0,path_mode='RELATIVE',embed_textures=False)
        v['runtime_triangles']=sum(len(p.vertices)-2 for p in assembly.data.polygons);v['runtime_material_slots']=len(assembly.data.materials);v['runtime_mesh_count']=1
        bpy.data.objects.remove(assembly,do_unlink=True)
        for mesh_data in copy_meshes:
            try:
                if mesh_data.users==0:bpy.data.meshes.remove(mesh_data)
            except ReferenceError:pass
        import gc;gc.collect()
    # Per-clip files also support import pipelines that only read one FBX take.
    (OUT/'animations').mkdir(exist_ok=True)
    bind_data=bpy.data.meshes.new('AnimationBindMesh');bind_data.from_pydata([(0,0,0),(.001,0,0),(0,.001,0)],[],[(0,1,2)]);bind_data.update();bind_mesh=bpy.data.objects.new('AnimationBindMesh',bind_data);bpy.context.collection.objects.link(bind_mesh);bind_mesh.parent=rig;bind_mesh.vertex_groups.new(name='Root').add([0,1,2],1,'REPLACE');bind_modifier=bind_mesh.modifiers.new('Explicit rest binding','ARMATURE');bind_modifier.object=rig
    for clip in contract['clips']:
        export_contract.select_action(bpy,rig,bpy.data.actions[clip])
        bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig;rig.animation_data.action=bpy.data.actions[clip];scene.frame_start=1;scene.frame_end=int(bpy.data.actions[clip].frame_range[1]);scene.frame_set(1);scene.name=clip;bind_mesh.select_set(True)
        bpy.ops.export_scene.fbx(use_triangles=triangulate,filepath=str(OUT/'animations'/(clip+'.fbx')),use_selection=True,object_types={'MESH','ARMATURE'},use_mesh_modifiers=False,axis_forward='-Z',axis_up='Y',apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',add_leaf_bones=False,use_armature_deform_only=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_simplify_factor=0)
    bpy.data.objects.remove(bind_mesh,do_unlink=True);bpy.data.meshes.remove(bind_data)
    # Preserve a separate modular firearm source export; variant FBXs already include it.
    bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);modules['Weapon_R'].hide_set(False);modules['Weapon_R'].select_set(True)
    bpy.ops.export_scene.fbx(use_triangles=triangulate,filepath=str(OUT/'Krag_Weapon.fbx'),use_selection=True,object_types={'MESH','ARMATURE'},axis_forward='-Z',axis_up='Y',apply_unit_scale=True,add_leaf_bones=False,bake_anim=False,path_mode='RELATIVE')
    contract['geometryExport']={'triangulated':triangulate,'method':'Temporary assembly BMesh triangulation with cached shape coordinates and corner normals restored' if triangulate else 'Original polygon topology'}
    contract['exports']=[n+'.fbx' for n in contract['variants']]+['Krag_Weapon.fbx'];contract['files_are_generated']=True
    (OUT/'krag_asset_contract.json').write_text(json.dumps(contract,indent=2),newline='\n');save_manifest()
    print('EXPORT COMPLETE. Render validation runs separately.',flush=True)
