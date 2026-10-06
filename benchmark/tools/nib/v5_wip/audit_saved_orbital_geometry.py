"""Prepared read-only fitted eye/lid extraction for geometric closure work.

No shape, material, skeleton, animation or source is written. Run only in the
allocated guarded Blender slot. The output is a local numerical cache plus a
small hash/bounds report, not a render or an accepted eyelid repair.
"""
import argparse,hashlib,json,sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Matrix

parser=argparse.ArgumentParser()
parser.add_argument('--source',type=Path,required=True)
parser.add_argument('--expected-sha',required=True)
parser.add_argument('--cache',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if sha(args.source)!=args.expected_sha:raise RuntimeError('Wrong pinned source for orbital audit')
bpy.ops.wm.open_mainfile(filepath=str(args.source),load_ui=False)
scene=bpy.context.scene;rig=bpy.data.objects['Nib_Rig'];head=bpy.data.objects['Nib v5 fitted animation face']
for obj in scene.objects:
    if obj.type=='MESH':
        obj.hide_set(True)
        for mod in obj.modifiers:
            if mod.type=='ARMATURE':mod.show_viewport=False
rig.hide_set(False);rig.hide_viewport=False;rig.animation_data.action=None
for track in rig.animation_data.nla_tracks:track.mute=True
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
scene.frame_set(1);bpy.context.view_layer.update()
inverse=head.matrix_world.inverted()
arrays={'source':np.asarray([a.vector[:] for a in head.data.attributes['nib_source_position'].data]),
    'basis':np.asarray([v.co[:] for v in head.data.shape_keys.key_blocks['Basis'].data]),
    'edges':np.asarray([e.vertices[:] for e in head.data.edges],dtype=np.int32),
    'faces':np.asarray([p.vertices[:] for p in head.data.polygons],dtype=np.int32),
    'faceSets':np.asarray([a.value for a in head.data.attributes['.sculpt_face_set'].data],dtype=np.int32),
    'headMatrixWorld':np.asarray(head.matrix_world)}
report={'status':'Read-only actual orbital geometry extraction; no repair or artistic acceptance',
    'source':str(args.source),'sourceSha256':args.expected_sha,'codeSha256':sha(Path(__file__)),
    'coordinateSpace':'All fitted points and Eye bind centers expressed in the unchanged head object coordinate frame',
    'eyeSurfaces':{},'sharedChanged':False}
for side in ['L','R']:
    center=inverse@rig.matrix_world@rig.data.bones['Eye_'+side].head_local
    report['eyeSurfaces'][side]={'bindCenter':list(center)}
    arrays['eyeCenter_'+side]=np.asarray(center)
    for part in ['sclera','iris']:
        obj=bpy.data.objects['Nib v5 fitted '+part+' '+side]
        obj.hide_set(False);obj.hide_viewport=False
        for mod in obj.modifiers:
            if mod.type=='ARMATURE':mod.show_viewport=True
        bpy.context.view_layer.update();evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        mesh=evaluated.to_mesh()
        try:
            transform=inverse@evaluated.matrix_world
            p=np.asarray([tuple(transform@v.co) for v in mesh.vertices])
            mesh.calc_loop_triangles();triangles=np.asarray([t.vertices[:] for t in mesh.loop_triangles],dtype=np.int32)
            if not np.isfinite(p).all():raise RuntimeError('Nonfinite ocular points')
            arrays[part+'_'+side]=p;arrays[part+'Triangles_'+side]=triangles
            report['eyeSurfaces'][side][part]={'vertices':len(p),'triangles':len(triangles),
                'boundsMin':p.min(axis=0).tolist(),'boundsMax':p.max(axis=0).tolist()}
        finally:evaluated.to_mesh_clear()
if sha(args.source)!=args.expected_sha:raise RuntimeError('Read-only orbital audit changed source')
args.cache.parent.mkdir(parents=True,exist_ok=True)
np.savez_compressed(args.cache,**arrays)
report['cacheSha256']=sha(args.cache);report['cache']=str(args.cache)
args.output.parent.mkdir(parents=True,exist_ok=True)
args.output.write_text(json.dumps(report,indent=2)+'\n',newline='\n')
print('NIB_SAVED_ORBITAL_GEOMETRY_AUDIT_COMPLETE',flush=True)
