"""Roundtrip isolated clips against their true-rest reference and source poses.

This checks portable skeletal fidelity, not skin deformation or artistic quality.
The input receipt and every FBX are fingerprinted before import. All seven clips
must retain duration, every bone's binding and motion, and local facial acting.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Quaternion, Vector

parser=argparse.ArgumentParser()
parser.add_argument('--directory',type=Path,required=True)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
directory=args.directory
output=directory/'roundtrip.json'
if output.exists():raise RuntimeError('Preserve prior roundtrip evidence')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((directory/'export.json').read_text())
errors=[]
connection_normalizations={}
canonical={'Idle','Walk','Run','Melee','Shoot','Hit','FacePerformance'}
if set(manifest['clips'])!=canonical:errors.append('Expected exactly seven canonical runtime clips')


def angular_error(a,b):
    dot=abs(sum(float(a[i])*float(b[i]) for i in range(4)))
    norm=math.sqrt(sum(float(x)**2 for x in a)*sum(float(x)**2 for x in b))
    if norm<1e-15:raise RuntimeError('Invalid zero quaternion')
    return math.degrees(2*math.acos(min(1.,dot/norm)))


def load(entry,animated):
    path=directory/entry['file']
    if sha(path)!=entry['sha256']:raise RuntimeError('FBX differs from export receipt '+str(path))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(path),use_anim=animated)
    rigs=[o for o in bpy.data.objects if o.type=='ARMATURE']
    if len(rigs)!=1:raise RuntimeError('Expected one imported rig')
    rig=rigs[0]
    # Blender5.2 infers use_connect=True whenever child head equals parent
    # tail, even with force_connect_children=False. This suppresses valid FBX
    # translation curves (proved for Pelvis and TongueTip). Restore the source
    # authoring constraint flags without moving/reparenting any bind joint.
    before={b.name:b.matrix_local.copy() for b in rig.data.bones}
    changed=[b.name for b in rig.data.bones if b.name in manifest['sourceConnected'] and b.use_connect!=manifest['sourceConnected'][b.name]]
    if changed:
        bpy.context.view_layer.objects.active=rig;rig.select_set(True)
        bpy.ops.object.mode_set(mode='EDIT')
        for name in changed:rig.data.edit_bones[name].use_connect=manifest['sourceConnected'][name]
        bpy.ops.object.mode_set(mode='OBJECT')
    drift=max(max(abs(b.matrix_local[i][j]-before[b.name][i][j]) for i in range(4) for j in range(4)) for b in rig.data.bones)
    if drift>1e-6:raise RuntimeError('Source connection restoration changed bind geometry')
    connection_normalizations[entry['file']]={'restoredSourceConnectionFlags':changed,'maximumBindMatrixDrift':drift,
        'reason':'Blender inferred edit-bone connection can suppress correctly imported FBX translation tracks; source flags restored for playback comparison',
        'fbxFileModified':False}
    return rig


rig=load(manifest['bindReference'],False)
reference={b.name:(rig.matrix_world@b.matrix_local).copy() for b in rig.data.bones}
parents={b.name:b.parent.name if b.parent else None for b in rig.data.bones}
if set(reference)!=set(manifest['bones']):errors.append('Rest reference bone names differ from source')
if parents!=manifest['sourceParents']:errors.append('Rest reference hierarchy differs from source')
source_bind_error=max(max(abs(reference[n][i][j]-Matrix(m)[i][j]) for i in range(4) for j in range(4))
                      for n,m in manifest['sourceRest'].items() if n in reference)
if source_bind_error>1e-4:errors.append('True rest FBX matrix differs from saved source')
results={}
for name,entry in manifest['clips'].items():
    rig=load(entry,True)
    world_rest={b.name:(rig.matrix_world@b.matrix_local).copy() for b in rig.data.bones}
    missing=sorted(set(reference)-set(world_rest));extra=sorted(set(world_rest)-set(reference))
    bind_pos=bind_rot=bind_matrix=0.
    imported_parents={b.name:b.parent.name if b.parent else None for b in rig.data.bones}
    for bone in set(reference)&set(world_rest):
        bind_pos=max(bind_pos,(reference[bone].translation-world_rest[bone].translation).length)
        bind_rot=max(bind_rot,angular_error(reference[bone].to_quaternion(),world_rest[bone].to_quaternion()))
        bind_matrix=max(bind_matrix,max(abs(reference[bone][i][j]-world_rest[bone][i][j]) for i in range(4) for j in range(4)))
    actions=list(bpy.data.actions)
    if len(actions)!=1:
        errors.append(name+' expected exactly one runtime take, got '+str([a.name for a in actions]))
    if not actions:continue
    action=actions[0];rig.animation_data_create();rig.animation_data.action=action
    if not (action.name==name or action.name.endswith('|'+name)):
        errors.append(name+' wrong take name '+action.name)
    if action.slots:rig.animation_data.action_slot=action.slots[0]
    scene=bpy.context.scene;fps=scene.render.fps/scene.render.fps_base
    first,last=action.frame_range;source_first,source_last=entry['frameRange']
    duration=(last-first)/fps;source_duration=(source_last-source_first)/entry['fps']
    controls=[b.name for b in rig.pose.bones if b.name=='FaceRoot' or any(p.name=='FaceRoot' for p in b.parent_recursive)]
    local_samples={n:[] for n in controls}
    max_pos=max_rot=max_scale=0.;worst_pos=worst_rot=None
    if len(entry['sourceSamples'])!=17:errors.append(name+' incomplete source sample coverage')
    for sample in entry['sourceSamples']:
        at=first+(sample['frame']-source_first)/entry['fps']*fps
        scene.frame_set(math.floor(at),subframe=at-math.floor(at));bpy.context.view_layer.update()
        for bone,data in sample['bones'].items():
            if bone not in rig.pose.bones:continue
            world=rig.matrix_world@rig.pose.bones[bone].matrix
            pe=(world.translation-Vector(data['head'])).length
            rq=(world@world_rest[bone].inverted()).to_quaternion()
            re=angular_error(rq,Quaternion(data['deformationQuaternion']))
            max_scale=max(max_scale,max(abs(a-b) for a,b in zip(world.to_scale(),data['worldScale'])))
            if pe>max_pos:max_pos=pe;worst_pos={'bone':bone,'sourceFrame':sample['frame']}
            if re>max_rot:max_rot=re;worst_rot={'bone':bone,'sourceFrame':sample['frame']}
        for bone in controls:local_samples[bone].append(rig.pose.bones[bone].matrix_basis.copy())
    varying=[]
    for bone,values in local_samples.items():
        a=values[0]
        if any((a.translation-b.translation).length>1e-6 or angular_error(a.to_quaternion(),b.to_quaternion())>.001 for b in values[1:]):
            varying.append(bone)
    if missing or extra:errors.append(name+' bone set differs from true rest')
    if imported_parents!=parents:errors.append(name+' hierarchy differs from true rest')
    if bind_pos>1e-4 or bind_rot>.05 or bind_matrix>1e-4:errors.append(name+' incompatible true-rest binding')
    if abs(duration-source_duration)>1e-4:errors.append(name+' duration differs from source')
    if max_pos>1e-4 or max_rot>.05 or max_scale>1e-4:errors.append(name+' sampled motion differs from source')
    if not varying:errors.append(name+' has no varying local facial control')
    results[name]={'sha256':entry['sha256'],'boneCount':len(world_rest),'missingBones':missing,'extraBones':extra,
        'actionNames':[a.name for a in actions],'frameRange':[first,last],'fps':fps,'durationSeconds':duration,
        'sourceDurationSeconds':source_duration,'maxBindPositionErrorMeters':bind_pos,'maxBindRotationErrorDegrees':bind_rot,
        'maxBindMatrixElementError':bind_matrix,'hierarchyMatches':imported_parents==parents,'maxPoseScaleError':max_scale,
        'sampledFrames':len(entry['sourceSamples']),'maxPosePositionErrorMeters':max_pos,'worstPositionSample':worst_pos,
        'maxPoseRotationErrorDegrees':max_rot,'worstRotationSample':worst_rot,'varyingLocalFacialControls':varying}
    print('ROUNDTRIP',name,json.dumps(results[name]),flush=True)
report={'sourceSha256':manifest['sourceSha256'],'exportReceiptSha256':sha(directory/'export.json'),
    'maxSourceRestMatrixElementError':source_bind_error,
    'recipeSha256':sha(Path(__file__)),'structuralValidationPassed':not errors,'errors':errors,'clips':results,
    'blenderConnectionNormalization':connection_normalizations,
    'sharedAssetsChanged':False,'artisticAcceptance':False,
    'limits':'17 skeletal samples per take; does not validate mesh deformation, slopes or engine rendering'}
output.write_text(json.dumps(report,indent=2)+'\n',newline='\n')
if errors:raise RuntimeError('; '.join(errors))
print('KRAG_KINGS_MOTION_ROUNDTRIP_COMPLETE',flush=True)
