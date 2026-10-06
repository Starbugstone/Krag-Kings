"""Prepared bounded card-root attachment; existing atlas and guide tips stay.

This is not a general fur/style acceptance. It removes a measured construction
defect (floating squared roots) before the separate regional flow/texture pass.
"""
import math,sys
from pathlib import Path
import numpy as np
from mathutils import Vector,Quaternion
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'v5_wip'))
from nib_groom_v5 import avoid_goggles

def smooth(value):
    t=max(0.,min(1.,value));return t*t*(3-2*t)

def surface_tree(objects):
    points=[];faces=[]
    for obj in objects:
        offset=len(points);points.extend(obj.matrix_world@v.co for v in obj.data.vertices)
        faces.extend(tuple(offset+i for i in p.vertices) for p in obj.data.polygons)
    return BVHTree.FromPolygons(points,faces)

def repair(obj,guides,tree):
    if obj.data.shape_keys:raise RuntimeError('Card root recipe requires the existing unshaped groom card mesh')
    if np.max(abs(np.asarray(obj.matrix_world)-np.eye(4)))>1e-7:raise RuntimeError('Existing card vertices must be in rig/world metres')
    before=np.asarray([v.co[:] for v in obj.data.vertices],float);after=before.copy()
    normals=[Vector(n.vector) for n in obj.data.corner_normals]
    bone=obj.get('bone');cursor=0;root_rows=[];changes=[];depths=[];normal_targets={};goggle_bounded=[]
    def reconstructed(guide,angle,row,sign):
        short=guide['shortNap'];segments=3 if short else 5;t=row/segments
        root=Vector(guide['root']);middle=Vector(guide['middle']);tip=Vector(guide['tip']);normal=Vector(guide['normal'])
        center=(1-t)**2*root+2*t*(1-t)*middle+t*t*tip
        if bone=='Head':center=avoid_goggles(center)
        tangent=(2*(1-t)*(middle-root)+2*t*(tip-middle)).normalized()
        across=tangent.cross(normal)
        if across.length<1e-6:across=tangent.cross(Vector((1,0,0)))
        if across.length<1e-6:across=tangent.cross(Vector((0,1,0)))
        across.normalize();across=Quaternion(tangent,angle)@across
        width=guide['halfWidthMeters']*(.72+.38*math.sin(t*math.pi))*(1-t)**.35
        point=center+sign*width*across
        if bone=='Head':point=avoid_goggles(point)
        return point,center,tangent,width
    reconstruction_error=0.
    for guide_index,guide in enumerate(guides):
        segments=3 if guide['shortNap'] else 5
        root=Vector(guide['root']);skin,normal,_,distance=tree.find_nearest(root)
        if skin is None or distance>.006:raise RuntimeError('Actual groom root has no nearby anatomical support '+str((obj.name,guide_index,distance)))
        if normal.dot(Vector(guide['normal']))<.4:raise RuntimeError('Actual root support faces away from authored guide')
        for angle in ([0.] if guide['shortNap'] else [-.40,.40]):
            # Verify every existing vertex against the exact saved guide recipe
            # before relying on its row topology. No nearest-component guess.
            for j in range(segments):
                for k,sign in enumerate([-1,1]):
                    old,center,tangent,width=reconstructed(guide,angle,j,sign)
                    index=cursor+j*2+k
                    error=(old-Vector(before[index])).length;reconstruction_error=max(reconstruction_error,error)
                    if error>2e-7:raise RuntimeError('Saved card/guide point correspondence differs '+str((obj.name,index,error)))
                    t=j/segments
                    if t>=.4:continue
                    across=tangent.cross(normal)
                    if across.length<1e-6:raise RuntimeError('Root tangent is normal to its actual skin support')
                    across.normalize();across=Quaternion(tangent,angle*smooth(t/.45))@across
                    root_shift=skin-root-normal*.00050
                    point=center+root_shift*(1-smooth(t/.4))+across*width*sign
                    if j==0:
                        support,n,_,root_distance=tree.find_nearest(point)
                        if support is None or root_distance>.006:raise RuntimeError('Card root corner lost anatomical support')
                        point=support-n*.00050
                        if bone=='Head':
                            safe=avoid_goggles(point)
                            if (safe-point).length>.00005:
                                # A root under a lens must not be pushed onto a
                                # false flat envelope. Record and preserve it
                                # for the subsequent guide-placement pass.
                                goggle_bounded.append(index);continue
                        depth=float((point-support).dot(n));depths.append(depth);root_rows.append(index);normal_targets[index]=n
                    else:normal_targets[index]=normal
                    if bone=='Head':point=avoid_goggles(point)
                    displacement=(point-Vector(before[index])).length
                    if displacement>.006:raise RuntimeError('Bounded attachment exceeds six millimetres '+str((obj.name,index,displacement)))
                    after[index]=point;changes.append(displacement)
            tip=Vector(guide['tip']);tip=avoid_goggles(tip) if bone=='Head' else tip
            reconstruction_error=max(reconstruction_error,(tip-Vector(before[cursor+segments*2])).length)
            if (tip-Vector(before[cursor+segments*2])).length>2e-7:raise RuntimeError('Saved card tip differs from recorded guide')
            cursor+=segments*2+1
    if cursor!=len(before):raise RuntimeError('Guide/card vertex counts differ')
    obj.data.vertices.foreach_set('co',after.astype(np.float32).ravel());obj.data.update()
    for loop in obj.data.loops:
        if loop.vertex_index in normal_targets:normals[loop.index]=normal_targets[loop.vertex_index]
    obj.data.normals_split_custom_set(normals)
    obj.data.calc_loop_triangles();tri=np.asarray([t.vertices[:] for t in obj.data.loop_triangles],int)
    def vectors(points):
        p=points[tri];return np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0])
    old=vectors(before);new=vectors(after);old_area=np.linalg.norm(old,axis=1);new_area=np.linalg.norm(new,axis=1)
    degenerate=int(np.sum((new_area<=1e-16)&(old_area>1e-16)))
    if degenerate:raise RuntimeError('Attachment introduced a degenerate card triangle')
    dots=np.sum(old*new,axis=1)/np.maximum(old_area*new_area,1e-25)
    return {'object':obj.name,'guides':len(guides),'cards':int(obj.get('fur_cards',0)),
        'exactGuideCorrespondenceMaxMeters':reconstruction_error,'changedVertices':int(np.any(after!=before,axis=1).sum()),
        'maximumVertexMoveMeters':max(changes,default=0.),'embeddedRootCorners':len(root_rows),
        'rootSignedDepthRangeMeters':[min(depths,default=0.),max(depths,default=0.)],
        'lensEnvelopeExceptionsPreserved':goggle_bounded,'introducedDegenerateTriangles':degenerate,
        'trianglesRotatedOver90':int(np.sum(dots<0)),'minimumAreaRatio':float(np.min(new_area/np.maximum(old_area,1e-25))),
        'tipVerticesAndRowsFrom40PercentUnchanged':True,'atlasUVTopologyMaterialsWeightsUnchanged':True,
        'status':'Actual geometry operation; root visibility and flow still require source renders'}
