"""Isolated v9g wrapper; preserves all frozen v9f authoring source files.

Only the shared continuous face fit/tusks and scarf constructor are replaced in
memory. The firearm module, v9f assembly scale and anatomical rig are unchanged.
"""
from pathlib import Path
import sys,runpy,json,hashlib
import bpy
HERE=Path(__file__).resolve().parent;BASE=HERE.parent
sys.path.insert(0,str(BASE));sys.path.insert(0,str(HERE))
import krag_head_v9,krag_scarf_v3
import face_planes,scarf_cloth
original_fit=krag_head_v9.fit

def fitted(points):
    return face_planes.refine(points,original_fit(points))
krag_head_v9.fit=fitted
original_build=krag_head_v9.build

def head_build(c):
    original_tube=c['tube']
    specs=face_planes.tusk_specification(fitted)
    def tube(name,points,radii,*args,**kwargs):
        if name=='Lower ivory tusk':
            side=1 if points[0][0]>0 else -1
            spec=next(spec for spec in specs if spec['side']==side)
            return original_tube(name,spec['points'],spec['radii'],*args,**kwargs)
        return original_tube(name,points,radii,*args,**kwargs)
    c['tube']=tube
    try:return original_build(c)
    finally:c['tube']=original_tube
krag_head_v9.build=head_build
krag_scarf_v3.build=scarf_cloth.build
state=runpy.run_path(str(BASE/'build_krag.py'),run_name='__main__')
# Append exact isolated patch sources before the final saved-source hash exists.
for filename in ['build_v9g.py','face_planes.py','scarf_cloth.py']:
    path=HERE/filename;block=bpy.data.texts.get('v9g_wip/'+filename) or bpy.data.texts.new('v9g_wip/'+filename)
    block.clear();block.write(path.read_text(encoding='utf-8'))
contract_path=state['OUT']/'krag_asset_contract.json';contract=json.loads(contract_path.read_text())
contract['isolatedSourceStudy']={'version':'v9g','status':'Generated source study; not accepted or promoted',
    'frozenBaseRecipe':'benchmark/art/krag/v9f-prepared-recipe.json',
    'changes':['Common continuous facial fit and visible curved tusks','Physically settled asymmetrical broad scarf'],
    'weaponModuleChanged':False,'headProportionScaleChanged':False,
    'patches':{f:hashlib.sha256((HERE/f).read_bytes()).hexdigest() for f in ['build_v9g.py','face_planes.py','scarf_cloth.py']}}
if state.get('scarf_cloth_study'):contract['scarfClothStudy']=state['scarf_cloth_study']
contract_path.write_text(json.dumps(contract,indent=2)+'\n',encoding='utf-8',newline='\n')
bpy.ops.wm.save_as_mainfile(filepath=str(state['MASTER_PATH']),compress=True)
print('KRAG v9g isolated source study saved; no export or acceptance',flush=True)
