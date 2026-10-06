"""Provisional rooted Nib ear motion; no simulation or rigid whole-ear flap.

Two existing Ear bones stay under FaceRoot. Optional distal children provide
small delayed cartilage follow-through. Source generation/posed review and
matching skeleton exports are required before either engine consumes this.
"""
import math
import numpy as np

CENTERS=np.asarray([(.066,0,1.178),(.114,.006,1.218),(.170,.015,1.257),
                    (.220,.026,1.301),(.269,.038,1.347),(.309,.05,1.385)])

def smooth(a,b,value):
    t=np.clip((value-a)/(b-a),0,1)
    return t*t*(3-2*t)

def along_ear(points):
    """Closest progress on the existing auricle's authored center curve."""
    p=np.asarray(points,dtype=np.float64).copy();p[:,0]=abs(p[:,0])
    # Shape-dependent cupping changes Y. The original auricle construction
    # uses X/Z for progress, so avoid projecting its bowl depth onto length.
    p=p[:,[0,2]];centers=CENTERS[:,[0,2]]
    best=np.full(len(p),np.inf);result=np.zeros(len(p))
    for i,(a,b) in enumerate(zip(centers[:-1],centers[1:])):
        v=b-a;t=np.clip(((p-a)@v)/(v@v),0,1)
        distance=np.sum((p-a-t[:,None]*v)**2,axis=1);take=distance<best
        best[take]=distance[take];result[take]=(i+t[take])/5
    return result

def weights(points):
    t=along_ear(points);base=smooth(.015,.20,t);distal=smooth(.55,.95,t)
    result=np.column_stack((1-base,base*(1-distal),base*distal))
    if not np.isfinite(result).all() or np.max(abs(result.sum(axis=1)-1))>1e-12:
        raise RuntimeError('Invalid continuous ear weights')
    return result

def pulse(seconds,onset,attack=.045,recovery=.16):
    time=seconds-onset
    if time<=0 or time>=attack+recovery:return 0.
    if time<attack:return float(smooth(0,attack,time))
    return 1-float(smooth(attack,attack+recovery,time))

def pose(clip,seconds,duration):
    """Small independent alert twitches; all event curves return to rest."""
    events={
        'Idle':{'L':[(.58,2.5)],'R':[(1.89,-2.1)]},
        'Walk':{'L':[(.27,1.0)],'R':[]},
        'Run':{'L':[],'R':[(.19,-.55)]},
        'Melee':{'L':[(duration*.16,1.4)],'R':[(duration*.58,-1.0)]},
        'Shoot':{'L':[(duration*.48,1.1)],'R':[(duration*.58,-1.4)]},
        'Hit':{'L':[(duration*.10,2.1)],'R':[(duration*.15,-1.8)]},
        'FacePerformance':{'L':[(.67,2.1),(3.13,1.6)],'R':[(1.73,-2.4),(3.46,-1.7)]},
    }.get(clip,{'L':[],'R':[]})
    result={}
    for side,sign in [('L',1),('R',-1)]:
        twitch=sum(amplitude*pulse(seconds,onset) for onset,amplitude in events[side])
        follow=sum(amplitude*.38*pulse(seconds,onset+.025,.055,.20) for onset,amplitude in events[side])
        recoil=sum(amplitude*.055*pulse(seconds,onset+.13,.07,.15) for onset,amplitude in events[side])
        # Most twitch displacement is small basal swivel, with much smaller
        # flexion through the distal cartilage. Existing 16–18 degree rigid
        # reactions are deliberately not carried into this authored proposal.
        result['Ear_'+side]=(twitch*.26,0,sign*twitch)
        result['EarTip_'+side]=(follow-recoil,0,-sign*follow*.20)
    return result

def install(rig,collection):
    import bpy
    from mathutils import Vector
    originals={b.name:b.matrix_local.copy() for b in rig.data.bones}
    bpy.ops.object.select_all(action='DESELECT');rig.hide_set(False);rig.select_set(True)
    bpy.context.view_layer.objects.active=rig;bpy.ops.object.mode_set(mode='EDIT')
    for side,sign in [('L',1),('R',-1)]:
        if 'EarTip_'+side in rig.data.edit_bones:raise RuntimeError('Ear extension already installed')
        parent=rig.data.edit_bones['Ear_'+side]
        if parent.parent.name!='FaceRoot':raise RuntimeError('Unexpected ear facial hierarchy')
        bone=rig.data.edit_bones.new('EarTip_'+side)
        bone.head=Vector((sign*CENTERS[3,0],CENTERS[3,1],CENTERS[3,2]))
        bone.tail=Vector((sign*CENTERS[-1,0],CENTERS[-1,1],CENTERS[-1,2]))
        bone.parent=parent;bone.use_deform=True;bone.align_roll(Vector((0,-1,0)))
    bpy.ops.object.mode_set(mode='OBJECT')
    for name,matrix in originals.items():
        if max(abs(a-b) for ra,rb in zip(matrix,rig.data.bones[name].matrix_local) for a,b in zip(ra,rb))>1e-7:
            raise RuntimeError('Ear extension moved an existing rest bone: '+name)
    report={'addedBones':['EarTip_L','EarTip_R'],'existingRestBonesPreserved':True,
        'faceRootSubtree':True,'method':'Head/base/distal continuous auricle weights, independently timed authored alert pulses',
        'components':[],'status':'Source proposal; actual deformation/temporal/engine review required'}
    for obj in collection.objects:
        tag=obj.get('bone','')
        if obj.type!='MESH' or tag not in ['Ear_L','Ear_R']:continue
        side=tag[-1];names=['Head',tag,'EarTip_'+side]
        transform=rig.matrix_world.inverted()@obj.matrix_world
        points=np.asarray([tuple(transform@v.co) for v in obj.data.vertices])
        field=weights(points)
        # Only existing wholly ear-bound modules are in scope. Refuse to
        # silently replace facial/body weighting on an unexpected component.
        if any(obj.vertex_groups[g.group].name!=tag and g.weight>1e-7 for v in obj.data.vertices for g in v.groups):
            raise RuntimeError('Unexpected mixed-weight ear module: '+obj.name)
        obj.vertex_groups.clear();groups=[obj.vertex_groups.new(name=name) for name in names]
        for i,row in enumerate(field):
            for group,value in zip(groups,row):
                if value>1e-8:group.add([i],float(value),'REPLACE')
        report['components'].append({'name':obj.name,'vertices':len(points),
            'meanHeadBaseTipWeight':field.mean(axis=0).tolist(),'maximumInfluences':3})
    if not report['components']:raise RuntimeError('No authored ear modules found')
    return report

def author_tracks(rig,clips):
    import bpy
    from bpy_extras.anim_utils import action_get_channelbag_for_slot
    bones=['Ear_L','Ear_R','EarTip_L','EarTip_R'];paths={f'pose.bones["{name}"]' for name in bones}
    report={};scene=bpy.context.scene
    for clip in clips:
        action=bpy.data.actions[clip];start,end=map(float,action.frame_range)
        rig.animation_data.action=action;slot=rig.animation_data.action_slot
        if slot is None:raise RuntimeError('Missing assigned animation slot: '+clip)
        bag=action_get_channelbag_for_slot(action,slot)
        if bag is None:raise RuntimeError('Missing source action channelbag: '+clip)
        for curve in list(bag.fcurves):
            if any(curve.data_path.startswith(path) for path in paths):bag.fcurves.remove(curve)
        duration=(end-start)/scene.render.fps;frames=np.linspace(start,end,int(round((end-start)*2))+1)
        samples=[]
        for frame in frames:
            seconds=(frame-start)/scene.render.fps;angles=pose(clip,seconds,duration)
            for name,value in angles.items():
                bone=rig.pose.bones[name];bone.rotation_mode='XYZ'
                bone.rotation_euler=tuple(math.radians(a) for a in value)
                bone.keyframe_insert('rotation_euler',frame=float(frame),group=name)
            samples.append({'frame':float(frame),'degrees':angles})
        for curve in bag.fcurves:
            if any(curve.data_path.startswith(path) for path in paths):
                for key in curve.keyframe_points:key.interpolation='LINEAR'
        for endpoint in [samples[0],samples[-1]]:
            if any(abs(a)>1e-10 for value in endpoint['degrees'].values() for a in value):
                raise RuntimeError('Ear event does not settle at clip boundary: '+clip)
        report[clip]={'durationSeconds':duration,'maximumRootAngleDegrees':max(abs(a) for s in samples for n,v in s['degrees'].items() if n in ['Ear_L','Ear_R'] for a in v),
            'samples':samples,'sourceTemporalReviewRequired':True}
    return report
