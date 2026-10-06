"""Prepared cavity and canonical open-pose lip fitting, isolated from body motion.

Exterior face warps must not sculpt the interior roof/floor into a second
muzzle. Oral topology uses its own affine fit, blended into the real lip rims.
A canonical Jaw pose then fits a smooth lower-lip arc to the actual teeth.
"""
from pathlib import Path
import sys,json,hashlib,math
import numpy as np
import bpy
from mathutils import Matrix
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];BASE=HERE.parent
sys.path.insert(0,str(BASE/'v9j_wip'));import dental_arch,semantic_jaw_v3
ART=ROOT/'benchmark/art/krag';SOURCE=ART/'Krag_MouthAnatomy_v9j_WIP.blend';OUTPUT=ART/'Krag_MouthPoseFit_v9k_WIP.blend'
EXPECTED='dc62a79bd51e3be04593287fb2a66fc5b8d34555d75ca89c744ba731c973874f'
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==EXPECTED
bpy.ops.wm.open_mainfile(filepath=str(SOURCE));rig=bpy.data.objects['Krag_Rig'];rig.animation_data.action=None
for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update();modules={o.get('module'):o for o in bpy.data.objects if o.type=='MESH'and 'module'in o}
head=modules['Head'];mesh=head.data;n=len(mesh.vertices);oral=modules['MouthInterior']
raw=np.empty(n*3,dtype=np.float32);mesh.attributes['krag_reference_position'].data.foreach_get('vector',raw);raw=raw.reshape(-1,3)
sets=np.asarray([a.value for a in mesh.attributes['.sculpt_face_set'].data]);faces=[tuple(p.vertices)for p in mesh.polygons];edges=np.asarray([tuple(e.vertices)for e in mesh.edges]);tags=np.zeros(n,dtype=np.uint64)
for face,tag in zip(faces,sets):tags[list(face)]|=np.uint64(1)<<np.uint64(tag)
member=lambda tag:(tags&(np.uint64(1)<<np.uint64(tag)))!=0
bag=member(7);upper=member(33);lower=member(24);ur=bag&upper;lr=bag&lower;corners=ur&lr
keys=mesh.shape_keys.key_blocks;cached={k.name:np.asarray([tuple(v.co)for v in k.data])for k in keys};basis=cached['Basis']
d=semantic_jaw_v3.distances(raw,edges,ur|lr,bag);blend=np.zeros(n);t=np.clip(d[bag]/.014,0,1);blend[bag]=t*t*(3-2*t)
# Source mouth topology gets one coherent interior scale. The exact shared
# vermilion boundaries remain fixed. No exterior nose/chin displacement field.
raw_anchor=np.mean(raw[corners],axis=0);anchor=np.mean(basis[corners],axis=0)
interior=anchor+(raw-raw_anchor)*np.asarray((2.10,1.20,.85))
cavity=(interior-basis)*blend[:,None]
new_basis=basis+cavity
for key in keys:
    original_delta=cached[key.name]-basis
    # Core oral lining follows skeleton, not nasal/brow/skin expression fields.
    key.data.foreach_set('co',(new_basis+original_delta*(1-blend[:,None])).astype(np.float32).ravel())
mesh.vertices.foreach_set('co',new_basis.astype(np.float32).ravel())
material=bpy.data.materials.new('Krag_InnerMouth_v9k');material.use_nodes=True
nodes=material.node_tree.nodes;links=material.node_tree.links;bs=nodes.get('Principled BSDF')
bs.inputs['Base Color'].default_value=(.068,.017,.014,1);bs.inputs['Roughness'].default_value=.39;bs.inputs['Subsurface Weight'].default_value=.07
noise=nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=420;noise.inputs['Detail'].default_value=2
bump=nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.18;bump.inputs['Distance'].default_value=.000065
links.new(noise.outputs['Fac'],bump.inputs['Height']);links.new(bump.outputs['Normal'],bs.inputs['Normal'])
slot=len(mesh.materials);mesh.materials.append(material)
for polygon,tag in zip(mesh.polygons,sets):
    if tag==7:polygon.material_index=slot
# Canonical pure mandibular opening, with other facial controls neutral.
angle=23.;rig.pose.bones['Jaw'].rotation_mode='XYZ';rig.pose.bones['Jaw'].rotation_euler.x=math.radians(angle);bpy.context.view_layer.update()
def evaluated(obj):
    e=obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    return np.asarray([tuple(e.matrix_world@v.co)for v in e.data.vertices])
posed=evaluated(head);oral_pose=evaluated(oral);oral_basis=np.asarray([tuple(v.co)for v in oral.data.vertices])
ivory={v for p in oral.data.polygons if oral.data.materials[p.material_index].name=='Krag_DentalEnamel'for v in p.vertices};jaw_group=oral.vertex_groups['Jaw'].index
lower_teeth=[]
for part in dental_arch.components(oral.data):
    if int(part[0])not in ivory:continue
    if not any(g.group==jaw_group and g.weight>.99 for g in oral.data.vertices[int(part[0])].groups):continue
    center=oral_basis[part].mean(0)
    lower_teeth.append((abs(center[0]),part))
central=[part for _,part in sorted(lower_teeth,key=lambda p:p[0])[:2]]
if len(central)!=2:raise RuntimeError('Missing central lower incisors')
tip_points=[];front_points=[]
for part in central:
    tip=part[oral_basis[part,2]>=np.quantile(oral_basis[part,2],.90)];tip_points.extend(oral_pose[tip]);front_points.extend(oral_pose[part])
tip_center=np.mean(tip_points,axis=0);tooth_front=float(np.min(np.asarray(front_points)[:,1]))
corner_ids=np.flatnonzero(corners);left,right=corner_ids[np.argsort(raw[corner_ids,0])]
frac=np.clip((raw[:,0]-raw[left,0])/(raw[right,0]-raw[left,0]),0,1);s=frac*2-1
ellipse=np.sqrt(np.maximum(0,1-s*s));endpoints=posed[left]*(1-frac[:,None])+posed[right]*frac[:,None]
target_bottom=float(tip_center[2]-.0055);depth=float((posed[left,2]+posed[right,2])*.5-target_bottom)
if not .015<depth<.11:raise RuntimeError('Canonical oral opening depth is implausible')
target=endpoints.copy();target[:,2]-=depth*ellipse
front_center=tooth_front-.0015;target[:,1]+=(front_center-(posed[left,1]+posed[right,1])*.5)*ellipse
# Only the lower anatomical rim is constrained. A topology-harmonic falloff
# carries that pose change into adjacent lip tissue and inner lining smoothly.
rim_delta=np.zeros((n,3));rim_delta[lr]=target[lr]-posed[lr]
allowed=lower|bag;distance=semantic_jaw_v3.distances(raw,edges,lr,allowed)
known=lr|~allowed|(distance>=.010)|upper
unknown=~known;value=rim_delta.copy();value[known&~lr]=0
edge_length=np.linalg.norm(raw[edges[:,0]]-raw[edges[:,1]],axis=1);conductance=1/np.maximum(edge_length,1e-10);a,b=edges.T
def neighbors(v):
    return np.bincount(a,conductance*v[b],minlength=n)+np.bincount(b,conductance*v[a],minlength=n)
diagonal=(np.bincount(a,conductance,minlength=n)+np.bincount(b,conductance,minlength=n))[unknown]
iterations=[]
for axis in range(3):
    rhs=neighbors(value[:,axis])[unknown]
    def multiply(x):
        all_x=np.zeros(n);all_x[unknown]=x
        return diagonal*x-neighbors(all_x)[unknown]
    x=np.zeros(unknown.sum());residual=rhs.copy();z=residual/diagonal;direction=z.copy();rz=float(residual@z);initial=max(np.linalg.norm(rhs),1e-30)
    for it in range(1500):
        if np.linalg.norm(residual)/initial<1e-9:break
        product=multiply(direction);den=float(direction@product)
        if den<=0:raise RuntimeError('Lip harmonic operator lost positive definiteness')
        alpha=rz/den;x+=alpha*direction;residual-=alpha*product;z=residual/diagonal;next_rz=float(residual@z);direction=z+(next_rz/rz)*direction;rz=next_rz
    if np.linalg.norm(residual)/initial>=1e-9:raise RuntimeError('Lip pose fit failed convergence')
    value[unknown,axis]=x;iterations.append(it+1)
# Invert the actual linear skin transform to store the correction before
# Armature. FBX/runtime carries the ordinary JawOpen morph, not a Blender driver.
matrices={name:np.asarray(rig.pose.bones[name].matrix@rig.data.bones[name].matrix_local.inverted())[:3,:3]for name in ['Head','Jaw','Neck']}
skin=np.zeros((n,3,3));names={g.index:g.name for g in head.vertex_groups}
for vertex in mesh.vertices:
    for item in vertex.groups:
        if item.weight<1e-8:continue
        if names[item.group]not in matrices:raise RuntimeError('Unexpected head skin influence')
        skin[vertex.index]+=matrices[names[item.group]]*item.weight
weight=float(keys['JawOpen'].value)
if not .85<weight<1.01:raise RuntimeError('Canonical JawOpen driver not evaluated')
local=np.linalg.solve(skin,value[...,None]).squeeze(-1)/weight
if np.max(np.linalg.norm(local,axis=1))>.030:raise RuntimeError('Required lip correction exceeds bounded source region')
old_open=np.asarray([tuple(v.co)for v in keys['JawOpen'].data]);keys['JawOpen'].data.foreach_set('co',(old_open+local).astype(np.float32).ravel())
mesh.update();bpy.context.view_layer.update();corrected=evaluated(head)
error=np.linalg.norm(corrected[lr]-target[lr],axis=1)
if error.max()>.0002:raise RuntimeError('Actual canonical lip target error exceeds 0.2 mm')
rig.pose.bones['Jaw'].rotation_euler=(0,0,0);rig.animation_data.action=bpy.data.actions['Idle'];bpy.context.scene.frame_set(1)
block=bpy.data.texts.new('v9k_mouth/'+Path(__file__).name);block.write(Path(__file__).read_text())
bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT),compress=True)
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==EXPECTED
report={'status':'Generated isolated cavity/open-pose mouth study; actual neutral/open/profile review required','artisticAcceptance':False,'sharedPromotion':False,
 'input':{'path':SOURCE.relative_to(ROOT).as_posix(),'sha256':EXPECTED},'source':{'path':OUTPUT.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(OUTPUT.read_bytes()).hexdigest()},
 'cavity':{'affineScale':[2.10,1.20,.85],'rimBlendSourceMeters':.014,'maximumRestCorrectionMeters':float(np.linalg.norm(cavity,axis=1).max()),'externalSkinNeutralUnchanged':bool(np.max(np.linalg.norm(cavity[~bag],axis=1))==0)},
 'lip':{'canonicalJawDegrees':angle,'driverWeight':weight,'targetIncisalClearanceMeters':.0055,'openingDepthMeters':depth,'maximumStoredCorrectiveMeters':float(np.linalg.norm(local,axis=1).max()),'actualCanonicalRimErrorMaximumMeters':float(error.max()),'harmonicIterations':iterations},
 'preserved':['Body geometry/bind/actions','Weapon','Dental and tongue source geometry','Full natural master','Shared exports']}
(ART/'mouth-pose-fit-v9k.json').write_text(json.dumps(report,indent=2)+'\n',newline='\n')
print('Krag v9k cavity/open-pose mouth source saved; actual art review required',flush=True)
