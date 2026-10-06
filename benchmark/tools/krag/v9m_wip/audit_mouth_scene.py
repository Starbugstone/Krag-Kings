"""Read-only all-mesh mouth visibility attribution against actual portrait rays.

Includes Body and Scarf, which the former Head-only diagnostic did not test.
Does not save a blend or change any anatomy/rig/shared asset.
"""
from pathlib import Path
import json,hashlib
import numpy as np
import bpy
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[4];ART=ROOT/'benchmark/art/krag'
SOURCE=ART/'Krag_MouthPoseFit_v9ka_WIP.blend';EXPECTED='3639a7fbbba1b81d5749658ba6db924020fbe6ea1e47cfd71c445cd05f04a297'
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==EXPECTED
bpy.ops.wm.open_mainfile(filepath=str(SOURCE));rig=bpy.data.objects['Krag_Rig'];rig.animation_data.action=bpy.data.actions['FacePerformance'];bpy.context.scene.frame_set(146);bpy.context.view_layer.update()
contract=json.loads((ART/'v9h-source-contract.json').read_text());off=set(contract['variants']['Krag_Natural']['off'])
deps=bpy.context.evaluated_depsgraph_get();trees=[];bounds={}
for obj in bpy.data.objects:
    if obj.type!='MESH'or not obj.get('module')or obj['module']in off:continue
    evaluated=obj.evaluated_get(deps);coords=[evaluated.matrix_world@v.co for v in evaluated.data.vertices];array=np.asarray([tuple(p)for p in coords])
    bounds[obj.name]=[array.min(0).tolist(),array.max(0).tolist()]
    if array[:,2].max()<1.68 or array[:,2].min()>1.88 or array[:,0].min()>.22 or array[:,0].max()<-.22:continue
    polygons=[tuple(p.vertices)for p in evaluated.data.polygons]
    tree=BVHTree.FromPolygons(coords,polygons);tags=evaluated.data.attributes.get('.sculpt_face_set')
    metadata=[{'material':evaluated.data.materials[p.material_index].name,'sourceFaceSet':int(tags.data[p.index].value)if tags else None}for p in evaluated.data.polygons]
    trees.append((obj.name,obj['module'],tree,metadata))
cam=Vector((1.1,-4,2.05));target=Vector((0,-.02,1.9));q=(target-cam).to_track_quat('-Z','Y');right=q@Vector((1,0,0));up=q@Vector((0,1,0));direction=q@Vector((0,0,-1));scale=.53
probes=[];counts={}
for x in range(342,501,16):
    for y in range(690,795,16):
        origin=cam+right*((x+.5)/1000-.5)*scale+up*(.5-(y+.5)/1000)*scale;hits=[]
        for name,module,tree,metadata in trees:
            point,normal,face,distance=tree.ray_cast(origin,direction,8.)
            if point is None:continue
            hits.append({'object':name,'module':module,'distance':distance,'point':list(point),'face':int(face),**metadata[face]})
        hits.sort(key=lambda h:h['distance'])
        if hits:
            label=hits[0]['module']+'/'+hits[0]['material'];counts[label]=counts.get(label,0)+1
        probes.append({'pixel':[x,y],'visibleHits':hits[:5]})
report={'status':'Actual saved-source all-mesh portrait-ray attribution; not a repair','source':SOURCE.relative_to(ROOT).as_posix(),'sourceSha256':EXPECTED,'clip':'FacePerformance','frame':146,'view':'Natural_Head','pixelSpace':'1000x1000, origin top-left, neutral portrait camera','visibleSurfaceCounts':counts,'evaluatedModuleBounds':bounds,'probes':probes,'sourceUnchanged':True}
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==EXPECTED
(ART/'anatomy-study/mouth-scene-overlap-v9ka.json').write_text(json.dumps(report,indent=2)+'\n',newline='\n')
print(json.dumps(counts,indent=2),flush=True)
