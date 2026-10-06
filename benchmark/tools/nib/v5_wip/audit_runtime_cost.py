"""Read-only cost audit of pinned Nib master; does not save or export it."""
import bpy, json, hashlib
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
SOURCE=ROOT/'benchmark/art/nib/Nib_Master.blend'
OUT=ROOT/'benchmark/art/nib/v5-study/runtime-cost-audit.json'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE),load_ui=False)
items=[]
for obj in bpy.data.objects:
    if obj.type!='MESH' or obj.get('bone') is None:continue
    mesh=obj.data;mesh.calc_loop_triangles()
    entry={'name':obj.name,'boneTag':obj.get('bone'),'variant':obj.get('variant','all'),
           'vertices':len(mesh.vertices),'triangles':len(mesh.loop_triangles),
           'shapeCount':len(mesh.shape_keys.key_blocks)-1 if mesh.shape_keys else 0,
           'furStrands':obj.get('fur_strands',0),
           'materialSlots':[m.name for m in mesh.materials],
           'modifiers':[m.type for m in obj.modifiers]}
    items.append(entry)
items.sort(key=lambda x:x['triangles'],reverse=True)
totals={}
for item in items:
    key=item['boneTag'];totals[key]=totals.get(key,0)+item['triangles']
report={'sourceSha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        'status':'Source-component audit, includes mutually exclusive variants; not a runtime benchmark.',
        'components':items,'trianglesByBoneTag':dict(sorted(totals.items(),key=lambda x:-x[1]))}
OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2))
print(json.dumps({'components':len(items),'largest':items[:20],'trianglesByBoneTag':report['trianglesByBoneTag']},indent=2),flush=True)
# The library animation head's named/face-set regions may identify original ear
# topology precisely. Append this one base object for read-only metadata only.
library=ROOT/'benchmark/art/reference-anatomy/blender-studio-human-base-meshes/source/human-base-meshes-bundle-v1.4.1/human_base_meshes_bundle.blend'
with bpy.data.libraries.load(str(library),link=False) as (available,requested):
    requested.objects=['GEO-head_animation_realistic']
head=requested.objects[0]
details={'object':head.name,'attributes':[],'materials':[m.name for m in head.data.materials]}
for attribute in head.data.attributes:
    entry={'name':attribute.name,'domain':attribute.domain,'dataType':attribute.data_type}
    if attribute.data_type=='INT':entry['values']=[d.value for d in attribute.data]
    details['attributes'].append(entry)
(OUT.parent/'head-topology-attributes.json').write_text(json.dumps(details,indent=2))
print('REFERENCE_HEAD_ATTRIBUTES',[a['name'] for a in details['attributes']],flush=True)
