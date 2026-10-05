"""Record recipes for the already verified v7 bake only if its source/maps are unchanged."""
import bpy,sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent));from material_cache import recipe,sha
ROOT=Path(__file__).resolve().parents[3];ART=ROOT/'benchmark/art/krag';OUT=ROOT/'benchmark/shared/characters/krag';TEX=OUT/'textures'
receipt=json.loads((ART/'v7-bake-receipt.json').read_text());source=ART/'Krag_Master.blend'
assert sha(source)==receipt['sourceSha256'],'Current master differs from recorded bake source; cannot seed this cache.'
for file,h in receipt['mapHashes'].items():assert sha(TEX/file)==h,'Baked map changed: '+file
bpy.ops.wm.open_mainfile(filepath=str(source));contract=json.loads((OUT/'krag_asset_contract.json').read_text());entries={}
for mat in bpy.data.materials:
    if mat.name in contract['material_maps']:
        maps=contract['material_maps'][mat.name];entries[mat.name]={'recipeHash':recipe(mat),'maps':maps,'mapHashes':{c:sha(TEX/f) for c,f in maps.items()}}
(ART/'material-cache.json').write_text(json.dumps({'schemaVersion':1,'sourceBlendSha256':receipt['sourceSha256'],'materials':entries},indent=2));print('VERIFIED MATERIAL CACHE SEEDED',len(entries),flush=True)
