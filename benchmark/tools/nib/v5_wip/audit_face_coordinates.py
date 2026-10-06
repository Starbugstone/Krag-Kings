"""Read-only saved-mesh facial-space audit. Run Blender through the guard.

Reports evaluated neutral/Idle mouth occlusion and exact world coordinates;
it creates no mesh assets, rendered images, or exports.
"""
import argparse, hashlib, json, sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[4]
ORAL_PREFIXES=('Provisional recessed oral cavity','Upper provisional gum ridge',
               'Lower provisional gum ridge','Upper provisional tooth',
               'Lower provisional tooth','Canonical dark blue Nib tongue')

def bounds(points):
    a=np.asarray(points,dtype=np.float64)
    return {'count':len(a),'minimum':a.min(0).tolist(),'maximum':a.max(0).tolist(),
            'mean':a.mean(0).tolist()} if len(a) else {'count':0}

def evaluated(obj,depsgraph):
    copy=obj.evaluated_get(depsgraph);mesh=copy.to_mesh()
    try:
        points=[copy.matrix_world@v.co for v in mesh.vertices]
        faces=[list(p.vertices) for p in mesh.polygons]
        return points,faces
    finally:copy.to_mesh_clear()

def facial_snapshot(scene,rig,head):
    bpy.context.view_layer.update();depsgraph=bpy.context.evaluated_depsgraph_get()
    points,faces=evaluated(head,depsgraph)
    tree=BVHTree.FromPolygons(points,faces,all_triangles=False)
    source=head.data.attributes.get('nib_source_position')
    if source is None:raise RuntimeError('Audited facial source-coordinate attribute is absent')
    source=np.asarray([a.vector[:] for a in source.data])
    mouth=(abs(source[:,0])<.037)&(source[:,2]>.225)&(source[:,2]<.248)&(source[:,1]<-.117)
    upper=mouth&(source[:,2]>.235);lower=mouth&(source[:,2]<=.235)
    p=np.asarray(points)
    result={'headWorld':bounds(p),'upperLipRegionWorld':bounds(p[upper]),'lowerLipRegionWorld':bounds(p[lower]),
            'oral':{},'bones':{},'morphValues':{key.name:key.value for key in head.data.shape_keys.key_blocks}}
    mask=head.data.attributes.get('NibNoseMask')
    if mask:
        values=np.asarray([item.value for item in mask.data]);result['noseMask']={
            'min':float(values.min()),'max':float(values.max()),'overHalf':int((values>.5).sum()),
            'worldBoundsAboveHalf':bounds(p[values>.5]),'materialSlots':[m.name for m in head.data.materials]}
    for obj in bpy.data.collections['Nib_Authored_Components'].objects:
        if obj.type!='MESH' or not obj.name.startswith(ORAL_PREFIXES):continue
        q,_=evaluated(obj,depsgraph)
        exposed=[];sampled=list(range(0,len(q),max(1,len(q)//256)))
        for index in sampled:
            point=q[index];origin=Vector((point.x,-1,point.z));hit,normal,face,distance=tree.ray_cast(origin,Vector((0,1,0)),2)
            # Negative Y is the viewing side. A strictly nearer facial surface
            # occludes this sample; a missed ray is also exposed.
            if hit is None or hit.y>point.y-.0001:exposed.append(index)
        result['oral'][obj.name]={'world':bounds(q),'objectLocation':list(obj.location),
                                 'frontalSamples':len(sampled),'unoccludedSamples':len(exposed),
                                 'unoccludedVertexIds':exposed[:12]}
    for name in ['Head','FaceRoot','Jaw','TongueBase','TongueTip','Eye_L','Eye_R','LidUpper_L','LidUpper_R']:
        bone=rig.pose.bones[name]
        result['bones'][name]={'restHeadWorld':list(rig.matrix_world@bone.bone.head_local),
                               'posedHeadWorld':list(rig.matrix_world@bone.head),
                               'basisTranslation':list(bone.matrix_basis.translation),
                               'basisQuaternion':list(bone.matrix_basis.to_quaternion())}
    return result

def surface_diagnostics():
    """Localize source zero-area/UV defects; do not alter any geometry."""
    defects=[]
    for obj in bpy.data.collections['Nib_Authored_Components'].objects:
        if obj.type!='MESH':continue
        mesh=obj.data;mesh.calc_loop_triangles()
        vertices=np.asarray([v.co[:] for v in mesh.vertices],dtype=np.float64)
        tris=np.asarray([t.vertices[:] for t in mesh.loop_triangles],dtype=np.int32)
        if not len(tris):continue
        p=vertices[tris];area=np.linalg.norm(np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0]),axis=1)
        zero=np.flatnonzero(area==0);uvzero=np.array([],dtype=int)
        if mesh.uv_layers.active:
            uv=np.asarray([v.uv[:] for v in mesh.uv_layers.active.data],dtype=np.float64)
            loops=np.asarray([t.loops[:] for t in mesh.loop_triangles],dtype=np.int32)
            q=uv[loops];a=q[:,1]-q[:,0];b=q[:,2]-q[:,0]
            uvzero=np.flatnonzero((a[:,0]*b[:,1]-a[:,1]*b[:,0])==0)
        if len(zero) or len(uvzero):
            defects.append({'object':obj.name,'variant':obj.get('variant','all'),
                            'materials':[m.name for m in mesh.materials],
                            'triangles':len(tris),'exactZeroAreaTriangles':len(zero),
                            'exactCollapsedUvTriangles':len(uvzero),
                            'zeroAreaVertexIds':tris[zero[:12]].tolist(),
                            'collapsedUvVertexIds':tris[uvzero[:12]].tolist()})
    return defects

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:]);digest=hashlib.sha256(args.source.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(args.source),load_ui=False)
    scene=bpy.context.scene;rig=bpy.data.objects['Nib_Rig'];head=bpy.data.objects['Nib v5 fitted animation face']
    result={'source':str(args.source),'sourceSha256':digest,'status':'Coordinate/occlusion diagnostic; not visual acceptance','poses':{}}
    result['sourceSurfaceDefects']=surface_diagnostics()
    for label,action,frame in [('Neutral',None,1),('Idle1','Idle',1),('Tongue103','FacePerformance',103)]:
        rig.animation_data.action=bpy.data.actions[action] if action else None
        for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
        scene.frame_set(frame);bpy.context.view_layer.update()
        result['poses'][label]=facial_snapshot(scene,rig,head)
    assert hashlib.sha256(args.source.read_bytes()).hexdigest()==digest
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,indent=2)+'\n',newline='\n')
    print('NIB_FACE_COORDINATES_WRITTEN',str(args.out),flush=True)

if __name__=='__main__':main()
