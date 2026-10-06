"""Prepared source-preservation contracts copied from the actual semantic repair.

No bpy scene side effects at import. Full handles/easing and frame ranges count.
"""
import hashlib,json
import numpy as np
from bpy_extras.anim_utils import action_get_channelbag_for_slot
import bpy

def rig_contract(rig):
    original=rig.animation_data.action;actions={}
    for action in bpy.data.actions:
        rig.animation_data.action=action;bag=action_get_channelbag_for_slot(action,rig.animation_data.action_slot)
        if bag is None:continue
        rows=[(c.data_path,c.array_index,c.extrapolation,[(tuple(k.co),tuple(k.handle_left),tuple(k.handle_right),k.interpolation,k.handle_left_type,k.handle_right_type,k.easing,k.amplitude,k.back,k.period) for k in c.keyframe_points]) for c in bag.fcurves]
        actions[action.name]=hashlib.sha256(json.dumps({'frameRange':list(action.frame_range),'curves':sorted(rows)},separators=(',',':')).encode()).hexdigest()
    rig.animation_data.action=original
    return {'world':[list(r) for r in rig.matrix_world],'bones':{b.name:{'matrix':[list(r) for r in b.matrix_local],'parent':b.parent.name if b.parent else None,'connected':b.use_connect,'rotationMode':rig.pose.bones[b.name].rotation_mode} for b in rig.data.bones},'actions':actions}

def surface_hash(obj):
    h=hashlib.sha256();m=obj.data;v=np.empty(len(m.vertices)*3,np.float32);m.vertices.foreach_get('co',v);h.update(v.tobytes())
    for key in m.shape_keys.key_blocks if m.shape_keys else []:key.data.foreach_get('co',v);h.update(key.name.encode());h.update(v.tobytes())
    for uv in m.uv_layers:
        values=np.empty(len(uv.data)*2,np.float32);uv.data.foreach_get('uv',values);h.update(uv.name.encode());h.update(values.tobytes())
    payload={'faces':[(list(p.vertices),p.material_index) for p in m.polygons],'groups':[g.name for g in obj.vertex_groups],'weights':[[(g.group,g.weight) for g in v.groups] for v in m.vertices],'materials':[m.name if m else None for m in m.materials],'basis':[list(r) for r in obj.matrix_basis],'parentInverse':[list(r) for r in obj.matrix_parent_inverse],'parent':obj.parent.name if obj.parent else None,'parentType':obj.parent_type,'parentBone':obj.parent_bone}
    h.update(json.dumps(payload,separators=(',',':')).encode());return h.hexdigest()

