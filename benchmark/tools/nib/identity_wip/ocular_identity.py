"""Prepared opaque ocular pigment study; no new transparent cornea contract.

Actual existing shell geometry and eye pivots remain unchanged. The point
attribute requires baking on the real iris UV atlas, never a generic carrier.
This material has not been applied, rendered, baked or imported in an engine.
"""
import bpy
import numpy as np


def iris_coordinates(obj):
    points = np.asarray([v.co[:] for v in obj.data.vertices], np.float64)
    center = (points.min(0)+points.max(0))*.5
    half_span = (points.max(0)-points.min(0))*.5
    if not (.006 < half_span[0] < .011 and .004 < half_span[2] < .009):
        raise RuntimeError('Actual fitted iris dimensions differ from audited source')
    normalized = np.column_stack(((points[:, 0]-center[0])/half_span[0],
                                  (points[:, 2]-center[2])/half_span[2],
                                  np.zeros(len(points)))).astype(np.float32)
    name = 'Nib_IrisCoord'
    attribute = obj.data.attributes.get(name) or obj.data.attributes.new(name, 'FLOAT_VECTOR', 'POINT')
    if attribute.domain != 'POINT' or attribute.data_type != 'FLOAT_VECTOR':
        raise RuntimeError('Existing iris coordinate attribute is incompatible')
    attribute.data.foreach_set('vector', normalized.ravel())
    return {'object': obj.name, 'attribute': name, 'centerLocalMeters': center.tolist(),
            'halfSpanLocalMeters': half_span.tolist(),
            'anteriorSurfaceDepthRangeMeters': float(points[:, 1].max()-points[:, 1].min()),
            'geometryAndPivotsChanged': False,
            'coordinateMeaning': 'Anatomical fitted planar X/Z; source topology retains the actual slit pupil opening'}


def materials():
    output = {}
    for part, name, roughness in [('globe', 'Nib_IdentityOcularGlobe', .20),
                                   ('iris', 'Nib_IdentityOcularIris', .25)]:
        if bpy.data.materials.get(name):
            raise RuntimeError('Preserve any previous ocular study material')
        material = bpy.data.materials.new(name)
        material.use_nodes = True
        nodes = material.node_tree.nodes
        links = material.node_tree.links
        bs = nodes.get('Principled BSDF')
        bs.inputs['Metallic'].default_value = 0
        bs.inputs['Roughness'].default_value = roughness
        bs.inputs['IOR'].default_value = 1.38
        bs.inputs['Subsurface Weight'].default_value = 0
        # A restrained warm dark exposed globe remains consistent with the
        # concept's nearly absent white. It is no longer leather albedo/noise.
        bs.inputs['Base Color'].default_value = (.022, .014, .008, 1)
        if part == 'iris':
            coord = nodes.new('ShaderNodeAttribute')
            coord.attribute_name = 'Nib_IrisCoord'
            separate = nodes.new('ShaderNodeSeparateXYZ')
            links.new(coord.outputs['Vector'], separate.inputs[0])
            radius = nodes.new('ShaderNodeVectorMath'); radius.operation = 'LENGTH'
            links.new(coord.outputs['Vector'], radius.inputs[0])

            def scalar(operation, a, b=None):
                node = nodes.new('ShaderNodeMath'); node.operation = operation
                for i, value in enumerate([a] if b is None else [a, b]):
                    if isinstance(value, (int, float)):
                        node.inputs[i].default_value = value
                    else:
                        links.new(value, node.inputs[i])
                return node.outputs[0]

            angle = scalar('ARCTAN2', separate.outputs['Y'], separate.outputs['X'])
            # Unequal low-amplitude fibres avoid a perfectly repeating star.
            low = scalar('SINE', scalar('ADD', scalar('MULTIPLY', angle, 47), scalar('MULTIPLY', radius.outputs['Value'], 23)))
            high = scalar('SINE', scalar('ADD', scalar('MULTIPLY', angle, 113), scalar('MULTIPLY', radius.outputs['Value'], -37)))
            variation = scalar('ADD', .84, scalar('ADD', scalar('MULTIPLY', low, .11), scalar('MULTIPLY', high, .05)))
            palette = nodes.new('ShaderNodeValToRGB')
            palette.label = 'Warm amber pigment with limbal and pupil-side variation'
            values = [(0, (.032, .012, .002, 1)), (.22, (.16, .056, .005, 1)),
                      (.42, (.43, .19, .024, 1)), (.73, (.29, .115, .013, 1)),
                      (.9, (.080, .028, .004, 1)), (1, (.017, .009, .002, 1))]
            ramp = palette.color_ramp
            ramp.elements.remove(ramp.elements[-1])
            ramp.elements[0].position, ramp.elements[0].color = values[0]
            for position, color in values[1:]:
                entry = ramp.elements.new(position); entry.color = color
            links.new(radius.outputs['Value'], palette.inputs[0])
            multiply = nodes.new('ShaderNodeMixRGB'); multiply.blend_type = 'MULTIPLY'
            multiply.inputs[0].default_value = 1
            links.new(palette.outputs['Color'], multiply.inputs[1]); links.new(variation, multiply.inputs[2])
            links.new(multiply.outputs[0], bs.inputs['Base Color'])
            # No generic skin/leather bump and no apparent depth claimed from
            # pigment alone. Existing opaque shell curvature remains visible.
            material['requiresActualMeshAtlas'] = 'Nib_IrisCoord on actual iris UVs; generic tile bake forbidden'
        material['identityStudyStatus'] = 'Prepared opaque ocular study; actual source/baked/engine comparison required'
        output[part] = material
    return output
