"""Bounded boundary-quad diagonal correction; preserves all point payloads.

Only declared four-corner polygons become two consistently wound triangles.
Every new corner maps to its original UV/custom-data corner, never a UV rebake.
"""
import bpy
import numpy as np


def triangulate_boundary(source, replacements):
    old=source.data
    if old.has_custom_normals:raise RuntimeError('Uncovered custom normals on neck Body')
    polygons=[];face_map=[];corner_map=[]
    for face in old.polygons:
        original=list(face.vertices);new=replacements.get(face.index,[original])
        if face.index in replacements:
            if len(original)!=4 or len(new)!=2 or any(len(t)!=3 for t in new):raise RuntimeError('Invalid local quad plan')
            if set(v for t in new for v in t)!=set(original):raise RuntimeError('Local diagonal changed polygon vertices')
        for f in new:
            polygons.append(f);face_map.append(face.index)
            corner_map.extend(face.loop_start+original.index(v) for v in f)
    point=np.asarray([v.co[:] for v in old.vertices],np.float32)
    mesh=bpy.data.meshes.new(old.name+' corrected neck diagonals');mesh.from_pydata(point,[],polygons);mesh.update()
    obj=source.copy();obj.data=mesh
    for collection in source.users_collection:collection.objects.link(obj)
    obj.vertex_groups.clear();groups=[obj.vertex_groups.new(name=g.name)for g in source.vertex_groups]
    for vertex in old.vertices:
        for g in vertex.groups:groups[g.group].add([vertex.index],g.weight,'REPLACE')
    for material in old.materials:mesh.materials.append(material)
    for new,index in zip(mesh.polygons,face_map):
        new.material_index=old.polygons[index].material_index;new.use_smooth=old.polygons[index].use_smooth
    corner_map=np.asarray(corner_map,np.int32);face_map=np.asarray(face_map,np.int32)
    for uv in old.uv_layers:
        layer=mesh.uv_layers.new(name=uv.name);values=np.asarray([v.uv[:]for v in uv.data],np.float32)[corner_map]
        layer.data.foreach_set('uv',values.ravel())
    if old.uv_layers.active:mesh.uv_layers.active=mesh.uv_layers[old.uv_layers.active.name]
    old_edges={tuple(sorted(e.vertices)):e.index for e in old.edges}
    edge_map=np.asarray([old_edges.get(tuple(sorted(e.vertices)),-1)for e in mesh.edges],np.int32)
    fields={'FLOAT':('value',np.float32),'FLOAT_VECTOR':('vector',np.float32),'FLOAT2':('vector',np.float32),
            'FLOAT_COLOR':('color',np.float32),'BYTE_COLOR':('color',np.float32),'INT':('value',np.int32),'BOOLEAN':('value',bool)}
    for attr in old.attributes:
        if attr.name=='position' or attr.name in mesh.attributes:continue
        if attr.data_type not in fields:raise RuntimeError('Uncovered mesh attribute '+attr.name+':'+attr.data_type)
        field,dtype=fields[attr.data_type];values=np.asarray([getattr(v,field)for v in attr.data],dtype)
        if attr.domain=='POINT':mapped=values
        elif attr.domain=='CORNER':mapped=values[corner_map]
        elif attr.domain=='FACE':mapped=values[face_map]
        elif attr.domain=='EDGE':
            mapped=np.zeros((len(edge_map),*values.shape[1:]),dtype);valid=edge_map>=0;mapped[valid]=values[edge_map[valid]]
        else:raise RuntimeError('Uncovered domain '+attr.domain)
        layer=mesh.attributes.new(attr.name,attr.data_type,attr.domain);layer.data.foreach_set(field,mapped.ravel())
    if old.shape_keys:
        for key in old.shape_keys.key_blocks:
            new=obj.shape_key_add(name=key.name,from_mix=False);values=np.asarray([v.co[:]for v in key.data],np.float32)
            new.data.foreach_set('co',values.ravel());new.slider_min=key.slider_min;new.slider_max=key.slider_max
            new.interpolation=key.interpolation;new.vertex_group=key.vertex_group;new.value=0
        for key in old.shape_keys.key_blocks:mesh.shape_keys.key_blocks[key.name].relative_key=mesh.shape_keys.key_blocks[key.relative_key.name]
        mesh.shape_keys.use_relative=old.shape_keys.use_relative
    # Direct payload assertions before replacing the scene object.
    if not np.array_equal(point,np.asarray([v.co[:]for v in mesh.vertices],np.float32)):raise RuntimeError('Diagonal altered Basis')
    for old_key,new_key in zip(old.shape_keys.key_blocks if old.shape_keys else [],mesh.shape_keys.key_blocks if mesh.shape_keys else []):
        if old_key.name!=new_key.name or not np.array_equal(np.asarray([v.co[:]for v in old_key.data],np.float32),np.asarray([v.co[:]for v in new_key.data],np.float32)):raise RuntimeError('Diagonal altered named morph')
    for uv in mesh.uv_layers:
        expected=np.asarray([v.uv[:]for v in old.uv_layers[uv.name].data],np.float32)[corner_map]
        if not np.array_equal(expected,np.asarray([v.uv[:]for v in uv.data],np.float32)):raise RuntimeError('Diagonal altered mapped UV')
    for a,b in zip(old.vertices,mesh.vertices):
        if [(g.group,g.weight)for g in a.groups]!=[(g.group,g.weight)for g in b.groups]:raise RuntimeError('Diagonal altered skin weights')
    name=source.name;hidden=source.hide_get();bpy.data.objects.remove(source,do_unlink=True);obj.name=name;obj.hide_set(hidden)
    mesh.update()
    return obj,{'triangulatedQuads':len(replacements),'pointIndexAndMorphCoordinatesExact':True,'mappedCornerUVsExact':True,'skinWeightsExact':True,'newFaces':len(mesh.polygons),'previousFaces':len(old.polygons)}
