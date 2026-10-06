"""Read-only decomposition of the actual saved v5 mouth deformation.

Run only in a serialized guarded Blender process. This writes evidence JSON
and a local numerical cache, never a .blend or shared export. The tongue view
is decomposed into skeletal, morph-only and isolated Jaw contributions before
any repair is selected.
"""
import argparse, hashlib, json, sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

HERE=Path(__file__).parent
ROOT=HERE.parents[3]
sys.path.insert(0,str(HERE))
from audit_face_coordinates import bounds

parser=argparse.ArgumentParser()
parser.add_argument('--source',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
parser.add_argument('--cache',type=Path,required=True)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before=sha(args.source)
bpy.ops.wm.open_mainfile(filepath=str(args.source),load_ui=False)
scene=bpy.context.scene;rig=bpy.data.objects['Nib_Rig']
head=bpy.data.objects['Nib v5 fitted animation face']
# Disable unrelated dense assemblies during this numerical inspection.
for obj in scene.objects:
    if obj.type=='MESH':
        obj.hide_set(obj is not head)
        for mod in obj.modifiers:
            if mod.type=='ARMATURE':mod.show_viewport=(obj is head)
head.hide_set(False);head.hide_viewport=False;rig.hide_set(False);rig.hide_viewport=False
source=np.asarray([tuple(item.vector) for item in head.data.attributes['nib_source_position'].data],dtype=np.float64)
local=np.asarray([tuple(v.co) for v in head.data.vertices],dtype=np.float64)
faces=[list(p.vertices) for p in head.data.polygons]
edges=np.asarray([tuple(e.vertices) for e in head.data.edges],dtype=np.int32)
keys=head.data.shape_keys
drivers=list(keys.animation_data.drivers) if keys.animation_data else []
groups={g.index:g.name for g in head.vertex_groups}
jaw=np.zeros(len(source));head_weights=np.zeros(len(source));neck=np.zeros(len(source))
for v in head.data.vertices:
    for group in v.groups:
        target={'Jaw':jaw,'Head':head_weights,'Neck':neck}.get(groups[group.group])
        if target is not None:target[v.index]=group.weight
face_sets=head.data.attributes.get('.sculpt_face_set')
face_sets=np.asarray([a.value for a in face_sets.data],dtype=np.int32) if face_sets else np.full(len(faces),-1)
face_materials=np.asarray([p.material_index for p in head.data.polygons],dtype=np.int32)

def key_values():return {key.name:float(key.value) for key in keys.key_blocks if key.name!='Basis'}
def set_keys(values):
    for driver in drivers:driver.mute=True
    for key in keys.key_blocks:
        if key.name!='Basis':key.value=values.get(key.name,0.)
def rest_rig():
    rig.animation_data.action=None
    for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
    bpy.context.view_layer.update()
def evaluated_points():
    bpy.context.view_layer.update();deps=bpy.context.evaluated_depsgraph_get()
    obj=head.evaluated_get(deps);mesh=obj.to_mesh()
    try:
        if len(mesh.vertices)!=len(source):raise RuntimeError('Audit modifier changed vertex indexing')
        return np.asarray([tuple(obj.matrix_world@v.co) for v in mesh.vertices],dtype=np.float64)
    finally:obj.to_mesh_clear()

rest_rig();set_keys({});neutral=evaluated_points()
for driver in drivers:driver.mute=False
rig.animation_data.action=bpy.data.actions['FacePerformance'];scene.frame_set(103)
bpy.context.view_layer.update();full=evaluated_points();active=key_values()
poses={bone.name:bone.matrix_basis.copy() for bone in rig.pose.bones}
full_pose={name:{'translation':list(matrix.translation),'quaternion':list(matrix.to_quaternion())}
           for name,matrix in poses.items()}
set_keys({});skeletal=evaluated_points()
rest_rig();set_keys(active);morph=evaluated_points()
rest_rig();set_keys({});rig.pose.bones['Jaw'].matrix_basis=poses['Jaw'];jaw_only=evaluated_points()
stages={'neutral':neutral,'fullTongue':full,'skeletalOnly':skeletal,'morphOnly':morph,'jawOnly':jaw_only}

x,y,z=source.T
regions={
    'nasalTip':(abs(x)<.026)&(y<-.14)&(z>.259)&(z<.282),
    'philtrumUpperMuzzle':(abs(x)<.035)&(y<-.11)&(z>.242)&(z<=.259),
    'upperLipProbe':(abs(x)<.037)&(y<-.117)&(z>.234)&(z<=.242),
    'lowerLipProbe':(abs(x)<.037)&(y<-.117)&(z>.223)&(z<=.234),
    'chinProbe':(abs(x)<.037)&(y<-.08)&(z>.18)&(z<=.215),
}
mouth=(abs(x)<.060)&(y<-.08)&(z>.20)&(z<.282)
selected_edges=np.flatnonzero(mouth[edges].all(axis=1))
rest_lengths=np.linalg.norm(neutral[edges[:,0]]-neutral[edges[:,1]],axis=1)
report={'status':'Actual saved-mesh numerical diagnosis only; no repair, render acceptance or source write',
        'source':str(args.source),'sourceSha256':before,'codeSha256':sha(Path(__file__)),
        'vertexCount':len(source),'polygonCount':len(faces),'jawBoneRestMatrix':[list(row) for row in rig.data.bones['Jaw'].matrix_local],
        'tongueAction':'FacePerformance','tongueFrame':103,'activeMorphs':active,
        'activeFacialPose':{name:full_pose.get(name) for name in ['Jaw','TongueBase','TongueTip','MouthCorner_L','MouthCorner_R']},
        'regions':{},'stages':{},'topology':{}}
for name,mask in regions.items():
    ids=np.flatnonzero(mask)
    report['regions'][name]={'vertices':len(ids),'sourceBounds':bounds(source[ids]),
        'neutralWorldBounds':bounds(neutral[ids]),
        'jawWeightMin':float(jaw[ids].min()) if len(ids) else None,
        'jawWeightMax':float(jaw[ids].max()) if len(ids) else None,
        'jawWeightMean':float(jaw[ids].mean()) if len(ids) else None,
        'maxJawOnlyDisplacementMeters':float(np.linalg.norm(jaw_only[ids]-neutral[ids],axis=1).max()) if len(ids) else None}

for name,points in stages.items():
    lengths=np.linalg.norm(points[edges[:,0]]-points[edges[:,1]],axis=1)
    ratios=lengths/np.maximum(rest_lengths,1e-12)
    worst=selected_edges[np.argsort(ratios[selected_edges])[-20:][::-1]]
    result={'maxMouthEdgeStretchRatio':float(ratios[selected_edges].max()),
            'worstEdges':[],'frontalSkinHits':[]}
    for edge_id in worst:
        a,b=map(int,edges[edge_id])
        result['worstEdges'].append({'edge':int(edge_id),'vertices':[a,b],
            'source':[source[a].tolist(),source[b].tolist()],
            'posedWorld':[points[a].tolist(),points[b].tolist()],
            'jawWeights':[float(jaw[a]),float(jaw[b])],
            'restLengthMeters':float(rest_lengths[edge_id]),'posedLengthMeters':float(lengths[edge_id]),
            'stretchRatio':float(ratios[edge_id])})
    tree=BVHTree.FromPolygons([Vector(p) for p in points],faces)
    for px in [-.035,-.0175,0,.0175,.035]:
        for pz in [1.055,1.063,1.071,1.079,1.087,1.095]:
            hit,normal,index,_=tree.ray_cast(Vector((px,-1,pz)),Vector((0,1,0)),2)
            if index is None:continue
            ids=faces[index]
            result['frontalSkinHits'].append({'queryXZ':[px,pz],'hit':list(hit),'normal':list(normal),
                'polygon':index,'sourceCenter':source[ids].mean(0).tolist(),
                'faceSet':int(face_sets[index]),'material':head.data.materials[int(face_materials[index])].name,
                'jawWeightRange':[float(jaw[ids].min()),float(jaw[ids].max())]})
    report['stages'][name]=result

# The reference has a closed oral bag, so zero open boundary edges does not
# itself imply an aperture is capped. Record near-front upper/lower crossings
# and face-set membership; their anatomy must be interpreted, not deleted by
# a blanket z test.
cross=[]
for polygon,ids in enumerate(faces):
    s=source[ids]
    if np.max(abs(s[:,0]))>.050 or s[:,1].max()>-.117:continue
    if s[:,2].min()<.234 and s[:,2].max()>.238:
        cross.append({'polygon':polygon,'vertices':ids,'source':s.tolist(),
            'faceSet':int(face_sets[polygon]),'jawWeights':jaw[ids].tolist()})
report['topology']['nearFrontUpperLowerCrossingFaces']=cross
report['topology']['note']='Coordinate probes do not replace audited upper/lower lip loops. Closed bag topology can have zero boundaries without capping the mouth.'
args.cache.parent.mkdir(parents=True,exist_ok=True)
np.savez_compressed(args.cache,source=source,local=local,jaw_weights=jaw,
                    head_weights=head_weights,neck_weights=neck,edges=edges,
                    faces=np.asarray(faces,dtype=object),face_sets=face_sets,
                    face_materials=face_materials,**stages)
report['numericCache']={'path':str(args.cache),'sha256':sha(args.cache)}
if sha(args.source)!=before:raise RuntimeError('Read-only audit changed source')
report['sourceUnchanged']=True
args.output.write_text(json.dumps(report,indent=2)+'\n',newline='\n')
print('NIB_SAVED_MOUTH_DEFORMATION_AUDIT_COMPLETE',flush=True)
