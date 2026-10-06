"""Reference-space IK gait, exact gun aim, facial performance and muscle drivers."""
import bpy,math,json
from mathutils import Vector,Quaternion
from nib_face import build_deformation_contract

LOCOMOTION={
 'Walk':{'speedMetersPerSecond':.9,'cycleSeconds':.8,'leftContacts':[0],'rightContacts':[.5],'stanceFraction':.62,'strideDuringStanceMeters':.4464,'contactCharacter':'quiet cautious forefoot placement'},
 'Run':{'speedMetersPerSecond':2.7,'cycleSeconds':.6,'leftContacts':[0],'rightContacts':[.5],'stanceFraction':.32,'strideDuringStanceMeters':.5184,'contactCharacter':'brief light nimble contact'},
}

def put_world_rotation(rig,name,desired,parent_world=None):
    bone=rig.data.bones[name];pb=rig.pose.bones[name]
    rest=bone.matrix_local.to_quaternion()
    if bone.parent:
        restlocal=bone.parent.matrix_local.to_quaternion().inverted()@rest
        parent=parent_world or rig.pose.bones[bone.parent.name].matrix.to_quaternion()
        basis=restlocal.inverted()@parent.inverted()@desired
    else:basis=rest.inverted()@desired
    pb.rotation_euler=basis.to_euler('XYZ')

def two_bone(rig,upper,lower,end,target,pole,end_rotation):
    h=rig.pose.bones[upper].head.copy();a=rig.data.bones[upper];b=rig.data.bones[lower]
    l1=a.length;l2=b.length;delta=target-h;distance=min(l1+l2-.0002,max(.0002,delta.length));axis=delta.normalized()
    projection=(l1*l1-l2*l2+distance*distance)/(2*distance)
    height=math.sqrt(max(0,l1*l1-projection*projection))
    perpendicular=pole-h-axis*(pole-h).dot(axis)
    if perpendicular.length<.0001:perpendicular=axis.cross(Vector((1,0,0)))
    knee=h+axis*projection+perpendicular.normalized()*height;ankle=h+axis*distance
    qa=(a.tail_local-a.head_local).normalized().rotation_difference((knee-h).normalized())@a.matrix_local.to_quaternion()
    qb=(b.tail_local-b.head_local).normalized().rotation_difference((ankle-knee).normalized())@b.matrix_local.to_quaternion()
    put_world_rotation(rig,upper,qa)
    put_world_rotation(rig,lower,qb,qa)
    put_world_rotation(rig,end,end_rotation,qb)
    return ankle

def body_correctives(objects):
    centers={}
    for side,sign in [('L',1),('R',-1)]:
        for name,point,radius,amount in [('ShoulderRaise',(sign*.128,.005,.938),.075,.003),('ElbowFlex',(sign*.189,-.003,.769),.055,.003),('HipFlex',(sign*.066,.009,.594),.09,.004),('KneeFlex',(sign*.073,.015,.35),.065,.003)]:centers['Corrective_'+name+'_'+side]=(Vector(point),radius,amount)
    tags=['BodyAnatomy','Torso','Chest','Pelvis','Arm_','UpperArm_','LowerArm_','Leg_','Thigh_','Shin_']
    for obj in objects:
        if obj.type!='MESH' or not any(obj.get('bone','').startswith(tag) for tag in tags):continue
        candidates={}
        world=[obj.matrix_world@v.co for v in obj.data.vertices]
        for name,(center,radius,amount) in centers.items():
            if any((p-center).length<radius for p in world):candidates[name]=(center,radius,amount)
        if not candidates:continue
        if not obj.data.shape_keys:obj.shape_key_add(name='Basis',from_mix=False)
        inverse=obj.matrix_world.to_3x3().inverted()
        for name,(center,radius,amount) in candidates.items():
            key=obj.shape_key_add(name=name,from_mix=False)
            for i,p in enumerate(world):
                offset=p-center;dist=offset.length
                if dist<radius and dist>1e-8:
                    strength=(1-dist/radius)**2
                    key.data[i].co+=inverse@(offset.normalized()*amount*strength)

def wire_drivers(rig,objects,contract):
    for obj in objects:
        if obj.type!='MESH' or not obj.data.shape_keys:continue
        for rule in contract['drivers']:
            if rule['morph'] not in obj.data.shape_keys.key_blocks:continue
            key=obj.data.shape_keys.key_blocks[rule['morph']];driver=key.driver_add('value').driver;driver.type='SCRIPTED'
            prop='location' if rule['channel']=='translationDistanceMeters' else 'rotation_euler'
            for i,letter in enumerate('xyz'):
                var=driver.variables.new();var.name=letter;var.type='SINGLE_PROP';var.targets[0].id=rig;var.targets[0].data_path=f'pose.bones["{rule["bone"]}"].{prop}[{i}]'
            magnitude='sqrt(x*x+y*y+z*z)' if prop=='location' else '2*acos(min(1,abs(cos(x/2)*cos(y/2)*cos(z/2)+sin(x/2)*sin(y/2)*sin(z/2))))*57.2957795'
            driver.expression=f'min(1,max(0,(({magnitude})-{rule["start"]})/{rule["end"]-rule["start"]}))'

def apply_action_face(clip,t,rig,setrot):
    """Authored facial acting accompanies every body clip, with no random gestures."""
    def pulse(center,width):return max(0,1-abs(t-center)/width)
    if clip=='FacePerformance':return
    blink=brow_up=brow_down=squint=press=frown=jaw=smile=0.0;look=0.0
    if clip=='Idle':
        blink=pulse(.24,.032);brow_up=.0012+.0005*math.sin(t*math.tau);look=2*math.sin(t*math.tau)
        smile=.0012*max(0,math.sin(t*math.tau))
    elif clip=='Walk':
        brow_up=.0026;press=.0007;frown=2.5;look=1.2*math.sin(t*math.tau)
    elif clip=='Run':
        brow_up=.0038;squint=.0011;press=.0014;frown=4;jaw=1.5+.5*math.sin(t*math.tau*2)
    elif clip=='Melee':
        effort=pulse(.62,.38);brow_up=.0035*effort;brow_down=.0015*effort;press=.0018*effort;frown=7*effort;jaw=4*effort
    elif clip=='Shoot':
        aim=min(1,t/.2,(1-t)/.22);aim=max(0,aim)
        blink=pulse(.46,.065)*.8;squint=.0022*aim;brow_down=.0013*aim;press=.0025*aim
    elif clip=='Hit':
        hit=math.sin(min(t/.20,1)*math.pi/2) if t<.20 else (1-t)/.8
        blink=.92*hit;brow_up=.0075*hit;frown=10*hit;jaw=9*hit
    for side,sign in [('L',1),('R',-1)]:
        rig.pose.bones['LidUpper_'+side].location.y=-.007*blink
        rig.pose.bones['LidLower_'+side].location.y=squint
        rig.pose.bones['BrowOuter_'+side].location.y=brow_up
        rig.pose.bones['BrowInner_'+side].location.y=-brow_down
        rig.pose.bones['MouthCorner_'+side].location.x=sign*smile
        setrot('MouthCorner_'+side,frown);setrot('Eye_'+side,0,look,0)
    rig.pose.bones['LipUpper'].location.y=press;setrot('Jaw',jaw)

def build_animation(g):
    rig=g['rig'];scene=g['scene'];objects=g['OBJECTS'];reset=g['reset_pose'];setrot=g['setrot'];keyall=g['keyall']
    contract=build_deformation_contract();body_correctives(objects);wire_drivers(rig,objects,contract)
    # Keep the large editable component scene out of pose-solve dependency work.
    for obj in objects:obj.hide_set(True)
    actions=[];goals=[];weapon_samples=[];face_evidence={}
    for clip,frames in [('Idle',90),('Walk',24),('Run',18),('Melee',32),('Shoot',30),('Hit',28),('FacePerformance',150)]:
        reset();action=bpy.data.actions.new(clip);rig.animation_data_create();rig.animation_data.action=action;action.use_fake_user=True;actions.append(action)
        face_evidence[clip]=[]
        step=1 if clip in ['Walk','Run'] else 3
        for f in sorted(set(list(range(1,frames+2,step))+[frames+1]+([1+.46*frames] if clip=='Shoot' else []))):
            t=(f-1)/frames;phase=t*math.tau;reset()
            if clip=='Idle':
                setrot('Chest',math.sin(phase)*.65);setrot('Head',0,math.sin(phase)*1.2,math.sin(phase*.5)*.6)
                setrot('Ear_L',math.sin(phase*2)*1.5);setrot('Ear_R',math.sin(phase*2+.8)*1.1)
            elif clip in LOCOMOTION:
                spec=LOCOMOTION[clip];run=clip=='Run'
                rig.pose.bones['Pelvis'].location.y=(-.083 if run else -.058)+.003*math.cos(phase*2)
                setrot('Chest',9 if run else 4,0,math.sin(phase)*(1.8 if run else 1.0));setrot('Head',-7 if run else -3)
                bpy.context.view_layer.update()
                for side,sign in [('L',1),('R',-1)]:
                    p=(t+(0 if side=='L' else .5))%1;stance=spec['stanceFraction'];stride=spec['strideDuringStanceMeters']
                    if p<stance:y=-stride/2+stride*p/stance;z=.100
                    else:
                        u=(p-stance)/(1-stance);ease=u*u*(3-2*u);y=stride/2-stride*ease;z=.100+(.10 if run else .036)*math.sin(u*math.pi)
                    target=Vector((sign*.075,y,z));pole=Vector((sign*.080,-.4,.31))
                    goal=two_bone(rig,'Thigh_'+side,'Shin_'+side,'Foot_'+side,target,pole,rig.data.bones['Foot_'+side].matrix_local.to_quaternion())
                    wave=math.sin(phase+(0 if side=='L' else math.pi))
                    setrot('UpperArm_'+side,-wave*(23 if run else 11));setrot('LowerArm_'+side,(35 if run else 16)+max(0,wave)*(15 if run else 6))
                    setrot('Ear_'+side,math.sin(phase*2)*(2 if run else .7))
                    goals.append({'clip':clip,'frame':f,'bone':'Foot_'+side,'target':list(goal),'contact':p<stance})
            elif clip=='Shoot':
                aim=min(1,t/.20) if t<.20 else max(0,min(1,(1-t)/.22));aim=aim*aim*(3-2*aim)
                recoil=max(0,1-abs(t-.46)/.055)
                bpy.context.view_layer.update()
                alignment=Vector((0,0,-1)).rotation_difference(Vector((0,-1,0)))
                for side,sign in [('R',-1),('L',1)]:
                    palm=Vector((.0,(-.240 if side=='R' else -.308)+.012*recoil,.897+.005*recoil))
                    rest_palm=Vector((sign*.227,-.043,.582));rest_wrist=rig.data.bones['Hand_'+side].head_local
                    desired_rotation=alignment@rig.data.bones['Hand_'+side].matrix_local.to_quaternion()
                    aimed_wrist=palm-alignment@(rest_palm-rest_wrist)
                    start=rig.pose.bones['Hand_'+side].head.copy();target=start.lerp(aimed_wrist,aim)
                    rotation=rig.data.bones['Hand_'+side].matrix_local.to_quaternion().slerp(desired_rotation,aim)
                    pole=Vector((sign*.35,-.13,.83))
                    goal=two_bone(rig,'UpperArm_'+side,'LowerArm_'+side,'Hand_'+side,target,pole,rotation)
                    goals.append({'clip':clip,'frame':f,'bone':'Hand_'+side,'target':list(goal)})
                setrot('Index2_R',recoil*8)
                for finger in ['Index','Middle','Ring','Little']:setrot(finger+'2_L',aim*24)
            elif clip=='Melee':
                wind=max(0,math.sin(min(t/.4,1)*math.pi)) if t<.4 else 0
                strike=max(0,math.sin((t-.4)/.6*math.pi)) if t>=.4 else 0
                setrot('Chest',-wind*7+strike*10,0,wind*-12+strike*16)
                bpy.context.view_layer.update()
                rest=rig.pose.bones['Hand_L'].head.copy();target=rest.lerp(Vector((.025,-.32,.9)),strike)
                two_bone(rig,'UpperArm_L','LowerArm_L','Hand_L',target,Vector((.35,-.06,.85)),rig.data.bones['Hand_L'].matrix_local.to_quaternion())
                curl=max(wind,strike)
                for finger in ['Index','Middle','Ring','Little']:
                    setrot(finger+'1_L',curl*10);setrot(finger+'2_L',curl*32);setrot(finger+'3_L',curl*30)
                setrot('Thumb2_L',curl*16)
            elif clip=='Hit':
                hit=math.sin(min(t/.20,1)*math.pi/2) if t<.20 else (1-t)/.8
                setrot('Chest',-hit*12,0,hit*7);setrot('Head',-hit*7,0,-hit*9);setrot('Ear_L',hit*18);setrot('Ear_R',hit*16)
                bpy.context.view_layer.update()
                for side,sign in [('L',1),('R',-1)]:
                    start=rig.pose.bones['Hand_'+side].head.copy();target=start.lerp(Vector((sign*.07,-.20,.98)),hit*.75)
                    two_bone(rig,'UpperArm_'+side,'LowerArm_'+side,'Hand_'+side,target,Vector((sign*.35,-.06,.80)),rig.data.bones['Hand_'+side].matrix_local.to_quaternion())
                rig.pose.bones['BrowOuter_L'].location.y=.007*hit;rig.pose.bones['BrowOuter_R'].location.y=.007*hit
            elif clip=='FacePerformance':
                def pulse(center,width):return max(0,1-abs(t-center)/width)
                wary=pulse(.20,.17);flinch=pulse(.39,.055);playful=pulse(.68,.20);blink=pulse(.10,.018)+pulse(.43,.025)+pulse(.91,.024)
                for side,sign in [('L',1),('R',-1)]:
                    setrot('Eye_'+side,0,wary*15-playful*4,0)
                    rig.pose.bones['LidUpper_'+side].location.y=-.007*min(1,blink+flinch*.8)
                    rig.pose.bones['LidLower_'+side].location.y=.002*playful
                    rig.pose.bones['BrowOuter_'+side].location.y=.006*wary
                    rig.pose.bones['BrowInner_'+side].location.y=-.003*flinch
                    rig.pose.bones['MouthCorner_'+side].location.x=sign*.008*playful*(1 if side=='L' else .72)
                    setrot('MouthCorner_'+side,wary*7)
                    setrot('Ear_'+side,flinch*17+playful*3,0,sign*wary*4)
                rig.pose.bones['LipUpper'].location.y=.0025*wary
                setrot('Jaw',15*playful)
                rig.pose.bones['TongueTip'].location.y=.028*playful
            apply_action_face(clip,t,rig,setrot)
            keyall(f)
            active={}
            for pb in rig.pose.bones:
                parent=pb.parent;facial=pb.name=='FaceRoot'
                while parent:
                    if parent.name=='FaceRoot':facial=True;break
                    parent=parent.parent
                if facial and (pb.location.length>1e-8 or sum(abs(v) for v in pb.rotation_euler)>1e-8):active[pb.name]={'translationMeters':list(pb.location),'rotationEulerRadians':list(pb.rotation_euler)}
            face_evidence[clip].append({'frame':f,'normalizedTime':t,'activeFaceControls':active})
            if clip in ['Walk','Run','Shoot']:
                bpy.context.view_layer.update()
                for goal in reversed(goals):
                    if goal['clip']!=clip or goal['frame']!=f:break
                    actual=rig.pose.bones[goal['bone']].head.copy();goal['actual']=list(actual);goal['errorMeters']=(actual-Vector(goal['target'])).length
                    if goal['errorMeters']>.001:raise RuntimeError(f'IK target mismatch {clip} frame {f} {goal["bone"]}: {goal["errorMeters"]:.5f}m')
                if clip=='Shoot':
                    muzzle=rig.pose.bones['WeaponMuzzle'].head.copy();direction=(rig.pose.bones['WeaponAim'].head-muzzle).normalized();error=direction.angle(Vector((0,-1,0)))
                    weapon_samples.append({'frame':f,'normalizedTime':t,'muzzle':list(muzzle),'forward':list(direction),'forwardAimErrorDegrees':math.degrees(error)})
                    if .20<=t<=.78 and error>.001:raise RuntimeError('Full-aim muzzle is not parallel to character forward')
        action['clip_duration_seconds']=frames/30
        track=rig.animation_data.nla_tracks.new();track.name=clip;track.strips.new(clip,1,action);track.mute=True
    rig.animation_data.action=actions[0];reset();scene.frame_set(1)
    (g['OUT']/'facial-rig.json').write_text(json.dumps(contract,indent=2))
    (g['ART']/'facial-performance.json').write_text(json.dumps(face_evidence,indent=2))
    (g['ART']/'animation-targets.json').write_text(json.dumps({'locomotion':LOCOMOTION,'goals':goals,'weaponSamples':weapon_samples},indent=2))
    return actions,contract,LOCOMOTION
