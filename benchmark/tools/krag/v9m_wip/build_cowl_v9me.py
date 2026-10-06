"""Prepare returned folds on an explicitly hashed actual Krag source.

The v9ma source already removed the duplicated high Body neck. This source
changes only Scarf, preserving all other vertex/shape coordinates, rig binds,
and authored body action curves. The actual opened chin is measured again.
"""
from pathlib import Path
import sys,json,hashlib,argparse
import numpy as np
import bpy
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];ART=ROOT/'benchmark/art/krag'
sys.path.insert(0,str(HERE));import neck_composition,scarf_authored_v9me
parser=argparse.ArgumentParser();parser.add_argument('--source',required=True);parser.add_argument('--source-sha256',required=True)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:]);SOURCE=Path(args.source);EXPECTED=args.source_sha256
OUTPUT=ART/'Krag_Cowl_v9me_WIP.blend'
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==EXPECTED
if OUTPUT.exists():raise RuntimeError('Refusing to overwrite an actual cowl study')
bpy.ops.wm.open_mainfile(filepath=str(SOURCE));rig=bpy.data.objects['Krag_Rig'];rig.animation_data.action=None
for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update()
modules={o.get('module'):o for o in bpy.data.objects if o.type=='MESH'and 'module'in o}
body=modules['Body'];head=modules['Head'];old_scarf=modules['Scarf']
def fingerprint():
    h=hashlib.sha256()
    for obj in sorted((o for o in bpy.data.objects if o.type=='MESH' and o.get('module') and o.get('module')!='Scarf'),key=lambda o:o.name):
        points=np.empty(len(obj.data.vertices)*3,dtype=np.float32);obj.data.vertices.foreach_get('co',points);h.update(obj.name.encode());h.update(points.tobytes())
        if obj.data.shape_keys:
            for key in obj.data.shape_keys.key_blocks:key.data.foreach_get('co',points);h.update(key.name.encode());h.update(points.tobytes())
    for bone in rig.data.bones:h.update(bone.name.encode());h.update(np.asarray(bone.matrix_local,dtype=np.float64).tobytes())
    for action in sorted(bpy.data.actions,key=lambda a:a.name):
        h.update(action.name.encode())
        for layer in action.layers:
            for strip in layer.strips:
                for slot in action.slots:
                    bag=strip.channelbag(slot)
                    if bag:
                        for curve in bag.fcurves:
                            h.update(curve.data_path.encode());h.update(str(curve.array_index).encode())
                            for key in curve.keyframe_points:h.update(np.asarray(key.co,dtype=np.float64).tobytes())
    return h.hexdigest()
before=fingerprint();neck=json.loads((ART/'neck-scarf-v9ma.json').read_text())['neck']
# Re-evaluate the exact failed portrait rays before spending time on fabric.
# This tests the real edited Body surface, rather than a bounding-box claim.
rig.animation_data.action=bpy.data.actions['FacePerformance'];bpy.context.scene.frame_set(146);bpy.context.view_layer.update()
deps=bpy.context.evaluated_depsgraph_get();trees={}
for obj in [body,head,modules['MouthInterior'],modules['Face']]:
    evaluated=obj.evaluated_get(deps)
    trees[obj['module']]=BVHTree.FromPolygons([evaluated.matrix_world@v.co for v in evaluated.data.vertices],[tuple(p.vertices)for p in evaluated.data.polygons])
camera=Vector((1.1,-4,2.05));target=Vector((0,-.02,1.9));q=(target-camera).to_track_quat('-Z','Y');right=q@Vector((1,0,0));up=q@Vector((0,1,0));direction=q@Vector((0,0,-1))
proof=json.loads((ART/'anatomy-study/mouth-scene-overlap-v9ka.json').read_text());failed=[];resolved=[]
for probe in proof['probes']:
    if not probe['visibleHits'] or probe['visibleHits'][0]['module']!='Body':continue
    x,y=probe['pixel'];origin=camera+right*((x+.5)/1000-.5)*.53+up*(.5-(y+.5)/1000)*.53;hits=[]
    for name,tree in trees.items():
        point,normal,face,distance=tree.ray_cast(origin,direction,8.)
        if point is not None:hits.append((distance,name))
    hits.sort();first=hits[0][1] if hits else None
    (failed if first=='Body' else resolved).append({'pixel':[x,y],'firstSurface':first})
if failed:raise RuntimeError('Concealed-neck composition leaves original Body occluder on '+str(len(failed))+' mouth rays')
# Actual lowered chin landmark comes from exterior mandibular topology in the
# authored open-mouth pose, excluding the neck and oral lining.
ehead=head.evaluated_get(deps);raw=np.empty(len(head.data.vertices)*3,dtype=np.float32)
head.data.attributes['krag_reference_position'].data.foreach_get('vector',raw);raw=raw.reshape(-1,3)
mandible=np.zeros(len(raw),dtype=bool);tags=head.data.attributes['.sculpt_face_set']
for polygon in head.data.polygons:
    if tags.data[polygon.index].value==24:mandible[list(polygon.vertices)]=True
chin_region=mandible&(abs(raw[:,0])<.030)&(raw[:,1]<-.055)&(raw[:,2]>.171)&(raw[:,2]<.207)
if chin_region.sum()<20:raise RuntimeError('Actual lower-chin landmark support missing')
open_head=np.asarray([tuple(ehead.matrix_world@v.co)for v in ehead.data.vertices])
open_chin_min=float(open_head[chin_region,2].min())
rig.animation_data.action=None
for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update();cloth_material=old_scarf.data.materials[0]
bpy.data.objects.remove(old_scarf,do_unlink=True)
def mesh(name,vertices,faces,material,group,bone):
    data=bpy.data.meshes.new(name);data.from_pydata(vertices,[],faces);data.update();data.materials.append(material)
    obj=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(obj);obj['module']=group;obj['rig_bone']=bone
    uv=data.uv_layers.new(name='UVMap')
    for polygon in data.polygons:
        polygon.use_smooth=True
        for loop in polygon.loop_indices:
            index=data.loops[loop].vertex_index;u=index//29/176;v=index%29/28
            uv.data[loop].uv=(u*1.22,v*.22)
    return obj
context={'mesh':mesh,'cloth':cloth_material,'cages_are_final':True,'actual_body':body,'actual_head':head,'actual_open_chin_min_z':open_chin_min}
scarf=scarf_authored_v9me.build(context);scarf.name='Scarf';scarf.parent=rig
# The loose chest panel follows Chest. Only the supported high rear neckline
# gradually shares Neck motion; no jaw-weighted cloth or floating front pin.
chest=scarf.vertex_groups.new(name='Chest');neck_group=scarf.vertex_groups.new(name='Neck')
for vertex in scarf.data.vertices:
    nape=max(0,min(1,(vertex.co.y-.035)/.095));height=max(0,min(1,(vertex.co.z-1.69)/.12));w=.68*nape*height
    chest.add([vertex.index],1-w,'REPLACE')
    if w>0:neck_group.add([vertex.index],w,'REPLACE')
mod=scarf.modifiers.new('Krag weighted deformation','ARMATURE');mod.object=rig
rig.animation_data.action=bpy.data.actions['Idle'];bpy.context.scene.frame_set(1)
assert fingerprint()==before,'Cloth composition changed unrelated points, shapes, bind or authored action curves'
for path in [Path(__file__),HERE/'neck_composition.py',HERE/'scarf_authored_v9me.py']:
    block=bpy.data.texts.new('v9me_cowl/'+path.name);block.write(path.read_text())
bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT),compress=True)
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==EXPECTED
report={'status':'Actual authored returned-fold source; mouth, fabric and pose acceptance require renders','artisticAcceptance':False,'sharedPromotion':False,
 'input':{'path':SOURCE.relative_to(ROOT).as_posix(),'sha256':EXPECTED},'source':{'path':OUTPUT.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(OUTPUT.read_bytes()).hexdigest()},
 'neck':neck,'mouthRays':{'originalBodyOcclusions':len(resolved)+len(failed),'remainingBodyOcclusions':len(failed),'resolved':resolved},
 'cloth':context['scarf_cloth_study'],'preservedGeometryShapesBindFingerprint':before,'recipeFiles':[{'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}for p in [Path(__file__),HERE/'scarf_authored_v9me.py']],
 'pending':['Actual open-mouth/front/profile/scarf contact review','Cinematic final neck seam integration','Concept face/iris/cloth material fidelity','IronJaw anatomical replacement']}
(ART/'cowl-v9me.json').write_text(json.dumps(report,indent=2)+'\n',newline='\n')
print('Krag v9me cowl saved; actual art review required',flush=True)
