"""Prepared isolated fur/scarf construction, never editing shared or face."""
import argparse,hashlib,json,sys
from pathlib import Path
import bpy,numpy as np
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sys.path[:0]=[str(HERE),str(HERE.parent/'restorative_wip'),str(HERE.parent/'identity_wip'),str(HERE.parent/'v6_groom_wip'),str(HERE.parent/'v5_wip')]
from contracts import rig_contract,surface_hash
from fit_card_roots_v3 import surface_tree
from ear_groom_weights import bind as bind_ear
from flow_guides import build as build_guides
from alpha_clumps import emit
from returned_scarf import create as create_scarf
from nib_groom_v5 import GOGGLE_ENVELOPES
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--source-sha256',required=True);p.add_argument('--output-dir',type=Path,required=True);args=p.parse_args(sys.argv[sys.argv.index('--')+1:])
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if sha(args.source)!=args.source_sha256:raise RuntimeError('Pinned actual source changed')
if args.output_dir.exists():raise RuntimeError('Preserve preceding candidate')
if not args.output_dir.resolve().is_relative_to((ROOT/'benchmark/art/nib/groom-study').resolve()):raise RuntimeError('Owned isolated output required')
preflight=json.loads((HERE/'pattern-preflight.json').read_text())
if preflight['blocked']or preflight['patternSha256']!=sha(HERE/'cloth_pattern.py'):raise RuntimeError('Exact current cloth pattern must pass its numerical gate')
inherited=json.loads((args.source.parent/'source.json').read_text())
if inherited['candidateSha256']!=args.source_sha256 or not inherited['savedSourceReopened']:raise RuntimeError('Actual reopened source receipt required')
bpy.ops.wm.open_mainfile(filepath=str(args.source),load_ui=False);scene=bpy.context.scene;rig=bpy.data.objects['Nib_Rig'];collection=bpy.data.collections['Nib_Authored_Components'];head=bpy.data.objects['Nib v5 fitted animation face'];body=bpy.data.objects['Continuous Nib anatomy organic']
for name in ['Idle','Walk','Run','Melee','Shoot','Hit','FacePerformance']:
    if name not in bpy.data.actions:raise RuntimeError('Canonical take missing '+name)
    bpy.data.actions[name].use_fake_user=True
before=rig_contract(rig)
removed=[o for o in collection.objects if o.type=='MESH'and ((o.name.startswith(('Nib v6 cards ','Nib v6 opaque accents '))and o.get('bone')in['Head','Ear_L','Ear_R'])or o.name.startswith('Auricle basal cartilage fold')or o.name=='Nib v5 layered desert scarf')]
if len([o for o in removed if o.name.startswith('Auricle basal cartilage fold')])!=2:raise RuntimeError('Unexpected old cartilage tubes')
retained={o.name:surface_hash(o)for o in bpy.data.objects if o.type=='MESH'and o not in removed}
images={i.name:{'path':str(Path(bpy.path.abspath(i.filepath)).resolve()),'sha256':sha(Path(bpy.path.abspath(i.filepath)).resolve()),'colorspace':i.colorspace_settings.name}for i in bpy.data.images if i.source=='FILE'and i.filepath}
material_contract=str(scene['nib_groom_material_contract'])
materials={'head':bpy.data.objects['Nib v6 cards crown'].data.materials[0],'innerWisps':bpy.data.objects['Nib v6 cards inner_wisps_L'].data.materials[0],'outerEar':bpy.data.objects['Nib v6 cards outer_nap_L'].data.materials[0]}
scarf_material=bpy.data.objects['Nib v5 layered desert scarf'].data.materials[0]
# Confirm immutable archived fine-atlas bytes, not an old carrier texture.
archive=json.loads((ROOT/'benchmark/art/nib/source-textures/macroface-regional-ed53df/manifest.json').read_text())
for material in materials.values():
    if material.get('portableAlphaMode')!='MASK':raise RuntimeError('Expected existing portable MASK material')
    for node in material.node_tree.nodes:
        if node.type=='TEX_IMAGE'and node.image:
            e=archive['images'].get(node.image.name)
            if e is None or sha(Path(bpy.path.abspath(node.image.filepath)))!=e['sha256']:raise RuntimeError('Fine-atlas bytes differ from actual source')
rig.animation_data.action=None
for track in rig.animation_data.nla_tracks:track.mute=True
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
scene.frame_set(1);bpy.context.view_layer.update()
groups=build_guides(head,collection);trees={'Head':surface_tree([head])}
for side in ['L','R']:
    parts=[o for o in collection.objects if o.type=='MESH'and o.get('bone')=='Ear_'+side and o.name.startswith(('Fennec cupped ear','Ear inner velvet'))]
    if len(parts)!=2:raise RuntimeError('Actual closed ear/inner support missing')
    trees['Ear_'+side]=surface_tree(parts)
old=[]
for obj in removed:
    old.append({'name':obj.name,'surfaceSha256':surface_hash(obj),'triangles':sum(len(p.vertices)-2 for p in obj.data.polygons),'opaqueStrands':int(obj.get('fur_strands',0))})
    mesh=obj.data;bpy.data.objects.remove(obj,do_unlink=True)
    if mesh.users==0:bpy.data.meshes.remove(mesh)
new=[];groom=[]
for group in groups:
    obj,attachment=emit('Nib layered alpha '+group['region'],group['guides'],collection,rig,materials[group['materialRegion']],group['bone'],trees[group['bone']]);new.append(obj)
    ear=bind_ear(obj,rig)
    groom.append({'region':group['region'],'sampling':group['sampling'],'attachment':attachment,'earBinding':ear})
scarf,cloth=create_scarf(collection,rig,scarf_material,body,head);new.append(scarf)
geometry=[]
for obj in new:
    mesh=obj.data;mesh.calc_loop_triangles();points=np.asarray([v.co[:]for v in mesh.vertices],float);tri=np.asarray([t.vertices[:]for t in mesh.loop_triangles],int);q=points[tri]
    area=np.linalg.norm(np.cross(q[:,1]-q[:,0],q[:,2]-q[:,0]),axis=1)
    if not np.isfinite(points).all()or np.any(area<=1e-18):raise RuntimeError('Degenerate new surface '+obj.name)
    loops=np.asarray([t.loops[:]for t in mesh.loop_triangles],int);uv=np.asarray([d.uv[:]for d in mesh.uv_layers['UVMap'].data],float)[loops]
    a,b=uv[:,1]-uv[:,0],uv[:,2]-uv[:,0];uvarea=np.abs(a[:,0]*b[:,1]-a[:,1]*b[:,0])
    # Solidify side walls intentionally use adjacent cloth UVs; record their
    # zero area rather than silently declaring all surface UVs non-degenerate.
    zeros=int(np.sum(uvarea<=1e-14))
    if zeros and obj!=scarf:raise RuntimeError('Collapsed fur UVs '+obj.name)
    for v in mesh.vertices:
        weights=[w for w in v.groups if w.weight>1e-8]
        if len(weights)>3 or abs(sum(w.weight for w in weights)-1)>1e-6:raise RuntimeError('New surface skin weights invalid')
    intrusion=0
    if obj.get('bone')=='Head':
        for center,back in GOGGLE_ENVELOPES:
            radius=np.hypot(points[:,0]-center.x,points[:,2]-center.z);intrusion+=int(np.sum((radius<.031)&(points[:,1]<back-.00015)))
    if intrusion:raise RuntimeError('Fur enters lens envelope')
    geometry.append({'name':obj.name,'vertices':len(points),'triangles':len(tri),'cards':int(obj.get('fur_cards',0)),'minimumDoubleArea':float(area.min()),'collapsedUvTriangles':zeros,'goggleIntrusions':intrusion})
if sum(g['triangles']for g in geometry)>350000:raise RuntimeError('Bounded layered-fur/cloth geometry exceeded350k triangles')
# Actual posed cloth/anatomy distances. This is a local signed-distance proxy,
# not a self-intersection or material/appearance acceptance test.
cloth_poses=[]
for action,frame in [('Idle',1),('Walk',13),('Run',8),('Shoot',14),('FacePerformance',103)]:
    rig.animation_data.action=bpy.data.actions[action];scene.frame_set(frame);bpy.context.view_layer.update();deps=bpy.context.evaluated_depsgraph_get()
    vertices=[];polys=[]
    for obj in [body,head]:
        evaluated=obj.evaluated_get(deps);mesh=evaluated.to_mesh();mesh.calc_loop_triangles();offset=len(vertices)
        vertices.extend(obj.matrix_world@v.co for v in mesh.vertices);polys.extend(tuple(offset+i for i in t.vertices)for t in mesh.loop_triangles);evaluated.to_mesh_clear()
    tree=BVHTree.FromPolygons(vertices,polys,all_triangles=True);evaluated=scarf.evaluated_get(deps);mesh=evaluated.to_mesh();sample=np.linspace(0,len(mesh.vertices)-1,min(2000,len(mesh.vertices)),dtype=int);signed=[]
    for i in sample:
        point=scarf.matrix_world@mesh.vertices[int(i)].co;hit,n,index,distance=tree.find_nearest(point)
        if hit is None:raise RuntimeError('No actual posed scarf/anatomy comparison')
        signed.append(float((point-hit).dot(n)))
    evaluated.to_mesh_clear();minimum=min(signed)
    cloth_poses.append({'action':action,'frame':frame,'samples':len(sample),'minimumNearestNormalDistanceMeters':minimum,'samplesBelowMinus2mm':sum(v<-.002 for v in signed)})
    if minimum<-.003:raise RuntimeError('New scarf crosses actual posed anatomy by over3mm '+str(cloth_poses[-1]))
for name,digest in retained.items():
    if surface_hash(bpy.data.objects[name])!=digest:raise RuntimeError('Unrelated mesh changed '+name)
if rig_contract(rig)!=before or str(scene['nib_groom_material_contract'])!=material_contract:raise RuntimeError('Rig/actions/material contract changed')
expected={o.name:surface_hash(o)for o in new}
args.output_dir.mkdir(parents=True);guides_file=args.output_dir/'guides.json';guides_file.write_text(json.dumps({'groups':groups},indent=2)+'\n',newline='\n')
scene['source_version']='Isolated layered alpha fur and returned scarf; inherited macroface failure retained'
scene['nib_surface_layers']=json.dumps({'sourceSha256':args.source_sha256,'newCards':sum(g['cards']for g in geometry),'opaqueBundlesRemoved':True,'artisticAcceptance':False})
for file in [Path(__file__),HERE/'flow_guides.py',HERE/'alpha_clumps.py',HERE/'returned_scarf.py',HERE/'cloth_pattern.py']:
    text=bpy.data.texts.new('Nib surface layers '+file.name);text.write(file.read_text())
rig.animation_data.action=bpy.data.actions['Idle'];scene.frame_set(1);target=args.output_dir/'Nib_Coherent_SurfaceLayers_v1.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(target),compress=True);bpy.ops.wm.open_mainfile(filepath=str(target),load_ui=False)
if rig_contract(bpy.data.objects['Nib_Rig'])!=before:raise RuntimeError('Saved source lost bind/actions')
for name,digest in {**retained,**expected}.items():
    if surface_hash(bpy.data.objects[name])!=digest:raise RuntimeError('Saved surface changed '+name)
for name,entry in images.items():
    image=bpy.data.images[name];path=Path(bpy.path.abspath(image.filepath)).resolve();size=list(image.size)
    if str(path)!=entry['path']or sha(path)!=entry['sha256']or image.colorspace_settings.name!=entry['colorspace']or not image.has_data or min(size)<=0:raise RuntimeError('Saved immutable source image differs '+name)
if sha(args.source)!=args.source_sha256:raise RuntimeError('Pinned input changed')
report={'status':'Actual isolated construction source; images and art acceptance pending','sourceSha256':args.source_sha256,'candidateSha256':sha(target),'savedSourceReopened':True,'preservedRig':before,'retainedMeshHashes':retained,'changedMeshHashes':expected,'removed':old,'groom':groom,'geometry':geometry,'scarf':cloth,'clothPoses':cloth_poses,'guideSha256':sha(guides_file),'connectedImages':images,'preRenderGate':inherited['preRenderGate'],'numericalWarnings':inherited['numericalWarnings'],'artisticAcceptance':False,'sharedChanged':False,'requiresMatchingFullMeshAndClipExport':True,'codeSha256':{p.name:sha(p)for p in HERE.glob('*.py')}}
(args.output_dir/'source.json').write_text(json.dumps(report,indent=2)+'\n',newline='\n');print('NIB_SURFACE_LAYERS_SAVED_AND_REOPENED',flush=True)
