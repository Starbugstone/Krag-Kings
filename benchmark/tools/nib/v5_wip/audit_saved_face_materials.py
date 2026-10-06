"""Read-only saved-mesh material/normal audit; no render or source mutation.

Run in the serialized Blender guard. Its assigned-face bounds distinguish a
material selector fault from a shadow on the actual fitted muzzle surface.
"""
import argparse, hashlib, json, sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(Path(__file__).parent))
from audit_face_coordinates import bounds, enable_facial_evaluation

parser = argparse.ArgumentParser()
parser.add_argument('--source', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
def scalar_inputs(node):
    result={}
    for socket in node.inputs:
        value=getattr(socket,'default_value',None)
        if isinstance(value,(int,float,bool)): result[socket.name]=value
        elif value is not None and not isinstance(value,str):
            try:
                values=list(value)
                if all(isinstance(v,(int,float,bool)) for v in values): result[socket.name]=values
            except TypeError: pass
    return result
source_hash = sha(args.source)
bpy.ops.wm.open_mainfile(filepath=str(args.source), load_ui=False)
scene = bpy.context.scene
rig = bpy.data.objects['Nib_Rig']
head = bpy.data.objects['Nib v5 fitted animation face']
enable_facial_evaluation(rig, head)
rig.animation_data.action = bpy.data.actions['Idle']
scene.frame_set(1)
bpy.context.view_layer.update()
depsgraph = bpy.context.evaluated_depsgraph_get()
evaluated = head.evaluated_get(depsgraph)
mesh = evaluated.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)
try:
    points = np.asarray([tuple(evaluated.matrix_world @ v.co) for v in mesh.vertices])
    source = np.asarray([tuple(v.vector) for v in mesh.attributes['nib_source_position'].data])
    mask = np.asarray([v.value for v in mesh.attributes['NibNoseMask'].data])
    normal_matrix = evaluated.matrix_world.to_3x3().inverted().transposed()
    normals = np.asarray([tuple((normal_matrix @ p.normal).normalized()) for p in mesh.polygons])
    centers = np.asarray([points[list(p.vertices)].mean(0) for p in mesh.polygons])
    source_centers = np.asarray([source[list(p.vertices)].mean(0) for p in mesh.polygons])
    report = {'source':str(args.source), 'sourceSha256':source_hash,
              'status':'Read-only actual saved mesh audit; no artistic acceptance',
              'action':'Idle', 'frame':1, 'space':'World metres; forward is negative Y',
              'materialFaces':[], 'sourceRegions':{}, 'frontalHits':[], 'materialGraphs':{}}
    for index, material in enumerate(mesh.materials):
        faces = [p.index for p in mesh.polygons if p.material_index == index]
        vertices = sorted({v for i in faces for v in mesh.polygons[i].vertices})
        report['materialFaces'].append({'slot':index, 'material':material.name,
            'faces':len(faces), 'worldVertexBounds':bounds(points[vertices]),
            'worldCenterBounds':bounds(centers[faces]), 'sourceVertexBounds':bounds(source[vertices]),
            'noseMaskAboveHalfVertices':int((mask[vertices]>.5).sum()),
            'sampleFaceIds':faces[:12]})
        report['materialGraphs'][material.name] = {
            'nodes':[{'name':n.name, 'type':n.type,
                      **({'attribute':n.attribute_name} if n.type=='ATTRIBUTE' else {}),
                      **({'image':n.image.name if n.image else None} if n.type=='TEX_IMAGE' else {}),
                      'inputs':scalar_inputs(n)}
                     for n in material.node_tree.nodes],
            'links':[[l.from_node.name,l.from_socket.name,l.to_node.name,l.to_socket.name]
                     for l in material.node_tree.links]}
    x,y,z = source_centers.T
    regions = {'upperMuzzle':(abs(x)<.038)&(z>.235)&(z<.262)&(y<-.10),
               'lowerMuzzleChin':(abs(x)<.046)&(z>.180)&(z<=.235)&(y<-.08),
               'anteriorNeck':(abs(x)<.035)&(z<=.195)&(y<-.035),
               'nosePad':(abs(x)<.032)&(z>.251)&(z<.282)&(y<-.13)}
    for name, selection in regions.items():
        ids = np.flatnonzero(selection)
        slots = {m.name:sum(mesh.polygons[int(i)].material_index==j for i in ids)
                 for j,m in enumerate(mesh.materials)}
        report['sourceRegions'][name] = {'faces':len(ids),'materialFaceCounts':slots,
            'centerBounds':bounds(centers[ids]), 'worldNormalMean':normals[ids].mean(0).tolist() if len(ids) else None,
            'downFacingFraction':float(np.mean(normals[ids,2]<-.35)) if len(ids) else None}
    tree=BVHTree.FromPolygons([Vector(p) for p in points], [list(p.vertices) for p in mesh.polygons])
    for z in [1.015,1.035,1.055,1.070,1.085,1.100,1.110]:
        for x in [-.035,-.0175,0,.0175,.035]:
            point,normal,face,_=tree.ray_cast(Vector((x,-1,z)),Vector((0,1,0)),2)
            report['frontalHits'].append({'queryXZ':[x,z], 'hit':list(point) if point else None,
                'normal':list(normal) if normal else None, 'face':face,
                'material':mesh.materials[mesh.polygons[face].material_index].name if face is not None else None})
    report['noseAttribute']={'verticesAboveHalf':int((mask>.5).sum()),
                             'worldBoundsAboveHalf':bounds(points[mask>.5])}
finally:
    evaluated.to_mesh_clear()
if sha(args.source)!=source_hash: raise RuntimeError('Read-only audit changed source')
report['sourceUnchanged']=True
report['auditCodeSha256']=sha(Path(__file__))
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(report,indent=2)+'\n', newline='\n')
print('NIB_SAVED_FACE_MATERIAL_AUDIT_COMPLETE', flush=True)
