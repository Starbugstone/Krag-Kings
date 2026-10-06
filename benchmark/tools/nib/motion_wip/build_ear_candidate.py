"""Isolated ear skeleton/skinning/acting candidate; body clips stay pinned."""
import hashlib,json,sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Matrix
from bpy_extras.anim_utils import action_get_channelbag_for_slot

HERE=Path(__file__).parent;ROOT=HERE.parents[3]
sys.path.insert(0,str(HERE));sys.path.insert(0,str(HERE.parent/'v5_wip'))
from ear_motion import install,author_tracks
from audit_face_coordinates import facial_snapshot

ART=ROOT/'benchmark/art/nib';SOURCE=ART/'Nib_Master_v5h_EyelidRepair_WIP.blend'
TARGET=ART/'Nib_EarMotionStudy_v1.blend';OUT=ART/'motion-study/ear-motion-v1.json'
EXPECTED='3a7eeec4ff6ca61f5fb1c084af38302e94a17a308b9267676d8fc58c3c6c9e9e'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if sha(SOURCE)!=EXPECTED:raise RuntimeError('Pinned source does not match the reviewed v5h file')
if TARGET.exists():raise RuntimeError('Preserve existing ear-motion candidate')
bpy.ops.wm.open_mainfile(filepath=str(SOURCE),load_ui=False)
scene=bpy.context.scene;rig=bpy.data.objects['Nib_Rig'];collection=bpy.data.collections['Nib_Authored_Components']
rig.animation_data.action=None
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
scene.frame_set(1);bpy.context.view_layer.update()
clips=['Idle','Walk','Run','Melee','Shoot','Hit','FacePerformance']
ear_paths={f'pose.bones["{n}"]' for n in ['Ear_L','Ear_R','EarTip_L','EarTip_R']}
def digest(value):return hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest()
def non_ear_curves():
    result={}
    for clip in clips:
        action=bpy.data.actions[clip];rig.animation_data.action=action
        bag=action_get_channelbag_for_slot(action,rig.animation_data.action_slot)
        if bag is None:raise RuntimeError('Missing assigned clip slot '+clip)
        rows=[]
        for curve in bag.fcurves:
            if any(curve.data_path.startswith(p) for p in ear_paths):continue
            rows.append((curve.data_path,curve.array_index,[(list(k.co),list(k.handle_left),list(k.handle_right),k.interpolation) for k in curve.keyframe_points]))
        result[clip]=hashlib.sha256(json.dumps(sorted(rows),separators=(',',':')).encode()).hexdigest()
    return result
def geometry():
    result={}
    for obj in collection.objects:
        if obj.type!='MESH':continue
        result[obj.name]={'positions':digest(np.asarray([tuple(v.co) for v in obj.data.vertices],dtype=np.float32)),
            'polygons':digest(np.asarray([v for p in obj.data.polygons for v in p.vertices],dtype=np.int32)),
            'uv':{uv.name:digest(np.asarray([tuple(v.uv) for v in uv.data],dtype=np.float32)) for uv in obj.data.uv_layers},
            'shapeKeys':{k.name:digest(np.asarray([tuple(v.co) for v in k.data],dtype=np.float32)) for k in obj.data.shape_keys.key_blocks} if obj.data.shape_keys else {},
            'materials':[m.name for m in obj.data.materials]}
    return result
old_curves=non_ear_curves();old_geometry=geometry()
rig.animation_data.action=None
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update()
report={'status':'Isolated rooted-ear source candidate; actual pose/temporal/engine review required',
        'source':str(SOURCE),'sourceSha256':EXPECTED,'sharedChanged':False,'artisticAcceptance':False}
report['rigAndSkinning']=install(rig,collection)
report['acting']=author_tracks(rig,clips)
if old_curves!=non_ear_curves():raise RuntimeError('Ear authoring changed non-ear body/facial animation')
if old_geometry!=geometry():raise RuntimeError('Ear authoring changed neutral geometry/UVs/materials/morphs')
report['preserved']={'nonEarCurvesSha256':old_curves,'neutralGeometryUVsMaterialsAndMorphs':True,
    'originalBindMatrices':True,'bodyAnimationUnchanged':True}
report['boneCount']=len(rig.data.bones)
report['earSkinProof']={'method':'Linear blend skinning from actual saved rig poses and authored weights, in current Head-relative space; independent of dense evaluated mesh rendering',
    'samples':[],'limits':{'maximumHeadAnchoredDisplacementMeters':1e-6,'maximumTwitchDisplacementMeters':.025}}
ear_data=[]
for obj in collection.objects:
    tag=obj.get('bone','')
    if obj.type!='MESH' or tag not in ['Ear_L','Ear_R']:continue
    transform=rig.matrix_world.inverted()@obj.matrix_world
    p=np.asarray([tuple(transform@v.co) for v in obj.data.vertices],dtype=np.float64)
    names=['Head',tag,'EarTip_'+tag[-1]];groups={g.index:g.name for g in obj.vertex_groups}
    w=np.zeros((len(p),3))
    for vertex in obj.data.vertices:
        for g in vertex.groups:w[vertex.index,names.index(groups[g.group])]=g.weight
    if np.max(abs(w.sum(axis=1)-1))>1e-6:raise RuntimeError('Ear weights do not normalize')
    ear_data.append((obj.name,p,w,names))
rig.animation_data.action=bpy.data.actions['Idle']
for label,frame in [('Rest',1.),('LeftPeak',19.75),('LeftRecovery',25.15),('LeftSettled',31.),('RightPeak',59.05)]:
    scene.frame_set(int(frame),subframe=frame%1);bpy.context.view_layer.update()
    head_skin=rig.pose.bones['Head'].matrix@rig.data.bones['Head'].matrix_local.inverted()
    rows=[]
    for name,p,w,names in ear_data:
        q=np.zeros_like(p)
        for column,bone_name in enumerate(names):
            transform=head_skin.inverted()@rig.pose.bones[bone_name].matrix@rig.data.bones[bone_name].matrix_local.inverted()
            matrix=np.asarray(transform,dtype=np.float64)
            moved=p@matrix[:3,:3].T+matrix[:3,3]
            q+=w[:,column,None]*moved
        delta=np.linalg.norm(q-p,axis=1);anchored=w[:,0]>.99999
        anchor_error=float(delta[anchored].max()) if anchored.any() else 0.
        if anchor_error>1e-6 or delta.max()>.025:raise RuntimeError('Ear twitch/base displacement exceeds the bounded study range: '+name)
        rows.append({'component':name,'headAnchoredVertices':int(anchored.sum()),
            'maximumHeadAnchoredDisplacementMeters':anchor_error,'maximumHeadRelativeDisplacementMeters':float(delta.max())})
    report['earSkinProof']['samples'].append({'label':label,'frame':frame,'components':rows})
report['authoringCode']={name:sha(HERE/name) for name in ['build_ear_candidate.py','ear_motion.py']}
for name in report['authoringCode']:
    text=bpy.data.texts.new('Nib ear motion study '+name);text.write((HERE/name).read_text())
head=bpy.data.objects['Nib v5 fitted animation face']
rig.animation_data.action=None
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
scene.frame_set(1);report['neutralCoordinates']=facial_snapshot(scene,rig,head)
rig.animation_data.action=bpy.data.actions['Idle'];scene.frame_set(1)
report['idleCoordinates']=facial_snapshot(scene,rig,head)
issues=[p+': '+issue for p in ['neutralCoordinates','idleCoordinates'] for issue in report[p]['neutralStructuralBlockersIfClosedMouthExpected']]
report['preRenderGate']={'passed':not issues,'blockingIssues':issues,'scope':'Existing facial/neutral gate retained; this isolated study does not repair face geometry'}
scene['source_version']='Ear motion study v1 on unaccepted v5h; body tracks preserved, no runtime promotion'
bpy.ops.wm.save_as_mainfile(filepath=str(TARGET),compress=True)
if sha(SOURCE)!=EXPECTED:raise RuntimeError('Pinned source changed')
report['candidateSha256']=sha(TARGET)
OUT.write_text(json.dumps(report,indent=2)+'\n',newline='\n')
print('NIB_EAR_MOTION_CANDIDATE_SAVED',flush=True)
