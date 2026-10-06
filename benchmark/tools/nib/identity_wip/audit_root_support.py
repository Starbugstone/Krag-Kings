"""Read-only attribution of the failed card-root support normal gate."""
import argparse, hashlib, json, sys
from pathlib import Path
import bpy
from mathutils import Matrix, Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
from fit_card_roots import surface_tree
parser=argparse.ArgumentParser()
parser.add_argument('--source',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
if args.output.exists():raise RuntimeError('Preserve previous root support audit')
root=Path(__file__).resolve().parents[4]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
digest=sha(args.source)
if digest!='09da9c1eb51eabd0402fc1ed52b3d4b07f53a5a74150810796a2b04169d8c88e':raise RuntimeError('Pinned input differs')
bpy.ops.wm.open_mainfile(filepath=str(args.source),load_ui=False)
rig=bpy.data.objects['Nib_Rig'];rig.animation_data.action=None
for track in rig.animation_data.nla_tracks:track.mute=True
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
bpy.context.scene.frame_set(1);bpy.context.view_layer.update()
collection=bpy.data.collections['Nib_Authored_Components']
trees={'Head':surface_tree([bpy.data.objects['Nib v5 fitted animation face']])};trees['Jaw']=trees['Head']
for side in ['L','R']:
    trees['Ear_'+side]=surface_tree([o for o in collection.objects if o.type=='MESH' and o.get('bone')=='Ear_'+side and o.name.startswith(('Fennec cupped ear','Ear inner velvet'))])
guides=json.loads((root/'benchmark/art/nib/groom-study/coherent79-v2-runtime-wide-nap/groom-guides.json').read_text())['groups']
groups=[]
for group in guides:
    tree=trees[group['bone']];failures=[];minimum=1.
    for index,guide in enumerate(group['guides']):
        point=Vector(guide['root']);normal=Vector(guide['normal'])
        hit,n,face,distance=tree.find_nearest(point)
        dot=n.dot(normal) if hit else -1.;minimum=min(minimum,dot)
        if hit is None or distance>.006 or dot<.4:
            ray_hit,ray_n,ray_face,ray_distance=tree.ray_cast(point+normal*.010,-normal,.022)
            failures.append({'index':index,'root':list(point),'guideNormal':list(normal),'nearestPoint':list(hit) if hit else None,
                'nearestNormal':list(n) if n else None,'distanceMeters':distance,'normalDot':dot,
                'orientedRayPoint':list(ray_hit) if ray_hit else None,'orientedRayNormalDot':float(ray_n.dot(normal)) if ray_n else None,
                'orientedRayRootDistanceMeters':float((ray_hit-point).length) if ray_hit else None})
    groups.append({'region':group['region'],'bone':group['bone'],'guides':len(group['guides']),'minimumNormalDot':minimum,'failureCount':len(failures),'failures':failures})
report={'status':'Actual saved-source read-only root support attribution','sourceSha256':digest,'groups':groups,'scriptSha256':sha(Path(__file__)),'sharedChanged':False}
args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2)+'\n',newline='\n')
if sha(args.source)!=digest:raise RuntimeError('Read-only attribution changed input')
print(json.dumps([{k:v for k,v in g.items() if k!='failures'} for g in groups],indent=2))
print('NIB_ROOT_SUPPORT_AUDIT_COMPLETE',flush=True)
