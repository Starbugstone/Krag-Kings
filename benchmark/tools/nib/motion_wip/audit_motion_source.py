"""Read-only rest-frame, gait/idle arm trajectories and ear binding inventory.

Run under the shared Blender guard. This measures the actual saved action
poses without reauthoring clips, changing bind, or evaluating dense meshes.
"""
import argparse,hashlib,json,math,sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector,Matrix

parser=argparse.ArgumentParser()
parser.add_argument('--source',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before=sha(args.source)
bpy.ops.wm.open_mainfile(filepath=str(args.source),load_ui=False)
scene=bpy.context.scene;rig=bpy.data.objects['Nib_Rig']
for obj in scene.objects:
    if obj.type=='MESH':
        obj.hide_set(True)
        for modifier in obj.modifiers:
            if modifier.type=='ARMATURE':modifier.show_viewport=False
rig.hide_set(False);rig.hide_viewport=False
rig.animation_data.action=None
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
scene.frame_set(1);bpy.context.view_layer.update()
names=['Pelvis','Spine','Chest','Neck','Head','FaceRoot']
names += [part+'_'+side for side in ['L','R'] for part in ['Clavicle','UpperArm','LowerArm','Hand','Thigh','Shin','Foot','Ear']]
report={'status':'Actual saved-source numerical audit; no animation/model acceptance or source change',
    'source':str(args.source),'sourceSha256':before,'codeSha256':sha(Path(__file__)),
    'coordinates':'Armature local metres; forward -Y, up +Z; torso-relative vectors also recorded',
    'rest':{},'earComponents':[],'clips':{},'sharedChanged':False}
for name in names:
    bone=rig.data.bones[name]
    report['rest'][name]={'parent':bone.parent.name if bone.parent else None,
        'head':list(bone.head_local),'tail':list(bone.tail_local),'lengthMeters':bone.length,
        'basisAxes':[list(bone.matrix_local.to_3x3().col[i]) for i in range(3)]}
for obj in bpy.data.collections['Nib_Authored_Components'].objects:
    if obj.type!='MESH' or not obj.get('bone','').startswith('Ear_'):continue
    totals={};maximum_influences=0
    for vertex in obj.data.vertices:
        influences=[g for g in vertex.groups if g.weight>1e-7];maximum_influences=max(maximum_influences,len(influences))
        for group in influences:
            name=obj.vertex_groups[group.group].name
            totals[name]=totals.get(name,0.)+group.weight
    report['earComponents'].append({'name':obj.name,'boneTag':obj.get('bone'),
        'vertices':len(obj.data.vertices),'triangles':sum(len(p.vertices)-2 for p in obj.data.polygons),
        'meanWeightByBone':{k:v/len(obj.data.vertices) for k,v in totals.items()},'maximumInfluences':maximum_influences})

for clip in ['Idle','Walk','Run']:
    action=bpy.data.actions[clip];rig.animation_data.action=action
    start,end=map(float,action.frame_range);samples=[]
    for normalized in np.linspace(0,1,49):
        frame=start+(end-start)*normalized;scene.frame_set(int(frame),subframe=frame%1);bpy.context.view_layer.update()
        torso=rig.pose.bones['Chest'].matrix.to_3x3().inverted()
        arms={}
        for side in ['L','R']:
            shoulder=rig.pose.bones['UpperArm_'+side].head.copy();elbow=rig.pose.bones['LowerArm_'+side].head.copy();wrist=rig.pose.bones['Hand_'+side].head.copy()
            upper=(elbow-shoulder).normalized();lower=(wrist-elbow).normalized()
            bend=math.degrees(math.acos(max(-1,min(1,upper.dot(lower)))))
            path=(wrist-shoulder);upper_torso=torso@upper
            # Character sagittal abduction diagnostic; no local Euler-axis
            # assumption or inferred anatomical acceptance threshold.
            arms[side]={'shoulder':list(shoulder),'elbow':list(elbow),'wrist':list(wrist),
                'elbowBendDegrees':bend,'wristRelativeToShoulder':list(path),
                'upperDirectionTorsoLocal':list(upper_torso),
                'forearmDirection':list(lower),'foot':list(rig.pose.bones['Foot_'+side].head)}
        samples.append({'normalizedTime':float(normalized),'frame':frame,'arms':arms,
            'body':{name:{'head':list(rig.pose.bones[name].head),'rotationFromBindRadians':rig.pose.bones[name].matrix_basis.to_quaternion().angle} for name in ['Pelvis','Chest','Head']},
            'ears':{side:{'rotationEulerRadians':list(rig.pose.bones['Ear_'+side].rotation_euler),
                          'tip':list(rig.pose.bones['Ear_'+side].tail)} for side in ['L','R']}})
    summary={}
    for side in ['L','R']:
        bends=[s['arms'][side]['elbowBendDegrees'] for s in samples]
        wrists=np.asarray([s['arms'][side]['wristRelativeToShoulder'] for s in samples])
        feet=np.asarray([s['arms'][side]['foot'] for s in samples])
        correlation=None
        if min(np.std(wrists[:,1]),np.std(feet[:,1]))>1e-8:correlation=float(np.corrcoef(wrists[:,1],feet[:,1])[0,1])
        summary[side]={'elbowBendRangeDegrees':[min(bends),max(bends)],
            'wristRelativeBoundsMin':wrists.min(axis=0).tolist(),'wristRelativeBoundsMax':wrists.max(axis=0).tolist(),
            'ipsilateralFootWristForeAftCorrelation':correlation}
    report['clips'][clip]={'frameRange':[start,end],'durationSeconds':(end-start)/scene.render.fps,
        'summary':summary,'samples':samples}
if sha(args.source)!=before:raise RuntimeError('Read-only source audit changed input')
args.output.parent.mkdir(parents=True,exist_ok=True)
args.output.write_text(json.dumps(report,indent=2)+'\n',newline='\n')
print('NIB_MOTION_SOURCE_AUDIT_COMPLETE',flush=True)
