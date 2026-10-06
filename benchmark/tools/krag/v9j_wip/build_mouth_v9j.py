"""Isolated real-rim opening, lip rolls, dental arches and tongue source study.

Uses saved v9i topology and retains body motion, geometry, weapon and shared
exports. This is a bounded provisional anatomy correction, not acceptance.
"""
from pathlib import Path
import sys,json,hashlib
import numpy as np
import bpy
from mathutils import Matrix,Vector
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sys.path.insert(0,str(HERE));import semantic_jaw_v3,dental_arch
ART=ROOT/'benchmark/art/krag';SOURCE=ART/'Krag_MouthContact_v9i_WIP.blend';OUTPUT=ART/'Krag_MouthAnatomy_v9j_WIP.blend'
EXPECTED='a288c9446680929052aaf90213379e671588188d31072ee4ebf01b57148e87ff'
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==EXPECTED
bpy.ops.wm.open_mainfile(filepath=str(SOURCE));rig=bpy.data.objects['Krag_Rig'];rig.animation_data.action=None
for p in rig.pose.bones:p.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update()
modules={o.get('module'):o for o in bpy.data.objects if o.type=='MESH' and 'module'in o}
head=modules['Head'];mesh=head.data;n=len(mesh.vertices)
raw=np.empty(n*3,dtype=np.float32);mesh.attributes['krag_reference_position'].data.foreach_get('vector',raw);raw=raw.reshape(-1,3)
sets=np.asarray([x.value for x in mesh.attributes['.sculpt_face_set'].data]);faces=[tuple(p.vertices)for p in mesh.polygons];edges=np.asarray([tuple(e.vertices)for e in mesh.edges])
tags=np.zeros(n,dtype=np.uint64)
for face,tag in zip(faces,sets):tags[list(face)]|=np.uint64(1)<<np.uint64(tag)
member=lambda tag:(tags&(np.uint64(1)<<np.uint64(tag)))!=0
upper=member(33);lower=member(24);bag=member(7);ur=upper&bag;lr=lower&bag;corners=ur&lr
assert corners.sum()==2
neck=np.zeros(n);oldjaw=np.zeros(n);groups={name:head.vertex_groups[name]for name in ['Head','Jaw','Neck']}
for v in mesh.vertices:
    for entry in v.groups:
        if entry.group==groups['Neck'].index:neck[v.index]=entry.weight
        elif entry.group==groups['Jaw'].index:oldjaw[v.index]=entry.weight
jaw,jaw_report=semantic_jaw_v3.calculate(raw,faces,sets,edges,neck)
for i,value in enumerate(jaw):
    groups['Jaw'].add([i],float(value),'REPLACE');groups['Head'].add([i],float(1-neck[i]-value),'REPLACE')
keys=mesh.shape_keys.key_blocks
cached={key.name:np.asarray([tuple(p.co)for p in key.data])for key in keys}
basis=cached['Basis'];all_vertices=np.ones(n,dtype=bool)
du=semantic_jaw_v3.distances(raw,edges,ur,all_vertices)
dl=semantic_jaw_v3.distances(raw,edges,lr,all_vertices)
dc=semantic_jaw_v3.distances(raw,edges,corners,all_vertices)
drim=np.minimum(du,dl)
# Continuous rolled vermilion surface: move the existing lip loops and adjacent
# tissue, rather than appending separate lip cushions to the face.
roll=np.exp(-(drim/.0032)**2)*.0018
neutral=np.zeros_like(basis);neutral[:,1]-=roll
for name,coords in cached.items():keys[name].data.foreach_set('co',(coords+neutral).astype(np.float32).ravel())
mesh.vertices.foreach_set('co',(basis+neutral).astype(np.float32).ravel())
# A modest upper-lip release and soft commissure compression accompany opening.
# These are morph deltas on top of the semantic lower-jaw rotation.
width=max(abs(raw[corners,0]));across=np.clip(1-(raw[:,0]/width)**2,0,1)**.8
upper_support=np.exp(-(du/.007)**2)*dl/np.maximum(du+dl,1e-9)
opening=np.zeros_like(basis);opening[:,2]=.0024*upper_support*across
opening[:,1]+=.0010*np.exp(-(dc/.005)**2)
# Retain only the previous bounded chin corrective, attenuated where necessary.
ratio=np.zeros(n);valid=oldjaw>1e-5;ratio[valid]=np.minimum(1,jaw[valid]/oldjaw[valid])
chin=(cached['JawOpen']-basis)*ratio[:,None]
keys['JawOpen'].data.foreach_set('co',(basis+neutral+chin+opening).astype(np.float32).ravel())
if not np.isfinite(opening).all() or np.max(np.linalg.norm(opening,axis=1))>.003:raise RuntimeError('Unbounded oral corrective')
# Existing Smile/Frown targets were centered far outside the real commissures.
# Re-author only those four bounded serious-expression fields at the true rim.
for sign,side in [(-1,'R'),(1,'L')]:
    source_corner=raw[np.flatnonzero(corners)[np.argmax(raw[corners,0]*sign)]]
    support=np.exp(-np.sum(((raw-source_corner)/np.asarray((.012,.045,.015)))**2,axis=1))
    for prefix,lift,lateral in [('Smile',.0032,.0016),('Frown',-.0035,-.0005)]:
        expression=np.zeros_like(basis);expression[:,2]=lift*support;expression[:,0]=sign*lateral*support
        keys[prefix+'_'+side].data.foreach_set('co',(basis+neutral+expression).astype(np.float32).ravel())

# Refitting unweighted expression controls to true commissures does not change
# their source local translation tracks or any body/jaw bind transform.
old_bind={b.name:np.asarray(b.matrix_local).copy()for b in rig.data.bones}
bpy.context.view_layer.objects.active=rig;bpy.ops.object.mode_set(mode='EDIT')
corner_report={}
for sign,side in [(-1,'R'),(1,'L')]:
    i=np.flatnonzero(corners)[np.argmax(raw[corners,0]*sign)];bone=rig.data.edit_bones['MouthCorner_'+side]
    previous=np.asarray(bone.head).copy();offset=Vector(basis[i]+neutral[i])-bone.head
    bone.head+=offset;bone.tail+=offset
    corner_report[side]={'vertex':int(i),'old':previous.tolist(),'new':list(bone.head)}
bpy.ops.object.mode_set(mode='OBJECT')
for name,matrix in old_bind.items():
    if not name.startswith('MouthCorner_') and not np.allclose(np.asarray(rig.data.bones[name].matrix_local),matrix,atol=1e-7):raise RuntimeError('Unrelated bind changed '+name)
# Anatomical crown/gingiva/tongue meshes replace the old blocks and duplicate
# opaque lining. The real continuous inner bag remains part of Head.
oral,oral_report=dental_arch.rebuild(modules['MouthInterior'],rig)
# Lower tusks replace the canine sites and their roots now meet the fitted
# gingival arch; the exposed crown/tip remains at its reviewed silhouette.
face=modules['Face'];face_keys=face.data.shape_keys.key_blocks
fb=np.asarray([tuple(v.co)for v in face_keys['Basis'].data]);delta=np.zeros_like(fb)
ivory={v for p in face.data.polygons if face.data.materials[p.material_index].name=='Krag_Ivory'for v in p.vertices}
tusk_report=[]
for part in dental_arch.components(face.data):
    if int(part[0])not in ivory:continue
    if len(part)!=48:raise RuntimeError('Unexpected reviewed tusk topology')
    rings=part.reshape(3,16);centers=fb[rings].mean(1)
    root_ring=int(np.argmin(centers[:,2]));tip_ring=int(np.argmax(centers[:,2]));root=centers[root_ring]
    side='L'if root[0]>0 else'R';target=np.asarray(oral_report['tuskRootTargets'][side])
    shift=target-root
    if np.linalg.norm(shift)>.035:raise RuntimeError('Tusk root fit unexpectedly large')
    for r,indices in enumerate(rings):
        fade=np.clip((centers[tip_ring,2]-centers[r,2])/max(centers[tip_ring,2]-root[2],1e-8),0,1)**2
        delta[indices]+=shift*fade
    tusk_report.append({'side':side,'previousRoot':root.tolist(),'targetGumRoot':target.tolist(),'shiftMeters':shift.tolist(),'tipUnchanged':True})
for key in face_keys:
    coords=np.asarray([tuple(v.co)for v in key.data]);key.data.foreach_set('co',(coords+delta).astype(np.float32).ravel())
face.data.vertices.foreach_set('co',(fb+delta).astype(np.float32).ravel())
for p in [Path(__file__),HERE/'dental_arch.py',HERE/'semantic_jaw_v3.py']:
    block=bpy.data.texts.new('v9j_mouth/'+p.name);block.write(p.read_text())
head['krag_mouth_anatomy_v9j']='Provisional actual-lip-loop opening and rounded dental anatomy; review required'
rig.animation_data.action=bpy.data.actions['Idle'];bpy.context.scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT),compress=True)
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==EXPECTED
report={'status':'Generated provisional source only; neutral/open/profile pose review required','artisticAcceptance':False,'sharedPromotion':False,
 'input':{'path':SOURCE.relative_to(ROOT).as_posix(),'sha256':EXPECTED},'source':{'path':OUTPUT.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(OUTPUT.read_bytes()).hexdigest()},
 'jaw':jaw_report,'commissureControls':corner_report,'oralGeometry':oral_report,'tusks':tusk_report,
 'lipRollMaximumMeters':float(roll.max()),'openingCorrectiveMaximumMeters':float(np.linalg.norm(opening,axis=1).max()),
 'preserved':['Body geometry and actions','Jaw/eye/body bind','Current weapon','Shared exports'],
 'pending':['Actual rounded mouth opening and neutral dental occlusion','Tusk/gum contact in neutral/open','Tongue/cavity clearance','IronJaw organic exclusion','Concept facial likeness']}
(ART/'mouth-anatomy-v9j.json').write_text(json.dumps(report,indent=2)+'\n',newline='\n')
print('KRAG v9j mouth anatomy source saved; acceptance pending',flush=True)
