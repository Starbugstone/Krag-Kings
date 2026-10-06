"""Bounded exterior tusk-crown fit on the actual v9le source."""
from pathlib import Path
import sys,json,hashlib
import numpy as np
import bpy
from mathutils import Matrix
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];ART=ROOT/'benchmark/art/krag'
sys.path.insert(0,str(HERE));import tusk_exterior_fit
SOURCE=ART/'Krag_MandibleTusks_v9le_WIP.blend';OUTPUT=ART/'Krag_CrownFit_v9lf_WIP.blend'
EXPECTED='6fb2ef32e092b2924359dc9857727606b35e41d9fe8ae5497c61c807308115a7'
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==EXPECTED
if OUTPUT.exists():raise RuntimeError('Refusing to overwrite an actual mandibular study')
bpy.ops.wm.open_mainfile(filepath=str(SOURCE));rig=bpy.data.objects['Krag_Rig'];rig.animation_data.action=None
for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update();modules={o.get('module'):o for o in bpy.data.objects if o.type=='MESH'and 'module'in o}
head=modules['Head'];mesh=head.data;keys=mesh.shape_keys.key_blocks;n=len(mesh.vertices)
def unrelated_fingerprint():
    digest=hashlib.sha256()
    for obj in sorted((o for o in bpy.data.objects if o.type=='MESH'and o.get('module') and o!=modules['Face']),key=lambda o:o.name):
        coords=np.empty(len(obj.data.vertices)*3,dtype=np.float32);obj.data.vertices.foreach_get('co',coords);digest.update(obj.name.encode());digest.update(coords.tobytes())
        if obj.data.shape_keys:
            for key in obj.data.shape_keys.key_blocks:key.data.foreach_get('co',coords);digest.update(key.name.encode());digest.update(coords.tobytes())
    for bone in rig.data.bones:digest.update(bone.name.encode());digest.update(np.asarray(bone.matrix_local,dtype=np.float64).tobytes())
    for action in sorted(bpy.data.actions,key=lambda a:a.name):
        digest.update(action.name.encode())
        for layer in action.layers:
            for strip in layer.strips:
                for slot in action.slots:
                    bag=strip.channelbag(slot)
                    if bag:
                        for curve in bag.fcurves:
                            digest.update(curve.data_path.encode());digest.update(str(curve.array_index).encode())
                            for key in curve.keyframe_points:digest.update(np.asarray(key.co,dtype=np.float64).tobytes())
    return digest.hexdigest()
before=unrelated_fingerprint()
tusk_report=tusk_exterior_fit.apply(head,modules['Face'])
assert unrelated_fingerprint()==before,'Mandibular/tusk study modified unrelated geometry/bind/action data'
for path in [Path(__file__),HERE/'tusk_exterior_fit.py']:
    block=bpy.data.texts.new('v9lf_crown_fit/'+path.name);block.write(path.read_text())
rig.animation_data.action=bpy.data.actions['Idle'];bpy.context.scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT),compress=True)
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==EXPECTED
result={'status':'Actual exterior crown fit; neutral and open-mouth profile review required','artisticAcceptance':False,'sharedPromotion':False,
 'input':{'path':SOURCE.relative_to(ROOT).as_posix(),'sha256':EXPECTED},'source':{'path':OUTPUT.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(OUTPUT.read_bytes()).hexdigest()},
 'tusks':tusk_report,'preservedOtherGeometryBindActions':before,
 'knownUnchangedFailures':['Actual tusk emergence/contact still requires neutral/open profile review','Cowl still has regular U-bib folds','Brow, glabella, facial skin and armor/clothing likeness'],
 'preserved':['True oral bag and lip margins','Upper face and ocular geometry','Lower-neck transition','All mesh coordinates except fitted tusk crowns; complete Head and unrelated ocular shape coordinates verified exact','Body bind and actions','Current weapon','Shared exports']}
(ART/'crown-fit-v9lf.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n')
print('KRAG v9lf exterior crown fit source saved; actual silhouette and expression review required',flush=True)
