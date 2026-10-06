"""Actual native LBS anatomy and bounded pronation review, no source writes."""
import hashlib,json,sys,math
from pathlib import Path
import bpy
import numpy as np
from mathutils import Matrix,Quaternion,Vector

HERE=Path(__file__).parent;ROOT=HERE.parents[3]
SOURCE=ROOT/'benchmark/art/nib/Nib_AnatomicalBodyStudy_v1.blend'
OUT=ROOT/'benchmark/art/nib/motion-study/anatomical-body-v1-renders'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
receipt=json.loads((OUT.parent/'anatomical-body-v1.json').read_text())
expected=receipt['outputSha256']
if sha(SOURCE)!=expected:raise RuntimeError('Candidate source provenance mismatch')
if OUT.exists():raise RuntimeError('Preserve existing body review')
OUT.mkdir(parents=True)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE),load_ui=False)
scene=bpy.context.scene;rig=bpy.data.objects['Nib_Rig'];body=bpy.data.objects['Continuous Nib anatomy organic']
for obj in bpy.data.collections['Nib_Authored_Components'].objects:
    visible=obj.get('variant','all') in ['all','natural','organic'];obj.hide_render=not visible;obj.hide_viewport=not visible
rig.animation_data.action=None
for track in rig.animation_data.nla_tracks:track.mute=True
for obj in scene.objects:
    if obj.type!='MESH':continue
    for mod in obj.modifiers:
        if mod.type=='ARMATURE' and mod.object==rig and mod.use_deform_preserve_volume:
            raise RuntimeError('Diagnostic must use portable LBS, not Blender DQS')
scene.render.engine='BLENDER_WORKBENCH';scene.render.resolution_x=1000;scene.render.resolution_y=900
scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
scene.render.use_compositing=False;scene.render.use_sequencer=False;scene.render.film_transparent=False
shade=scene.display.shading;shade.light='STUDIO';shade.color_type='SINGLE';shade.single_color=(.54,.54,.54)
shade.show_shadows=True;shade.show_cavity=True;shade.cavity_type='BOTH';shade.background_type='WORLD';scene.world.color=(.07,.07,.07)
scene.display.render_aa='16';camera=scene.camera;camera.data.type='ORTHO';camera.data.ortho_scale=.74
target=Vector((0,-.005,.825))
report={'status':'Actual static LBS construction/twist diagnostics; not final motion/material/likeness acceptance',
    'source':str(SOURCE),'sourceSha256':expected,'codeSha256':sha(Path(__file__)),
    'blenderDQS':False,'poses':[],'sharedChanged':False,'artisticAcceptance':False}
body.data.calc_loop_triangles();tri=np.asarray([t.vertices[:] for t in body.data.loop_triangles],dtype=np.int32)
base=np.asarray([v.co[:] for v in body.data.vertices],dtype=np.float64)
base_area=np.linalg.norm(np.cross(base[tri[:,1]]-base[tri[:,0]],base[tri[:,2]]-base[tri[:,0]]),axis=1)
edges=np.asarray([e.vertices[:] for e in body.data.edges]);base_lengths=np.linalg.norm(base[edges[:,0]]-base[edges[:,1]],axis=1)
def put_world(name,q):
    bone=rig.data.bones[name];pb=rig.pose.bones[name];local=bone.parent.matrix_local.inverted()@bone.matrix_local
    pb.rotation_mode='QUATERNION';pb.rotation_quaternion=local.to_quaternion().inverted()@rig.pose.bones[bone.parent.name].matrix.to_quaternion().inverted()@q
    bpy.context.view_layer.update()
for label,bend,twist,offset in [('Neutral',0,0,Vector((0,-3,.10))),('Pronation90',0,90,Vector((.8,-3,.10))),('Flex60Pronation90',60,90,Vector((1.4,-3,.25)))]:
    for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
    scene.frame_set(1);bpy.context.view_layer.update()
    lower='LowerArm_L';roll='ForearmTwist_L';hand='Hand_L'
    rest=rig.data.bones[lower].matrix_local.to_quaternion()
    desired=Quaternion(Vector((1,0,0)),math.radians(-bend))@rest
    put_world(lower,desired)
    rig.pose.bones[roll].rotation_mode='QUATERNION';rig.pose.bones[roll].rotation_quaternion=Quaternion(Vector((0,1,0)),math.radians(twist*.5))
    bpy.context.view_layer.update()
    hand_world=desired@Quaternion(Vector((0,1,0)),math.radians(twist))@rest.inverted()@rig.data.bones[hand].matrix_local.to_quaternion()
    put_world(hand,hand_world)
    evaluated=body.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=evaluated.to_mesh()
    try:points=np.asarray([v.co[:] for v in mesh.vertices])
    finally:evaluated.to_mesh_clear()
    if points.shape!=base.shape or not np.isfinite(points).all():raise RuntimeError('Invalid actual posed anatomy surface')
    area=np.linalg.norm(np.cross(points[tri[:,1]]-points[tri[:,0]],points[tri[:,2]]-points[tri[:,0]]),axis=1)
    ratio=area/np.maximum(base_area,1e-15);stretch=np.linalg.norm(points[edges[:,0]]-points[edges[:,1]],axis=1)/np.maximum(base_lengths,1e-12)
    metrics={'minimumAreaRatio':float(ratio.min()),'maximumEdgeStretch':float(stretch.max()),
             'edgeStretchP99':float(np.percentile(stretch,99)),
             'newZeroAreaTriangles':int(np.count_nonzero((base_area>1e-12)&(area<=1e-12)))}
    if metrics['newZeroAreaTriangles']:raise RuntimeError('New degenerate faces in actual twist pose')
    camera.location=target+offset;camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
    image=OUT/(label+'.png');scene.render.filepath=str(image);bpy.ops.render.render(write_still=True)
    report['poses'].append({'label':label,'elbowFlexDegrees':bend,'forearmPronationDegrees':twist,
        'twistBoneLocalDegrees':twist*.5,'handRigQuaternion':list(rig.pose.bones[hand].matrix.to_quaternion()),
        'geometry':metrics,'image':str(image),'imageSha256':sha(image)})
    (OUT/'review.json').write_text(json.dumps(report,indent=2)+'\n',newline='\n')
if sha(SOURCE)!=expected:raise RuntimeError('Read-only body review changed source')
print('NIB_ANATOMICAL_BODY_DIAGNOSTIC_REVIEW_COMPLETE',flush=True)
