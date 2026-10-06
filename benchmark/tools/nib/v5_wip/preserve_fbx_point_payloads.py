"""Keep baseline point-domain normals/morphs on an already triangulated FBX.

No polygons, UVs, skeletons, weights, connections or animation are replaced.
The source and target must have exactly identical vertex coordinates/order.
Uses the installed Blender FBX parser/writer, not hand-edited binary offsets.
"""
import argparse, array, hashlib, importlib, json, sys, types
from pathlib import Path
import numpy as np


def preserve(source,target,addons,preserve_normals=True):
    package='io_scene_fbx'
    if package not in sys.modules:
        module=types.ModuleType(package);module.__path__=[str(addons/package)];sys.modules[package]=module
    parse=importlib.import_module(package+'.parse_fbx')
    encode=importlib.import_module(package+'.encode_bin')
    before,version=parse.parse(str(source));after,target_version=parse.parse(str(target))
    if version!=target_version:raise ValueError('FBX version mismatch')
    def child(node,name):return next(n for n in node.elems if n.id==name)
    def meshes(root):return [n for n in child(root,b'Objects').elems if n.id==b'Geometry' and n.props[2]==b'Mesh']
    bm,am=meshes(before),meshes(after)
    if len(bm)!=1 or len(am)!=1:raise ValueError('Expected one assembled mesh')
    source_vertices=child(bm[0],b'Vertices').props[0]
    target_vertices=child(am[0],b'Vertices').props[0]
    if source_vertices.tobytes()!=target_vertices.tobytes():raise ValueError('Cannot preserve point payloads after a vertex change')
    source_normal_mapping=None;normal_collapse_error=0.
    if preserve_normals:
        source_normal=child(bm[0],b'LayerElementNormal')
        source_normal_mapping=child(source_normal,b'MappingInformationType').props[0]
        if source_normal_mapping==b'ByPolygonVertex':
            raw=np.asarray(child(bm[0],b'PolygonVertexIndex').props[0],dtype=np.int64)
            indices=np.where(raw<0,-raw-1,raw)
            normals=np.asarray(child(source_normal,b'Normals').props[0],dtype=np.float64).reshape((-1,3))
            reference=child(source_normal,b'ReferenceInformationType').props[0]
            if reference==b'IndexToDirect':normals=normals[np.asarray(child(source_normal,b'NormalsIndex').props[0],dtype=np.int64)]
            elif reference!=b'Direct':raise ValueError('Unsupported source normal reference')
            if len(normals)!=len(indices):raise ValueError('Source loop normal count mismatch')
            points=np.zeros((len(source_vertices)//3,3),dtype=np.float64);points[indices]=normals
            normal_collapse_error=float(np.linalg.norm(normals-points[indices],axis=1).max())
            if normal_collapse_error>1e-7:raise ValueError('True split normals require a loop-aware remap, not point collapse')
            children=[]
            for node in source_normal.elems:
                if node.id in [b'NormalsIndex',b'NormalsW']:continue
                if node.id==b'MappingInformationType':node=node._replace(props=[b'ByVertice'])
                elif node.id==b'ReferenceInformationType':node=node._replace(props=[b'Direct'])
                elif node.id==b'Normals':node=node._replace(props=[array.array('d',points.ravel())])
                children.append(node)
            source_normal=source_normal._replace(elems=children)
        elif source_normal_mapping not in [b'ByVertice',b'ByVertex']:
            raise ValueError('Unsupported source normal mapping')
        old_normal=child(am[0],b'LayerElementNormal')
        am[0].elems[am[0].elems.index(old_normal)]=source_normal
    def shapes(root):return {n.props[1]:n for n in child(root,b'Objects').elems if n.id==b'Geometry' and n.props[2]==b'Shape'}
    bs,ass=shapes(before),shapes(after)
    if set(bs)!=set(ass):raise ValueError('Morph names differ')
    for name,node in ass.items():
        for field in [b'Indexes',b'Vertices']:
            old=child(node,field);node.elems[node.elems.index(old)]=child(bs[name],field)
    methods={'Z':'add_int8','Y':'add_int16','I':'add_int32','L':'add_int64',
             'B':'add_bool','C':'add_char','F':'add_float32','D':'add_float64',
             'R':'add_bytes','S':'add_string','i':'add_int32_array','l':'add_int64_array',
             'f':'add_float32_array','d':'add_float64_array','b':'add_bool_array','c':'add_byte_array'}
    def convert(node):
        output=encode.FBXElem(node.id)
        for kind,value in zip(node.props_type,node.props):getattr(output,methods[chr(kind)])(value)
        output.elems=[convert(n) for n in node.elems]
        return output
    encoded=convert(after)
    temporary=target.with_suffix('.fbx.payload.tmp')
    original_hash=hashlib.sha256(target.read_bytes()).hexdigest()
    encode.write(str(temporary),encoded,version)
    # Serialization cannot change unrelated values, even if the compression and
    # node offsets differ. Validate all nodes/properties against the intended tree.
    reread,_=parse.parse(str(temporary))
    def equivalent(a,b):
        if a.id!=b.id or a.props_type!=b.props_type or len(a.elems)!=len(b.elems):return False
        for x,y in zip(a.props,b.props):
            if hasattr(x,'tobytes'):
                if x.tobytes()!=y.tobytes():return False
            elif x!=y:return False
        return all(equivalent(x,y) for x,y in zip(a.elems,b.elems))
    if not equivalent(after,reread):raise RuntimeError('FBX serialization changed intended property values')
    temporary.replace(target)
    return {'source':str(source),'target':str(target),'sourceSha256':hashlib.sha256(source.read_bytes()).hexdigest(),
            'beforeSha256':original_hash,'afterSha256':hashlib.sha256(target.read_bytes()).hexdigest(),
            'pointCoordinatesByteIdentical':True,'restoredSourcePointNormalLayer':preserve_normals,
            'sourceNormalMapping':source_normal_mapping.decode() if source_normal_mapping else None,
            'sourceNormalVertexCollapseMaxError':normal_collapse_error,
            'restoredSparseMorphPayloads':len(bs),'allOtherSerializedPropertiesVerifiedUnchanged':True}


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--source-dir',type=Path,required=True)
    parser.add_argument('--candidate-dir',type=Path,required=True)
    parser.add_argument('--addons',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--names',nargs='+',default=['Nib_Natural','Nib_GripReplacement','Nib_LegReplacement'])
    parser.add_argument('--morphs-only',action='store_true',help='Leave the target normal layer unchanged; caller must validate it independently')
    args=parser.parse_args();results=[]
    for name in args.names:
        result=preserve(args.source_dir/(name+'.fbx'),args.candidate_dir/(name+'.fbx'),args.addons,not args.morphs_only)
        results.append(result);print(json.dumps(result),flush=True)
    args.output.write_text(json.dumps({'variants':results},indent=2)+'\n',newline='\n')
