"""Prepared isolated fabric pass on the actual captured-motion anatomical Nib.

V2 sewn-panel source has not been generated. Run only under the allocated
guard; a save is not a cloth/art pass. Old garments remain locally archived.
"""
import argparse,hashlib,json,sys,traceback

# Explicit task-owned exception evidence survives redirected stream failures.
def _report_exception(kind,value,tb):
    path=Path(__file__).resolve().parents[4]/"benchmark/local/nib-garments-v2-python-error.txt"
    path.write_text("".join(traceback.format_exception(kind,value,tb)),encoding="utf8",newline="\n")
    sys.__excepthook__(kind,value,tb)

from pathlib import Path
sys.excepthook=_report_exception
import bpy
import numpy as np
from mathutils import Matrix
from bpy_extras.anim_utils import action_get_channelbag_for_slot

HERE=Path(__file__).parent;ROOT=HERE.parents[3]
sys.path[:0]=[str(HERE),str(HERE.parent),str(ROOT/'benchmark/tools/krag')]
import cloth_patterns as patterns
import fitted_fabric as fabric
import shoulder_straps_v2 as shoulder_straps
import sewn_undershirt_v2
import torso_fabric_v2
from nib_animation import body_correctives
from runtime_reduction import attach_portable_drivers

SOURCE=ROOT/'benchmark/art/animation/nib-human-motion-v5/Nib_HumanMotion_Study_v5.blend'
EXPECTED='b82786d632424fd93b798b1a347aab29e568585ee700ce57b0ab435ee76a10da'
parser=argparse.ArgumentParser();parser.add_argument('--stage',choices=['shirt-straps'],default='shirt-straps')
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
STAGE=args.stage
OUT=ROOT/'benchmark/art/nib/garment-study/v2'
TARGET=OUT/('Nib_ShirtStrapsStudy_v2.blend' if STAGE=='shirt-straps' else 'Nib_GarmentStudy_v1.blend')
REPORT_PATH=OUT/('shirt-straps-source.json' if STAGE=='shirt-straps' else 'source.json')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if sha(SOURCE)!=EXPECTED:raise RuntimeError('Pinned motion/anatomy source changed')
if TARGET.exists():raise RuntimeError('Preserve previous garment study')
OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE),load_ui=False)
scene=bpy.context.scene;rig=bpy.data.objects['Nib_Rig'];collection=bpy.data.collections['Nib_Authored_Components']
if any(name not in rig.data.bones for name in ['ForearmTwist_L','ForearmTwist_R','EarTip_L','EarTip_R']):raise RuntimeError('Expected matching anatomical/ear skeleton')
bind_before={b.name:[list(row) for row in b.matrix_local] for b in rig.data.bones}
def curves():
    result={}
    for action in bpy.data.actions:
        rig.animation_data.action=action;bag=action_get_channelbag_for_slot(action,rig.animation_data.action_slot)
        if bag is None:continue
        rows=[(c.data_path,c.array_index,[(tuple(k.co),tuple(k.handle_left),tuple(k.handle_right),k.interpolation) for k in c.keyframe_points]) for c in bag.fcurves]
        result[action.name]=hashlib.sha256(json.dumps(sorted(rows),separators=(',',':')).encode()).hexdigest()
    return result
curves_before=curves();rig.animation_data.action=None
for track in rig.animation_data.nla_tracks:track.mute=True
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
scene.frame_set(1);bpy.context.view_layer.update()
body=bpy.data.objects['Continuous Nib anatomy organic'];head=bpy.data.objects['Nib v5 fitted animation face']
cage=bpy.data.objects['EDITABLE Nib continuous body control cage']
def retained_geometry():
    result={}
    for obj in collection.objects:
        if obj.type!='MESH' or not (obj.name in ['Continuous Nib anatomy organic','Nib v5 fitted animation face'] or obj.name.startswith(('Nib v5 coherent hand','Ear membrane','Ear outer','Ear inner'))):continue
        digest=hashlib.sha256()
        points=np.empty(len(obj.data.vertices)*3,dtype=np.float32);obj.data.vertices.foreach_get('co',points);digest.update(points.tobytes())
        corners=np.asarray([v for p in obj.data.polygons for v in p.vertices],dtype=np.int32);digest.update(corners.tobytes())
        for uv in obj.data.uv_layers:
            values=np.empty(len(uv.data)*2,dtype=np.float32);uv.data.foreach_get('uv',values);digest.update(values.tobytes())
        if obj.data.shape_keys:
            for key in obj.data.shape_keys.key_blocks:key.data.foreach_get('co',points);digest.update(key.name.encode());digest.update(points.tobytes())
        weights=[[(obj.vertex_groups[g.group].name,g.weight) for g in v.groups] for v in obj.data.vertices]
        digest.update(json.dumps(weights,separators=(',',':')).encode());result[obj.name]=digest.hexdigest()
    if not any(name.startswith('Nib v5 coherent hand') for name in result):raise RuntimeError('Actual retained hands missing from preservation audit')
    return result
retained_before=retained_geometry()
old_shirt=bpy.data.objects['Sleeveless dust undershirt'];old_scarf=bpy.data.objects['Nib v5 layered desert scarf']
shirt_name=old_shirt.name;scarf_name=old_scarf.name
archive=bpy.data.collections.new('PRESERVED pre-refit Nib garments');scene.collection.children.link(archive);archive.hide_render=True;archive.hide_viewport=True
for obj in [old_shirt]:
    collection.objects.unlink(obj);archive.objects.link(obj);obj.hide_render=True;obj.hide_set(True);obj.name='PRESERVED INPUT '+obj.name

pattern=sewn_undershirt_v2.pattern()
fit_report=torso_fabric_v2.fit(pattern,body)
shirt,pin=fabric.create(shirt_name,pattern,collection,old_shirt.data.materials[0])
shirt['bone']='Torso';shirt['variant']='all'
shirt_pattern=shirt.copy();shirt_pattern.data=shirt.data.copy();shirt_pattern.name='EDITABLE fitted undershirt pattern'
archive.objects.link(shirt_pattern);shirt_pattern.hide_render=True;shirt_pattern.hide_set(True)
report={'status':'Isolated fitted fabric source; actual neutral/action/contact review required','source':str(SOURCE),'sourceSha256':EXPECTED,
    'sharedChanged':False,'artisticAcceptance':False,'bodyShapeAndBindChanged':False,'shirt':{'initialFit':fit_report,'patternBoundaryLoops':len(pattern['loops']),'construction':'Sewn front/back panels with narrow shoulder bridges and side seams below axilla'}}
report['shirt']['settle']=fabric.settle(shirt,pin,[body,head],42)
fabric.finish(shirt,.0013);report['shirt']['skin']=torso_fabric_v2.bind(shirt,rig,body)
# Retain actual settled support for light route diagnosis without another solve.
_,support_points,support_triangles=fabric.tree(shirt)
np.savez_compressed(ROOT/'benchmark/local/nib-fitted-shirt-support-v2.npz',
    points=support_points,triangles=support_triangles,source_sha256=EXPECTED,
    cloth_patterns_sha256=sha(HERE/'sewn_undershirt_v2.py'),fabric_sha256=sha(HERE/'fitted_fabric.py'))
report['shirt']['supportCache']='benchmark/local/nib-fitted-shirt-support-v2.npz'

report['newStraps']=[];new_straps=[]
for old in list(collection.objects):
    if old.type!='MESH' or not old.name.startswith('Overalls shoulder strap'):continue
    name=old.name;points_old=np.asarray([tuple(old.matrix_world@v.co) for v in old.data.vertices])
    front=(points_old[:,1]<-.025)&(points_old[:,2]>.86);side=1 if points_old[front,0].mean()>0 else -1
    material=old.data.materials[0];collection.objects.unlink(old);archive.objects.link(old)
    old.hide_render=True;old.hide_set(True);old.name='PRESERVED INPUT '+name
    strap,entry=shoulder_straps.build(name,side,material,collection,rig,body,shirt,bpy.data.objects['Utility belt leather']);report['newStraps'].append(entry);new_straps.append(strap)

prefixes=('Overalls draped bib','Bib sewn chest pocket','Bib pocket flap','Bib stitched outer seam','Bib hand stitching',
    'Strap adjustment buckle','Buckle hollow insert')
report['layers']=[]
for obj in list(collection.objects):
    if obj.type!='MESH' or not obj.name.startswith(prefixes):continue
    rigid=obj.name.startswith(('Strap adjustment buckle','Buckle hollow insert'))
    report['layers'].append(fabric.refit_layer(obj,old_shirt,shirt,body,rig,rigid))

garments=[shirt]+new_straps
report['scarf']={'changed':False,'status':'Original failed scarf retained unchanged; separate authored cowl replacement pending'}
body_correctives(garments);contract=json.loads(scene['deformation_contract'])
for obj in garments:attach_portable_drivers(obj,rig,contract)

if retained_geometry()!=retained_before:raise RuntimeError('Garment study modified retained anatomy/head/hand/ear data')
if bind_before!={b.name:[list(row) for row in b.matrix_local] for b in rig.data.bones}:raise RuntimeError('Garment pass changed rig bind')
if curves_before!=curves():raise RuntimeError('Garment pass changed captured/facial/ear action curves')
report['preserved']={'exactBind':True,'boneCount':len(rig.data.bones),'allActionCurvesSha256':curves_before,
    'headEyesMouthEarsHandsAnatomicalBody':'No mesh edits in this recipe','auditedRetainedMeshHashes':retained_before}
report['garments']={obj.name:{'vertices':len(obj.data.vertices),'triangles':sum(len(p.vertices)-2 for p in obj.data.polygons),
    'boundsMin':np.asarray([v.co[:] for v in obj.data.vertices]).min(axis=0).tolist(),
    'boundsMax':np.asarray([v.co[:] for v in obj.data.vertices]).max(axis=0).tolist()} for obj in garments}
report['authoringCode']={name:sha(HERE/name) for name in ['build_shirt_straps_v2.py','sewn_undershirt_v2.py','torso_fabric_v2.py','cloth_patterns.py','fitted_fabric.py','shoulder_straps_v2.py']}
for name in report['authoringCode']:
    text=bpy.data.texts.new('Nib garment study '+name);text.write((HERE/name).read_text())
rig.animation_data.action=bpy.data.actions['Idle'];scene.frame_set(1)
scene['source_version']='Sewn fitted garment '+STAGE+' v2 on Nib79 captured motion; unaccepted pending source/posed cloth review'
report['stage']=STAGE
bpy.ops.wm.save_as_mainfile(filepath=str(TARGET),compress=True)
if sha(SOURCE)!=EXPECTED:raise RuntimeError('Garment pass changed source file')
report['output']=str(TARGET);report['outputSha256']=sha(TARGET)
REPORT_PATH.write_text(json.dumps(report,indent=2)+'\n',newline='\n')
print('NIB_SEWN_GARMENT_V2_STUDY_SAVED',flush=True)
