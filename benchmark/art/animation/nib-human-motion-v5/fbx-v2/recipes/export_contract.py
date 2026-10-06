"""Keep character FBX takes and cadence consistent with the saved source.

This runs only inside the disposable Blender export process. Detailed masters
retain their preserved study actions; only the seven runtime actions are baked.
"""
import json
import math

CLIPS = ['Idle','Walk','Run','Melee','Shoot','Hit','FacePerformance']


def select_action(bpy, rig, action):
    """Reset unevaluated channels before selecting a standalone take."""
    from mathutils import Matrix
    rig.animation_data_create();rig.animation_data.action=None
    for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
    if action is not None:
        rig.animation_data.action=action
        slots=[slot for slot in action.slots if slot.target_id_type=='OBJECT']
        if len(slots)!=1:raise RuntimeError('Expected one rig object slot in '+action.name)
        rig.animation_data.action_slot=slots[0]


def complete_transform_tracks(bpy):
    """Make unkeyed bone components explicitly neutral in every runtime take.

    Embedded FBX all-actions export restores the original active pose between
    takes. New controls must therefore not inherit that pose in older actions.
    This operates on disposable export data only; masters are not saved.
    """
    from bpy_extras.anim_utils import action_get_channelbag_for_slot
    rigs=[o for o in bpy.data.objects if o.type=='ARMATURE' and 'Pelvis' in o.data.bones]
    if len(rigs)!=1:raise RuntimeError('Expected one character rig for clip completion')
    rig=rigs[0];result={}
    for name in CLIPS:
        action=bpy.data.actions[name];first,last=action.frame_range
        select_action(bpy,rig,action)
        bag=action_get_channelbag_for_slot(action,rig.animation_data.action_slot)
        if bag is None:raise RuntimeError('Missing rig channel bag '+name)
        present={(c.data_path,c.array_index) for c in bag.fcurves}
        added=[]
        for bone in rig.pose.bones:
            rotation=('rotation_quaternion' if bone.rotation_mode=='QUATERNION' else
                      'rotation_axis_angle' if bone.rotation_mode=='AXIS_ANGLE' else 'rotation_euler')
            for channel in ['location',rotation,'scale']:
                path=bone.path_from_id()+'.'+channel
                for index in range(len(getattr(bone,channel))):
                    if (path,index) in present:continue
                    for frame in [first,last]:bone.keyframe_insert(channel,index=index,frame=frame,group=bone.name)
                    added.append({'bone':bone.name,'channel':channel,'index':index,'neutralValue':getattr(bone,channel)[index]})
        result[name]=added
    select_action(bpy,rig,None)
    return result


def prepare(bpy, fallback_locomotion):
    scene = bpy.context.scene
    missing = [name for name in CLIPS if name not in bpy.data.actions]
    if missing: raise RuntimeError('Missing runtime actions: '+str(missing))
    has_capture = any(bpy.data.actions[name].get('motion_source') for name in ['Walk','Run'])
    generation = scene.get('retargeted_motion_generation')
    if has_capture and not generation:
        raise RuntimeError('Retargeted actions need matching saved-source locomotion metadata')
    locomotion = json.loads(scene['locomotion_contract']) if generation else fallback_locomotion
    fps = scene.render.fps/scene.render.fps_base
    for name in ['Walk','Run']:
        entry = locomotion[name]
        first,last = bpy.data.actions[name].frame_range
        duration = (last-first)/fps
        if abs(duration-entry['cycleSeconds']) > 1e-5:
            raise RuntimeError('Saved action and locomotion cadence differ for '+name)
        if not math.isfinite(entry['speedMetersPerSecond']) or entry['speedMetersPerSecond'] <= 0:
            raise RuntimeError('Invalid source speed for '+name)
        if not 0 < entry['stanceFraction'] < 1: raise RuntimeError('Invalid source support duration')
        for side in ['leftContacts','rightContacts']:
            values = entry[side]
            if not values or any(not math.isfinite(v) or not 0 <= v < 1 for v in values):
                raise RuntimeError('Invalid source foot contact phases '+name+'/'+side)
    removed = []
    # Blender5.2's all-actions FBX loop exports every compatible Action,
    # including archived study clips. Fake-user flags do not filter that loop.
    for action in list(bpy.data.actions):
        if action.name not in CLIPS:
            removed.append(action.name)
            bpy.data.actions.remove(action, do_unlink=True)
    report = {'runtimeActions':CLIPS, 'excludedStudyActions':removed,
              'sourceMotionGeneration':generation, 'sourceMasterModified':False,
              'neutralTracksForMissingComponents':complete_transform_tracks(bpy),
              'actionDurationsSeconds':{name:(bpy.data.actions[name].frame_range[1]-bpy.data.actions[name].frame_range[0])/fps for name in CLIPS}}
    return locomotion,report
