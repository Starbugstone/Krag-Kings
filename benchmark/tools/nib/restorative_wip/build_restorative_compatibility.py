"""Prepared isolated variant compatibility after anatomical hand migration.

Requires root's final wrap-source hash at execution. Natural anatomy, natural
hands, new wraps, all rest bones and all actions must remain bitwise unchanged.
No shared asset is written. Cuff, hand and posed variant reviews are mandatory.
"""
import argparse,hashlib,json,sys
from pathlib import Path
import bpy
from mathutils import Matrix

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path[:0] = [str(HERE),str(HERE.parent/'motion_wip'),str(ROOT/'benchmark/tools/krag')]
from contracts import rig_contract,surface_hash
from partition_body import derive
from refit_mechanical_digits import refit
from runtime_reduction import attach_portable_drivers

parser = argparse.ArgumentParser()
parser.add_argument('--source',type=Path,required=True)
parser.add_argument('--source-sha256',required=True)
parser.add_argument('--output-dir',type=Path,required=True)
args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
if sha(args.source) != args.source_sha256:
    raise RuntimeError('Pinned final coherent input changed')
if not args.output_dir.resolve().is_relative_to((ROOT/'benchmark/art/nib').resolve()):
    raise RuntimeError('Owned isolated source output required')
target = args.output_dir/'Nib_Coherent_RestorativeCompatibility_v1.blend'
report_path = args.output_dir/'source.json'
if target.exists() or report_path.exists():
    raise RuntimeError('Preserve earlier restorative compatibility output')
args.output_dir.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(args.source),load_ui=False)
scene = bpy.context.scene
rig = bpy.data.objects['Nib_Rig']
collection = bpy.data.collections['Nib_Authored_Components']
canonical = ['Idle','Walk','Run','Melee','Shoot','Hit','FacePerformance']
if any(n not in bpy.data.actions for n in canonical):
    raise RuntimeError('Input saved source lost a canonical action')
for name in canonical:
    bpy.data.actions[name].use_fake_user = True
rig_before = rig_contract(rig)
rig.animation_data.action = None
for track in rig.animation_data.nla_tracks:
    track.mute = True
for bone in rig.pose.bones:
    bone.matrix_basis = Matrix.Identity(4)
scene.frame_set(1)
bpy.context.view_layer.update()
semantic_report_path = ROOT/'benchmark/art/nib/motion-study/semantic-body-v2/source.json'
semantic = json.loads(semantic_report_path.read_text())
body = bpy.data.objects['Continuous Nib anatomy organic']
fuzz = bpy.data.objects['Fine skin fuzz organic']
if surface_hash(body) != semantic['bodyPayloadSha256'] or surface_hash(fuzz) != semantic['fuzzPayloadSha256']:
    raise RuntimeError('Input differs from reviewed semantic Natural Body/fuzz')
if rig_before != semantic['preservedRig']:
    raise RuntimeError('Input is not the exact current migrated bind/action contract')
changed_names = {o.name for o in collection.objects
                 if o.get('variant')=='grip' and o.name.startswith((
                     'Articulated replacement finger','Replacement finger hinge','Restorative thumb'))}
before = {o.name:surface_hash(o) for o in bpy.data.objects
          if o.type=='MESH' and o.name not in changed_names}
new_parts, partition_report = derive(rig,ROOT,collection,attach_portable_drivers)
mechanical_parts, mechanical_report = refit(rig,collection,ROOT)
if {o.name for o in mechanical_parts} != changed_names:
    raise RuntimeError('Mechanical mutation scope differs from planned parts')
archive = bpy.data.collections.get('PRESERVED Nib pre-coherent restorative surfaces')
if archive is None:
    archive = bpy.data.collections.new('PRESERVED Nib pre-coherent restorative surfaces')
    scene.collection.children.link(archive)
for name in ['Continuous Nib anatomy grip','Fine skin fuzz grip']:
    obj = bpy.data.objects[name]
    collection.objects.unlink(obj)
    archive.objects.link(obj)
    obj.hide_render = True
    obj.hide_set(True)
archive.hide_render = True
archive.hide_viewport = True
for name,digest in before.items():
    if surface_hash(bpy.data.objects[name]) != digest:
        raise RuntimeError('Restorative pass changed retained surface '+name)
if rig_contract(rig) != rig_before:
    raise RuntimeError('Restorative pass changed bind/actions')
candidate_hashes = {o.name:surface_hash(o) for o in new_parts+mechanical_parts}
for obj in collection.objects:
    show = obj.get('variant','all') in ['all','organic','natural']
    obj.hide_render = not show
    obj.hide_set(not show)
rig.animation_data.action = bpy.data.actions['Idle']
scene.frame_set(1)
scene['nib_restorative_compatibility'] = json.dumps({
    'sourceSha256':args.source_sha256,'naturalBodyUnchanged':True,
    'leftForearmPartition':'original source face set12',
    'leftMechanicalDigits':'Refitted to existing migrated anatomical rest joints',
    'rigAndActionsUnchanged':True,'artisticAcceptance':False})
scene['source_version'] = 'Coherent Nib restorative compatibility v1; inherited art failures and actual variant checks pending'
for name in ['build_restorative_compatibility.py','partition_body.py','surface_subset.py','refit_mechanical_digits.py']:
    block = bpy.data.texts.new('Nib restorative compatibility v1 '+name)
    block.write((HERE/name).read_text())
bpy.ops.wm.save_as_mainfile(filepath=str(target),compress=True)
bpy.ops.wm.open_mainfile(filepath=str(target),load_ui=False)
rig = bpy.data.objects['Nib_Rig']
if rig_contract(rig) != rig_before or any(n not in bpy.data.actions for n in canonical):
    raise RuntimeError('Saved restorative source lost bind/action contract')
for name,digest in {**before,**candidate_hashes}.items():
    if surface_hash(bpy.data.objects[name]) != digest:
        raise RuntimeError('Saved source changed mesh payload '+name)
if sha(args.source) != args.source_sha256:
    raise RuntimeError('Input source changed')
report = {'status':'Actual saved/reopened restorative compatibility candidate; posed review required',
          'source':str(args.source),'sourceSha256':args.source_sha256,
          'candidate':str(target),'candidateSha256':sha(target),
          'semanticReferenceReportSha256':sha(semantic_report_path),
          'preservedRig':rig_before,'retainedMeshHashes':before,
          'candidateMeshHashes':candidate_hashes,'partition':partition_report,
          'mechanicalDigits':mechanical_report,'savedSourceReopened':True,
          'savedCanonicalActionsPresent':canonical,'artisticAcceptance':False,
          'sharedChanged':False,'codeSha256':{p.name:sha(p) for p in HERE.glob('*.py')},
          'pending':['Actual cuff retained-skin/metal interface','Neutral/curl/Shoot restorative hand contact',
                     'Raised-arm axilla and neutral-shirt contact defects remain',
                     'Coordinated face/ear/groom likeness and cloth refinement','Matching all-clip mesh/FBX exports']}
report_path.write_text(json.dumps(report,indent=2)+'\n',newline='\n')
print('NIB_RESTORATIVE_COMPATIBILITY_SAVED_AND_REOPENED',flush=True)
