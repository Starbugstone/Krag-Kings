"""Prepared actual-field PBR baking helpers. No bake has been run yet.

Face attributes are baked on the real mesh, with new nonoverlapping UVs.
UV-only groom fields are evaluated on their exact original 0..1 coordinate
domain, preserving each strand's clump U and root-to-tip V coordinates.
"""
import hashlib
from pathlib import Path
import bpy
import numpy as np

CHANNELS={'BaseColor':'Base Color','Roughness':'Roughness','Metallic':'Metallic'}

def sha(path):
    # Large source/FBX files must not allocate a second full payload just to hash.
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()

def principled(material):
    nodes=[n for n in material.node_tree.nodes if n.type=='BSDF_PRINCIPLED']
    if len(nodes)!=1:raise RuntimeError('Expected one Principled surface: '+material.name)
    return nodes[0]

def uv_field_audit(material):
    """Reject geometry/object-dependent inputs rather than silently flattening them."""
    root=principled(material);pending=[];seen=set();coordinate_links=[]
    for socket in ['Base Color','Normal','Roughness','Metallic']:
        pending.extend((l.from_node,l.from_socket.name) for l in root.inputs[socket].links)
    while pending:
        node,socket=pending.pop()
        if (node.name,socket) in seen:continue
        seen.add((node.name,socket))
        if node.type in {'ATTRIBUTE','VERTEX_COLOR','NEW_GEOMETRY','OBJECT_INFO','PARTICLE_INFO','HAIR_INFO','BEVEL','BUMP','GROUP'}:
            raise RuntimeError('UV carrier cannot preserve '+material.name+'/'+node.name+' ('+node.type+')')
        if node.type=='NORMAL_MAP' and node.space!='TANGENT':
            raise RuntimeError('UV carrier requires tangent-space normals: '+material.name)
        if node.type=='TEX_COORD':
            if socket!='UV':raise RuntimeError('Non-UV coordinate field in '+material.name+': '+socket)
            coordinate_links.append(node.name+'.UV')
        if node.type.startswith('TEX_') and node.type not in {'TEX_IMAGE','TEX_COORD'}:
            if 'Vector' in node.inputs and not node.inputs['Vector'].is_linked:
                raise RuntimeError('Implicit Generated coordinate field in '+material.name+'/'+node.name)
        for inp in node.inputs:pending.extend((l.from_node,l.from_socket.name) for l in inp.links)
    return {'visitedSocketCount':len(seen),'explicitUvCoordinates':coordinate_links,
            'geometryDependentInputs':False,'implicitImageCoordinates':'same UVMap domain'}

def preserve_shader_uv(material,source_uv,previous_uv):
    nodes=material.node_tree.nodes;links=material.node_tree.links
    uv=nodes.new('ShaderNodeUVMap');uv.uv_map=source_uv
    for node in list(nodes):
        if node==uv:continue
        if node.type=='TEX_IMAGE' and not node.inputs['Vector'].is_linked:
            links.new(uv.outputs['UV'],node.inputs['Vector'])
        if node.type=='TEX_COORD':
            for link in list(node.outputs['UV'].links):links.new(uv.outputs['UV'],link.to_socket)
        if node.type in {'NORMAL_MAP','UVMAP'} and node.uv_map in {'',previous_uv}:node.uv_map=source_uv

def make_face_uv(head):
    original=head.data.uv_layers.active
    if original is None:raise RuntimeError('Face has no source UV coordinates')
    previous_uv=original.name
    original.name='Nib_SourceUV';original.active_render=True
    source_uv=original.name
    new=head.data.uv_layers.new(name='UVMap');head.data.uv_layers.active=new
    new.active_render=True
    for material in head.data.materials:preserve_shader_uv(material,source_uv,previous_uv)
    bpy.ops.object.select_all(action='DESELECT');head.hide_set(False);head.select_set(True)
    bpy.context.view_layer.objects.active=head
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=1.1519173,margin_method='FRACTION',island_margin=.015,area_weight=.25,correct_aspect=True,scale_to_bounds=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    new=head.data.uv_layers['UVMap']
    if any(min(p.uv)<-1e-6 or max(p.uv)>1.000001 for p in new.data):raise RuntimeError('Face atlas UVs outside0..1')
    return source_uv

def source_uv_domain(objects,material):
    """A finite 0..1 carrier cannot preserve fields sampled outside that domain."""
    receipts=[]
    for obj in objects:
        slots=[i for i,m in enumerate(obj.data.materials) if m==material]
        if not slots:continue
        layer=obj.data.uv_layers.active
        if layer is None:raise RuntimeError('Region mesh lacks UVs: '+obj.name)
        indices=[i for p in obj.data.polygons if p.material_index in slots for i in p.loop_indices]
        if not indices:continue
        values=np.asarray([tuple(layer.data[i].uv) for i in indices],dtype=np.float64)
        if not np.isfinite(values).all() or values.min()<-1e-6 or values.max()>1.000001:
            raise RuntimeError('Region field needs an actual-mesh bake, UVs leave carrier domain: '+obj.name)
        receipts.append({'object':obj.name,'uvLayer':layer.name,'minimum':values.min(0).tolist(),
                         'maximum':values.max(0).tolist(),'sampledCorners':len(indices)})
    if not receipts:raise RuntimeError('Field material has no authored surface assignments: '+material.name)
    return receipts

def plane(material):
    mesh=bpy.data.meshes.new('Nib UV-field bake carrier')
    mesh.from_pydata([(0,0,0),(1,0,0),(1,1,0),(0,1,0)],[],[(0,1,2,3)]);mesh.update()
    uv=mesh.uv_layers.new(name='UVMap')
    for loop in mesh.loops:uv.data[loop.index].uv=mesh.vertices[loop.vertex_index].co.xy
    obj=bpy.data.objects.new('Nib UV-field bake carrier',mesh);bpy.context.scene.collection.objects.link(obj)
    mesh.materials.append(material);return obj

def bake_maps(obj,name,texture_dir,sizes):
    """Bake connected source shader fields, preserving geometry attributes."""
    texture_dir=Path(texture_dir);texture_dir.mkdir(parents=True,exist_ok=True)
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=8
    scene.render.threads_mode='FIXED';scene.render.threads=4
    bpy.ops.object.select_all(action='DESELECT');obj.hide_set(False);obj.hide_render=False;obj.select_set(True)
    bpy.context.view_layer.objects.active=obj
    modifiers=[(m,m.show_viewport,m.show_render) for m in obj.modifiers if m.type=='ARMATURE']
    for m,_,_ in modifiers:m.show_viewport=False;m.show_render=False
    keys=obj.data.shape_keys;drivers=[];values=[]
    if keys:
        if keys.animation_data:
            for d in keys.animation_data.drivers:drivers.append((d,d.mute));d.mute=True
        for k in keys.key_blocks:values.append((k,k.value));k.value=0
    records=[];maps={}
    for material in set(obj.data.materials):
        bs=principled(material);nodes=material.node_tree.nodes
        out=next(n for n in nodes if n.type=='OUTPUT_MATERIAL' and n.is_active_output)
        saved=out.inputs['Surface'].links[0].from_socket
        target=nodes.new('ShaderNodeTexImage');nodes.active=target
        records.append((material,bs,out,saved,target))
    try:
        for channel,size in sizes.items():
            image=bpy.data.images.new(name+'_'+channel,width=size,height=size,alpha=False)
            image.colorspace_settings.name='sRGB' if channel=='BaseColor' else 'Non-Color'
            emissions=[]
            try:
                for mat,bs,out,saved,target in records:
                    nodes=mat.node_tree.nodes;links=mat.node_tree.links
                    for node in nodes:node.select=False
                    target.select=True;target.image=image;nodes.active=target
                    if channel=='Normal':links.new(saved,out.inputs['Surface'])
                    else:
                        emit=nodes.new('ShaderNodeEmission');emissions.append((mat,emit))
                        source=bs.inputs[CHANNELS[channel]]
                        if source.is_linked:links.new(source.links[0].from_socket,emit.inputs['Color'])
                        else:
                            value=source.default_value
                            emit.inputs['Color'].default_value=(value,value,value,1) if isinstance(value,(int,float)) else value
                        links.new(emit.outputs[0],out.inputs['Surface'])
                bpy.ops.object.bake(type='NORMAL' if channel=='Normal' else 'EMIT',normal_space='TANGENT',normal_r='POS_X',normal_g='POS_Y',normal_b='POS_Z',margin=16,use_clear=True,use_selected_to_active=False)
                path=texture_dir/(name+'_'+channel+'.png');image.filepath_raw=str(path);image.file_format='PNG';image.save()
                maps[channel]={'file':path.name,'sha256':sha(path),'resolution':size,'colorSpace':image.colorspace_settings.name}
                print('NIB_FIELD_BAKED',name,channel,size,flush=True)
            finally:
                for mat,emit in emissions:mat.node_tree.nodes.remove(emit)
                for mat,bs,out,saved,target in records:mat.node_tree.links.new(saved,out.inputs['Surface']);target.image=None
                bpy.data.images.remove(image)
    finally:
        for mat,bs,out,saved,target in records:
            mat.node_tree.links.new(saved,out.inputs['Surface']);mat.node_tree.nodes.remove(target)
        for driver,mute in drivers:driver.mute=mute
        for key,value in values:key.value=value
        for modifier,viewport,render in modifiers:modifier.show_viewport=viewport;modifier.show_render=render
    return maps

def portable_material(name,texture_dir,maps,template):
    material=bpy.data.materials.new(name);material.use_nodes=True
    bs=principled(material);original=principled(template)
    for socket in ['Subsurface Weight','Subsurface Radius','IOR','Specular IOR Level']:
        bs.inputs[socket].default_value=original.inputs[socket].default_value
    nodes=material.node_tree.nodes;links=material.node_tree.links
    for channel,entry in maps.items():
        image=bpy.data.images.load(str(Path(texture_dir)/entry['file']),check_existing=True)
        image.colorspace_settings.name=entry['colorSpace']
        node=nodes.new('ShaderNodeTexImage');node.image=image
        if channel=='Normal':
            normal=nodes.new('ShaderNodeNormalMap');normal.inputs['Strength'].default_value=1
            links.new(node.outputs['Color'],normal.inputs['Color']);links.new(normal.outputs['Normal'],bs.inputs['Normal'])
        else:links.new(node.outputs['Color'],bs.inputs[CHANNELS[channel]])
    material['runtimePbrBake']='Actual connected shader fields, not a replacement generic tile'
    return material

def head_mask_receipt(head):
    attribute=head.data.attributes.get('NibNoseMask')
    if attribute is None or attribute.domain!='POINT':raise RuntimeError('Missing point-domain nose mask')
    values=np.empty(len(attribute.data),dtype=np.float32);attribute.data.foreach_get('value',values)
    if not np.isfinite(values).all() or values.max()<.5:raise RuntimeError('No substantial authored nose-mask field to preserve')
    connected=[]
    for material in head.data.materials:
        pending=[l.from_node for l in principled(material).inputs['Base Color'].links];seen=set()
        while pending:
            node=pending.pop()
            if node.name in seen:continue
            seen.add(node.name)
            if node.type=='ATTRIBUTE' and node.attribute_name=='NibNoseMask':connected.append(material.name)
            for socket in node.inputs:pending.extend(l.from_node for l in socket.links)
    if not connected:raise RuntimeError('Nose-mask attribute is not connected to face Base Color')
    return {'attribute':'NibNoseMask','sourceValuesSha256':hashlib.sha256(values.tobytes()).hexdigest(),
            'minimum':float(values.min()),'maximum':float(values.max()),'verticesAboveHalf':int(np.sum(values>.5)),
            'connectedBaseColorMaterials':connected,
            'preservation':'Connected mask is evaluated on actual face during BaseColor bake; source attribute retained for audit'}
