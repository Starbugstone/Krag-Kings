"""Actual rigid boot surfaces in rig space, for offline contact fitting."""
import bpy
import numpy as np


def capture(rig, species):
    old = rig.data.pose_position
    rig.data.pose_position = 'REST'
    bpy.context.view_layer.update()
    clouds, records = {}, {}
    try:
        depsgraph = bpy.context.evaluated_depsgraph_get()
        for side in ['L', 'R']:
            pieces, names = [], []
            for obj in bpy.data.objects:
                if obj.type != 'MESH': continue
                match = (obj.get('module') == 'Boot_'+side if species == 'Krag' else
                         obj.get('bone') == 'Foot_'+side and obj.get('variant', 'all') in ['all', 'natural', 'organic'])
                if not match: continue
                for vertex in obj.data.vertices:
                    weights = {obj.vertex_groups[g.group].name:g.weight for g in vertex.groups if g.weight > 1e-7}
                    if weights != {'Foot_'+side: 1.0}:
                        raise RuntimeError('Contact cache needs verified rigid foot weighting: '+obj.name)
                evaluated = obj.evaluated_get(depsgraph); mesh = evaluated.to_mesh()
                try:
                    local = np.empty((len(mesh.vertices), 3), dtype=np.float64)
                    mesh.vertices.foreach_get('co', local.ravel())
                    matrix = np.asarray(rig.matrix_world.inverted() @ evaluated.matrix_world)
                    points = local @ matrix[:3, :3].T+matrix[:3, 3]
                    pieces.append(points); names.append(obj.name)
                finally: evaluated.to_mesh_clear()
            if not pieces: raise RuntimeError('No rigid foot geometry found for '+side)
            clouds[side] = np.concatenate(pieces)
            records[side] = {'components':names, 'vertices':len(clouds[side]),
                             'restMinimumZ':float(clouds[side][:, 2].min()),
                             'restBounds':[clouds[side].min(axis=0).tolist(),clouds[side].max(axis=0).tolist()]}
    finally:
        rig.data.pose_position = old
        bpy.context.view_layer.update()
    return clouds, records


def minimum(rig, clouds, side):
    foot = rig.pose.bones['Foot_'+side]
    transform = np.asarray(foot.matrix @ foot.bone.matrix_local.inverted())
    return float((clouds[side] @ transform[2, :3]+transform[2, 3]).min())
