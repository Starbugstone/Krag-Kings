"""Read-only source component localization for exactly zero-area triangles."""
import argparse,hashlib,json,sys
from pathlib import Path
import bpy
import numpy as np

parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
bpy.ops.wm.open_mainfile(filepath=str(args.source));results=[]
for obj in bpy.data.objects:
    if obj.type!='MESH' or 'module' not in obj:continue
    mesh=obj.data;mesh.calc_loop_triangles()
    coords=np.empty(len(mesh.vertices)*3,dtype=np.float32);mesh.vertices.foreach_get('co',coords)
    coords=coords.reshape(-1,3).astype(np.float64)
    indices=np.empty(len(mesh.loop_triangles)*3,dtype=np.int32);mesh.loop_triangles.foreach_get('vertices',indices)
    indices=indices.reshape(-1,3);a,b,c=(coords[indices[:,i]] for i in range(3))
    zero=np.all(np.cross(b-a,c-a)==0.0,axis=1);bad=np.flatnonzero(zero)
    if not len(bad):continue
    materials={};samples=[]
    for index in bad:
        triangle=mesh.loop_triangles[int(index)];polygon=mesh.polygons[triangle.polygon_index]
        material=mesh.materials[polygon.material_index].name if polygon.material_index<len(mesh.materials) else '<none>'
        materials[material]=materials.get(material,0)+1
        if len(samples)<24:samples.append({'triangle':int(index),'polygon':triangle.polygon_index,
            'vertexIds':list(triangle.vertices),'localCoordinatesMeters':coords[indices[index]].tolist(),'material':material})
    results.append({'object':obj.name,'module':obj['module'],'triangles':len(mesh.loop_triangles),
        'exactZeroAreaTriangles':len(bad),'materials':materials,'samples':samples})
report={'source':str(args.source),'sourceSha256':hashlib.sha256(args.source.read_bytes()).hexdigest(),
        'readOnly':True,'components':results,'exactZeroAreaTriangles':sum(r['exactZeroAreaTriangles'] for r in results),
        'note':'Point positions and morphs remain untouched. Final disposable assembly may delete only exact zero-area faces through the existing opt-in triangulation helper.'}
args.output.write_text(json.dumps(report,indent=2)+'\n',newline='\n');print(json.dumps(report,indent=2))
