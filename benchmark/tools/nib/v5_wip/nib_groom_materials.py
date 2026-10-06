"""Concept-region color studies for the isolated Nib source, not shared maps.

Numeric palettes are authoring proposals in sRGB, converted to shader-linear.
All fields use UV coordinates so standard opaque PBR maps can be baked later.
"""
import bpy

PALETTES={
    'head':((.48,.39,.29),(.80,.74,.63)),
    'innerWisps':((.56,.45,.34),(.88,.82,.71)),
    'outerEar':((.36,.22,.13),(.67,.46,.25)),
    'innerSkin':((.43,.25,.23),(.70,.46,.39)),
    'outerUndercoat':((.39,.25,.14),(.62,.43,.24)),
}

def linear(color):
    return tuple(c/12.92 if c<=.04045 else ((c+.055)/1.055)**2.4 for c in color)+(1,)

def make_region(source,name,palette,strands=False,roughness=.68):
    material=bpy.data.materials[source].copy();material.name=name
    nodes=material.node_tree.nodes;links=material.node_tree.links
    bs=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
    for socket in ['Base Color','Roughness','Metallic']:
        for link in list(bs.inputs[socket].links):links.remove(link)
    bs.inputs['Roughness'].default_value=roughness;bs.inputs['Metallic'].default_value=0
    uv=nodes.new('ShaderNodeTexCoord');ramp=nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position=.10;ramp.color_ramp.elements[0].color=linear(palette[0])
    ramp.color_ramp.elements[1].position=.94;ramp.color_ramp.elements[1].color=linear(palette[1])
    if strands:
        axis=nodes.new('ShaderNodeSeparateXYZ');links.new(uv.outputs['UV'],axis.inputs[0]);links.new(axis.outputs['Y'],ramp.inputs[0])
        bs.inputs['Subsurface Weight'].default_value=0
        for link in list(bs.inputs['Normal'].links):links.remove(link)
        noise=nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=11;noise.inputs['Detail'].default_value=.5
        links.new(uv.outputs['UV'],noise.inputs['Vector'])
        variation=nodes.new('ShaderNodeMapRange');variation.inputs['From Min'].default_value=0;variation.inputs['From Max'].default_value=1
        variation.inputs['To Min'].default_value=.86;variation.inputs['To Max'].default_value=1.08
        links.new(noise.outputs['Fac'],variation.inputs['Value'])
        tint=nodes.new('ShaderNodeMixRGB');tint.blend_type='MULTIPLY';tint.inputs[0].default_value=1
        links.new(ramp.outputs['Color'],tint.inputs[1]);links.new(variation.outputs['Result'],tint.inputs[2])
        links.new(tint.outputs['Color'],bs.inputs['Base Color'])
    else:
        noise=nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=7.5;noise.inputs['Detail'].default_value=2
        links.new(uv.outputs['UV'],noise.inputs['Vector']);links.new(noise.outputs['Fac'],ramp.inputs[0])
        bs.inputs['Subsurface Weight'].default_value=.08
        links.new(ramp.outputs['Color'],bs.inputs['Base Color'])
    material.diffuse_color=linear(palette[1]);material['paletteProposalSRGB']=str(palette)
    material['portableBakeCoordinates']='UVMap; region has its own opaque PBR material'
    return material

def create_regions(collection):
    materials={
        'head':make_region('Nib_Hair','Nib_v5_HeadFur',PALETTES['head'],True,.60),
        'innerWisps':make_region('Nib_Hair','Nib_v5_InnerEarWisps',PALETTES['innerWisps'],True,.65),
        'outerEar':make_region('Nib_Hair','Nib_v5_TawnyEarFur',PALETTES['outerEar'],True,.68),
        'innerSkin':make_region('Nib_EarInner','Nib_v5_DustyPinkEar',PALETTES['innerSkin'],False,.66),
        'outerUndercoat':make_region('Nib_Skin','Nib_v5_TawnyEarUndercoat',PALETTES['outerUndercoat'],False,.75),
    }
    assignments=[]
    for obj in collection.objects:
        region=None
        if obj.name.startswith('Ear inner velvet'):region='innerSkin'
        elif obj.name.startswith(('Fennec cupped ear','Rounded auricle cartilage rim','Auricle basal cartilage fold')):region='outerUndercoat'
        if region:
            obj.data.materials.clear();obj.data.materials.append(materials[region])
            for p in obj.data.polygons:p.material_index=0
            assignments.append({'object':obj.name,'region':region,'material':materials[region].name})
    return materials,{'status':'Ungenerated palette proposal until next native review',
                      'reference':'concept-art/02-nib-character-sheet.png',
                      'paletteColorSpace':'sRGB converted to linear shader colors',
                      'palettesSRGB':PALETTES,'earSurfaceAssignments':assignments,
                      'sharedMapsUpdated':False}
