"""Fit scarf over united anatomy and remove polygon-quantized lid pigment."""
import bpy,math,json,hashlib,sys,ast,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];ART=ROOT/'benchmark/art/nib';TOOLS=Path(__file__).parent
sys.path.insert(0,str(TOOLS));from nib_animation import body_correctives,wire_drivers
archive=ART/'versions/v4-prepatch';archive.mkdir(parents=True,exist_ok=True)
for name in ['Nib_Master.blend','source-report.json']:
    if not (archive/name).exists():shutil.copy2(ART/name,archive/name)
for capture in (ART/'renders').glob('*'):
    if capture.is_file() and not (archive/capture.name).exists():shutil.copy2(capture,archive/capture.name)
bpy.ops.wm.open_mainfile(filepath=str(ART/'Nib_Master.blend'))
scene=bpy.context.scene;rig=bpy.data.objects['Nib_Rig'];collection=bpy.data.collections['Nib_Authored_Components']
for obj in collection.objects:
    if obj.get('bone')=='FaceSurface':
        for polygon in obj.data.polygons:polygon.material_index=0
old=bpy.data.objects['Draped desert scarf'];data=old.data;bpy.data.objects.remove(old,do_unlink=True)
if data.users==0:bpy.data.meshes.remove(data)
source=(TOOLS/'create_nib.py').read_text();context={'bpy':bpy,'math':math,'COL':collection,'OBJECTS':[],'VARIANT_PARTS':{},'CLOTH':bpy.data.materials['Nib_Cloth']}
for node in ast.parse(source).body:
    if isinstance(node,ast.FunctionDef) and node.name in ['own','shade','apply','uv']:
        exec(compile(ast.Module(body=[node],type_ignores=[]),str(TOOLS/'create_nib.py'),'exec'),context)
a=source.index('# Broad desert scarf');b=source.index("print('NIB_STAGE clothing'",a);exec(source[a:b],context)
scarf=context['o'];scarf.parent=rig;scarf.vertex_groups.new(name='Chest').add(list(range(len(scarf.data.vertices))),1.0,'REPLACE');scarf.modifiers.new('Nib deformation','ARMATURE').object=rig
body_correctives([scarf]);wire_drivers(rig,[scarf],json.loads(scene['deformation_contract']))
scene['source_version']='v4b fitted scarf and continuous neutral eyelids review candidate'
bpy.ops.wm.save_as_mainfile(filepath=str(ART/'Nib_Master.blend'),compress=True)
report=json.loads((ART/'source-report.json').read_text());report['sourceVersion']=scene['source_version'];report['sourceSha256']=hashlib.sha256((ART/'Nib_Master.blend').read_bytes()).hexdigest();report['nativeCompressed']=True
report['patchSha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();report['currentReproductionCodeSha256']={name:hashlib.sha256((TOOLS/name).read_bytes()).hexdigest() for name in ['create_nib.py','nib_face.py','nib_animation.py','nib_anatomy.py']}
(ART/'source-report.json').write_text(json.dumps(report,indent=2));print('NIB_V4_PATCH_SAVED '+report['sourceSha256'],flush=True)
