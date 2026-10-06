"""One frozen, isolated Natural target stage per guarded native process."""
import argparse,json,runpy,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];sys.path.insert(0,str(HERE))
from strand_contract import sha
p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--stage',required=True);a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
plan=json.loads(a.plan.read_text());stage=plan['stages'][a.stage]
def verify(entries):
    for row in entries:
        if sha(ROOT/row['path'])!=row['sha256']:raise RuntimeError('Pinned filtered-target input changed '+row['path'])
verify(plan['pins']);base=ROOT/plan['outputRoot'];receipt=base/'receipts'/(a.stage+'.json')
if receipt.exists():raise RuntimeError('Preserve prior filtered-target stage')
def invoke(relative,args,blender=True):
    script=ROOT/relative;sys.argv=[str(script)]+(['--']if blender else[])+[str(v)for v in args];runpy.run_path(str(script),run_name='__main__')
checked=set()
def dependency(name):
    if name in checked:return
    for ancestor in plan['stages'][name]['dependencies']:dependency(ancestor)
    old=json.loads((base/'receipts'/(name+'.json')).read_text())
    if old['planSha256']!=sha(a.plan):raise RuntimeError('Previous output belongs to another frozen plan')
    verify(old['outputs']);checked.add(name)
for name in stage['dependencies']:dependency(name)
for relative in stage.get('freshOutputs',[]):
    if (base/relative).exists():raise RuntimeError('Prior pilot output exists '+relative)
source_dir=base/'source';source=source_dir/'Nib_NativeGroom_FilteredTarget_PBR.blend';report=source_dir/'source.json';snapshot=base/'source-contract.json';reference=base/'reference';final=base/'triangulated';textures=ROOT/plan['textureDirectory']
if a.stage=='source':
    invoke('benchmark/tools/nib/native_groom_wip/prepare_filtered_target.py',['--source',ROOT/plan['source'],'--source-sha256',plan['sourceSha256'],'--groom-report',ROOT/plan['groomReport'],'--groom-report-sha256',plan['groomReportSha256'],'--output-dir',source_dir])
elif a.stage=='snapshot':
    invoke('benchmark/tools/unreal/nib_candidate/snapshot_source.py',['--source',source,'--source-sha256',json.loads(report.read_text())['candidateSha256'],'--output',snapshot])
elif a.stage in ['reference','triangles']:
    args=['--source',source,'--source-report',report,'--out',reference if a.stage=='reference'else final,'--texture-dir',textures,'--card-texture-dir',textures,'--baseline-dir',reference,'--variants','natural','--reuse-animations-from',ROOT/plan['animationReuseDirectory']]
    if a.stage=='triangles':args+=['--triangulate']
    invoke('benchmark/tools/nib/export_nib.py',args)
    if a.stage=='triangles':
        contract=json.loads(snapshot.read_text());manifest=json.loads((final/'manifest.json').read_text())
        if manifest['sourceSha256']!=contract['sourceSha256']or [v['name']for v in manifest['variants']]!=['Nib_Natural']:raise RuntimeError('Filtered Natural export identity differs')
        contract['bindReference']={'file':'Nib_Natural.fbx','sha256':sha(final/'Nib_Natural.fbx')}
        if set(contract['clips'])!=set(manifest['animations']):raise RuntimeError('Filtered pilot lost canonical clips')
        for name,clip in contract['clips'].items():clip.update(file=manifest['animations'][name],sha256=sha(final/manifest['animations'][name]))
        (final/'export.json').write_text(json.dumps(contract,indent=2)+'\n',newline='\n')
        source_report=json.loads(report.read_text())
        for material in manifest['materials']:
            for channel in ['baseColor','normal','roughness','metallic']:
                path=final/material[channel]
                if sha(path)!=source_report['textureHashes'][path.name]:raise RuntimeError('Filtered pilot changed PBR map '+path.name)
elif a.stage=='payload':
    invoke('benchmark/tools/nib/v5_wip/validate_triangulated_payload.py',['--source-dir',reference,'--candidate-dir',final,'--names','Nib_Natural','--output',base/'payload-validation.json'],blender=False)
    from check_binding_mask import compare
    mask=compare(reference/'Nib_Natural.fbx',final/'Nib_Natural.fbx',json.loads(report.read_text()))
    (base/'binding-mask-validation.json').write_text(json.dumps(mask,indent=2)+'\n',newline='\n')
elif a.stage=='variant':
    invoke('benchmark/tools/unreal/nib_candidate/validate_variant.py',['--directory',final,'--source-contract',snapshot,'--variant','Nib_Natural','--output',base/'variant-validation.json'])
elif a.stage=='clips':
    invoke('benchmark/tools/animation/validate_motion_candidate.py',['--directory',final])
else:raise RuntimeError('Unknown filtered-target stage')
verify(plan['pins']);outputs=[]
for relative in stage['outputs']:
    path=base/relative
    for file in sorted(path.rglob('*'))if path.is_dir()else[path]:
        if file.is_file():outputs.append({'path':file.relative_to(ROOT).as_posix(),'sha256':sha(file),'bytes':file.stat().st_size})
receipt.parent.mkdir(parents=True,exist_ok=True);receipt.write_text(json.dumps({'stage':a.stage,'planSha256':sha(a.plan),'outputs':outputs,'artisticAcceptance':False,'engineImported':False,'sharedChanged':False},indent=2)+'\n',newline='\n')
print('NIB_NATIVE_FILTERED_STAGE_COMPLETE '+a.stage,flush=True)
