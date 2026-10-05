"""Remeasure an unchanged derivative with corrected barycentric precision.

Read-only Blender job. Does not regenerate the candidate or alter shared files.
"""
import bpy,json,hashlib,sys
from pathlib import Path
import numpy as np
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).parent))
from runtime_reduction import coordinates,triangles,correspondence,statistics

ROOT=Path(__file__).resolve().parents[3];ART=ROOT/'benchmark/art/krag'
sys.path.insert(0,str(ROOT/'benchmark/tools/nib/v5_wip'))
from posed_skin_check import collect_poses,compare_posed_skin
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
source=ART/'Krag_Runtime.blend';candidate=ART/'Krag_Runtime_Optimized_v7.blend'
old=json.loads((ART/'runtime-reduction-v7.json').read_text())
contract=json.loads((ART/'runtime-candidate-v7.contract.json').read_text())
assert sha(source)==old['sourceRuntimeSha256'] and sha(candidate)==old['candidateSha256']
bpy.ops.wm.open_mainfile(filepath=str(source),load_ui=False)
rig=bpy.data.objects['Krag_Rig'];original={o.get('module'):o for o in bpy.data.objects if o.type=='MESH' and 'module' in o}
samples=collect_poses(rig,contract['deformation'])
names={obj.name for obj in original.values()}
with bpy.data.libraries.load(str(candidate),link=False) as (available,loaded):loaded.objects=[name for name in available.objects if name in names]
derived={obj.get('module'):obj for obj in loaded.objects if obj is not None and obj.type=='MESH'}
report={'status':'In progress; read-only corrected measurement','sourceSha256':sha(source),'candidateSha256':sha(candidate),
        'helperSha256':sha(Path(__file__).parent/'runtime_reduction.py'),'modules':[],'artisticAcceptance':False,'passed':True}
target=ART/'runtime-reduction-v7-precision-recheck.json'
for previous in old['modules']:
    if not previous.get('reduced'):continue
    group=previous['module'];a,b=original[group],derived[group]
    sv=coordinates(a.data.shape_keys.key_blocks['Basis'].data);dv=coordinates(b.data.shape_keys.key_blocks['Basis'].data);tri=triangles(b.data)
    selected=np.unique(np.linspace(0,len(sv)-1,min(16000,len(sv)),dtype=np.int32))
    tree=BVHTree.FromPolygons(dv.tolist(),tri.tolist(),all_triangles=True)
    ids,weights,distance=correspondence(tree,dv,tri,sv[selected])
    entry={'module':group,'morphs':{},'sourceToDerivedSurfaceError':statistics(distance)}
    for shape in list(a.data.shape_keys.key_blocks)[1:]:
        sd=coordinates(shape.data)-sv;dd=coordinates(b.data.shape_keys.key_blocks[shape.name].data)-dv
        error=np.linalg.norm(np.einsum('ijk,ij->ik',dd[ids],weights)-sd[selected],axis=1)
        metric=statistics(error);entry['morphs'][shape.name]=metric
        if metric['maxMeters']>(.001 if group=='Head' else .0015):report['passed']=False
    entry['posedSkinComparison']=compare_posed_skin(a,b,rig,samples,correspondence,statistics,max_error=.0025 if group=='Head' else .004,raise_on_failure=False)
    report['passed'] &= entry['posedSkinComparison']['passed'];report['modules'].append(entry)
    target.write_text(json.dumps(report,indent=2),newline='\n');print('PRECISION RECHECK',group,entry['posedSkinComparison']['maxMeters'],flush=True)
report['status']='Corrected-precision remeasurement passed' if report['passed'] else 'Corrected-precision remeasurement failed; candidate remains unchanged'
target.write_text(json.dumps(report,indent=2),newline='\n')
if not report['passed']:raise RuntimeError('Corrected derivative checks failed; inspect '+str(target))
