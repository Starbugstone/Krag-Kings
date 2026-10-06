"""Isolated profile/gum/Jaw study based on the unchanged v9f authoring recipe."""
from pathlib import Path
import sys,runpy,json,hashlib
import numpy as np
import bpy
HERE=Path(__file__).resolve().parent;BASE=HERE.parent
sys.path.insert(0,str(BASE));sys.path.insert(0,str(BASE/'v9g_wip'));sys.path.insert(0,str(HERE))
import krag_head_v9,krag_face,profile_fit,krag_jaw_domains
original_fit=krag_head_v9.fit

def fitted(points):return profile_fit.refine(points,original_fit(points))
krag_head_v9.fit=fitted
original_build=krag_head_v9.build

def head_build(c):
    original_tube=c['tube'];specs=profile_fit.tusk_specification(fitted)
    def tube(name,points,radii,*args,**kwargs):
        if name=='Lower ivory tusk':
            side=1 if points[0][0]>0 else -1;spec=next(s for s in specs if s['side']==side)
            return original_tube(name,spec['points'],spec['radii'],*args,**kwargs)
        return original_tube(name,points,radii,*args,**kwargs)
    c['tube']=tube;c['tusk_gum_study']=specs
    try:return original_build(c)
    finally:c['tube']=original_tube
krag_head_v9.build=head_build
original_weights=krag_face.face_weights;original_delta=krag_face.continuous_face_delta
jaw_mask=None;jaw_statistics=None

def face_weights(modules):
    global jaw_mask,jaw_statistics
    original_weights(modules);jaw_statistics=krag_jaw_domains.apply(modules)
    head=modules['Head'];group=head.vertex_groups['Jaw'];jaw_mask=np.zeros(len(head.data.vertices))
    for vertex in head.data.vertices:
        for entry in vertex.groups:
            if entry.group==group.index:jaw_mask[vertex.index]=entry.weight

def face_delta(raw,name):
    delta=original_delta(raw,name)
    if name=='JawOpen':
        if jaw_mask is None or len(jaw_mask)!=len(raw):raise RuntimeError('Jaw corrective lacks corresponding semantic support')
        delta=delta*jaw_mask[:,None]
    return delta
krag_face.face_weights=face_weights;krag_face.continuous_face_delta=face_delta
state=runpy.run_path(str(BASE/'build_krag.py'),run_name='__main__')
patches=[Path(__file__),HERE/'profile_fit.py',BASE/'v9g_wip/krag_jaw_domains.py',krag_jaw_domains.shared_solver()[1]]
for path in patches:
    name='v9h_study/'+path.name;block=bpy.data.texts.get(name) or bpy.data.texts.new(name)
    block.clear();block.write(path.read_text(encoding='utf-8'))
contract_path=state['OUT']/'krag_asset_contract.json';contract=json.loads(contract_path.read_text())
contract['isolatedSourceStudy']={'version':'v9h-profile-jaw','status':'Generated source study; likeness/pose acceptance pending',
    'baseRecipe':'benchmark/art/krag/v9f-prepared-recipe.json',
    'changes':['Remove beaked brow/chin fit peaks; broader bounded connected profile','Tusk roots on actual lower gum and crown through true lip aperture','Audited semantic Jaw weights and mandibular-only JawOpen corrective support'],
    'unchanged':['Whole-head scale','Body/hand rig','Weapon module','Preserved failed v9f scarf','Serious character acting'],
    'patches':{str(p.relative_to(state['ROOT'])).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in patches}}
contract['semanticJawStudy']=jaw_statistics;contract['tuskGumStudy']=state['tusk_gum_study']
contract_path.write_text(json.dumps(contract,indent=2)+'\n',encoding='utf-8',newline='\n')
(state['ART']/(state['MASTER_PATH'].stem+'-jaw-domain-verification.json')).write_text(json.dumps(jaw_statistics,indent=2)+'\n',encoding='utf-8',newline='\n')
bpy.ops.wm.save_as_mainfile(filepath=str(state['MASTER_PATH']),compress=True)
print('KRAG v9h profile/gum/Jaw study saved; no acceptance or export',flush=True)
