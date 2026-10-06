"""Separate reviewed-source runtime/cinematic groom candidate, never shared.

No new face, body, ear cartilage or cloth deformation is authored here. Run only
after the allocated face review and through the project's heavy-task guard.
"""
import argparse,hashlib,json,os,sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Matrix,Vector

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
sys.path.insert(0,str(HERE));sys.path.insert(0,str(HERE.parent/'v5_wip'))
from atlas import make_atlas,REGIONS
from card_materials import create_card_material
from guide_recipe import build_guides,legacy_guides
from card_geometry import emit_cards
from ear_groom_weights import bind as bind_ear_groom
from nib_groom_v5 import strand_mesh,GOGGLE_ENVELOPES

parser=argparse.ArgumentParser()
parser.add_argument('--source',type=Path,required=True)
parser.add_argument('--source-report',type=Path,required=True)
parser.add_argument('--output-dir',type=Path,required=True)
parser.add_argument('--representation',choices=['runtime','cinematic'],required=True)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source_hash=sha(args.source)
source_report=json.loads(args.source_report.read_text())
if source_report.get('candidateSha256')!=source_hash:raise RuntimeError('Saved source/report hash mismatch')
if not source_report.get('preRenderGate',{}).get('passed'):raise RuntimeError('Face source has not passed its structural gate; do not conceal it with fur')
if not args.output_dir.resolve().is_relative_to((ROOT/'benchmark/art/nib/groom-study').resolve()):
    raise RuntimeError('Groom study outputs must remain in the separate owned art/nib/groom-study directory')
target=args.output_dir/('Nib_Groom_v6_'+args.representation+'_WIP.blend')
if target.exists():raise RuntimeError('Preserve the previous candidate; choose a new output directory')
args.output_dir.mkdir(parents=True,exist_ok=True)
textures=args.output_dir/'textures'
bpy.ops.wm.open_mainfile(filepath=str(args.source),load_ui=False)
scene=bpy.context.scene;rig=bpy.data.objects['Nib_Rig']
if not np.allclose(np.asarray(rig.matrix_world),np.eye(4),atol=1e-8):raise RuntimeError('World-authored fur requires the established identity rig transform')
rig.animation_data.action=None
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
scene.frame_set(1);bpy.context.view_layer.update()
collection=bpy.data.collections['Nib_Authored_Components']
head=bpy.data.objects['Nib v5 fitted animation face']
prefixes=('Nib v5 scalp clumped coat','Nib v5 auricle clumped coat',
          'Nib v5 outer auricle short nap','Nib v5 tapered chin tuft')

def surface_hash(obj):
    h=hashlib.sha256();mesh=obj.data
    h.update(np.asarray(obj.matrix_world,dtype=np.float64).tobytes())
    coordinates=np.empty(len(mesh.vertices)*3,np.float32);mesh.vertices.foreach_get('co',coordinates);h.update(coordinates.tobytes())
    corners=np.empty(len(mesh.loops),np.int32);mesh.loops.foreach_get('vertex_index',corners);h.update(corners.tobytes())
    for uv in mesh.uv_layers:
        values=np.empty(len(uv.data)*2,np.float32);uv.data.foreach_get('uv',values);h.update(uv.name.encode());h.update(values.tobytes())
    if mesh.shape_keys:
        for key in mesh.shape_keys.key_blocks:
            key.data.foreach_get('co',coordinates);h.update(key.name.encode());h.update(coordinates.tobytes())
    for vertex in mesh.vertices:
        h.update(np.asarray([(g.group,g.weight) for g in vertex.groups],dtype=np.float64).tobytes())
    return h.hexdigest()

retained=[o for o in collection.objects if o.type=='MESH' and not o.name.startswith(prefixes)]
before={o.name:surface_hash(o) for o in retained}
atlas=make_atlas(textures)
nap_coverage=float(np.mean([t['coverageInContentAtCutoff'] for t in atlas['tiles'] if t['family']=='nap']))
guides=build_guides(head,collection,nap_coverage)
guide_path=args.output_dir/'groom-guides.json'
guide_path.write_text(json.dumps({'sourceSha256':source_hash,'groups':guides},indent=2)+'\n',newline='\n')
cards={region:create_card_material(next(e for e in atlas['materials'] if e['name']==entry[0]),textures)
       for region,entry in REGIONS.items()} if args.representation=='runtime' else {}
opaque={region:bpy.data.materials[name] for region,name in
        [('head','Nib_v5_HeadFur'),('innerWisps','Nib_v5_InnerEarWisps'),('outerEar','Nib_v5_TawnyEarFur')]}
removed=[]
for obj in list(collection.objects):
    if obj.type!='MESH' or not obj.name.startswith(prefixes):continue
    removed.append({'name':obj.name,'triangles':sum(len(p.vertices)-2 for p in obj.data.polygons)})
    mesh=obj.data;bpy.data.objects.remove(obj,do_unlink=True)
    if mesh.users==0:bpy.data.meshes.remove(mesh)
generated=[];group_receipts=[]
for group in guides:
    items=group['guides'];short=all(g['shortNap'] for g in items)
    group_receipt={'region':group['region'],'guides':len(items),'sampling':group['sampling'],'objects':[]}
    if args.representation=='runtime':
        obj,metrics=emit_cards('Nib v6 cards '+group['region'],items,collection,rig,cards[group['materialRegion']],group['bone'])
        generated.append(obj);group_receipt['objects'].append(metrics)
        accents=items[::8 if short else 4]
        obj=strand_mesh('Nib v6 opaque accents '+group['region'],legacy_guides(accents),collection,rig,
                        opaque[group['materialRegion']],group['bone'],cinematic=False,short_nap=short)
        generated.append(obj)
    else:
        # Stream zero contains the exact runtime accent fiber seeds. A second
        # deterministic stream adds detail without changing the guide coverage.
        for stream in [0,1]:
            chosen=[{**g,'seed':g['seed']+stream*1000000} for g in items]
            obj=strand_mesh('Nib v6 cinematic '+group['region']+' '+str(stream),legacy_guides(chosen),collection,rig,
                            opaque[group['materialRegion']],group['bone'],cinematic=True,short_nap=short)
            generated.append(obj)
    group_receipts.append(group_receipt)

def validate(obj):
    mesh=obj.data;mesh.calc_loop_triangles()
    points=np.asarray([v.co[:] for v in mesh.vertices],dtype=np.float64)
    triangles=np.asarray([t.vertices[:] for t in mesh.loop_triangles],dtype=np.int32)
    xyz=points[triangles];area2=np.linalg.norm(np.cross(xyz[:,1]-xyz[:,0],xyz[:,2]-xyz[:,0]),axis=1)
    if not np.isfinite(points).all() or np.any(area2<=1e-18):raise RuntimeError('Degenerate/nonfinite groom geometry: '+obj.name)
    uv=mesh.uv_layers['UVMap'];indices=np.asarray([t.loops[:] for t in mesh.loop_triangles],dtype=np.int32)
    values=np.asarray([item.uv[:] for item in uv.data],dtype=np.float64)[indices]
    a=values[:,1]-values[:,0];b=values[:,2]-values[:,0];uvarea=np.abs(a[:,0]*b[:,1]-a[:,1]*b[:,0])
    if np.any(uvarea<=1e-14):raise RuntimeError('Collapsed groom UV triangle: '+obj.name)
    tag=obj.get('bone','')
    allowed={'Head',tag,'EarTip_'+tag[-1]} if tag in ['Ear_L','Ear_R'] else {tag}
    maximum=3 if tag in ['Ear_L','Ear_R'] else 1
    for vertex in mesh.vertices:
        active=[group for group in vertex.groups if group.weight>1e-8]
        if not active or len(active)>maximum or abs(sum(group.weight for group in active)-1)>1e-6:
            raise RuntimeError('Invalid normalized groom skin weights')
        if any(obj.vertex_groups[group.group].name not in allowed for group in active):
            raise RuntimeError('Unexpected groom bone influence')
    intrusions=0
    if obj.get('bone')=='Head':
        for center,back_y in GOGGLE_ENVELOPES:
            r=np.hypot(points[:,0]-center.x,points[:,2]-center.z)
            intrusions+=int(((r<.031)&(points[:,1]<back_y-.00015)).sum())
    if intrusions:raise RuntimeError('Groom geometry crosses a goggle lens: '+obj.name)
    return {'name':obj.name,'vertices':len(points),'triangles':len(triangles),
            'minimumDoubleAreaMetersSquared':float(area2.min()),'minimumDoubleUvArea':float(uvarea.min()),
            'cards':int(obj.get('fur_cards',0)),'strands':int(obj.get('fur_strands',0)),
            'materials':[m.name for m in mesh.materials],'goggleLensIntrusions':intrusions}

ear_binding=[entry for o in generated if (entry:=bind_ear_groom(o,rig)) is not None]
geometry=[validate(o) for o in generated]
after={o.name:surface_hash(o) for o in retained}
if before!=after:raise RuntimeError('Retained face/body/fuzz/cloth topology, weights, UVs or morphs changed')
# Resolve all old relative image paths while the old source is still active,
# then make them relative to this separate candidate file's directory.
for image in bpy.data.images:
    if image.source=='FILE' and image.filepath and not image.packed_file:
        absolute=Path(bpy.path.abspath(image.filepath))
        image.filepath='//'+os.path.relpath(absolute,target.parent).replace('\\','/')
scene['source_version']='v6 '+args.representation+' groom candidate over reviewed '+args.source.name+'; unaccepted'
scene['nib_groom_source_sha256']=source_hash
scene['nib_groom_material_contract']=json.dumps(atlas['materials'] if args.representation=='runtime' else [])
scene.cycles.transparent_max_bounces=16
rig.animation_data.action=bpy.data.actions['Idle'];scene.frame_set(1)
code_files=[Path(__file__),HERE/'atlas.py',HERE/'guide_recipe.py',HERE/'card_geometry.py',HERE/'card_materials.py',HERE/'ear_groom_weights.py',HERE.parent/'motion_wip/ear_motion.py',HERE.parent/'v5_wip/nib_groom_v5.py']
code={p.name:sha(p) for p in code_files}
for path in code_files:
    block=bpy.data.texts.new('Nib v6 source '+path.name);block.write(path.read_text())
bpy.ops.wm.save_as_mainfile(filepath=str(target),compress=True,relative_remap=False)
if sha(args.source)!=source_hash:raise RuntimeError('Pinned source file changed')
report={'status':'Saved unaccepted groom candidate; actual views and engine verification required',
    'source':str(args.source),'sourceSha256':source_hash,'sourceReportSha256':sha(args.source_report),
    'candidate':str(target),'candidateSha256':sha(target),'representation':args.representation,
    'preRenderGate':source_report['preRenderGate'],'artisticAcceptance':False,
    'removedGroom':removed,'retainedSurfaceHashes':before,'retainedSurfacesUnchanged':True,
    'fineBodyAndFaceFuzz':'Retained unchanged, including all weights and morphs',
    'guideSha256':sha(guide_path),'groups':group_receipts,'geometry':geometry,'earBinding':ear_binding,
    'newGroomTriangles':sum(m['triangles'] for m in geometry),'newGroomCards':sum(m['cards'] for m in geometry),
    'newGroomOpaqueStrands':sum(m['strands'] for m in geometry),
    'materials':atlas['materials'] if args.representation=='runtime' else [],
    'newGroomMaterialSlots':sorted({name for m in geometry for name in m['materials']}),
    'atlasReportSha256':sha(args.output_dir/'groom-atlas.json'),'authoringCode':code,
    'sharedAssetsModified':False,'simulation':False,
    'pending':['Matched Face/Profile/ThreeQuarter/Back and ear closeup; exposed pink membrane/full tawny and cream coverage',
               'Animated eye/goggle/muzzle intrusion and silhouette review',
               'Portable PBR/FBX handoff and actual engine backface/mips/overdraw/VRAM/frame times']}
(args.output_dir/'groom-source.json').write_text(json.dumps(report,indent=2)+'\n',newline='\n')
print('NIB_GROOM_CANDIDATE_SAVED',str(target),flush=True)
