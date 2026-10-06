"""Portable PBR bake for geometry-dependent continuous facial skin regions.

Runs only inside the separate runtime bake job. The editable source is untouched.
The atlas replaces Head material slots, and Head UVs must not be density-scaled.
"""
import bpy,json,hashlib
from pathlib import Path


def bake(head,texture_dir,optical=False):
    attribute='Krag_IrisCoord' if optical else 'Krag_SkinRegion'
    if attribute not in head.data.attributes:
        raise RuntimeError('Facial atlas requested without source field '+attribute)
    uv=head.data.uv_layers.active
    if uv is None or any(min(x.uv)<-1e-5 or max(x.uv)>1.00001 for x in uv.data):
        raise RuntimeError('Facial atlas requires packed UV coordinates within [0,1]')
    source_materials=list(head.data.materials)
    if not source_materials:raise RuntimeError('Head has no source materials')
    bpy.ops.object.select_all(action='DESELECT');head.hide_set(False);head.hide_render=False;head.select_set(True);bpy.context.view_layer.objects.active=head
    modifier_visibility={m.name:(m.show_viewport,m.show_render) for m in head.modifiers if m.type=='ARMATURE'}
    for m in head.modifiers:
        if m.type=='ARMATURE':m.show_viewport=False;m.show_render=False
    # Bone-driven morphs are sampled at neutral values; temporarily mute their
    # drivers rather than baking a facial performance into material coordinates.
    keys=head.data.shape_keys
    driver_states=[]
    if keys:
        if keys.animation_data:
            for curve in keys.animation_data.drivers:driver_states.append((curve,curve.mute));curve.mute=True
        for key in keys.key_blocks:key.value=0
    records=[]
    for material in source_materials:
        nodes=material.node_tree.nodes;links=material.node_tree.links
        bs=next(n for n in nodes if n.type=='BSDF_PRINCIPLED');out=next(n for n in nodes if n.type=='OUTPUT_MATERIAL')
        target=nodes.new('ShaderNodeTexImage');nodes.active=target
        records.append((material,bs,out,out.inputs['Surface'].links[0].from_socket,target))
    texture_dir=Path(texture_dir);texture_dir.mkdir(parents=True,exist_ok=True)
    maps={};name='Krag_OpticalDetailsAtlas' if optical else 'Krag_FacialSkinAtlas'
    for channel,size in [('BaseColor',2048 if optical else 4096),('Normal',2048 if optical else 4096),('Roughness',1024),('Metallic',128)]:
        image=bpy.data.images.new(name+'_'+channel,width=size,height=size,alpha=False)
        image.colorspace_settings.name='sRGB' if channel=='BaseColor' else 'Non-Color'
        temporary_emission=[]
        for material,bs,out,saved,target in records:
            nodes=material.node_tree.nodes;links=material.node_tree.links
            for node in nodes:node.select=False
            target.select=True;target.image=image;nodes.active=target
            if channel=='Normal':links.new(saved,out.inputs['Surface'])
            else:
                emit=nodes.new('ShaderNodeEmission');temporary_emission.append((material,emit))
                source=bs.inputs[{'BaseColor':'Base Color','Roughness':'Roughness','Metallic':'Metallic'}[channel]]
                if source.is_linked:links.new(source.links[0].from_socket,emit.inputs['Color'])
                else:
                    value=source.default_value;emit.inputs['Color'].default_value=(value,value,value,1) if isinstance(value,(int,float)) else value
                links.new(emit.outputs[0],out.inputs['Surface'])
        bpy.ops.object.bake(type='NORMAL' if channel=='Normal' else 'EMIT',normal_space='TANGENT',margin=16,use_clear=True)
        image.filepath_raw=str(texture_dir/(name+'_'+channel+'.png'));image.file_format='PNG';image.save();maps[channel]=Path(image.filepath_raw).name
        for material,emit in temporary_emission:material.node_tree.nodes.remove(emit)
        print('FACIAL ATLAS SAVED',channel,size,flush=True)
    for material,bs,out,saved,target in records:
        material.node_tree.links.new(saved,out.inputs['Surface']);material.node_tree.nodes.remove(target)
    for curve,muted in driver_states:curve.mute=muted
    for modifier in head.modifiers:
        if modifier.name in modifier_visibility:modifier.show_viewport,modifier.show_render=modifier_visibility[modifier.name]
    material=bpy.data.materials.new(name);material.use_nodes=True
    head.data.materials.clear();head.data.materials.append(material)
    for polygon in head.data.polygons:polygon.material_index=0
    head['runtime_uv_atlas']=True
    receipt={'kind':'Actual mesh PBR atlas; preserves geometry attribute '+attribute,'material':name,
             'maps':maps,'mapHashes':{c:hashlib.sha256((texture_dir/f).read_bytes()).hexdigest() for c,f in maps.items()},
             'vertices':len(head.data.vertices),'triangles':sum(len(p.vertices)-2 for p in head.data.polygons),
             'uvDensityNormalizationSkipped':True,'status':'Baked; source-versus-runtime actual render still required'}
    return material,maps,receipt
