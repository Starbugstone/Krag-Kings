"""Prepared clean closed neck termination fitted to the retained anatomy.

No scarf edits. This closes the fitted head mesh and conforms its lower neck to
the retained source body; it does not claim a whole-character topology weld.
"""
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from fit_head_v5d import neck_blend

CUT_Z=.166

def cut_and_close(bm):
    bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),
                          dist=1e-7,plane_co=(0,0,CUT_Z),plane_no=(0,0,1),
                          clear_inner=True,clear_outer=False,use_snap_center=True)
    edges=[e for e in bm.edges if e.is_boundary and all(abs(v.co.z-CUT_Z)<2e-6 for v in e.verts)]
    if len(edges)<6:raise RuntimeError('Missing clean lower neck boundary')
    faces=bmesh.ops.holes_fill(bm,edges=edges,sides=0)['faces']
    if not faces:raise RuntimeError('Neck boundary did not close')
    bmesh.ops.triangulate(bm,faces=faces)
    if any(e.is_boundary and all(abs(v.co.z-CUT_Z)<2e-6 for v in e.verts) for e in bm.edges):
        raise RuntimeError('Open lower neck edges remain after closure')
    return {'cutSourceZ':CUT_Z,'cutBoundaryEdges':len(edges),'closed':True,
            'method':'Actual planar bisect and filled lower boundary; no scarf coverage change'}

def conform_to_body(original,fitted,collection,drop):
    body=next(o for o in collection.objects if o.get('bone')=='BodyAnatomy' and o.get('variant')=='organic')
    points=[body.matrix_world@v.co for v in body.data.vertices]
    tree=BVHTree.FromPolygons(points,[list(p.vertices) for p in body.data.polygons])
    weights=neck_blend(original);count=0;maximum=0.
    for index,weight in enumerate(weights):
        if weight<1e-5:continue
        current=Vector(fitted[index])+Vector((0,0,drop))
        hit,normal,face,distance=tree.find_nearest(current)
        if hit is None or distance>.080:raise RuntimeError('Head neck cannot reach retained anatomy')
        # Terminal ring lies just within the closed body skin. The shared Neck
        # weighting keeps the seam together when Head moves above it.
        target=hit-normal*.0002
        point=current.lerp(target,float(weight))-Vector((0,0,drop))
        maximum=max(maximum,(point-Vector(fitted[index])).length)
        fitted[index]=tuple(point);count+=1
    if count==0:raise RuntimeError('No lower-neck vertices fitted')
    return weights,{'retainedBody':body.name,'fittedVertices':count,
                    'maximumAdjustmentMeters':maximum,'terminalInsetMeters':.0002,
                    'wholeCharacterTopologyWeld':False,
                    'reviewRequired':'Actual bare neck silhouette plus Head/Neck posed seam; source body remains separate'}
