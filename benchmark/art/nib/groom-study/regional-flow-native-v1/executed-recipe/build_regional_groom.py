"""Prepared isolated regional groom from the frozen fitted-neck source.

Replaces only five head and four inward/rim groups. Actual fine-strands maps,
outer-ear short nap, fine skin fuzz, shape/bind/actions and cloth remain exact.
This never edits shared files or produces an engine export.
"""
import argparse,hashlib,json,sys
from pathlib import Path
import bpy,numpy as np
from mathutils import Matrix,Vector
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sys.path[:0]=[str(HERE),str(HERE.parent/'restorative_wip'),str(HERE.parent/'identity_wip'),str(HERE.parent/'v6_groom_wip'),str(HERE.parent/'v5_wip')]
from contracts import rig_contract,surface_hash
from guide_recipe import replacement_groups,HEAD_COUNTS,COUNTS
from importlib.util import spec_from_file_location,module_from_spec
_card_spec=spec_from_file_location('nib_regional_card_geometry',HERE/'card_geometry.py')
_card_module=module_from_spec(_card_spec);_card_spec.loader.exec_module(_card_module)
emit=_card_module.emit
from fit_card_roots_v3 import surface_tree
from ear_groom_weights import bind as bind_ear_groom
from nib_groom_v5 import strand_mesh,GOGGLE_ENVELOPES
parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,required=True);parser.add_argument('--source-sha256',required=True);parser.add_argument('--output-dir',type=Path,required=True)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:]);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if sha(args.source)!=args.source_sha256:raise RuntimeError('Frozen coherent source changed')
if args.output_dir.exists():raise RuntimeError('Preserve previous regional candidate')
if not args.output_dir.resolve().is_relative_to((ROOT/'benchmark/art/nib/groom-study').resolve()):raise RuntimeError('Owned isolated groom output required')
inherited=json.loads((args.source.parent/'source.json').read_text())
if inherited['candidateSha256']!=args.source_sha256 or not inherited['savedSourceReopened']:raise RuntimeError('Actual coherent source receipt required')
bpy.ops.wm.open_mainfile(filepath=str(args.source),load_ui=False);scene=bpy.context.scene;rig=bpy.data.objects['Nib_Rig'];collection=bpy.data.collections['Nib_Authored_Components']
regions=list(HEAD_COUNTS)+[part+'_'+side for side in ['L','R']for part in COUNTS]
changed_names={prefix+region for region in regions for prefix in ['Nib v6 cards ','Nib v6 opaque accents ']}
if any(n not in bpy.data.objects for n in changed_names):raise RuntimeError('Actual prior regional group missing')
canonical=['Idle','Walk','Run','Melee','Shoot','Hit','FacePerformance']
for name in canonical:
    if name not in bpy.data.actions:raise RuntimeError('Missing canonical action '+name)
    bpy.data.actions[name].use_fake_user=True
before=rig_contract(rig);retained={o.name:surface_hash(o)for o in bpy.data.objects if o.type=='MESH'and o.name not in changed_names}
material_contract=str(scene['nib_groom_material_contract']);connected_images={}
for image in bpy.data.images:
    if image.source!='FILE' or not image.filepath:continue
    absolute=Path(bpy.path.abspath(image.filepath)).resolve()
    if not absolute.is_file():raise RuntimeError('Missing source image '+str(absolute))
    connected_images[image.name]={'absolute':str(absolute),'sha256':sha(absolute),'colorspace':image.colorspace_settings.name}
card_materials={region:bpy.data.objects['Nib v6 cards '+region].data.materials[0]for region in regions}
opaque_materials={region:bpy.data.objects['Nib v6 opaque accents '+region].data.materials[0]for region in regions}
# Prove current actual fine atlas, not the superseded original v6 images.
expected_atlas=(ROOT/'benchmark/art/nib/groom-study/fine-strands-v1/textures').resolve()
for material in card_materials.values():
    images=[n.image for n in material.node_tree.nodes if n.type=='TEX_IMAGE'and n.image]
    if not images or any(Path(bpy.path.abspath(i.filepath)).resolve().parent!=expected_atlas for i in images):raise RuntimeError('Regional groom material does not use the actual fine atlas')
rig.animation_data.action=None
for track in rig.animation_data.nla_tracks:track.mute=True
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
scene.frame_set(1);bpy.context.view_layer.update()
head=bpy.data.objects['Nib v5 fitted animation face'];groups=replacement_groups(head,collection)
trees={'Head':surface_tree([head])}
for side in ['L','R']:
    surfaces=[o for o in collection.objects if o.type=='MESH'and o.get('bone')=='Ear_'+side and o.name.startswith(('Fennec cupped ear','Ear inner velvet'))]
    if len(surfaces)!=2:raise RuntimeError('Expected actual closed outer/inner ear surfaces')
    trees['Ear_'+side]=surface_tree(surfaces)
removed=[]
for name in changed_names:
    obj=bpy.data.objects[name];mesh=obj.data
    removed.append({'name':name,'cards':int(obj.get('fur_cards',0)),'strands':int(obj.get('fur_strands',0)),'triangles':sum(len(p.vertices)-2 for p in mesh.polygons)})
    bpy.data.objects.remove(obj,do_unlink=True)
    if mesh.users==0:bpy.data.meshes.remove(mesh)
generated=[];records=[];ear_binding=[]
for group in groups:
    region=group['region'];guides=group['guides'];bone=group['bone']
    obj,attachment=emit('Nib v6 cards '+region,guides,collection,rig,card_materials[region],bone,trees[bone]);generated.append(obj)
    # More narrow cards do not require more thick opaque accent bundles.
    accents=guides[::8]
    legacy=[tuple(Vector(g[k])for k in ['root','normal','middle','tip'])+(g['halfWidthMeters'],g['seed'])for g in accents]
    accent=strand_mesh('Nib v6 opaque accents '+region,legacy,collection,rig,opaque_materials[region],bone,cinematic=False,short_nap=False);generated.append(accent)
    for part in [obj,accent]:
        binding=bind_ear_groom(part,rig)
        if binding:ear_binding.append(binding)
    records.append({'region':region,'sampling':group['sampling'],'guides':len(guides),'opaqueAccentGuides':len(accents),'attachment':attachment})

def validate(obj):
    m=obj.data;m.calc_loop_triangles();p=np.asarray([v.co[:]for v in m.vertices],float);tri=np.asarray([t.vertices[:]for t in m.loop_triangles],int)
    q=p[tri];a=np.linalg.norm(np.cross(q[:,1]-q[:,0],q[:,2]-q[:,0]),axis=1)
    if not np.isfinite(p).all()or np.any(a<=1e-18):raise RuntimeError('Degenerate new groom '+obj.name)
    loops=np.asarray([t.loops[:]for t in m.loop_triangles],int);uv=np.asarray([v.uv[:]for v in m.uv_layers['UVMap'].data],float)[loops]
    du=uv[:,1]-uv[:,0];dv=uv[:,2]-uv[:,0];ua=np.abs(du[:,0]*dv[:,1]-du[:,1]*dv[:,0])
    if np.any(ua<=1e-14):raise RuntimeError('Collapsed atlas corners '+obj.name)
    tag=obj['bone'];allowed={'Head',tag,'EarTip_'+tag[-1]}if tag.startswith('Ear_')else{tag}
    for v in m.vertices:
        active=[g for g in v.groups if g.weight>1e-8]
        if len(active)>3 or abs(sum(g.weight for g in active)-1)>1e-6 or any(obj.vertex_groups[g.group].name not in allowed for g in active):raise RuntimeError('Invalid groom skin '+obj.name)
    intrusions=0
    for center,back in GOGGLE_ENVELOPES:
        radial=np.hypot(p[:,0]-center.x,p[:,2]-center.z);intrusions+=int(np.sum((radial<.031)&(p[:,1]<back-.00015)))
    if intrusions:raise RuntimeError('New groom enters actual goggle lens '+obj.name)
    return {'name':obj.name,'vertices':len(p),'triangles':len(tri),'cards':int(obj.get('fur_cards',0)),'opaqueStrands':int(obj.get('fur_strands',0)),
      'minimumDoubleAreaMetersSquared':float(a.min()),'minimumDoubleUvArea':float(ua.min()),'goggleLensIntrusions':intrusions}
geometry=[validate(obj)for obj in generated]
for name,digest in retained.items():
    if surface_hash(bpy.data.objects[name])!=digest:raise RuntimeError('Regional study changed unrelated mesh '+name)
if rig_contract(rig)!=before:raise RuntimeError('Regional study changed bind/actions')
if str(scene['nib_groom_material_contract'])!=material_contract:raise RuntimeError('Masked material contract changed')
changed={o.name:surface_hash(o)for o in generated}
scene['nib_regional_groom']=json.dumps({'sourceSha256':args.source_sha256,'scope':'Head and inward ear/rim only; visible pink membrane, fine skin fuzz and outer nap retained','atlas':'actual fine-strands-v1','artisticAcceptance':False})
scene['source_version']='Coherent regional flowing groom candidate; unchanged face/neck/body/cloth/rig; unaccepted'
code=[Path(__file__),HERE/'guide_recipe.py',HERE/'card_geometry.py',HERE.parent/'identity_wip/fit_card_roots_v3.py',HERE.parent/'v6_groom_wip/ear_groom_weights.py',HERE.parent/'v5_wip/nib_groom_v5.py']
for p in code:
    t=bpy.data.texts.new('Nib regional groom '+p.name);t.write(p.read_text())
args.output_dir.mkdir(parents=True);guide_file=args.output_dir/'groom-guides.json';guide_file.write_text(json.dumps({'sourceSha256':args.source_sha256,'groups':groups},indent=2)+'\n',newline='\n')
rig.animation_data.action=bpy.data.actions['Idle'];scene.frame_set(1);target=args.output_dir/'Nib_Coherent_RegionalGroom_v1.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(target),compress=True);bpy.ops.wm.open_mainfile(filepath=str(target),load_ui=False)
if rig_contract(bpy.data.objects['Nib_Rig'])!=before:raise RuntimeError('Saved regional source changed rig/actions')
for name,digest in {**retained,**changed}.items():
    if surface_hash(bpy.data.objects[name])!=digest:raise RuntimeError('Saved groom payload differs '+name)
for name,entry in connected_images.items():
    image=bpy.data.images[name];absolute=Path(bpy.path.abspath(image.filepath)).resolve();size=list(image.size)
    if str(absolute)!=entry['absolute']or sha(absolute)!=entry['sha256']or image.colorspace_settings.name!=entry['colorspace']or not image.has_data or min(size)<=0:raise RuntimeError('Saved actual fine atlas/source map differs '+name)
if sha(args.source)!=args.source_sha256:raise RuntimeError('Frozen engine candidate changed')
report={'status':'Actual regional groom source; visual coverage, flow and ear posing pending','source':str(args.source),'sourceSha256':args.source_sha256,
 'candidate':str(target),'candidateSha256':sha(target),'savedSourceReopened':True,'preservedRig':before,'retainedMeshHashes':retained,'changedMeshHashes':changed,
 'groups':records,'geometry':geometry,'earBinding':ear_binding,'removedGroom':removed,'guideSha256':sha(guide_file),'connectedImageHashes':connected_images,
 'materialContractUnchanged':True,'newGroupTriangles':sum(v['triangles']for v in geometry),'oldGroupTriangles':sum(v['triangles']for v in removed),
 'preRenderGate':inherited['preRenderGate'],'codeSha256':{p.name:sha(p)for p in code},'sharedChanged':False,'artisticAcceptance':False,
 'pending':['Actual matched Neutral and oblique ear coverage/roots','Actual back/head and EarTip twitch extrema','Original adult facial identity and scarf remain failed','New engine cost/overdraw/deformation verification']}
(args.output_dir/'source.json').write_text(json.dumps(report,indent=2)+'\n',newline='\n');print('NIB_REGIONAL_GROOM_SAVED_AND_REOPENED',flush=True)
