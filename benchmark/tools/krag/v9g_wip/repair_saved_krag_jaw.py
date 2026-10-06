"""Prepared isolated patch of a saved Krag continuous head, not an art export.

Requires an explicitly named input/output. Preserves original source, geometry,
morphs, rest rig and acting. Records the actual weight patch and embedded recipe.
"""
from pathlib import Path
import argparse,sys,json,hashlib
import bpy
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sys.path.insert(0,str(HERE));import krag_jaw_domains
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--report',type=Path,required=True);opt=ap.parse_args(args)
if opt.source.resolve()==opt.output.resolve():raise RuntimeError('Jaw repair must preserve its input file')
source_sha=hashlib.sha256(opt.source.read_bytes()).hexdigest();bpy.ops.wm.open_mainfile(filepath=str(opt.source))

def geometry_fingerprint():
    h=hashlib.sha256()
    for obj in sorted((o for o in bpy.data.objects if o.type=='MESH'),key=lambda o:o.name):
        import numpy as np
        h.update(obj.name.encode())
        coords=np.empty(len(obj.data.vertices)*3,dtype=np.float32);obj.data.vertices.foreach_get('co',coords);h.update(coords.tobytes())
        if obj.data.shape_keys:
            for key in obj.data.shape_keys.key_blocks:
                h.update(key.name.encode());key.data.foreach_get('co',coords);h.update(coords.tobytes())
    return h.hexdigest()
before=geometry_fingerprint();modules={o.get('module'):o for o in bpy.data.objects if o.type=='MESH' and o.get('module')}
statistics=krag_jaw_domains.apply(modules)
assert geometry_fingerprint()==before,'Jaw patch modified geometry or morph coordinates'
for path in [Path(__file__),HERE/'krag_jaw_domains.py',krag_jaw_domains.shared_solver()[1]]:
    block=bpy.data.texts.get('semantic_jaw/'+path.name) or bpy.data.texts.new('semantic_jaw/'+path.name)
    block.clear();block.write(path.read_text(encoding='utf-8'))
bpy.ops.wm.save_as_mainfile(filepath=str(opt.output),compress=True)
assert hashlib.sha256(opt.source.read_bytes()).hexdigest()==source_sha
report={'status':'Actual source weights repaired; actual rendered expression/deformation acceptance pending',
    'source':str(opt.source),'sourceSha256':source_sha,'output':str(opt.output),
    'outputSha256':hashlib.sha256(opt.output.read_bytes()).hexdigest(),
    'meshAndShapeCoordinateFingerprintBeforeAndAfter':before,'jawDomain':statistics}
opt.report.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(statistics,indent=2),flush=True)
