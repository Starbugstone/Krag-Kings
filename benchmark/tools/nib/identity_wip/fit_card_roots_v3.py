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

class SmoothSurface:
    """Same interpolated vertex normals used by the actual guide sampler.

    The true triangle normal remains independent evidence for side/clearance.
    A sharp ear edge is not misclassified merely because its smooth normal
    differs from one narrow side-wall triangle.
    """
    def __init__(self, objects):
        points=[];faces=[];normals=[];self.origins=[]
        for obj in objects:
            offset=len(points);matrix=obj.matrix_world
            normal_matrix=matrix.to_3x3().inverted().transposed()
            points.extend(matrix@v.co for v in obj.data.vertices)
            normals.extend((normal_matrix@v.normal).normalized() for v in obj.data.vertices)
            obj.data.calc_loop_triangles()
            faces.extend(tuple(offset+i for i in triangle.vertices) for triangle in obj.data.loop_triangles)
            self.origins.extend({'object':obj.name,'polygon':triangle.polygon_index,'vertices':list(triangle.vertices)} for triangle in obj.data.loop_triangles)
        self.points=np.asarray(points,dtype=np.float64);self.faces=np.asarray(faces,dtype=np.int32)
        self.normals=np.asarray(normals,dtype=np.float64)
        self.tree=BVHTree.FromPolygons(points,faces,all_triangles=True)
    def geometric_normal(self,index):
        p=self.points[self.faces[index]];normal=np.cross(p[1]-p[0],p[2]-p[0]);length=np.linalg.norm(normal)
        if length<1e-15:raise RuntimeError('Degenerate anatomical support triangle')
        return Vector(normal/length)
    def smooth_normal(self,point,index):
        p=self.points[self.faces[index]];u=p[1]-p[0];v=p[2]-p[0];w=np.asarray(point)-p[0]
        uu=float(u@u);uv=float(u@v);vv=float(v@v);uw=float(u@w);vw=float(v@w);denom=uu*vv-uv*uv
        if denom<=1e-28:raise RuntimeError('Singular support correspondence')
        b=(vv*uw-uv*vw)/denom;c=(uu*vw-uv*uw)/denom;weights=np.asarray([1-b-c,b,c])
        if weights.min() < -1e-4:raise RuntimeError('Nearest support falls outside its reported triangle')
        weights=np.maximum(weights,0);weights/=weights.sum()
        normal=Vector(weights@self.normals[self.faces[index]])
        if normal.length<1e-6:raise RuntimeError('Invalid interpolated guide-support normal')
        return normal.normalized()
    def find_nearest(self,point):
        hit,normal,index,distance=self.tree.find_nearest(point)
        return hit,self.smooth_normal(hit,index) if hit is not None else None,index,distance
    def find_facing(self,point,direction):
        """Closest existing support on the original guide-facing side."""
        first=self.tree.find_nearest(point)
        def accepted(value):
            hit,geometric,index,distance=value
            if hit is None or distance>.006:return None
            normal=self.smooth_normal(hit,index)
            if normal.dot(direction)<.4 or geometric.dot(direction)<=0 or geometric.dot(normal)<=0:return None
            return hit,normal,index,distance
        direct=accepted(first)
        if direct is not None:return (*direct,None)
        nearby=self.tree.find_nearest_range(point,.006)
        for value in sorted(nearby,key=lambda item:item[3]):
            candidate=accepted(value)
            if candidate is not None:
                switch={'nearest':self.origins[first[2]] if first[0] is not None else None,
                        'fitted':self.origins[value[2]],'fittedDistanceMeters':value[3]}
                return (*candidate,switch)
        raise RuntimeError('No original-side guide support within six millimetres '+str(tuple(point)))
    def embedded(self,point,index):
        """Cap root burial by actual nearby opposing geometry, not flat width."""
        normal=self.geometric_normal(index);epsilon=.000002
        hit,n,face,distance=self.tree.ray_cast(point-normal*epsilon,-normal,.010)
        measured=None
        if hit is not None:
            measured=float(distance+epsilon)
            depth=min(.00050,measured*.20)
        else:depth=.00050
        # Below the source's geometric resolution, keep a surface attachment
        # rather than force it through an extremely thin ear boundary.
        if depth<.000002:depth=0.
        return point-normal*depth,depth,measured

def surface_tree(objects):
    return SmoothSurface(objects)

def repair(obj,guides,tree):
    if obj.data.shape_keys:raise RuntimeError('Card root recipe requires the existing unshaped groom card mesh')
    if np.max(abs(np.asarray(obj.matrix_world)-np.eye(4)))>1e-7:raise RuntimeError('Existing card vertices must be in rig/world metres')
    before=np.asarray([v.co[:] for v in obj.data.vertices],float);after=before.copy()
    normals=[Vector(n.vector) for n in obj.data.corner_normals]
    bone=obj.get('bone');cursor=0;root_rows=[];changes=[];depths=[];geometric_depths=[];normal_targets={};goggle_bounded=[]
    normal_agreement=[];geometric_agreement=[]
    support_switches=[];burial_depths=[];opposing_distances=[]
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
    reconstruction_error=0.;correspondence_tolerances=[]
    def source_precision_bound(point):
        # Reconstructing JSON guide operations involves float32 mathutils.
        # Four component ULPs cover accumulated rounding, capped at 1 micron.
        ulps=np.spacing(np.abs(np.asarray(point,dtype=np.float32))).astype(np.float64)
        return min(1e-6,max(1e-7,float(np.linalg.norm(4*ulps))))
    for guide_index,guide in enumerate(guides):
        segments=3 if guide['shortNap'] else 5
        root=Vector(guide['root']);guide_normal=Vector(guide['normal'])
        skin,normal,support_face,distance,switch=tree.find_facing(root,guide_normal)
        if switch is not None:support_switches.append({'guide':guide_index,'part':'center',**switch})
        if skin is None or distance>.006:raise RuntimeError('Actual groom root has no nearby anatomical support '+str((obj.name,guide_index,distance)))
        smooth_dot=normal.dot(guide_normal);geometric_dot=tree.geometric_normal(support_face).dot(guide_normal)
        normal_agreement.append(smooth_dot);geometric_agreement.append(geometric_dot)
        if smooth_dot<.4:raise RuntimeError('Interpolated support faces away from authored guide '+str((obj.name,guide_index,smooth_dot)))
        if geometric_dot<=0:raise RuntimeError('Actual geometric support is on the wrong side '+str((obj.name,guide_index,geometric_dot)))
        for angle in ([0.] if guide['shortNap'] else [-.40,.40]):
            # Verify every existing vertex against the exact saved guide recipe
            # before relying on its row topology. No nearest-component guess.
            for j in range(segments):
                for k,sign in enumerate([-1,1]):
                    old,center,tangent,width=reconstructed(guide,angle,j,sign)
                    index=cursor+j*2+k
                    error=(old-Vector(before[index])).length;reconstruction_error=max(reconstruction_error,error)
                    tolerance=source_precision_bound(before[index]);correspondence_tolerances.append(tolerance)
                    if error>tolerance:raise RuntimeError('Saved card/guide point correspondence differs '+str((obj.name,index,error,tolerance)))
                    t=j/segments
                    if t>=.4:continue
                    across=tangent.cross(normal)
                    if across.length<1e-6:raise RuntimeError('Root tangent is normal to its actual skin support')
                    across.normalize();across=Quaternion(tangent,angle*smooth(t/.45))@across
                    root_shift=skin-root
                    point=center+root_shift*(1-smooth(t/.4))+across*width*sign
                    if j==0:
                        support,n,corner_face,root_distance,switch=tree.find_facing(point,guide_normal)
                        if switch is not None:support_switches.append({'guide':guide_index,'corner':sign,'layerAngle':angle,**switch})
                        if support is None or root_distance>.006:raise RuntimeError('Card root corner lost anatomical support')
                        if tree.geometric_normal(corner_face).dot(n)<=0:
                            raise RuntimeError('Root corner smooth/geometric sides disagree '+str({'object':obj.name,'guide':guide_index,'corner':sign,'support':tree.origins[corner_face]}))
                        point,burial,opposing=tree.embedded(support,corner_face)
                        if bone=='Head':
                            safe=avoid_goggles(point)
                            if (safe-point).length>.00005:
                                # A root under a lens must not be pushed onto a
                                # false flat envelope. Record and preserve it
                                # for the subsequent guide-placement pass.
                                goggle_bounded.append(index);continue
                        depth=float((point-support).dot(n));depths.append(depth)
                        geometric_depths.append(float((point-support).dot(tree.geometric_normal(corner_face))))
                        burial_depths.append(burial)
                        if opposing is not None:opposing_distances.append(opposing)
                        root_rows.append(index);normal_targets[index]=n
                    else:normal_targets[index]=normal
                    if bone=='Head':point=avoid_goggles(point)
                    displacement=(point-Vector(before[index])).length
                    if displacement>.006:raise RuntimeError('Bounded attachment exceeds six millimetres '+str((obj.name,index,displacement)))
                    after[index]=point;changes.append(displacement)
            tip=Vector(guide['tip']);tip=avoid_goggles(tip) if bone=='Head' else tip
            reconstruction_error=max(reconstruction_error,(tip-Vector(before[cursor+segments*2])).length)
            tolerance=source_precision_bound(before[cursor+segments*2]);correspondence_tolerances.append(tolerance)
            if (tip-Vector(before[cursor+segments*2])).length>tolerance:raise RuntimeError('Saved card tip differs from recorded guide')
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
        'exactGuideCorrespondenceMaxMeters':reconstruction_error,
        'guideCorrespondenceToleranceRule':'Four float32 component ULPs, norm bounded between0.1 and1 micrometre',
        'guideCorrespondenceToleranceRangeMeters':[min(correspondence_tolerances),max(correspondence_tolerances)],'changedVertices':int(np.any(after!=before,axis=1).sum()),
        'maximumVertexMoveMeters':max(changes,default=0.),'embeddedRootCorners':len(root_rows),
        'rootSignedDepthRangeMeters':[min(depths,default=0.),max(depths,default=0.)],
        'rootGeometricPlaneDepthRangeMeters':[min(geometric_depths,default=0.),max(geometric_depths,default=0.)],
        'minimumInterpolatedSupportGuideNormalDot':min(normal_agreement,default=1.),
        'minimumIndependentGeometricGuideNormalDot':min(geometric_agreement,default=1.),
        'sameSideSupportSwitches':support_switches,
        'burialDepthRangeMeters':[min(burial_depths,default=0.),max(burial_depths,default=0.)],
        'measuredOpposingSurfaceDistanceRangeMeters':[min(opposing_distances,default=0.),max(opposing_distances,default=0.)],
        'burialRule':'At most0.5mm and20percent of measured inward ray clearance; extremely thin support remains surface-attached',
        'lensEnvelopeExceptionsPreserved':goggle_bounded,'introducedDegenerateTriangles':degenerate,
        'trianglesRotatedOver90':int(np.sum(dots<0)),'minimumAreaRatio':float(np.min(new_area/np.maximum(old_area,1e-25))),
        'tipVerticesAndRowsFrom40PercentUnchanged':True,'atlasUVTopologyMaterialsWeightsUnchanged':True,
        'status':'Actual geometry operation; root visibility and flow still require source renders'}
