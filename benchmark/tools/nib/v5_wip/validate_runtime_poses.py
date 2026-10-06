"""Read-only pose comparison for every changed runtime component, including fur."""
import bpy, json, hashlib, sys, gc
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(Path(__file__).parent))
sys.path.insert(0,str(ROOT/'benchmark/tools/krag'))
from posed_skin_check import collect_poses,compare_posed_skin
from runtime_reduction import correspondence,statistics
ART=ROOT/'benchmark/art/nib';SOURCE=ART/'Nib_Master.blend';DERIVED=ART/'Nib_Runtime_Optimized_v4b.blend'
REPORT=ART/'v5-study/runtime-posed-validation-v4b.json'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
reduction=json.loads((ART/'v5-study/runtime-reduction-v4b.json').read_text())
assert sha(SOURCE)==reduction['sourceSha256']
assert sha(DERIVED)==reduction['candidateSha256']
bpy.ops.wm.open_mainfile(filepath=str(DERIVED),load_ui=False)
rig=bpy.data.objects['Nib_Rig'];contract=json.loads(bpy.context.scene['deformation_contract'])
samples=collect_poses(rig,contract)
changed=[entry for entry in reduction['components'] if entry['runtimeTriangles']<entry['sourceTriangles']]
names=tuple(entry.get('module',entry.get('name')) for entry in changed)
derived={name:bpy.data.objects[name] for name in names}
with bpy.data.libraries.load(str(SOURCE),link=False) as (available,requested):requested.objects=list(names)
originals=list(requested.objects)
report={'sourceSha256':reduction['sourceSha256'],'candidateSha256':reduction['candidateSha256'],
        'method':'Every changed component, 23 actual authored action poses, up to 4000 fixed-rest surface correspondences per component; linear blend skinning and portable morph drivers.',
        'limitMeters':.0035,'passed':False,'components':[]}
def authored_world(obj):
    # Appended, unlinked objects do not have evaluated matrix_world caches.
    # Reconstruct their authored object hierarchy, excluding armature skinning
    # (which the comparison applies explicitly), before detaching the copy.
    if obj.parent is None:return obj.matrix_basis.copy()
    if obj.parent_type!='OBJECT':raise RuntimeError('Unexpected non-object source parenting')
    return authored_world(obj.parent)@obj.matrix_parent_inverse@obj.matrix_basis
for name,original in zip(names,originals):
    print('NIB_POSE_COMPARE',name,flush=True)
    source_world=authored_world(original);original.parent=None;original.matrix_world=source_world
    item=compare_posed_skin(original,derived[name],rig,samples,correspondence,statistics,sample_count=4000,raise_on_failure=False)
    item['name']=name;report['components'].append(item);REPORT.write_text(json.dumps(report,indent=2))
    data=original.data;bpy.data.objects.remove(original,do_unlink=True)
    if data.users==0:bpy.data.meshes.remove(data)
    gc.collect()
report['maxMeters']=max(item['maxMeters'] for item in report['components'])
report['passed']=all(item['passed'] for item in report['components'])
REPORT.write_text(json.dumps(report,indent=2))
if not report['passed']:raise RuntimeError('At least one changed component exceeded the 3.5 mm posed-surface comparison limit')
print('NIB_ALL_CHANGED_COMPONENT_POSES_PASS',report['maxMeters'],flush=True)
