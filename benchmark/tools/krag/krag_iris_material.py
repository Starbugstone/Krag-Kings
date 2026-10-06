"""Restrained amber iris pigment in anatomical ocular coordinates.

The source iris carries normalized coordinates and a mask through its creature
fit. Portable output must bake this onto the actual Face module's UV atlas.
A generic world-space material tile cannot preserve this treatment.
"""
import bpy
import numpy as np


def coordinates(obj,source_points,center):
    delta=np.asarray(source_points)-np.asarray(center)
    planar=delta[:,[0,2]]
    radius=float(np.quantile(np.linalg.norm(planar,axis=1),.99))
    if not .004<radius<.009:raise RuntimeError('Unexpected reference iris radius '+str(radius))
    data=np.column_stack((planar/radius,np.zeros(len(planar)))).astype(np.float32)
    attribute=obj.data.attributes.new('Krag_IrisCoord','FLOAT_VECTOR','POINT');attribute.data.foreach_set('vector',data.ravel())
    mask=obj.data.attributes.new('Krag_IrisMask','FLOAT','POINT');mask.data.foreach_set('value',np.ones(len(data),dtype=np.float32))


def configure(material):
    nodes=material.node_tree.nodes;links=material.node_tree.links
    bs=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
    original=bs.inputs['Base Color'].links[0].from_socket
    coord=nodes.new('ShaderNodeAttribute');coord.attribute_name='Krag_IrisCoord';coord.label='Original fitted ocular radial coordinates'
    mask=nodes.new('ShaderNodeAttribute');mask.attribute_name='Krag_IrisMask'
    separate=nodes.new('ShaderNodeSeparateXYZ');links.new(coord.outputs['Vector'],separate.inputs[0])
    radius=nodes.new('ShaderNodeVectorMath');radius.operation='LENGTH';links.new(coord.outputs['Vector'],radius.inputs[0])
    def scalar(operation,a,b=None):
        node=nodes.new('ShaderNodeMath');node.operation=operation
        for i,value in enumerate([a,b] if b is not None else [a]):
            if isinstance(value,(int,float)):node.inputs[i].default_value=value
            else:links.new(value,node.inputs[i])
        return node.outputs[0]
    theta=scalar('ARCTAN2',separate.outputs['Y'],separate.outputs['X'])
    waviness=scalar('MULTIPLY',scalar('SINE',scalar('MULTIPLY',theta,17)),1.8)
    phase=scalar('ADD',scalar('ADD',scalar('MULTIPLY',theta,79),scalar('MULTIPLY',radius.outputs['Value'],29)),waviness)
    fibres=scalar('SINE',phase)
    fibres=scalar('MULTIPLY_ADD',fibres,.16)
    fibres.node.inputs[2].default_value=.83
    palette=nodes.new('ShaderNodeValToRGB');palette.label='Amber radial pigment and dark limbal edge'
    values=[(.00,(.055,.022,.004,1)),(.36,(.34,.130,.010,1)),(.53,(.44,.202,.020,1)),(.77,(.25,.090,.008,1)),(.91,(.050,.020,.004,1)),(1,(.018,.009,.003,1))]
    ramp=palette.color_ramp;ramp.elements.remove(ramp.elements[-1]);ramp.elements[0].position=values[0][0];ramp.elements[0].color=values[0][1]
    for position,color in values[1:]:element=ramp.elements.new(position);element.color=color
    links.new(radius.outputs['Value'],palette.inputs[0])
    modulation=nodes.new('ShaderNodeMixRGB');modulation.blend_type='MULTIPLY';modulation.inputs[0].default_value=1
    links.new(palette.outputs['Color'],modulation.inputs[1]);links.new(fibres,modulation.inputs[2])
    mix=nodes.new('ShaderNodeMixRGB');links.new(mask.outputs['Fac'],mix.inputs[0]);links.new(original,mix.inputs[1]);links.new(modulation.outputs[0],mix.inputs[2]);links.new(mix.outputs[0],bs.inputs['Base Color'])
    bs.inputs['Roughness'].default_value=.18;bs.inputs['Metallic'].default_value=0
    relief=nodes.new('ShaderNodeBump');relief.inputs['Strength'].default_value=.16;relief.inputs['Distance'].default_value=.000018
    links.new(scalar('MULTIPLY',fibres,mask.outputs['Fac']),relief.inputs['Height']);links.new(relief.outputs['Normal'],bs.inputs['Normal'])
    material['requiresActualMeshAtlas']='Krag_IrisCoord and Krag_IrisMask: bake Face module UVs'
