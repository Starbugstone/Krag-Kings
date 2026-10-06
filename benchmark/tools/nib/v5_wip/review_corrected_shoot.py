"""Pose the repaired exported FBX, measure corrective isolation, render one face.

This is Blender import evidence, not a substitute for the running-engine check.
The preserved v4b source supplies only its review camera/lights/materials.
"""
import argparse, hashlib, json, math, sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector

parser=argparse.ArgumentParser()
parser.add_argument('--source',type=Path,required=True)
parser.add_argument('--candidate-dir',type=Path,required=True)
parser.add_argument('--output-dir',type=Path,required=True)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
args.output_dir.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(args.source))
scene=bpy.context.scene
materials={m.name:m for m in bpy.data.materials if m.name.startswith('Nib_')}
for obj in bpy.data.collections['Nib_Authored_Components'].objects:
    obj.hide_render=True;obj.hide_set(True)
source_rig=bpy.data.objects['Nib_Rig'];source_rig.hide_render=True;source_rig.hide_set(True)
before=set(bpy.data.objects);prior_actions=set(bpy.data.actions)
fbx=args.candidate_dir/'Nib_Natural.fbx'
bpy.ops.import_scene.fbx(filepath=str(fbx),use_anim=True)
imported=set(bpy.data.objects)-before
mesh=next(o for o in imported if o.type=='MESH')
rig=next(o for o in imported if o.type=='ARMATURE')
for slot in mesh.material_slots:
    name=slot.material.name.rsplit('.',1)[0] if slot.material.name.rsplit('.',1)[-1].isdigit() else slot.material.name
    if name not in materials:raise RuntimeError('Unknown imported material '+name)
    slot.material=materials[name]
manifest=json.loads((args.candidate_dir/'manifest.json').read_text())
rules=manifest['variants'][0].get('deformation',manifest['deformation'])['drivers']
actions=[a for a in set(bpy.data.actions)-prior_actions if a.name.endswith('|Shoot') and any(s.target_id_type=='OBJECT' for s in a.slots)]
if len(actions)!=1:raise RuntimeError('Expected one imported skeletal Shoot take: '+str([a.name for a in actions]))
rig.animation_data_create();rig.animation_data.action=actions[0]
rig.animation_data.action_slot=next(s for s in actions[0].slots if s.target_id_type=='OBJECT')
phase=.46;start,end=actions[0].frame_range;frame=start+(end-start)*phase
scene.frame_set(int(frame),subframe=frame-int(frame));bpy.context.view_layer.update()
keys=mesh.data.shape_keys.key_blocks
mesh.data.shape_keys.animation_data_clear()
for key in keys:key.value=0
weights={}
for rule in rules:
    pb=rig.pose.bones[rule['bone']]
    q=pb.matrix_basis.to_quaternion();q.normalize()
    value=math.degrees(2*math.acos(min(1,abs(q.w)))) if rule['channel']=='rotationMagnitudeDegrees' else pb.location.length
    weight=max(0,min(rule.get('maxWeight',1),(value-rule['start'])/(rule['end']-rule['start'])))
    if rule['morph'] not in keys:raise RuntimeError('Missing imported target '+rule['morph'])
    keys[rule['morph']].value=weight;weights[rule['morph']]=weight
def evaluated():
    bpy.context.view_layer.update();evaluated=mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
    geometry=evaluated.to_mesh()
    try:
        points=np.empty(len(geometry.vertices)*3,dtype=np.float64);geometry.vertices.foreach_get('co',points)
        transform=np.array(mesh.matrix_world,dtype=np.float64)
        return points.reshape(-1,3)@transform[:3,:3].T+transform[:3,3]
    finally:evaluated.to_mesh_clear()
basis=np.asarray([mesh.matrix_world@v.co for v in mesh.data.vertices]);head=basis[:,2]>1.040
full=evaluated()
for name in weights:
    if name.startswith('Corrective_'):keys[name].value=0
without_body=evaluated()
body_error=float(np.linalg.norm(full[head]-without_body[head],axis=1).max())
if body_error>1e-7:raise RuntimeError('Repaired body keys still alter posed head: '+str(body_error))
for key in keys:key.value=0
skin_only=evaluated()
for name,weight in weights.items():keys[name].value=weight
bpy.context.view_layer.update()
report={'status':'Actual repaired FBX imported and posed; artistic acceptance false, engine verification separate',
        'fbx':str(fbx),'fbxSha256':hashlib.sha256(fbx.read_bytes()).hexdigest(),
        'sceneSource':str(args.source),'sceneSourceSha256':hashlib.sha256(args.source.read_bytes()).hexdigest(),
        'action':actions[0].name,'normalizedPhase':phase,'frame':frame,'weights':weights,
        'headVertices':int(head.sum()),'bodyCorrectiveHeadMaxDisplacementMeters':body_error,
        'allMorphsVersusSkinOnlyHeadMaxDisplacementMeters':float(np.linalg.norm(full[head]-skin_only[head],axis=1).max()),
        'posedHeadBoundsMin':full[head].min(axis=0).tolist(),'posedHeadBoundsMax':full[head].max(axis=0).tolist(),
        'renderer':'Blender Cycles CPU','samples':20,'passed':True}
camera=scene.camera;camera.data.type='ORTHO';camera.data.ortho_scale=.69
camera.location=(.35,-3,1.33);camera.rotation_euler=(Vector((0,-.005,1.17))-camera.location).to_track_quat('-Z','Y').to_euler()
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=20;scene.cycles.use_denoising=True
scene.render.threads_mode='FIXED';scene.render.threads=4
scene.render.resolution_x=1400;scene.render.resolution_y=1100;scene.render.resolution_percentage=100
scene.render.filepath=str(args.output_dir/'Nib_RepairedShoot_Face.png')
bpy.ops.render.render(write_still=True)
(args.output_dir/'Nib_RepairedShoot_Face.json').write_text(json.dumps(report,indent=2)+'\n',newline='\n')
print('NIB_REPAIRED_SHOOT_REVIEW_PASSED',flush=True)
