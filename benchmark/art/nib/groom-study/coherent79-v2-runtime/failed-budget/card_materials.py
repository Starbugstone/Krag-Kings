"""Prepared Blender counterpart of the agreed portable MASK material fields."""
from pathlib import Path
import bpy

def create_card_material(entry,texture_dir):
    texture_dir=Path(texture_dir)
    material=bpy.data.materials.new(entry['name']);material.use_nodes=True
    material.use_backface_culling=False
    nodes=material.node_tree.nodes;links=material.node_tree.links
    nodes.clear();out=nodes.new('ShaderNodeOutputMaterial')
    shader=nodes.new('ShaderNodeBsdfPrincipled')
    shader.inputs['Roughness'].default_value=.6
    shader.inputs['Metallic'].default_value=0
    shader.inputs['Specular IOR Level'].default_value=.32
    shader.inputs['Subsurface Weight'].default_value=0
    uv=nodes.new('ShaderNodeTexCoord')
    images={}
    for field,color in [('baseColor','sRGB'),('normal','Non-Color'),('roughness','Non-Color'),('metallic','Non-Color')]:
        path=texture_dir/Path(entry[field]).name
        if not path.exists():raise RuntimeError('Missing generated fur map: '+str(path))
        image=bpy.data.images.load(str(path),check_existing=True);image.colorspace_settings.name=color
        if field=='baseColor':image.alpha_mode='STRAIGHT'
        node=nodes.new('ShaderNodeTexImage');node.image=image;node.extension='EXTEND'
        node.interpolation='Linear';links.new(uv.outputs['UV'],node.inputs['Vector']);images[field]=node
    links.new(images['baseColor'].outputs['Color'],shader.inputs['Base Color'])
    links.new(images['roughness'].outputs['Color'],shader.inputs['Roughness'])
    links.new(images['metallic'].outputs['Color'],shader.inputs['Metallic'])
    normal=nodes.new('ShaderNodeNormalMap');normal.space='TANGENT'
    links.new(images['normal'].outputs['Color'],normal.inputs['Color']);links.new(normal.outputs['Normal'],shader.inputs['Normal'])
    # Binary threshold reproduces the engine MASK contract without relying on
    # sorted transparency or an editor-only alpha blend mode.
    threshold=nodes.new('ShaderNodeMath');threshold.operation='GREATER_THAN'
    threshold.inputs[1].default_value=entry['alphaClipThreshold']
    links.new(images['baseColor'].outputs['Alpha'],threshold.inputs[0])
    transparent=nodes.new('ShaderNodeBsdfTransparent');mix=nodes.new('ShaderNodeMixShader')
    links.new(threshold.outputs[0],mix.inputs[0]);links.new(transparent.outputs[0],mix.inputs[1])
    links.new(shader.outputs[0],mix.inputs[2]);links.new(mix.outputs[0],out.inputs['Surface'])
    material['portableAlphaMode']='MASK';material['portableAlphaClipThreshold']=entry['alphaClipThreshold']
    material['portableDoubleSided']=True;material['portableNormalConvention']='OpenGL +Y'
    return material
