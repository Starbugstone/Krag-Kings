"""Bounded mandibular mass and actual gum/lip tusks on the v9md cowl source."""
from pathlib import Path
import sys,json,hashlib
import numpy as np
import bpy
from mathutils import Matrix
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];ART=ROOT/'benchmark/art/krag'
sys.path.insert(0,str(HERE));import mandibular_planes,tusk_eruption
SOURCE=ART/'Krag_Cowl_v9md_WIP.blend';OUTPUT=ART/'Krag_MandibleTusks_v9le_WIP.blend'
EXPECTED='15ff55dbe5d1e81564601e0c703d9d6b2d1b84e90fd0ce1612f23d9c4f82681a'
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==EXPECTED
if OUTPUT.exists():raise RuntimeError('Refusing to overwrite an actual mandibular study')
bpy.ops.wm.open_mainfile(filepath=str(SOURCE));rig=bpy.data.objects['Krag_Rig'];rig.animation_data.action=None
for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update();modules={o.get('module'):o for o in bpy.data.objects if o.type=='MESH'and 'module'in o}
head=modules['Head'];mesh=head.data;keys=mesh.shape_keys.key_blocks;n=len(mesh.vertices)
def unrelated_fingerprint():
    digest=hashlib.sha256()
    for obj in sorted((o for o in bpy.data.objects if o.type=='MESH'and o.get('module') and o not in [head,modules['Face']]),key=lambda o:o.name):
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
raw=np.empty(n*3,dtype=np.float32);mesh.attributes['krag_reference_position'].data.foreach_get('vector',raw);raw=raw.reshape(-1,3)
points=np.asarray([tuple(v.co)for v in keys['Basis'].data]);faces=[tuple(p.vertices)for p in mesh.polygons]
sets=np.asarray([v.value for v in mesh.attributes['.sculpt_face_set'].data]);edges=np.asarray([tuple(e.vertices)for e in mesh.edges])
delta,report=mandibular_planes.refine(raw,points,faces,sets,edges)
for key in keys:
    prior=np.asarray([tuple(v.co)for v in key.data]);key.data.foreach_set('co',(prior+delta).astype(np.float32).ravel())
mesh.vertices.foreach_set('co',(points+delta).astype(np.float32).ravel());mesh.update()
if mesh.has_custom_normals:mesh.normals_split_custom_set([(0.,0.,0.)]*len(mesh.loops));mesh.update()
tusk_report=tusk_eruption.apply(head,modules['Face'],modules['MouthInterior'],json.loads((ART/'mouth-anatomy-v9j.json').read_text())['oralGeometry']['tuskRootTargets'])
assert unrelated_fingerprint()==before,'Mandibular/tusk study modified unrelated geometry/bind/action data'
for path in [Path(__file__),HERE/'mandibular_planes.py',HERE/'geodesic_planes.py',HERE/'tusk_eruption.py']:
    block=bpy.data.texts.new('v9le_mandible_tusks/'+path.name);block.write(path.read_text())
rig.animation_data.action=bpy.data.actions['Idle'];bpy.context.scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT),compress=True)
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==EXPECTED
result={'status':'Actual bounded mandibular source; profile, neutral and open-mouth review required','artisticAcceptance':False,'sharedPromotion':False,
 'input':{'path':SOURCE.relative_to(ROOT).as_posix(),'sha256':EXPECTED},'source':{'path':OUTPUT.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(OUTPUT.read_bytes()).hexdigest()},
 'mandible':report,'tusks':tusk_report,'preservedOtherGeometryBindActions':before,
 'knownUnchangedFailures':['Actual tusk emergence/contact still requires neutral/open profile review','Cowl still has regular U-bib folds','Brow, glabella, facial skin and armor/clothing likeness'],
 'preserved':['True oral bag and lip margins','Upper face and ocular geometry','Lower-neck transition','All mesh coordinates except Head and rebuilt tusks; unrelated ocular shape coordinates verified exact','Body bind and actions','Current weapon','Shared exports']}
(ART/'mandible-tusks-v9le.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n')
print('KRAG v9le mandible/tusks source saved; actual silhouette and expression review required',flush=True)
