"""One bounded saved-source pass for user-reported mouth and arm failures.

Runs the prepared local oral attribution, then exposes actual evaluated gait
bone poses for the shared anatomical-arm solver work. No source is modified.
"""
from pathlib import Path
import runpy, json, hashlib
import bpy
from mathutils import Matrix

HERE = Path(__file__).resolve().parent
state = runpy.run_path(str(HERE / 'audit_saved_oral_contact.py'), run_name='__main__')
rig, source, expected = state['rig'], state['SOURCE'], state['EXPECTED']
root, art = state['ROOT'], state['ART']
scene = bpy.context.scene
names = ['Pelvis', 'Spine', 'Chest', 'Neck', 'Head'] + [part + '_' + side for side in ['L', 'R']
    for part in ['Clavicle', 'UpperArm', 'LowerArm', 'Hand', 'Thigh', 'Shin', 'Foot']]
rig.animation_data.action = None
for bone in rig.pose.bones:
    bone.matrix_basis = Matrix.Identity(4)
bpy.context.view_layer.update()
report = {'status': 'Read-only actual saved-source bone trajectories; no animation repair or artistic acceptance',
    'source': str(source.relative_to(root)), 'sourceSha256': expected,
    'coordinateSpace': 'Blender armature-local meters; X lateral, -Y forward, Z up',
    'rigMatrixWorld': [list(row) for row in rig.matrix_world],
    'rest': {name: {'head': list(rig.data.bones[name].head_local),
                    'tail': list(rig.data.bones[name].tail_local),
                    'matrix': [list(row) for row in rig.data.bones[name].matrix_local]} for name in names},
    'poses': {}}
for clip, closing_frame in [('Walk', 37), ('Run', 19)]:
    rig.animation_data.action = bpy.data.actions[clip]
    rows = []
    for phase in [0., .25, .5, .75]:
        frame = 1 + phase * (closing_frame - 1)
        scene.frame_set(int(frame), subframe=frame - int(frame))
        bpy.context.view_layer.update()
        rows.append({'normalizedPhase': phase, 'frame': frame, 'bones': {
            name: {'head': list(rig.pose.bones[name].head), 'tail': list(rig.pose.bones[name].tail),
                   'localEulerRadians': list(rig.pose.bones[name].rotation_euler),
                   'matrixBasis': [list(row) for row in rig.pose.bones[name].matrix_basis],
                   'matrixInRigSpace': [list(row) for row in rig.pose.bones[name].matrix]}
            for name in names}})
    report['poses'][clip] = rows
if hashlib.sha256(source.read_bytes()).hexdigest() != expected:
    raise RuntimeError('Read-only source changed')
(art / 'anatomy-study/locomotion-source-poses-v9h.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8', newline='\n')
print('Actual source gait poses saved; no source animation changed', flush=True)
