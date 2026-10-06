"""Prepared isolated root attachment on existing card topology and atlas.

Preserves face/ears/body/hand geometry, every bind/action and the existing
portable material contract. This is not the later regional fur-flow redesign.
"""
import argparse,hashlib,json,sys
from pathlib import Path
import bpy,numpy as np
from mathutils import Matrix

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sys.path[:0]=[str(HERE),str(HERE.parent/'restorative_wip'),str(HERE.parent/'v5_wip')]
from fit_card_roots import repair,surface_tree
from contracts import rig_contract,surface_hash
from nib_groom_v5 import configure_goggle_envelopes

parser=argparse.ArgumentParser()
parser.add_argument('--source',type=Path,required=True);parser.add_argument('--source-sha256',required=True)
parser.add_argument('--output-dir',type=Path,required=True)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if sha(args.source)!=args.source_sha256:raise RuntimeError('Pinned coherent source changed')
if args.output_dir.exists():raise RuntimeError('Preserve previous root-attachment output')
if not args.output_dir.resolve().is_relative_to((ROOT/'benchmark/art/nib/groom-study').resolve()):raise RuntimeError('Owned isolated groom output required')
args.output_dir.mkdir(parents=True)
guide_path=ROOT/'benchmark/art/nib/groom-study/coherent79-v2-runtime-wide-nap/groom-guides.json'
groom_report_path=guide_path.parent/'groom-source.json';groom_report=json.loads(groom_report_path.read_text())
if sha(guide_path)!=groom_report['guideSha256']:raise RuntimeError('Existing guide provenance changed')
guides=json.loads(guide_path.read_text())['groups'];inherited=json.loads((args.source.parent/'source.json').read_text())
if inherited['candidateSha256']!=args.source_sha256:raise RuntimeError('Source receipt differs')
bpy.ops.wm.open_mainfile(filepath=str(args.source),load_ui=False)
scene=bpy.context.scene;rig=bpy.data.objects['Nib_Rig'];collection=bpy.data.collections['Nib_Authored_Components']
canonical=['Idle','Walk','Run','Melee','Shoot','Hit','FacePerformance']
for n in canonical:
    if n not in bpy.data.actions:raise RuntimeError('Input lost canonical action '+n)
    bpy.data.actions[n].use_fake_user=True
contract=rig_contract(rig);card_names={'Nib v6 cards '+g['region'] for g in guides}
if any(name not in collection.objects for name in card_names):raise RuntimeError('Expected actual guide/card groups are absent')
retained={o.name:surface_hash(o) for o in bpy.data.objects if o.type=='MESH' and o.name not in card_names}
material_contract=str(scene['nib_groom_material_contract'])
rig.animation_data.action=None
for track in rig.animation_data.nla_tracks:track.mute=True
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
scene.frame_set(1);bpy.context.view_layer.update();configure_goggle_envelopes(collection)
trees={'Head':surface_tree([bpy.data.objects['Nib v5 fitted animation face']])}
trees['Jaw']=trees['Head']
for side in ['L','R']:
    surfaces=[o for o in collection.objects if o.type=='MESH' and o.get('bone')=='Ear_'+side and o.name.startswith(('Fennec cupped ear','Ear inner velvet'))]
    if len(surfaces)!=2:raise RuntimeError('Expected one outer and inner anatomical ear surface')
    trees['Ear_'+side]=surface_tree(surfaces)
def fixed_fields(obj):
    return {'faces':[list(p.vertices) for p in obj.data.polygons],
            'uv':{u.name:[list(v.uv) for v in u.data] for u in obj.data.uv_layers},
            'weights':[[(g.group,g.weight) for g in v.groups] for v in obj.data.vertices],
            'groups':[g.name for g in obj.vertex_groups],'materials':[m.name for m in obj.data.materials],
            'matrix':[list(r) for r in obj.matrix_world]}
results=[]
for group in guides:
    obj=bpy.data.objects['Nib v6 cards '+group['region']];fixed=fixed_fields(obj)
    results.append(repair(obj,group['guides'],trees[group['bone']]))
    if fixed_fields(obj)!=fixed:raise RuntimeError('Card root repair altered atlas UVs, topology, materials or weights')
    obj['root_attachment_study']='First two rows fit actual skin; 0.5mm root burial, crossing ramps from zero; unaccepted'
for name,digest in retained.items():
    if surface_hash(bpy.data.objects[name])!=digest:raise RuntimeError('Root attachment changed unrelated mesh '+name)
if rig_contract(rig)!=contract:raise RuntimeError('Root attachment changed bind/actions')
if str(scene['nib_groom_material_contract'])!=material_contract:raise RuntimeError('Root attachment changed portable atlas contract')
changed={name:surface_hash(bpy.data.objects[name]) for name in card_names}
scene['source_version']='Coherent card-root attachment v1; existing atlas and guide tips; unaccepted'
scene['nib_groom_root_attachment']=json.dumps({'sourceSha256':args.source_sha256,'guideSha256':sha(guide_path),'materialContractUnchanged':True,'artisticAcceptance':False})
for path in [Path(__file__),HERE/'fit_card_roots.py']:
    text=bpy.data.texts.new('Nib root attachment v1 '+path.name);text.write(path.read_text())
rig.animation_data.action=bpy.data.actions['Idle'];scene.frame_set(1)
target=args.output_dir/'Nib_Coherent_RootedGroom_v1.blend';bpy.ops.wm.save_as_mainfile(filepath=str(target),compress=True)
bpy.ops.wm.open_mainfile(filepath=str(target),load_ui=False)
if rig_contract(bpy.data.objects['Nib_Rig'])!=contract:raise RuntimeError('Saved groom source changed rig/actions')
for name,digest in {**retained,**changed}.items():
    if surface_hash(bpy.data.objects[name])!=digest:raise RuntimeError('Saved source changed mesh payload '+name)
if str(bpy.context.scene['nib_groom_material_contract'])!=material_contract:raise RuntimeError('Saved material contract changed')
if sha(args.source)!=args.source_sha256:raise RuntimeError('Input changed')
report={'status':'Actual isolated card-root attachment; source closeups still required','source':str(args.source),
    'sourceSha256':args.source_sha256,'candidate':str(target),'candidateSha256':sha(target),'savedSourceReopened':True,
    'preservedRig':contract,'retainedMeshHashes':retained,'changedCardHashes':changed,'groups':results,
    'guideSha256':sha(guide_path),'atlasSourceReportSha256':sha(groom_report_path),'materialContractUnchanged':True,
    'preRenderGate':inherited['preRenderGate'],'numericEvidence':inherited['numericEvidence'],
    'inheritedFaceReportSha256':sha(args.source.parent/'source.json'),
    'codeSha256':{p.name:sha(p) for p in [Path(__file__),HERE/'fit_card_roots.py']},
    'artisticAcceptance':False,'sharedChanged':False,
    'pending':['Actual Neutral/EyeCloseup attachment comparison using unchanged atlas','Recorded lens-bound root exceptions',
               'Regional guide flow/coverage and cream/tawny atlas refinement','Full adult face/ear/cloth and deformation quality']}
(args.output_dir/'source.json').write_text(json.dumps(report,indent=2)+'\n',newline='\n')
print('NIB_ROOTED_CARDS_SAVED_AND_REOPENED',flush=True)
