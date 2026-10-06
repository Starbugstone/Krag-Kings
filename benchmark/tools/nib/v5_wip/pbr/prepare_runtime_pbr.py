"""Prepare an isolated portable PBR derivative of a reviewed v5 source.

Run under Run-HeavyTask, never while another heavy job runs.
An actual source-vs-baked render and engine import remain required afterward.
"""
import argparse,hashlib,json,shutil,sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Matrix
sys.path.insert(0,str(Path(__file__).parent))
from bake_fields import bake_maps,head_mask_receipt,make_face_uv,plane,portable_material,sha,uv_field_audit,source_uv_domain
from portable_save import save_and_validate_pbr
from bake_ocular import bake_actual_irises
from groom_source_images import verify_card_source_images

ROOT=Path(__file__).resolve().parents[5]
parser=argparse.ArgumentParser()
parser.add_argument('--source',type=Path,required=True)
parser.add_argument('--source-report',type=Path,required=True)
parser.add_argument('--out',type=Path,required=True)
parser.add_argument('--reference-textures',type=Path,default=ROOT/'benchmark/shared/characters/nib/textures')
parser.add_argument('--card-texture-dir',type=Path,help='Original masked groom atlas; preserve its RGBA coverage and shared map names')
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
if not args.out.resolve().is_relative_to((ROOT/'benchmark/local/candidates').resolve()):
    raise RuntimeError('Prepared PBR outputs must remain under isolated local/candidates')
source_hash=sha(args.source);source_report=json.loads(args.source_report.read_text())
reported_source=(source_report.get('candidateSha256') or source_report.get('outputSha256') or source_report.get('sourceSha256'))
if reported_source!=source_hash:raise RuntimeError('Saved source/report hashes do not match')
if any(args.out.glob('*.blend')):raise RuntimeError('Choose a fresh candidate directory; an earlier bake is already present')
args.out.mkdir(parents=True,exist_ok=True);textures=args.out/'textures';textures.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(args.source))
scene=bpy.context.scene;collection=bpy.data.collections['Nib_Authored_Components'];rig=bpy.data.objects['Nib_Rig']
saved_action=rig.animation_data.action;saved_frame=scene.frame_current
rig.animation_data.action=None
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
scene.frame_set(1);bpy.context.view_layer.update()
source_objects=[o for o in collection.objects if o.type=='MESH']
visibility={o.name:(o.hide_get(),o.hide_render) for o in source_objects}
card_entries=json.loads(scene.get('nib_groom_material_contract','[]'))
card_contract={entry['name']:entry for entry in card_entries}
if len(card_contract)!=len(card_entries):raise RuntimeError('Duplicate groom material contract')
card_agreements={}
# Reject a stale supplied atlas before the expensive face/iris field bakes.
for material in {m for obj in source_objects for m in obj.data.materials if m is not None}:
    if material.name not in card_contract:
        if material.get('portableAlphaMode')=='MASK':
            raise RuntimeError('Masked surface lacks groom scene contract '+material.name)
        continue
    record=card_contract[material.name]
    if (record.get('alphaMode')!='MASK' or record.get('alphaSource')!='baseColor.a'
        or not 0<float(record.get('alphaClipThreshold',0))<1):
        raise RuntimeError('Invalid masked groom atlas contract '+material.name)
    if args.card_texture_dir is None:raise RuntimeError('Actual masked groom requires --card-texture-dir')
    card_agreements[material.name]=verify_card_source_images(material,record,args.card_texture_dir)
for obj in source_objects:obj.hide_set(True);obj.hide_render=True
def immutable_geometry(obj):
    records={}
    arrays={'Mesh':obj.data.vertices}
    if obj.data.shape_keys:arrays.update({'Key:'+k.name:k.data for k in obj.data.shape_keys.key_blocks})
    for name,array in arrays.items():
        values=np.empty(len(array)*3,dtype=np.float32);array.foreach_get('co',values)
        records[name]=hashlib.sha256(values.tobytes()).hexdigest()
    records['polygons']=hashlib.sha256(np.array([v for p in obj.data.polygons for v in p.vertices],dtype=np.int32).tobytes()).hexdigest()
    records['weights']=hashlib.sha256(repr([[(g.group,g.weight) for g in v.groups] for v in obj.data.vertices]).encode()).hexdigest()
    return records
before={obj.name:immutable_geometry(obj) for obj in source_objects}
head=next(o for o in source_objects if o.get('bone')=='FaceSurface')
report={'status':'PBR derivative requires actual matched render and both-engine verification; no art acceptance implied',
        'source':str(args.source),'sourceSha256':source_hash,'sourceReportSha256':sha(args.source_report),
        'sourceStructuralGate':source_report.get('preRenderGate'),
        'normalConvention':'OpenGL +Y tangent space','materials':[],'fieldBakes':[],
        'codeSha256':{p.name:sha(p) for p in [Path(__file__),Path(__file__).with_name('bake_fields.py'),Path(__file__).with_name('bake_ocular.py'),Path(__file__).with_name('groom_source_images.py'),Path(__file__).with_name('portable_save.py')]}}
mask=head_mask_receipt(head)
source_materials=list(head.data.materials);head.data.materials.clear()
for original in source_materials:
    copied=original.copy();copied.name=original.name+'_BakeEvaluation';head.data.materials.append(copied)
source_uv=make_face_uv(head)
atlas_name='Nib_v5_FacialSkinAtlas';maps=bake_maps(head,atlas_name,textures,{'BaseColor':4096,'Normal':4096,'Roughness':1024,'Metallic':128})
atlas=portable_material(atlas_name,textures,maps,source_materials[0])
head.data.materials.clear();head.data.materials.append(atlas)
for polygon in head.data.polygons:polygon.material_index=0
head.data.uv_layers.remove(head.data.uv_layers[source_uv])
head.data.uv_layers.active=head.data.uv_layers['UVMap'];head.data.uv_layers['UVMap'].active_render=True
head['runtime_uv_atlas']=True;head.hide_render=True;head.hide_set(True)
report['fieldBakes'].append({'material':atlas_name,'mode':'actual face geometry + source attribute',
                            'mask':mask,'maps':maps,'uv':'Fresh packed UVMap; original shader UV isolated during bake, then removed to keep export UV0 correct',
                            'reviewRequired':'Nose pigment, eyelids, lip edge and UV seams in same-camera source/baked render'})
baked_names={atlas_name}
iris_bakes=bake_actual_irises(source_objects,textures,source_report)
report['fieldBakes'].extend(iris_bakes)
baked_names.update(entry['material'] for entry in iris_bakes)
region_names=['Nib_v5_HeadFur','Nib_v5_InnerEarWisps','Nib_v5_TawnyEarFur',
              'Nib_v5_DustyPinkEar','Nib_v5_TawnyEarUndercoat','Nib_OcularGlobe','Nib_OcularIris',
              'Nib_IdentityOcularGlobe']
assigned_materials={m for obj in source_objects for m in obj.data.materials if m is not None}
for name in region_names:
    original=bpy.data.materials.get(name)
    if original not in assigned_materials:continue
    audit=uv_field_audit(original);domain=source_uv_domain(source_objects,original)
    copied=original.copy();copied.name=name+'_BakeEvaluation'
    carrier=plane(copied)
    maps=bake_maps(carrier,name,textures,{'BaseColor':1024,'Normal':512,'Roughness':512,'Metallic':128})
    original.name=name+'_ProceduralSource';runtime=portable_material(name,textures,maps,original)
    assignments=0
    for obj in source_objects:
        for slot in obj.material_slots:
            if slot.material==original:slot.material=runtime;assignments+=1
    geometry=carrier.data;bpy.data.objects.remove(carrier,do_unlink=True);bpy.data.meshes.remove(geometry)
    if copied.users==0:bpy.data.materials.remove(copied)
    baked_names.add(name)
    report['fieldBakes'].append({'material':name,'mode':'Exact UV-domain field on carrier; strand UVs untouched',
                                'shaderAudit':audit,'sourceUvDomain':domain,'maps':maps,'assignedSlots':assignments,
                                'reviewRequired':'Same root-to-tip/clump color and regional separation on actual geometry'})

used={m for obj in source_objects for m in obj.data.materials if m is not None}
for material in sorted(used,key=lambda m:m.name):
    if material.name in card_contract:
        record=dict(card_contract[material.name])
        record['sourceImageAgreement']=verify_card_source_images(material,record,args.card_texture_dir)
        if record['sourceImageAgreement']!=card_agreements[material.name]:
            raise RuntimeError('Source groom image binding changed during field bakes')
        for key in ['baseColor','normal','roughness','metallic']:
            relative=Path(record[key])
            if relative.is_absolute() or len(relative.parts)!=2 or relative.parts[0]!='textures':
                raise RuntimeError('Groom map must be textures/filename '+str(relative))
            original=args.card_texture_dir/relative.name;target=args.out/relative
            if not original.is_file():raise RuntimeError('Missing original groom map '+str(original))
            if original.resolve()!=target.resolve():shutil.copy2(original,target)
            if sha(original)!=sha(target):raise RuntimeError('Groom atlas copy changed bytes')
        record['mode']='Original masked atlas copied byte-identically, including unassociated coverage alpha'
        record['mapHashes']={key:sha(args.out/record[key]) for key in ['baseColor','normal','roughness','metallic']}
        report['materials'].append(record)
        continue
    if material.get('portableAlphaMode')=='MASK':raise RuntimeError('Masked surface lacks groom scene contract '+material.name)
    record={'name':material.name}
    for channel,key in [('BaseColor','baseColor'),('Normal','normal'),('Roughness','roughness'),('Metallic','metallic')]:
        filename=material.name+'_'+channel+'.png';target=textures/filename
        if material.name not in baked_names:
            original=args.reference_textures/filename
            if not original.exists():raise RuntimeError('Unbaked material lacks explicit PBR map: '+str(original))
            shutil.copy2(original,target)
        if not target.exists():raise RuntimeError('Missing generated map '+str(target))
        record[key]='textures/'+filename
    record['mapHashes']={key:sha(args.out/record[key]) for key in ['baseColor','normal','roughness','metallic']}
    report['materials'].append(record)
for material in list(bpy.data.materials):
    if material.users==0:bpy.data.materials.remove(material)
for obj in source_objects:
    if immutable_geometry(obj)!=before[obj.name]:raise RuntimeError('PBR process changed geometry, weights or morphs: '+obj.name)
    obj.hide_set(visibility[obj.name][0]);obj.hide_render=visibility[obj.name][1]
rig.animation_data.action=saved_action;scene.frame_set(saved_frame);bpy.context.view_layer.update()
report['geometryWeightsMorphsUnchanged']=True
scene['portable_pbr_bake']=json.dumps(report)
target=args.out/'Nib_Runtime_PBR.blend'
report['savedPbrImageValidation']=save_and_validate_pbr(target,report)
if sha(args.source)!=source_hash:raise RuntimeError('Input source changed')
report['candidateSha256']=sha(target);report['candidate']=str(target)
(args.out/'pbr-bake-report.json').write_text(json.dumps(report,indent=2)+'\n',newline='\n')
print('NIB_V5_PBR_BAKE_COMPLETE',flush=True)
