"""Compare authored source/derived skinning at sampled real animation poses.

Uses the rig's evaluated bone matrices, portable named morph drivers and linear
blend skinning. Mesh evaluation is disabled while sampling the rig. This is a
sampled source-vs-derivative test, not an engine or visual acceptance result.
"""
import bpy, math
import numpy as np
from mathutils.bvhtree import BVHTree

def coordinates(points):
    data=np.empty(len(points)*3,dtype=np.float32);points.foreach_get('co',data)
    return data.reshape(-1,3)

def collect_poses(rig,deformation,clips=None):
    clips=clips or ['Idle','Walk','Run','Melee','Shoot','Hit','FacePerformance']
    scene=bpy.context.scene;original_frame=scene.frame_current
    original_action=rig.animation_data.action if rig.animation_data else None
    hidden={o:o.hide_viewport for o in bpy.data.objects if o.type=='MESH'}
    original_pose={b.name:b.matrix_basis.copy() for b in rig.pose.bones}
    samples=[]
    try:
        for o in hidden:o.hide_viewport=True
        rig.animation_data_create()
        for clip in clips:
            action=bpy.data.actions.get(clip)
            if action is None:raise RuntimeError('Missing authored action '+clip)
            rig.animation_data.action=action
            if action.slots:rig.animation_data.action_slot=action.slots[0]
            start,end=action.frame_range
            for fraction in ([0,.25,.5,.75] if clip in ['Walk','Run'] else [.15,.46,.75]):
                frame=float(start)+(float(end)-float(start))*fraction
                scene.frame_set(int(frame),subframe=frame-int(frame));bpy.context.view_layer.update()
                world=rig.matrix_world;invworld=world.inverted()
                matrices={b.name:np.asarray(world@rig.pose.bones[b.name].matrix@b.matrix_local.inverted()@invworld,dtype=np.float64) for b in rig.data.bones}
                morphs={}
                for driver in deformation['drivers']:
                    pose=rig.pose.bones[driver['bone']]
                    if driver['channel']=='rotationMagnitudeDegrees':
                        q=pose.matrix_basis.to_quaternion();q.normalize()
                        metric=math.degrees(2*math.acos(min(1,abs(q.w))))
                    elif driver['channel']=='translationDistanceMeters':metric=pose.location.length
                    else:raise RuntimeError('Unsupported portable driver channel '+driver['channel'])
                    t=(metric-driver['start'])/(driver['end']-driver['start'])
                    morphs[driver['morph']]=min(driver.get('maxWeight',1),max(0,t))
                samples.append({'clip':clip,'fraction':fraction,'frame':frame,'boneMatrices':matrices,'morphs':morphs})
    finally:
        rig.animation_data.action=original_action
        scene.frame_set(original_frame)
        if original_action is None:
            for name,matrix in original_pose.items():rig.pose.bones[name].matrix_basis=matrix
        for obj,visibility in hidden.items():obj.hide_viewport=visibility
    return samples

def weight_groups(obj,indices,bone_names):
    index_to_name={g.index:g.name for g in obj.vertex_groups if g.name in bone_names}
    collected={}
    for new_index,old_index in enumerate(indices):
        for entry in obj.data.vertices[int(old_index)].groups:
            name=index_to_name.get(entry.group)
            if name is not None and entry.weight>0:
                pair=collected.setdefault(name,([],[]));pair[0].append(new_index);pair[1].append(entry.weight)
    return {name:(np.asarray(pair[0],dtype=np.int32),np.asarray(pair[1],dtype=float)) for name,pair in collected.items()}

def shaped_points(obj,indices):
    shapes=obj.data.shape_keys
    basis=coordinates(shapes.key_blocks['Basis'].data if shapes else obj.data.vertices)
    base=basis[indices]
    deltas={shape.name:(coordinates(shape.data)-basis)[indices] for shape in list(shapes.key_blocks)[1:]} if shapes else {}
    return base,deltas

def skin(base,deltas,groups,world,sample):
    points=base.copy()
    for name,delta in deltas.items():points+=delta*sample['morphs'].get(name,0)
    world_points=points@world[:3,:3].T+world[:3,3]
    result=np.zeros_like(world_points,dtype=float)
    for name,(indices,weights) in groups.items():
        matrix=sample['boneMatrices'][name]
        result[indices]+=(world_points[indices]@matrix[:3,:3].T+matrix[:3,3])*weights[:,None]
    return result

def compare_posed_skin(source,derived,rig,samples,correspondence,statistics,sample_count=8000,max_error=.0035,raise_on_failure=True):
    # The wrapper uses the already reviewed barycentric correspondence helper.
    sv=coordinates(source.data.shape_keys.key_blocks['Basis'].data if source.data.shape_keys else source.data.vertices)
    lv=coordinates(derived.data.shape_keys.key_blocks['Basis'].data if derived.data.shape_keys else derived.data.vertices)
    derived.data.calc_loop_triangles();triangles=np.asarray([tuple(t.vertices) for t in derived.data.loop_triangles],dtype=np.int32)
    selected=np.unique(np.linspace(0,len(sv)-1,min(sample_count,len(sv)),dtype=np.int32))
    tree=BVHTree.FromPolygons(lv.tolist(),triangles.tolist(),all_triangles=True)
    ids,weights,_=correspondence(tree,lv,triangles,sv[selected])
    source_base,source_delta=shaped_points(source,selected)
    derived_base,derived_delta=shaped_points(derived,np.arange(len(lv),dtype=np.int32))
    source_groups=weight_groups(source,selected,rig.data.bones)
    derived_groups=weight_groups(derived,np.arange(len(lv)),rig.data.bones)
    world=np.asarray(source.matrix_world,dtype=float);derived_world=np.asarray(derived.matrix_world,dtype=float)
    if np.max(np.abs(world-derived_world))>1e-7:raise RuntimeError('Source/derived transforms differ')
    report={'samplesPerPose':len(selected),'method':'Evaluated authored rig matrices, named portable morph drivers, LBS and fixed rest barycentric correspondence.','poses':[]}
    worst_max=-1
    def vertex_weights(obj,index):
        return {obj.vertex_groups[w.group].name:float(w.weight) for w in obj.data.vertices[int(index)].groups if w.weight>1e-8 and obj.vertex_groups[w.group].name in rig.data.bones}
    for sample in samples:
        source_pose=skin(source_base,source_delta,source_groups,world,sample)
        derived_pose=skin(derived_base,derived_delta,derived_groups,derived_world,sample)
        reconstructed=np.einsum('ijk,ij->ik',derived_pose[ids],weights)
        errors=np.linalg.norm(source_pose-reconstructed,axis=1)
        metrics=statistics(errors)
        report['poses'].append({'clip':sample['clip'],'fraction':sample['fraction'],'frame':sample['frame'],**metrics})
        if metrics['maxMeters']>worst_max:
            worst_max=metrics['maxMeters'];worst=[]
            for local in np.argsort(-errors)[:12]:
                source_index=int(selected[local]);triangle=[int(i) for i in ids[local]]
                worst.append({'errorMeters':float(errors[local]),'sourceVertexId':source_index,
                              'sourceRestLocalMeters':sv[source_index].tolist(),
                              'sourceWorldPosedMeters':source_pose[local].tolist(),
                              'derivedWorldReconstructedMeters':reconstructed[local].tolist(),
                              'sourceBoneWeights':vertex_weights(source,source_index),
                              'derivedTriangleVertexIds':triangle,
                              'derivedTriangleRestLocalMeters':lv[triangle].tolist(),
                              'barycentricWeights':weights[local].tolist(),
                              'derivedTriangleBoneWeights':[vertex_weights(derived,i) for i in triangle]})
            report['worstPose']={'clip':sample['clip'],'fraction':sample['fraction'],'frame':sample['frame'],
                                 'activeMorphWeights':{n:float(w) for n,w in sample['morphs'].items() if w>1e-7},
                                 'worstVertices':worst}
    report['maxMeters']=max(p['maxMeters'] for p in report['poses'])
    report['passed']=report['maxMeters']<=max_error
    if not report['passed'] and raise_on_failure:raise RuntimeError(f'{source.name}: posed skin discrepancy {report["maxMeters"]}m exceeds {max_error}m')
    return report
