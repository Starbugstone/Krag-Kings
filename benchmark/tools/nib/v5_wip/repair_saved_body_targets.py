"""Restore only body targets from their existing radial authoring definition.

Preserve the diagnosed source, all Basis geometry, facial keys, rig and clips.
Do not carry mixed old target deltas into the independently saved derivative.
"""
import bpy,hashlib,json,sys
from pathlib import Path
import numpy as np
from mathutils import Matrix
ROOT=Path(__file__).resolve().parents[4];ART=ROOT/'benchmark/art/nib'
SOURCE=ART/'Nib_Runtime_Optimized_v4b.blend';TARGET=ART/'Nib_Runtime_Optimized_v4b_MorphRepair.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
rig=bpy.data.objects['Nib_Rig'];scene=bpy.context.scene;action=rig.animation_data.action
rig.animation_data.action=None
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update()
centers={}
for side,sign in [('L',1),('R',-1)]:
    for name,point,radius,amount in [('ShoulderRaise',(sign*.128,.005,.938),.075,.003),('ElbowFlex',(sign*.189,-.003,.769),.055,.003),('HipFlex',(sign*.066,.009,.594),.09,.004),('KneeFlex',(sign*.073,.015,.35),.065,.003)]:
        centers['Corrective_'+name+'_'+side]=(np.array(point),radius,amount)
def coordinates(data):
    a=np.empty(len(data)*3,dtype=np.float32);data.foreach_get('co',a);return a.reshape(-1,3)
changes=[];invariants=[]
for obj in bpy.data.collections['Nib_Authored_Components'].objects:
    if obj.type!='MESH' or not obj.data.shape_keys:continue
    keys=obj.data.shape_keys.key_blocks;basis=coordinates(keys['Basis'].data)
    immutable={k.name:hashlib.sha256(coordinates(k.data).tobytes()).hexdigest() for k in keys if not k.name.startswith('Corrective_')}
    transform=np.array(obj.matrix_world,dtype=np.float64);rotation=transform[:3,:3];inverse=np.linalg.inv(rotation)
    world=basis@rotation.T+transform[:3,3]
    for key in keys:
        if not key.name.startswith('Corrective_'):continue
        if key.name not in centers:raise RuntimeError('Unknown authored body target '+key.name)
        center,radius,amount=centers[key.name];offset=world-center;distance=np.linalg.norm(offset,axis=1)
        support=(distance<radius)&(distance>1e-8);delta=np.zeros_like(world)
        delta[support]=(offset[support]/distance[support,None])*(amount*(1-distance[support]/radius)**2)[:,None]
        previous=(coordinates(key.data)-basis)@rotation.T
        key.data.foreach_set('co',(basis+delta@inverse.T).astype(np.float32).ravel())
        actual=(coordinates(key.data)-basis)@rotation.T
        error=float(np.linalg.norm(actual-delta,axis=1).max())
        if error>1e-7:raise RuntimeError('Reconstructed body delta changed beyond float storage tolerance')
        changes.append({'object':obj.name,'target':key.name,'supportCenterMeters':center.tolist(),
                        'radiusMeters':radius,'authoredAmplitudeMeters':amount,
                        'oldMaxWorldDeltaMeters':float(np.linalg.norm(previous,axis=1).max()),
                        'newMaxWorldDeltaMeters':float(np.linalg.norm(actual,axis=1).max()),
                        'formulaStorageMaxErrorMeters':error,'supportedVertices':int(support.sum())})
    for name,digest in immutable.items():
        if hashlib.sha256(coordinates(keys[name].data).tobytes()).hexdigest()!=digest:raise RuntimeError('Unrelated key changed: '+obj.name+'/'+name)
    invariants.append({'object':obj.name,'nonBodyTargetAndBasisHashes':immutable})
rig.animation_data.action=action;scene.frame_set(1);bpy.context.view_layer.update()
scene['body_corrective_repair']='Only existing body keys rebuilt from Basis + original radial centers/radii/amplitudes; mixed-key contamination removed.'
bpy.ops.wm.save_as_mainfile(filepath=str(TARGET),compress=True)
original=json.loads((ART/'v5-study/runtime-reduction-v4b.json').read_text())
report={'passed':True,'sourceSha256':original['sourceSha256'],'inputRuntimeSource':str(SOURCE),
        'inputRuntimeSourceSha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        'candidate':str(TARGET),'candidateSha256':hashlib.sha256(TARGET.read_bytes()).hexdigest(),
        'recipeSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'changes':changes,'unchangedBasisAndFacialKeys':invariants,
        'status':'Technical body-target repair of unaccepted v4b art; engine verification pending',
        'scope':'No topology, UV, weights, material, facial target, bone or animation edits'}
(ART/'v5-study/runtime-morph-repair-source-v4b.json').write_text(json.dumps(report,indent=2)+'\n',newline='\n')
print('NIB_SAVED_BODY_TARGET_REPAIR_COMPLETE',flush=True)
