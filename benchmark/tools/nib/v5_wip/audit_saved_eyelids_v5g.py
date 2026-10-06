"""Read-only attribution of the actual v5g Blink failure against saved v5f.

No source is saved. The old Blink deltas are substituted only in memory,
preserving the new Basis and the same actual animation/bone pose, to isolate
the newly introduced support cutoff from inherited closure/squint defects.
"""
import hashlib,json,sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Matrix

HERE=Path(__file__).parent;ROOT=HERE.parents[3]
sys.path.insert(0,str(HERE))
from face_planes_v5g import semantics

ART=ROOT/'benchmark/art/nib';OUT=ART/'v5-study/native-v5g-eyelid-audit.json'
PRIOR=ART/'Nib_Master_v5f_JawRepair_WIP.blend'
CURRENT=ART/'Nib_Master_v5g_FacePlanes_WIP.blend'
EXPECTED=['9b3380fd9b44eb2cff299310ae89f95d3faa4600c5653cc6ca06fba6fcf5c90e',
          '1586cb3a4c66897be5d1b2c5ba43fdb34a462a6fc96d6d51d90fa417dd185db9']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
coordinates=lambda items:np.asarray([tuple(v.co) for v in items],dtype=np.float64)
for p,expected in zip([PRIOR,CURRENT],EXPECTED):
    if sha(p)!=expected:raise RuntimeError('Frozen source changed: '+p.name)

bpy.ops.wm.open_mainfile(filepath=str(PRIOR),load_ui=False)
prior=bpy.data.objects['Nib v5 fitted animation face'];prior_keys=prior.data.shape_keys
old_basis=coordinates(prior_keys.key_blocks['Basis'].data)
old_deltas={k.name:coordinates(k.data)-old_basis for k in prior_keys.key_blocks if k.name.startswith(('Blink_','Squint_'))}
old_source=np.asarray([tuple(v.vector) for v in prior.data.attributes['nib_source_position'].data])
bpy.ops.wm.open_mainfile(filepath=str(CURRENT),load_ui=False)
scene=bpy.context.scene;rig=bpy.data.objects['Nib_Rig'];head=bpy.data.objects['Nib v5 fitted animation face']
for obj in scene.objects:
    if obj.type=='MESH':
        obj.hide_set(obj is not head)
        for modifier in obj.modifiers:
            if modifier.type=='ARMATURE':modifier.show_viewport=(obj is head)
head.hide_set(False);head.hide_viewport=False;rig.hide_set(False);rig.hide_viewport=False
keys=head.data.shape_keys;drivers=list(keys.animation_data.drivers)
basis=coordinates(keys.key_blocks['Basis'].data)
source=np.asarray([tuple(v.vector) for v in head.data.attributes['nib_source_position'].data])
if not np.array_equal(source,old_source):raise RuntimeError('Retained source correspondence changed')
faces=[list(p.vertices) for p in head.data.polygons]
edges=np.asarray([tuple(e.vertices) for e in head.data.edges],dtype=np.int32)
sets=np.asarray([v.value for v in head.data.attributes['.sculpt_face_set'].data],dtype=np.int32)
tags=semantics(len(source),faces,sets);nasal=tags[11]
boundary=nasal[edges[:,0]]!=nasal[edges[:,1]]
x,y,z=source.T;region=(abs(x)<.090)&(y<-.075)&(z>.265)&(z<.352)
selected=region[edges].all(axis=1)
new_deltas={name:coordinates(keys.key_blocks[name].data)-basis for name in old_deltas}
length=np.linalg.norm(basis[edges[:,1]]-basis[edges[:,0]],axis=1)

def values():return {k.name:float(k.value) for k in keys.key_blocks if k.name!='Basis'}
def set_values(state):
    for driver in drivers:driver.mute=True
    for key in keys.key_blocks:
        if key.name!='Basis':key.value=state.get(key.name,0.)
def rest():
    rig.animation_data.action=None
    for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
    bpy.context.view_layer.update()
def evaluated():
    head.data.update();bpy.context.view_layer.update()
    obj=head.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=obj.to_mesh()
    try:
        if len(mesh.vertices)!=len(source):raise RuntimeError('Audit modifier changed vertex indexing')
        return np.asarray([tuple(obj.matrix_world@v.co) for v in mesh.vertices])
    finally:obj.to_mesh_clear()
def stretch(points,neutral):
    current=np.linalg.norm(points[edges[:,1]]-points[edges[:,0]],axis=1)
    rest_length=np.linalg.norm(neutral[edges[:,1]]-neutral[edges[:,0]],axis=1)
    valid=selected&(rest_length>1e-8);ratio=current[valid]/rest_length[valid]
    ids=np.flatnonzero(valid);worst=ids[np.argsort(ratio)[-12:][::-1]]
    return {'maximum':float(ratio.max()),'p99':float(np.percentile(ratio,99)),
        'worstEdges':[{'edge':int(i),'vertices':edges[i].tolist(),'nasalBoundary':bool(boundary[i]),
            'neutralLengthMeters':float(rest_length[i]),'posedLengthMeters':float(current[i])} for i in worst]}

rest();set_values({});neutral=evaluated()
report={'status':'Actual saved-pose diagnosis; no repair, render acceptance or source save',
    'sources':{p.name:h for p,h in zip([PRIOR,CURRENT],EXPECTED)},'codeSha256':sha(Path(__file__)),
    'vertexCount':len(source),'nasalVertices':int(nasal.sum()),'nasalBoundaryEdges':int(boundary.sum()),
    'keyBoundaryGradients':{},'poses':{},'sharedChanged':False}
for name in old_deltas:
    row={}
    for label,delta in [('v5f',old_deltas[name]),('v5g',new_deltas[name])]:
        difference=np.linalg.norm(delta[edges[:,1]]-delta[edges[:,0]],axis=1)
        ids=np.flatnonzero(boundary&selected);worst=int(ids[np.argmax(difference[ids]/np.maximum(length[ids],1e-10))])
        row[label]={'nasalMaximumDeltaMeters':float(np.linalg.norm(delta[nasal],axis=1).max()),
            'maximumBoundaryDeltaJumpMeters':float(difference[ids].max()),
            'maximumBoundaryGradient':float(np.max(difference[ids]/np.maximum(length[ids],1e-10))),
            'worstEdge':int(worst),'worstEdgeVertices':edges[worst].tolist()}
    report['keyBoundaryGradients'][name]=row
cache={'source':source,'basis':basis,'priorBasis':old_basis,'edges':edges,
       'faces':np.asarray(faces,dtype=object),'face_sets':sets,'neutral':neutral}
for name in old_deltas:cache['old_'+name]=old_deltas[name];cache['new_'+name]=new_deltas[name]
for name,frame in [('Blink',16),('Tongue',103)]:
    for driver in drivers:driver.mute=False
    rig.animation_data.action=bpy.data.actions['FacePerformance'];scene.frame_set(frame)
    full=evaluated();active=values()
    set_values({});skeletal=evaluated()
    rest();set_values(active);morph=evaluated()
    # Restore the same full bone pose, then substitute only the old Blink
    # relative fields onto the new Basis. The candidate is never saved.
    for driver in drivers:driver.mute=False
    rig.animation_data.action=bpy.data.actions['FacePerformance'];scene.frame_set(frame)
    for key_name in old_deltas:
        if key_name.startswith('Blink_'):
            keys.key_blocks[key_name].data.foreach_set('co',(basis+old_deltas[key_name]).astype(np.float32).ravel())
    old_blink=evaluated()
    for key_name in old_deltas:
        keys.key_blocks[key_name].data.foreach_set('co',(basis+new_deltas[key_name]).astype(np.float32).ravel())
    report['poses'][name]={'frame':frame,'actualKeyValues':active,
        'full':stretch(full,neutral),'skeletalOnly':stretch(skeletal,neutral),'morphOnly':stretch(morph,neutral),
        'oldBlinkCounterfactual':stretch(old_blink,neutral),
        'oldBlinkSubstitutionMaximumDifferenceMeters':float(np.linalg.norm(full-old_blink,axis=1).max()),
        'nasalMaximumFullDisplacementMeters':float(np.linalg.norm(full[nasal]-neutral[nasal],axis=1).max())}
    for label,points in [('full',full),('skeletal',skeletal),('morph',morph),('oldBlink',old_blink)]:cache[name+'_'+label]=points
for p,expected in zip([PRIOR,CURRENT],EXPECTED):
    if sha(p)!=expected:raise RuntimeError('Audit changed a saved source')
cache_path=ROOT/'benchmark/local/nib-v5g-eyelid-audit.npz';np.savez_compressed(cache_path,**cache)
report['cacheSha256']=sha(cache_path)
OUT.write_text(json.dumps(report,indent=2)+'\n',newline='\n')
print('NIB_V5G_EYELID_AUDIT_COMPLETE',flush=True)
