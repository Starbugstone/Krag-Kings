"""Rebuild the failed Krag palm with coherent licensed anatomical topology.

Isolated source study. Retains the original forearm above a planar cut, welds a
continuous wrist, adds actual DIP joints, and reauthors only left digit tracks.
No shared asset or engine import is changed by this script.
"""
import argparse,hashlib,json,sys
from pathlib import Path
from collections import Counter
import bpy,bmesh,numpy as np
from mathutils import Matrix,Vector
from bpy_extras.anim_utils import action_get_channelbag_for_slot
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path[:0]=[str(HERE),str(HERE.parent),str(ROOT/'tools/nib/v5_wip'),str(ROOT/'tools/nib/restorative_wip')]
from surface_join import clip,cut_loop,connect
from contracts import rig_contract,surface_hash
from export_contract import CLIPS,select_action
from nib_hand_v5 import SOURCE_CHAINS
import hand_skin_domains,pose
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--source-sha256',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  while chunk:=f.read(1024*1024):h.update(chunk)
 return h.hexdigest()
library=ROOT/'art/reference-anatomy/blender-studio-human-base-meshes/source/human-base-meshes-bundle-v1.4.1/human_base_meshes_bundle.blend'
if sha(a.source)!=a.source_sha256:raise RuntimeError('Pinned source changed')
if a.output.exists():raise RuntimeError('Preserve previous candidate')
a.output.mkdir(parents=True);inputs={str(p):sha(p) for p in [a.source,library]}
bpy.ops.wm.open_mainfile(filepath=str(a.source),load_ui=False)
rig=bpy.data.objects['Krag_Rig'];obj=bpy.data.objects['BioForearm_L'];old=obj.data;scene=bpy.context.scene
before=rig_contract(rig);stable={o.name:surface_hash(o) for o in bpy.data.objects if o.type=='MESH' and o!=obj}
if np.max(np.abs(np.asarray(obj.matrix_world)-np.asarray(rig.matrix_world)))>1e-7:raise RuntimeError('Unexpected source coordinate space')
select_action(bpy,rig,None)
for track in rig.animation_data.nla_tracks:track.mute=True
w=np.array(rig.data.bones['Hand_L'].head_local);row=np.array(rig.data.bones['Finger1_0_L'].head_local)-rig.data.bones['Finger1_3_L'].head_local;row/=np.linalg.norm(row)
long=np.array(rig.data.bones['Hand_L'].tail_local)-w;long-=row*(long@row);long/=np.linalg.norm(long);normal=np.cross(row,long);up=-long
# Concept-scaled broad hand, with normal anatomical thickness and relative
# phalange proportions. This is not a new species-proportion approval.
linear=np.stack([-row*2.,normal*1.5,up*1.32],axis=1)
def fit(points):
 points=np.asarray(points);return (points-np.array([.008,0,0]))@linear.T+w
mapping={'Little':0,'Ring':1,'Middle':2,'Index':3}
def rename(name):
 for digit,number in mapping.items():
  if name.startswith(digit):return 'Finger'+name[len(digit):].replace('_L','_'+str(number)+'_L')
 return name
with bpy.data.libraries.load(str(library),link=False) as (available,requested):requested.objects=['Hand  - Realistic']
hand=requested.objects[0];scene.collection.objects.link(hand);hand.parent=None;hand.matrix_parent_inverse=Matrix.Identity(4);hand.matrix_world=Matrix.Identity(4);hand.modifiers.clear();hand.vertex_groups.clear()
raw=np.array([v.co[:] for v in hand.data.vertices]);faces=[list(p.vertices) for p in hand.data.polygons]
domains,domain_report=hand_skin_domains.solve(raw,faces,source_cage=True,proximal_chains=SOURCE_CHAINS)
names,weights,weight_report=hand_skin_domains.weights(raw,domains,SOURCE_CHAINS,side='L',joint_half_width=.008);names=[rename(n) for n in names]
for name in names:hand.vertex_groups.new(name=name)
for i,values in enumerate(weights):
 for j in np.flatnonzero(values>1e-8):hand.vertex_groups[int(j)].add([i],float(values[j]),'REPLACE')
for index,digit in enumerate(hand_skin_domains.DIGITS):
 attr=hand.data.attributes.new('Krag_DigitDomain_'+str({'Little':0,'Ring':1,'Middle':2,'Index':3,'Thumb':4}[digit])+'_v3','FLOAT','POINT');attr.data.foreach_set('value',domains[:,index].astype(np.float32))
hand.data.vertices.foreach_set('co',fit(raw).astype(np.float32).ravel())
bm=bmesh.new();bm.from_mesh(hand.data);bmesh.ops.reverse_faces(bm,faces=list(bm.faces));bm.to_mesh(hand.data);bm.free()
bpy.ops.object.select_all(action='DESELECT');hand.select_set(True);bpy.context.view_layer.objects.active=hand
sub=hand.modifiers.new('Coherent anatomical surface','SUBSURF');sub.levels=2;bpy.ops.object.modifier_apply(modifier=sub.name)
# Explicit digit bind migration; Hand_L and all other body/facial bones stay.
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig;bpy.ops.object.mode_set(mode='EDIT');changed_bones=[]
for digit,chain in SOURCE_CHAINS.items():
 for segment in range(len(chain)-1):
  name=rename(digit+str(segment+1)+'_L');bone=rig.data.edit_bones.get(name) or rig.data.edit_bones.new(name)
  bone.use_connect=False;bone.head=Vector(fit(chain[segment]));bone.tail=Vector(fit(chain[segment+1]));bone.align_roll(Vector(normal));bone.use_deform=True
  bone.parent=rig.data.edit_bones['Hand_L' if segment==0 else rename(digit+str(segment)+'_L')];changed_bones.append(name)
bpy.ops.object.mode_set(mode='OBJECT')
for name in changed_bones:rig.pose.bones[name].rotation_mode='XYZ'
all_groups=list(dict.fromkeys([g.name for g in obj.vertex_groups]+names));group_map={n:i for i,n in enumerate(all_groups)}
key_meta={key.name:{'slider_min':key.slider_min,'slider_max':key.slider_max,'interpolation':key.interpolation,'relative_key':key.relative_key.name,'vertex_group':key.vertex_group,'mute':key.mute} for key in old.shape_keys.key_blocks} if old.shape_keys else {}
old_coords=np.array([v.co[:] for v in old.vertices]);old_keys={key.name:np.array([v.co[:] for v in key.data])-old_coords for key in old.shape_keys.key_blocks} if old.shape_keys else {}
point_attrs={attr.name:attr.data_type for attr in old.attributes if attr.domain=='POINT' and attr.data_type in ['FLOAT','FLOAT_VECTOR'] and attr.name!='position'}
uv_names=[uv.name for uv in old.uv_layers]
def arrays(mesh,owner,is_hand):
 points=np.array([v.co[:] for v in mesh.vertices]);faces=[list(p.vertices) for p in mesh.polygons];fields={'weights':np.zeros((len(points),len(all_groups)))}
 for v in mesh.vertices:
  for g in v.groups:
   name=owner.vertex_groups[g.group].name
   if name in group_map:fields['weights'][v.index,group_map[name]]=g.weight
 for name,deltas in old_keys.items():fields['morph:'+name]=np.zeros_like(points) if is_hand else deltas
 for name,typ in point_attrs.items():
  width=3 if typ=='FLOAT_VECTOR' else 1;attr=mesh.attributes.get(name)
  if attr:
   values=np.empty(len(points)*width,np.float32);attr.data.foreach_get('vector' if width==3 else 'value',values);values=values.reshape(-1,3) if width==3 else values
  else:values=np.ones(len(points)) if name=='Krag_ArmDomain_v2' else np.zeros((len(points),3) if width==3 else len(points))
  fields['attr:'+name]=values
 uvs={}
 for name in uv_names:
  source=mesh.uv_layers.get(name) or mesh.uv_layers.active
  uvs[name]=[[tuple(source.data[i].uv) if source else (.5,.5) for i in p.loop_indices] for p in mesh.polygons]
 return points,faces,[0 if is_hand else p.material_index for p in mesh.polygons],uvs,fields
old_data=arrays(old,obj,False);new_data=arrays(hand.data,hand,True)
upper=clip(*old_data,(old_data[0]-w)@up-.055);lower=clip(*new_data,.015-(new_data[0]-w)@up)
upper_ring=cut_loop(upper,w,up,.055);lower_ring=cut_loop(lower,w,up,.015)
joined=connect(upper,lower,upper_ring,lower_ring,w,row,normal)
mesh=bpy.data.meshes.new('Krag coherent hand and continuous wrist');mesh.from_pydata(joined['points'].tolist(),[],joined['faces']);mesh.update()
for material in old.materials:mesh.materials.append(material)
for polygon,material in zip(mesh.polygons,joined['materials']):polygon.material_index=material;polygon.use_smooth=True
for name,faces_uv in joined['uvs'].items():
 uv=mesh.uv_layers.new(name=name);uv.data.foreach_set('uv',np.array([p for face in faces_uv for p in face],np.float32).ravel())
# Recalculate consistent outward normals on the actual connected topology.
bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free();mesh.update()
obj.data=mesh;obj.vertex_groups.clear()
for name in all_groups:obj.vertex_groups.new(name=name)
weights=joined['fields']['weights'];weights[weights<1e-8]=0
order=np.argsort(-weights,axis=1);limit=np.zeros_like(weights)
for j in range(4):limit[np.arange(len(weights)),order[:,j]]=weights[np.arange(len(weights)),order[:,j]]
total=limit.sum(1)
if np.min(total)<1e-7:raise RuntimeError('Unweighted rebuilt surface')
limit/=total[:,None]
for i,values in enumerate(limit):
 for j in np.flatnonzero(values):obj.vertex_groups[int(j)].add([i],float(values[j]),'REPLACE')
for name,typ in point_attrs.items():
 attr=mesh.attributes.new(name,typ,'POINT');attr.data.foreach_set('vector' if typ=='FLOAT_VECTOR' else 'value',joined['fields']['attr:'+name].astype(np.float32).ravel())
for name,metadata in key_meta.items():
 key=obj.shape_key_add(name=name,from_mix=False);key.data.foreach_set('co',(joined['points']+joined['fields']['morph:'+name]).astype(np.float32).ravel())
 for prop in ['slider_min','slider_max','interpolation','vertex_group','mute']:setattr(key,prop,metadata[prop])
for name,metadata in key_meta.items():mesh.shape_keys.key_blocks[name].relative_key=mesh.shape_keys.key_blocks[metadata['relative_key']]
if old.shape_keys and old.shape_keys.animation_data:
 if old.shape_keys.animation_data.drivers:raise RuntimeError('Source shape drivers require explicit migration')
 if old.shape_keys.animation_data.action:
  mesh.shape_keys.animation_data_create();mesh.shape_keys.animation_data.action=old.shape_keys.animation_data.action
bpy.data.objects.remove(hand,do_unlink=True)
# Morph-preserving edge/topology checks. The old elbow boundary must be exact.
def boundary(faces):
 counts=Counter(tuple(sorted((f[i],f[(i+1)%len(f)]))) for f in faces for i in range(len(f)));return [e for e,n in counts.items() if n==1],sum(n>2 for n in counts.values())
old_edges,_=boundary(old_data[1]);new_edges,nonmanifold=boundary(joined['faces'])
if nonmanifold:raise RuntimeError('Nonmanifold welded wrist')
def edge_set(edges,points):return {tuple(sorted(tuple(np.round(points[v],7)) for v in edge)) for edge in edges}
if edge_set(old_edges,old_data[0])!=edge_set(new_edges,joined['points']):raise RuntimeError('New seam or lost original elbow boundary')
mesh.calc_loop_triangles();tri=np.array([tuple(t.vertices) for t in mesh.loop_triangles]);v=np.array([v.co[:] for v in mesh.vertices]);cross=np.cross(v[tri[:,1]]-v[tri[:,0]],v[tri[:,2]]-v[tri[:,0]])
areas=np.linalg.norm(cross,axis=1)
if np.any(areas<1e-12):raise RuntimeError('Degenerate rebuilt triangle')
# Preserve every non-digit curve, including body contact and facial acting.
paths={rig.pose.bones[name].path_from_id()+'.'+channel for name in changed_bones for channel in ['location','rotation_euler','rotation_quaternion','rotation_axis_angle','scale']}
def untouched(action):
 select_action(bpy,rig,action);bag=action_get_channelbag_for_slot(action,rig.animation_data.action_slot)
 rows=[(c.data_path,c.array_index,c.extrapolation,[(tuple(k.co),tuple(k.handle_left),tuple(k.handle_right),k.interpolation,k.handle_left_type,k.handle_right_type,k.easing,k.amplitude,k.back,k.period) for k in c.keyframe_points]) for c in bag.fcurves if c.data_path not in paths]
 return hashlib.sha256(json.dumps(sorted(rows),separators=(',',':')).encode()).hexdigest()
clip_report={}
for clip_name in CLIPS:
 original=bpy.data.actions[clip_name];expected=untouched(original);original.name='Preserved_'+clip_name+'_BeforeCoherentKragHand';original.use_fake_user=True
 action=original.copy();action.name=clip_name;action.use_fake_user=True;select_action(bpy,rig,action);bag=action_get_channelbag_for_slot(action,rig.animation_data.action_slot)
 for curve in list(bag.fcurves):
  if curve.data_path in paths:bag.fcurves.remove(curve)
 first,last=map(round,action.frame_range)
 for frame in range(first,last+1):
  scene.frame_set(frame);changed=pose.apply(rig,clip_name,(frame-first)/max(1,last-first))
  for name in changed:rig.pose.bones[name].keyframe_insert('rotation_euler',frame=frame,group=name)
 for curve in bag.fcurves:
  if curve.data_path in paths:
   for key in curve.keyframe_points:key.interpolation='LINEAR'
 if untouched(action)!=expected:raise RuntimeError('Non-digit action changed '+clip_name)
 clip_report[clip_name]={'frameRange':[first,last],'unchangedOtherCurvesSha256':expected}
after=rig_contract(rig)
for name,payload in before['bones'].items():
 if name not in changed_bones and after['bones'][name]!=payload:raise RuntimeError('Unrelated bind changed '+name)
for name,digest in stable.items():
 if surface_hash(bpy.data.objects[name])!=digest:raise RuntimeError('Unrelated mesh changed '+name)
select_action(bpy,rig,bpy.data.actions['Idle']);scene.frame_set(1)
expected_surface=surface_hash(obj);output=a.output/'Krag_CoherentHand_v1.blend';bpy.ops.wm.save_as_mainfile(filepath=str(output),compress=True)
bpy.ops.wm.open_mainfile(filepath=str(output),load_ui=False)
if rig_contract(bpy.data.objects['Krag_Rig'])!=after:raise RuntimeError('Saved rig/actions changed')
if surface_hash(bpy.data.objects['BioForearm_L'])!=expected_surface:raise RuntimeError('Saved rebuilt surface changed')
for name,digest in stable.items():
 if surface_hash(bpy.data.objects[name])!=digest:raise RuntimeError('Saved unrelated mesh changed '+name)
for path,digest in inputs.items():
 if sha(Path(path))!=digest:raise RuntimeError('Input changed')
report={'status':'Actual isolated coherent hand and welded wrist; visual and action contact review required','inputs':inputs,'output':str(output),'outputSha256':sha(output),'savedSourceReopened':True,'anatomyReference':'Blender Studio Human Base Meshes v1.4.1 / Hand  - Realistic / CC0','referenceFitScales':{'across':2.,'depth':1.5,'length':1.32},'sourceCageVertices':len(raw),'vertices':len(joined['points']),'triangles':len(tri),'wristJoin':joined['join'],'originalElbowBoundaryPreserved':True,'newNonManifoldEdges':nonmanifold,'newDegenerateTriangles':0,'minimumDoubleTriangleArea':float(areas.min()),'domainSolve':domain_report,'sourceWeights':weight_report,'maximumInfluences':4,'changedDigitBones':changed_bones,'totalBindBones':len(after['bones']),'unchangedMeshComponents':len(stable),'clips':clip_report,'recipeHashes':{path.name:sha(path) for path in [Path(__file__),HERE/'surface_join.py',HERE/'pose.py',Path(hand_skin_domains.__file__)]},'artisticAcceptance':False,'surfaceIntersectionsProven':False,'engineExported':False,'sharedChanged':False}
(a.output/'coherent-hand.json').write_text(json.dumps(report,indent=2)+'\n',newline='\n');print('KRAG_COHERENT_HAND_SAVED_AND_REOPENED',flush=True)
