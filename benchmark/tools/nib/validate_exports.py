"""Fresh-process FBX reimport inspection; records evidence instead of assuming export worked."""
import bpy,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'benchmark/shared/characters/nib';ART=ROOT/'benchmark/art/nib'
manifest=json.loads((OUT/'manifest.json').read_text());report={'variants':[],'animations':[]};reference_rest={}
for item in manifest['variants']:
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    for action in list(bpy.data.actions):bpy.data.actions.remove(action)
    bpy.data.orphans_purge(do_local_ids=True,do_linked_ids=False,do_recursive=True)
    bpy.ops.import_scene.fbx(filepath=str(OUT/item['fbx']),use_anim=True)
    meshes=[o for o in bpy.context.scene.objects if o.type=='MESH'];rigs=[o for o in bpy.context.scene.objects if o.type=='ARMATURE']
    minimum=[min((o.matrix_world@v.co)[i] for o in meshes for v in o.data.vertices) for i in range(3)]
    maximum=[max((o.matrix_world@v.co)[i] for o in meshes for v in o.data.vertices) for i in range(3)]
    actions=[a.name for a in bpy.data.actions]
    missing=[name for name in ['Idle','Walk','Run','Melee','Shoot','Hit','FacePerformance'] if not any(name in a for a in actions)]
    errors=[]
    if len(meshes)!=1:errors.append('Expected one consolidated mesh')
    if len(rigs)!=1:errors.append('Expected one armature')
    if missing:errors.append('Missing clips: '+','.join(missing))
    if len(rigs)==1 and not reference_rest:reference_rest={bone.name:[value for row in (rigs[0].matrix_world@bone.matrix_local) for value in row] for bone in rigs[0].data.bones}
    rest_error=max((max(abs(a-b) for a,b in zip(reference_rest[bone.name],[value for row in (rig.matrix_world@bone.matrix_local) for value in row])) for rig in rigs for bone in rig.data.bones if bone.name in reference_rest),default=0)
    if rest_error>1e-4:errors.append('Variant bind matrix mismatch: '+str(rest_error))
    morphs=sorted({key.name.split('.')[-1] for o in meshes if o.data.shape_keys for key in o.data.shape_keys.key_blocks if key.name!='Basis'})
    bones={bone.name for rig in rigs for bone in rig.data.bones}
    for rule in item.get('deformation',manifest['deformation'])['drivers']:
        if rule['morph'] not in morphs:errors.append('Missing morph '+rule['morph'])
        if rule['bone'] not in bones:errors.append('Missing driver bone '+rule['bone'])
    if 'FaceRoot' not in bones:errors.append('Missing FaceRoot')
    bad_weights=sum(1 for o in meshes for v in o.data.vertices if not v.groups or len(v.groups)>4 or abs(sum(g.weight for g in v.groups)-1)>.005)
    if bad_weights:errors.append(str(bad_weights)+' invalid skin vertices')
    entry={'variant':item['name'],'meshCount':len(meshes),'boneCount':len(rigs[0].data.bones) if rigs else 0,'triangles':sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in meshes),'materials':sorted(set(m.name for o in meshes for m in o.data.materials)),'boundsMin':minimum,'boundsMax':maximum,'bindMatrixMaxAbsoluteError':rest_error,'actions':actions,'morphs':morphs,'invalidWeightCount':bad_weights,'errors':errors}
    report['variants'].append(entry)
for clip in manifest['clips']:
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    for action in list(bpy.data.actions):bpy.data.actions.remove(action)
    bpy.data.orphans_purge(do_local_ids=True,do_linked_ids=False,do_recursive=True)
    bpy.ops.import_scene.fbx(filepath=str(OUT/clip['fbx']),use_anim=True)
    actions=[a.name for a in bpy.data.actions]
    rigs=[obj for obj in bpy.context.scene.objects if obj.type=='ARMATURE'];moving=[];active=[]
    missing_bones=[name for name in reference_rest if not rigs or name not in rigs[0].data.bones]
    rest_error=max((max(abs(a-b) for a,b in zip(reference_rest[bone.name],[value for row in (rig.matrix_world@bone.matrix_local) for value in row])) for rig in rigs for bone in rig.data.bones if bone.name in reference_rest),default=0)
    if len(rigs)==1 and len(actions)==1:
        rig=rigs[0];action=bpy.data.actions[actions[0]];rig.animation_data_create();rig.animation_data.action=action
        if action.slots:rig.animation_data.action_slot=action.slots[0]
        values={}
        for pose in rig.pose.bones:
            parent=pose.parent;facial=pose.name=='FaceRoot'
            while parent:
                if parent.name=='FaceRoot':facial=True;break
                parent=parent.parent
            if facial:values[pose.name]=[]
        for sample in range(25):
            frame=action.frame_range[0]+(action.frame_range[1]-action.frame_range[0])*sample/24
            bpy.context.scene.frame_set(int(frame),subframe=frame-int(frame));bpy.context.view_layer.update()
            for name in values:
                pose=rig.pose.bones[name];values[name].append(list(pose.location)+list(pose.matrix_basis.to_quaternion()))
        for name,rows in values.items():
            if any(max(row[i] for row in rows)-min(row[i] for row in rows)>1e-6 for i in range(7)):moving.append(name)
            if any(sum(abs(v) for v in row[:3])+abs(row[3]-1)+sum(abs(v) for v in row[4:])>1e-6 for row in rows):active.append(name)
    report['animations'].append({'clip':clip['name'],'actions':actions,'singleTake':len(actions)==1,'activeFaceBones':active,'movingFaceBones':moving,'facialMotionVerified':bool(moving),'bindMatrixMaxAbsoluteError':rest_error,'missingBones':missing_bones,'bindPoseVerified':not missing_bones and rest_error<1e-4})
report['passed']=all(not r['errors'] for r in report['variants']) and all(r['singleTake'] and r['facialMotionVerified'] and r['bindPoseVerified'] for r in report['animations'])
(ART/'export-validation.json').write_text(json.dumps(report,indent=2));print('NIB_FBX_VALIDATION '+json.dumps(report),flush=True)
if not report['passed']:raise RuntimeError('Nib export validation failed; see export-validation.json')
