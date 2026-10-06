"""Prepared small cloth-only source study from the pinned actual v9g face file.

No anatomy generation or shared export. Only Scarf is replaced in a new saved
source; all other evaluated mesh coordinates/shape coordinates are preserved.
"""
from pathlib import Path
import sys,hashlib,json,numpy as np
import bpy
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sys.path.insert(0,str(HERE));import scarf_cloth_v4
source=ROOT/'benchmark/art/krag/Krag_Master_v9gFace_WIP.blend'
output=ROOT/'benchmark/art/krag/Krag_ScarfPlacement_v9h_WIP.blend'
expected='2898288570fa840f656986d1b7673cf1daaa5203347c5e65df21e6bd7651d875'
assert hashlib.sha256(source.read_bytes()).hexdigest()==expected
bpy.ops.wm.open_mainfile(filepath=str(source))
rig=bpy.data.objects['Krag_Rig'];saved_action=rig.animation_data.action if rig.animation_data else None
# Bone evaluation is irrelevant while settling against the actual static cages.
if rig.animation_data:rig.animation_data.action=None
for bone in rig.pose.bones:bone.rotation_euler=(0,0,0);bone.location=(0,0,0)

def fingerprint():
    h=hashlib.sha256()
    for obj in sorted((o for o in bpy.data.objects if o.type=='MESH' and o.get('module') and o.get('module')!='Scarf'),key=lambda o:o.name):
        p=np.empty(len(obj.data.vertices)*3,dtype=np.float32);obj.data.vertices.foreach_get('co',p);h.update(obj.name.encode());h.update(p.tobytes())
        if obj.data.shape_keys:
            for key in obj.data.shape_keys.key_blocks:key.data.foreach_get('co',p);h.update(key.name.encode());h.update(p.tobytes())
    return h.hexdigest()
before=fingerprint();old=bpy.data.objects['Scarf'];cloth=old.data.materials[0]
bpy.data.objects.remove(old,do_unlink=True)
def mesh(name,vertices,faces,material,group,bone):
    data=bpy.data.meshes.new(name);data.from_pydata(vertices,[],faces);data.update();data.materials.append(material)
    obj=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(obj);obj['module']=group;obj['rig_bone']=bone
    for p in data.polygons:p.use_smooth=True
    return obj
context={'mesh':mesh,'cloth':cloth,'cages_are_final':True}
scarf=scarf_cloth_v4.build(context);scarf.name='Scarf'
scarf.parent=rig;vg=scarf.vertex_groups.get('Chest') or scarf.vertex_groups.new(name='Chest');vg.add(list(range(len(scarf.data.vertices))),1,'REPLACE')
mod=scarf.modifiers.new('Krag weighted deformation','ARMATURE');mod.object=rig
if saved_action:rig.animation_data.action=saved_action
bpy.context.scene.frame_set(1)
assert fingerprint()==before,'Cloth study changed unrelated geometry/shape coordinates'
for path in [Path(__file__),HERE/'scarf_cloth_v4.py']:
    text=bpy.data.texts.get('v9h_cloth/'+path.name) or bpy.data.texts.new('v9h_cloth/'+path.name);text.clear();text.write(path.read_text(encoding='utf-8'))
bpy.ops.wm.save_as_mainfile(filepath=str(output),compress=True)
assert hashlib.sha256(source.read_bytes()).hexdigest()==expected
report={'status':'Actual isolated cloth source; drape/intersection/pose acceptance requires renders','source':str(source.relative_to(ROOT)),'sourceSha256':expected,'output':str(output.relative_to(ROOT)),'outputSha256':hashlib.sha256(output.read_bytes()).hexdigest(),'unrelatedGeometryAndShapeFingerprintBeforeAndAfter':before,'cloth':context['scarf_cloth_study']}
(ROOT/'benchmark/art/krag/scarf-placement-v9h-result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
print('KRAG isolated scarf source saved; not accepted',flush=True)
