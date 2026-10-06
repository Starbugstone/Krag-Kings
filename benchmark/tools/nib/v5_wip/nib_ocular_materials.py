"""Prepared smooth opaque ocular materials for the next isolated head study.

Not applied to promoted v4b. New slots require explicit PBR baking before any
engine export; this source shader is not itself a portable material handoff.
"""
import bpy

def create_ocular_materials():
    result={};evidence={}
    for part,source,name,rough in [('sclera','Nib_Dark','Nib_OcularGlobe',.16),
                                   ('iris','Nib_Eye','Nib_OcularIris',.20)]:
        material=bpy.data.materials[source].copy();material.name=name
        node=next(n for n in material.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
        removed=[]
        for socket in ['Normal','Roughness','Metallic','Subsurface Weight']:
            for link in list(node.inputs[socket].links):
                removed.append({'socket':socket,'sourceNode':link.from_node.name})
                material.node_tree.links.remove(link)
        node.inputs['Roughness'].default_value=rough
        node.inputs['Metallic'].default_value=0
        node.inputs['Subsurface Weight'].default_value=0
        result[part]=material
        evidence[part]={'material':name,'source':source,'removedInheritedLinks':removed,
                        'roughness':rough,'metallic':0,'subsurfaceWeight':0,
                        'normal':'smooth geometric shell; no generic skin/leather normal map',
                        'status':'Ungenerated next-study proposal; source review and PBR baking required'}
    return result,evidence
