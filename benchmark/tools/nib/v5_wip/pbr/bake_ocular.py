"""Actual fitted-iris field baking; never substitute a UV carrier for attributes."""
import hashlib

import bpy
import numpy as np

from bake_fields import bake_maps, make_face_uv, portable_material, principled


def iris_field_receipt(obj):
    field = obj.data.attributes.get('Nib_IrisCoord')
    if field is None or field.domain != 'POINT' or field.data_type != 'FLOAT_VECTOR':
        raise RuntimeError('Actual iris lacks its point-domain coordinate field: '+obj.name)
    values = np.empty((len(field.data),3), dtype=np.float32)
    field.data.foreach_get('vector', values.ravel())
    if not np.isfinite(values).all() or np.ptp(values[:,0]) < 1 or np.ptp(values[:,1]) < 1:
        raise RuntimeError('Iris pigment coordinate domain is invalid: '+obj.name)
    connected = []
    for material in obj.data.materials:
        pending = [link.from_node for link in principled(material).inputs['Base Color'].links]
        seen = set()
        while pending:
            node = pending.pop()
            if node.name in seen:
                continue
            seen.add(node.name)
            if node.type == 'ATTRIBUTE' and node.attribute_name == 'Nib_IrisCoord':
                connected.append(material.name)
            for socket in node.inputs:
                pending.extend(link.from_node for link in socket.links)
    if not connected:
        raise RuntimeError('Iris coordinate field is disconnected from actual pigment')
    return {'object':obj.name, 'attribute':'Nib_IrisCoord',
            'sourceValuesSha256':hashlib.sha256(values.tobytes()).hexdigest(),
            'minimum':values.min(0).tolist(), 'maximum':values.max(0).tolist(),
            'connectedBaseColorMaterials':connected}


def bake_actual_irises(source_objects, textures, source_report):
    original = bpy.data.materials.get('Nib_IdentityOcularIris')
    assigned = [obj for obj in source_objects if original and original in list(obj.data.materials)]
    if not assigned:
        return []
    if len(assigned) != 2:
        raise RuntimeError('Expected the two actual fitted iris surfaces')
    result = []
    runtime_names = set()
    for obj in sorted(assigned, key=lambda obj:obj.name):
        if len(obj.data.materials) != 1 or obj.data.materials[0] != original:
            raise RuntimeError('Mixed-material iris requires explicit surface mapping: '+obj.name)
        side = obj.name.rsplit(' ',1)[-1]
        if side not in {'L','R'}:
            raise RuntimeError('Ambiguous fitted-iris side: '+obj.name)
        name = 'Nib_IdentityOcularIris_'+side
        if name in runtime_names:
            raise RuntimeError('Duplicate fitted-iris side')
        runtime_names.add(name)
        field = iris_field_receipt(obj)
        expected = source_report.get('irisAttributeHashes',{}).get(obj.name)
        if expected and expected != field['sourceValuesSha256']:
            raise RuntimeError('Saved iris field differs from the actual source report')
        copied = original.copy()
        copied.name = name+'_BakeEvaluation'
        obj.data.materials[0] = copied
        source_uv = make_face_uv(obj)
        maps = bake_maps(obj,name,textures,{'BaseColor':1024,'Normal':512,'Roughness':256,'Metallic':128})
        runtime = portable_material(name,textures,maps,original)
        obj.data.materials[0] = runtime
        obj.data.uv_layers.remove(obj.data.uv_layers[source_uv])
        obj.data.uv_layers.active = obj.data.uv_layers['UVMap']
        obj.data.uv_layers['UVMap'].active_render = True
        values = np.empty((len(obj.data.attributes['Nib_IrisCoord'].data),3),dtype=np.float32)
        obj.data.attributes['Nib_IrisCoord'].data.foreach_get('vector',values.ravel())
        if hashlib.sha256(values.tobytes()).hexdigest() != field['sourceValuesSha256']:
            raise RuntimeError('Actual-surface bake changed the iris attribute')
        obj['runtime_uv_atlas'] = True
        obj.hide_render = True
        obj.hide_set(True)
        if copied.users == 0:
            bpy.data.materials.remove(copied)
        result.append({'material':name,'mode':'Actual fitted iris geometry + point attribute',
                       'field':field,'maps':maps,'sourceMaterial':original.name,
                       'uv':'Separate nonoverlapping actual-surface atlas; original source UV isolated during bake',
                       'geometryAttributePreservation':'Attribute hash unchanged; outer candidate gate checks vertices, polygons, morphs, weights and rig',
                       'reviewRequired':'Same-camera source/baked iris pigment, limbal edge, slit pupil and original shell curvature'})
    return result
