"""Isolated atlas comparison on unchanged, already fitted Nib groom geometry."""
import argparse, hashlib, json, os, sys
from pathlib import Path
import bpy

HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE),str(HERE.parent/'nib/restorative_wip')]
from contracts import rig_contract, surface_hash
import nib_fur_atlas_study

p=argparse.ArgumentParser()
p.add_argument('--source',type=Path,required=True)
p.add_argument('--source-sha256',required=True)
p.add_argument('--output',type=Path,required=True)
p.add_argument('--validate-existing',action='store_true',
               help='Read-only recovery of a saved candidate after a validation-only failure')
a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
if sha(a.source)!=a.source_sha256:raise RuntimeError('Pinned source changed')
if a.output.exists() and not a.validate_existing:raise RuntimeError('Preserve previous groom comparison')
source_report=a.source.parent/'source.json'
inherited=json.loads(source_report.read_text(encoding='utf-8'))
if inherited['candidateSha256']!=a.source_sha256:raise RuntimeError('Source receipt mismatch')
a.output.mkdir(parents=True,exist_ok=a.validate_existing)
atlas=(json.loads((a.output/'groom-atlas.json').read_text()) if a.validate_existing
       else nib_fur_atlas_study.generate(a.output/'textures'))
saved_input=(a.output/'Nib_Coherent_FineStrands_v1.blend')
saved_input_hash=sha(saved_input) if a.validate_existing else None
if a.validate_existing and (a.output/'source.json').exists():
    raise RuntimeError('Preserve previous completed verification')
bpy.ops.wm.open_mainfile(filepath=str(a.source),load_ui=False)
rig=bpy.data.objects['Nib_Rig'];before=rig_contract(rig)
surfaces={o.name:surface_hash(o) for o in bpy.data.objects if o.type=='MESH'}
scene=bpy.context.scene
contract=json.loads(scene['nib_groom_material_contract'])
if contract!=atlas['materials']:raise RuntimeError('Atlas changed material names, UV convention or portable render fields')
changed=[]
for entry in atlas['materials']:
    material=bpy.data.materials.get(entry['name'])
    if material is None:raise RuntimeError('Original groom material missing')
    expected={Path(entry[channel]).name for channel in ['baseColor','normal','roughness','metallic']}
    seen=set()
    for node in material.node_tree.nodes:
        if node.type!='TEX_IMAGE' or node.image is None:continue
        name=node.image.filepath.replace('\\','/').rsplit('/',1)[-1]
        if name not in expected:raise RuntimeError('Unexpected card texture '+name)
        old=node.image
        new=bpy.data.images.load(str(a.output/'textures'/name),check_existing=True)
        new.colorspace_settings.name=old.colorspace_settings.name
        new.alpha_mode=old.alpha_mode
        node.image=new;seen.add(name)
        changed.append({'material':material.name,'map':name,'sha256':sha(a.output/'textures'/name)})
    if seen!=expected:raise RuntimeError('Not all expected card maps were replaced')
# Resolve while the old scene path is active, then save relative to the new
# file with remapping disabled. Reopen and decode every connected image below.
materials={m for obj in bpy.data.collections['Nib_Authored_Components'].objects
           if obj.type=='MESH' for m in obj.data.materials if m}
images={node.image for material in materials if material.use_nodes
        for node in material.node_tree.nodes if node.type=='TEX_IMAGE' and node.image}
expected_images={}
for image in images:
    if image.source!='FILE' or image.packed_file:continue
    absolute=Path(bpy.path.abspath(image.filepath,library=image.library)).resolve()
    if not absolute.is_file():raise RuntimeError('Missing source material image '+image.name)
    expected_images[image.name]={'path':str(absolute),'sha256':sha(absolute),
                                 'colorSpace':image.colorspace_settings.name}
    image.filepath='//'+os.path.relpath(absolute,a.output).replace('\\','/')
for name in ['Idle','Walk','Run','Melee','Shoot','Hit','FacePerformance']:
    bpy.data.actions[name].use_fake_user=True
scene['nib_fine_atlas_study']='Finer independent fibers; same card geometry and coverage regions; unaccepted'
output=a.output/'Nib_Coherent_FineStrands_v1.blend'
if not a.validate_existing:
    bpy.ops.wm.save_as_mainfile(filepath=str(output),compress=True,relative_remap=False)
bpy.ops.wm.open_mainfile(filepath=str(output),load_ui=False)
if rig_contract(bpy.data.objects['Nib_Rig'])!=before:raise RuntimeError('Saved source changed rig/actions')
for name,digest in surfaces.items():
    if surface_hash(bpy.data.objects[name])!=digest:raise RuntimeError('Saved source changed mesh '+name)
decoded=[]
for name,expected in expected_images.items():
    image=bpy.data.images[name]
    path=Path(bpy.path.abspath(image.filepath,library=image.library)).resolve()
    if path!=Path(expected['path']) or sha(path)!=expected['sha256']:
        raise RuntimeError('Reopened image path/content changed '+name)
    if image.colorspace_settings.name!=expected['colorSpace']:
        raise RuntimeError('Reopened image color space changed '+name)
    image.reload()
    lazy_before=bool(image.has_data)
    dimensions=list(image.size) # Request lazy pixel loading before checking has_data.
    if not image.has_data or min(dimensions)<=0:raise RuntimeError('Reopened image failed decode '+name)
    decoded.append({'name':name,'dimensions':dimensions,'hasDataBeforeSizeRequest':lazy_before,
                    'hasDataAfterSizeRequest':bool(image.has_data),**expected})
if sha(a.source)!=a.source_sha256:raise RuntimeError('Input changed')
if saved_input_hash and sha(output)!=saved_input_hash:raise RuntimeError('Read-only verification changed candidate')
report={'status':'Actual unchanged-geometry atlas candidate; matched native views required',
        'source':str(a.source),'sourceSha256':a.source_sha256,
        'candidate':str(output),'candidateSha256':sha(output),'savedSourceReopened':True,
        'readOnlyValidationRecovery':a.validate_existing,
        'generationRecipeHashes':{p.name:sha(p) for p in (a.output/'generation-recipe').glob('*')}
             if a.validate_existing else None,
        'preservedRig':before,'retainedMeshHashes':surfaces,'changedCardMaps':changed,
        'reopenedImages':decoded,'preRenderGate':inherited['preRenderGate'],
        'numericEvidence':inherited['numericEvidence'],
        'sourceReportSha256':sha(source_report),'atlasReportSha256':sha(a.output/'groom-atlas.json'),
        'recipeHashes':{p.name:sha(p) for p in [Path(__file__),Path(nib_fur_atlas_study.__file__)]},
        'artisticAcceptance':False,'sharedChanged':False,'engineExported':False}
(a.output/'source.json').write_text(json.dumps(report,indent=2)+'\n')
print('NIB_FINE_FUR_ATLAS_SAVED_AND_REOPENED',flush=True)
