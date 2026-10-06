"""Isolated scarf replacement after the actual groom-only checkpoint.

The input's exact groom, skin, morphs, rigs, images and action curves remain
unchanged. This is a construction candidate; geometric gates are not approval.
"""
import argparse,hashlib,json,sys
from pathlib import Path
import bpy,numpy as np
from mathutils import Matrix
from mathutils.bvhtree import BVHTree

HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE),str(HERE.parent/'restorative_wip')]
from contracts import rig_contract,surface_hash
from returned_scarf import create

p=argparse.ArgumentParser()
p.add_argument('--source',type=Path,required=True)
p.add_argument('--source-sha256',required=True)
p.add_argument('--output-dir',type=Path,required=True)
args=p.parse_args(sys.argv[sys.argv.index('--')+1:])
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
if sha(args.source)!=args.source_sha256:raise RuntimeError('Pinned actual groom source differs')
if args.output_dir.exists():raise RuntimeError('Preserve previous scarf candidate')
if not args.output_dir.resolve().is_relative_to((HERE.parents[3]/'benchmark/art/nib/garment-study').resolve()):
    raise RuntimeError('Owned isolated garment-study output required')
inherited=json.loads((args.source.parent/'source.json').read_text())
if inherited['candidateSha256']!=args.source_sha256 or not inherited['savedSourceReopened']:
    raise RuntimeError('Actual reopened input receipt required')
preflight=json.loads((HERE/'pattern-preflight.json').read_text())
if preflight['blocked'] or preflight['patternSha256']!=sha(HERE/'cloth_pattern.py'):
    raise RuntimeError('Current rest pattern has not passed its numerical preflight')
bpy.ops.wm.open_mainfile(filepath=str(args.source),load_ui=False)
scene=bpy.context.scene;rig=bpy.data.objects['Nib_Rig']
collection=bpy.data.collections['Nib_Authored_Components']
old=bpy.data.objects['Nib v5 layered desert scarf']
body=bpy.data.objects['Continuous Nib anatomy organic']
head=bpy.data.objects['Nib v5 fitted animation face']
before=rig_contract(rig)
retained={o.name:surface_hash(o) for o in bpy.data.objects if o.type=='MESH' and o!=old}
old_hash=surface_hash(old);material=old.data.materials[0]
material_contract=str(scene['nib_groom_material_contract'])
images={i.name:{'path':str(Path(bpy.path.abspath(i.filepath)).resolve()),
               'sha256':sha(Path(bpy.path.abspath(i.filepath))),
               'colorSpace':i.colorspace_settings.name}
        for i in bpy.data.images if i.source=='FILE' and i.filepath}
rig.animation_data.action=None
for track in rig.animation_data.nla_tracks:track.mute=True
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
scene.frame_set(1);bpy.context.view_layer.update()
# Create and validate before discarding only the superseded local object.
# Existing support is actual Body/Head skin; old scarf is not a collider.
scarf,construction=create(collection,rig,material,body,head)
mesh=scarf.data;mesh.calc_loop_triangles()
points=np.asarray([v.co[:] for v in mesh.vertices],float)
tris=np.asarray([t.vertices[:] for t in mesh.loop_triangles],int)
q=points[tris];areas=np.linalg.norm(np.cross(q[:,1]-q[:,0],q[:,2]-q[:,0]),axis=1)
if not np.isfinite(points).all() or np.any(areas<=1e-18):
    raise RuntimeError('Degenerate actual scarf surface')
for vertex in mesh.vertices:
    w=[g.weight for g in vertex.groups if g.weight>1e-8]
    if len(w)>2 or abs(sum(w)-1)>1e-6:raise RuntimeError('Scarf weight contract differs')
poses=[]
for action,frame in [('Idle',1),('Walk',13),('Run',8),('Shoot',14),('FacePerformance',103)]:
    rig.animation_data.action=bpy.data.actions[action]
    scene.frame_set(frame);bpy.context.view_layer.update()
    deps=bpy.context.evaluated_depsgraph_get();vertices=[];triangles=[]
    for obj in [body,head]:
        ev=obj.evaluated_get(deps);data=ev.to_mesh();data.calc_loop_triangles();offset=len(vertices)
        vertices.extend(obj.matrix_world@v.co for v in data.vertices)
        triangles.extend(tuple(offset+i for i in t.vertices) for t in data.loop_triangles)
        ev.to_mesh_clear()
    tree=BVHTree.FromPolygons(vertices,triangles,all_triangles=True)
    ev=scarf.evaluated_get(deps);data=ev.to_mesh();signed=[]
    for index in np.linspace(0,len(data.vertices)-1,min(2000,len(data.vertices)),dtype=int):
        point=scarf.matrix_world@data.vertices[int(index)].co
        hit,normal,_,distance=tree.find_nearest(point)
        if hit is None:raise RuntimeError('Actual posed support unavailable')
        signed.append(float((point-hit).dot(normal)))
    ev.to_mesh_clear()
    sample={'action':action,'frame':frame,'sampleCount':len(signed),
            'minimumNearestNormalDistanceMeters':min(signed),
            'belowMinus2mm':sum(v<-.002 for v in signed)}
    poses.append(sample);print('NIB_SCARF_POSED_SUPPORT',json.dumps(sample),flush=True)
    if min(signed)<-.003:raise RuntimeError('Scarf crosses actual posed skin by more than 3 mm')
old_mesh=old.data;bpy.data.objects.remove(old,do_unlink=True)
if old_mesh.users==0:bpy.data.meshes.remove(old_mesh)
if rig_contract(rig)!=before:raise RuntimeError('Scarf construction changed bind/actions')
for name,digest in retained.items():
    if surface_hash(bpy.data.objects[name])!=digest:raise RuntimeError('Unrelated mesh changed '+name)
new_hash=surface_hash(scarf);new_name=scarf.name
for file in [Path(__file__),HERE/'returned_scarf.py',HERE/'cloth_pattern.py']:
    text=bpy.data.texts.new('Nib returned scarf '+file.name);text.write(file.read_text())
rig.animation_data.action=bpy.data.actions['Idle'];scene.frame_set(1)
scene['source_version']='Actual layered groom retained; isolated returned-fold scarf; art failures remain'
args.output_dir.mkdir(parents=True)
target=args.output_dir/'Nib_Coherent_ReturnedScarf_v1.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(target),compress=True)
bpy.ops.wm.open_mainfile(filepath=str(target),load_ui=False)
if rig_contract(bpy.data.objects['Nib_Rig'])!=before:raise RuntimeError('Saved bind/actions differ')
for name,digest in {**retained,new_name:new_hash}.items():
    if surface_hash(bpy.data.objects[name])!=digest:raise RuntimeError('Saved mesh differs '+name)
for name,entry in images.items():
    image=bpy.data.images[name];size=list(image.size);path=Path(bpy.path.abspath(image.filepath)).resolve()
    if str(path)!=entry['path'] or sha(path)!=entry['sha256'] or not image.has_data or min(size)<=0 or image.colorspace_settings.name!=entry['colorSpace']:
        raise RuntimeError('Saved assigned texture differs '+name)
if str(bpy.context.scene['nib_groom_material_contract'])!=material_contract:
    raise RuntimeError('Unrelated groom material contract differs')
if sha(args.source)!=args.source_sha256:raise RuntimeError('Input source changed')
report={'status':'Actual isolated scarf construction; matched visual review required',
        'sourceSha256':args.source_sha256,'candidateSha256':sha(target),'savedSourceReopened':True,
        'preservedRig':before,'retainedMeshHashes':retained,'removedScarfHash':old_hash,
        'changedMeshHashes':{new_name:new_hash},'scarf':construction,'clothPoses':poses,
        'vertices':len(points),'triangles':len(tris),'minimumDoubleArea':float(areas.min()),
        'connectedImages':images,'preRenderGate':inherited['preRenderGate'],
        'numericalWarnings':inherited['numericalWarnings'],'artisticAcceptance':False,
        'sharedChanged':False,'scarfMaterialUnchanged':True,
        'codeSha256':{f.name:sha(f) for f in [Path(__file__),HERE/'returned_scarf.py',HERE/'cloth_pattern.py']}}
(args.output_dir/'source.json').write_text(json.dumps(report,indent=2)+'\n',newline='\n')
print('NIB_RETURNED_SCARF_SAVED_AND_REOPENED',flush=True)
