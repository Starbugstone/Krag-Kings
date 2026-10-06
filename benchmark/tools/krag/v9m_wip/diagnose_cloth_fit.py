"""One read-only failed-fit attribution using the exact frozen v9m recipe.

No limit is changed, no simulation runs after a failed placement gate, and no
Blender source is saved. Instruments the initial skin-contact fit locally.
"""
from pathlib import Path
import sys,json,hashlib,types
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];ART=ROOT/'benchmark/art/krag'
sys.path.insert(0,str(HERE))
original=(HERE/'scarf_cloth_v5.py').read_text();script=(HERE/'build_neck_scarf.py').read_text()
expected={'scarf_cloth_v5.py': '8232b492dc7d0b5844ae8a0dbd94d24715bb42eb6462c171a70e45c8148080c6', 'build_neck_scarf.py': 'c7a410f187cf0bdc713d8bd694f0bea9609a10deaa8cd989ad0f7db1428b9263'}
for name,digest in expected.items():assert hashlib.sha256((HERE/name).read_bytes()).hexdigest()==digest
instrumented=original.replace('adjusted=0;max_adjustment=0.','adjusted=0;max_adjustment=0.;contact_records=[]')
instrumented=instrumented.replace('original=vertex.co.copy()','original=vertex.co.copy();steps=[]')
instrumented=instrumented.replace('for tree in bvhs:\n            point,normal,index,distance=tree.find_nearest(vertex.co)', 'for collider_index,tree in enumerate(bvhs):\n            start=vertex.co.copy()\n            point,normal,index,distance=tree.find_nearest(vertex.co)')
instrumented=instrumented.replace('if signed<.006 and distance<.055:vertex.co=point+normal*.006',"if signed<.006 and distance<.055:vertex.co=point+normal*.006\n            steps.append({'collider':colliders[collider_index].name,'start':list(start),'nearest':list(point),'normal':list(normal),'distance':distance,'signed':signed,'after':list(vertex.co),'triangle':int(index)})")
instrumented=instrumented.replace('d=(vertex.co-original).length','d=(vertex.co-original).length\n        contact_records.append({\'vertex\':vertex.index,\'patternRow\':vertex.index//29,\'patternColumn\':vertex.index%29,\'start\':list(original),\'final\':list(vertex.co),\'adjustmentMeters\':d,\'steps\':steps})')
instrumented=instrumented.replace("if max_adjustment>.055:raise RuntimeError", "if max_adjustment>.055:\n        from pathlib import Path\n        records=sorted(contact_records,key=lambda r:r['adjustmentMeters'],reverse=True)\n        report={'status':'Actual bounded-fit attribution; failure retained, no source saved','maximumAdjustmentMeters':max_adjustment,'unchangedBoundMeters':.055,'worstPoints':records[:20],'radialFitCount':fitted_count,'maximumRadialFitMeters':max_radial_fit,'shoulderLiftCount':lifted_count,'maximumShoulderLiftMeters':max_vertical_fit}\n        (Path(__file__).resolve().parents[3]/'art/krag/anatomy-study/scarf-initial-fit-v9m-failure.json').write_text(json.dumps(report,indent=2)+'\\n',newline='\\n')\n        raise RuntimeError")
instrumented=instrumented.replace('    # The saved editable pattern',"    raise RuntimeError('Read-only diagnostic stops before simulation')\n    # The saved editable pattern")
module=types.ModuleType('scarf_cloth_v5');module.__file__=str(HERE/'scarf_cloth_v5.py');exec(compile(instrumented,module.__file__,'exec'),module.__dict__);sys.modules['scarf_cloth_v5']=module
scope={'__file__':str(HERE/'build_neck_scarf.py'),'__name__':'__main__'}
try:exec(compile(script,scope['__file__'],'exec'),scope)
except Exception:
    report={'status':'Actual in-memory neck repair passed before unchanged cloth failure; no source or render saved','inputSha256':'3639a7fbbba1b81d5749658ba6db924020fbe6ea1e47cfd71c445cd05f04a297','neck':scope.get('neck'),'resolvedMouthRays':scope.get('resolved'),'remainingMouthRays':scope.get('failed'),'frozenRecipe':{name:hashlib.sha256((HERE/name).read_bytes()).hexdigest()for name in ['scarf_cloth_v5.py','build_neck_scarf.py']}}
    (ART/'anatomy-study/neck-in-memory-v9m-failure.json').write_text(json.dumps(report,indent=2)+'\n',newline='\n')
    raise
