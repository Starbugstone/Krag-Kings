"""Fit an ordinary restorative socket and wrist to the actual coherent source.

Grip-only replacement surfaces. Natural meshes, all bind matrices, canonical
actions and previously migrated mechanical digits remain exact. No shared write.
"""
import argparse, hashlib, json, math, sys
from pathlib import Path
import bpy, bmesh
import numpy as np
from mathutils import Matrix, Vector

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
sys.path[:0]=[str(HERE),str(ROOT/'benchmark/tools/krag')]
from contracts import rig_contract, surface_hash
from socket_geometry import design
from runtime_reduction import attach_portable_drivers

parser=argparse.ArgumentParser()
parser.add_argument('--source',type=Path,required=True)
parser.add_argument('--source-sha256',required=True)
parser.add_argument('--output-dir',type=Path,required=True)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if sha(args.source)!=args.source_sha256:raise RuntimeError('Pinned restorative source changed')
if not args.output_dir.resolve().is_relative_to((ROOT/'benchmark/art/nib').resolve()):raise RuntimeError('Isolated owned output required')
if args.output_dir.exists():raise RuntimeError('Preserve previous socket source/evidence')
args.output_dir.mkdir(parents=True)
bpy.ops.wm.open_mainfile(filepath=str(args.source),load_ui=False)
scene=bpy.context.scene;rig=bpy.data.objects['Nib_Rig'];collection=bpy.data.collections['Nib_Authored_Components']
canonical=['Idle','Walk','Run','Melee','Shoot','Hit','FacePerformance']
if any(n not in bpy.data.actions for n in canonical):raise RuntimeError('Input lost canonical actions')
for n in canonical:bpy.data.actions[n].use_fake_user=True
contract=rig_contract(rig)
retained={o.name:surface_hash(o) for o in bpy.data.objects if o.type=='MESH'}
rig.animation_data.action=None
for track in rig.animation_data.nla_tracks:track.mute=True
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
scene.frame_set(1);bpy.context.view_layer.update()
body=bpy.data.objects['Continuous Nib anatomy organic']
if np.max(abs(np.asarray(body.matrix_world)-np.eye(4)))>1e-7:raise RuntimeError('Body coordinates must be armature/world metres')
points=np.asarray([v.co[:] for v in body.data.shape_keys.key_blocks['Basis'].data],float)
faces=[list(p.vertices) for p in body.data.polygons]
partition_path=args.source.parent/'source.json'
previous=json.loads(partition_path.read_text())
if previous['candidateSha256']!=args.source_sha256:raise RuntimeError('Actual partition receipt does not match input')
cut_ids=previous['partition']['body']['newCutOriginalVertexIds']
elbow=np.asarray(rig.data.bones['LowerArm_L'].head_local,float)
wrist=np.asarray(rig.data.bones['Hand_L'].head_local,float)
fit=design(points,faces,cut_ids,elbow,wrist)
new=[]

def mesh(name,coordinates,polygons,material,bone,uvs=None):
    data=bpy.data.meshes.new(name+' mesh');data.from_pydata(coordinates,[],polygons);data.update()
    obj=bpy.data.objects.new(name,data);collection.objects.link(obj)
    obj['variant']='grip';obj['bone']=bone;obj['restorative_socket_revision']='Actual body-surface socket and continuous wrist v1'
    data.materials.append(bpy.data.materials[material])
    bm=bmesh.new();bm.from_mesh(data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(data);bm.free()
    for p in data.polygons:p.use_smooth=True
    uv=data.uv_layers.new(name='UVMap')
    for p in data.polygons:
        for li in p.loop_indices:
            vi=data.loops[li].vertex_index
            uv.data[li].uv=uvs[vi] if uvs is not None else (coordinates[vi][0]*10,coordinates[vi][2]*10)
    obj.parent=rig;obj.matrix_parent_inverse=Matrix.Identity(4)
    mod=obj.modifiers.new('Portable linear skinning','ARMATURE');mod.object=rig;mod.use_deform_preserve_volume=False
    if bone in rig.data.bones:
        group=obj.vertex_groups.new(name=bone);group.add(list(range(len(data.vertices))),1,'REPLACE')
    new.append(obj);return obj

around=fit['around'];rows=fit['rows'];count=around*rows
coordinates=np.vstack([fit['outer'],fit['inner']]);polygons=[]
for row in range(rows-1):
    for c in range(around):
        d=(c+1)%around;a=row*around+c;b=row*around+d
        polygons.append((a,b,b+around,a+around))
        polygons.append((a+count,a+around+count,b+around+count,b+count))
for c in range(around):
    d=(c+1)%around
    polygons.append((c,c+count,d+count,d))
    a=(rows-1)*around+c;b=(rows-1)*around+d
    polygons.append((a,b,b+count,a+count))
uvs=[(c/around,row/(rows-1)) for row in range(rows) for c in range(around)]*2
socket=mesh('Restorative fitted leather socket v1',coordinates,polygons,'Nib_Leather','RestorativeSocket',uvs)
for p in socket.data.polygons:
    ids=list(p.vertices);columns=[i%around for i in ids]
    cap=len({(i%count)//around for i in ids})==1
    for li in p.loop_indices:
        i=socket.data.loops[li].vertex_index
        if cap:
            d=coordinates[i]-fit['startCenter' if (i%count)//around==0 else 'endCenter']
            socket.data.uv_layers.active.data[li].uv=(.5+d[0]*10,.5+d[1]*10)
        elif min(columns)==0 and max(columns)==around-1 and i%around==0:
            socket.data.uv_layers.active.data[li].uv.x=1.
source_weights=[{body.vertex_groups[g.group].name:g.weight for g in v.groups} for v in body.data.vertices]
skin_blends=[];max_influences=0
for index,(triangle,bary) in enumerate(fit['supports']):
    # Follow retained living tissue proximally; metal-facing edge is rigid at
    # the distal support plate. Blend over the measured socket, never to fingers.
    fraction=fit['fractions'][index]
    t=np.clip((fraction-.065)/.12,0,1);rigid=float(t*t*(3-2*t));skin_blends.append(1-rigid)
    weights={'LowerArm_L':rigid}
    for vi,w in zip(triangle,bary):
        for name,amount in source_weights[vi].items():weights[name]=weights.get(name,0)+(1-rigid)*w*amount
    weights={n:v for n,v in weights.items() if v>1e-8};total=sum(weights.values())
    max_influences=max(max_influences,len(weights))
    if max_influences>8:raise RuntimeError('Socket exceeds supported skin influences')
    for name,amount in weights.items():
        group=socket.vertex_groups.get(name) or socket.vertex_groups.new(name=name)
        group.add([index,index+count],amount/total,'REPLACE')
socket.shape_key_add(name='Basis',from_mix=False)
triangles=np.asarray([p[0] for p in fit['supports']],int);bary=np.asarray([p[1] for p in fit['supports']],float)
blend=np.asarray(skin_blends)[:,None];socket_shape_extents={}
for key in body.data.shape_keys.key_blocks:
    if key.name=='Basis':continue
    delta=np.asarray([v.co[:] for v in key.data])-points
    sampled=np.sum(delta[triangles]*bary[:,:,None],axis=1)*blend
    if np.max(np.linalg.norm(sampled,axis=1))<1e-8:continue
    target=socket.shape_key_add(name=key.name,from_mix=False)
    target.data.foreach_set('co',(coordinates+np.vstack([sampled,sampled])).astype(np.float32).ravel())
    socket_shape_extents[key.name]=float(np.max(np.linalg.norm(sampled,axis=1)))
attach_portable_drivers(socket,rig,json.loads(scene['deformation_contract']))

# The flat load plate is distal to every point on the actual cut loop. This
# covers the stump rather than letting an intersecting ring masquerade as fit.
axis=fit['axis'];center=fit['endCenter'];plate_ring=fit['outer'][-around:]+axis*.0007
plate_back=plate_ring+axis*.003
plate_points=np.vstack([plate_ring,plate_back,center+axis*.0007,center+axis*.0037])
plate_faces=[]
for c in range(around):
    d=(c+1)%around;plate_faces.extend([(c,d,d+around,c+around),(2*around,d,c),(2*around+1,c+around,d+around)])
plate=mesh('Restorative distal support plate v1',plate_points,plate_faces,'Nib_Steel','LowerArm_L')

def tube(name,path,radii,material,bone,sides=20):
    path=np.asarray(path,float);radii=np.broadcast_to(np.asarray(radii,float),len(path));points=[];uv=[]
    # Common transported frame for these gently curved ordinary guide tubes.
    for i,p in enumerate(path):
        tangent=path[min(i+1,len(path)-1)]-path[max(0,i-1)];tangent/=np.linalg.norm(tangent)
        first=np.cross(tangent,[0,1,0])
        if np.linalg.norm(first)<.01:first=np.cross(tangent,[1,0,0])
        first/=np.linalg.norm(first);second=np.cross(tangent,first)
        for j in range(sides):
            a=math.tau*j/sides;points.append(p+radii[i]*(first*math.cos(a)+second*math.sin(a)));uv.append((j/sides,i/(len(path)-1)))
    polygons=[]
    for i in range(len(path)-1):
        for j in range(sides):k=(j+1)%sides;polygons.append((i*sides+j,i*sides+k,(i+1)*sides+k,(i+1)*sides+j))
    polygons.extend([tuple(reversed(range(sides))),tuple((len(path)-1)*sides+j for j in range(sides))])
    result=mesh(name,points,polygons,material,bone,uv)
    for face in result.data.polygons:
        ids=list(face.vertices);columns=[i%sides for i in ids]
        cap=len({i//sides for i in ids})==1
        for li in face.loop_indices:
            i=result.data.loops[li].vertex_index;j=i%sides
            if cap:result.data.uv_layers.active.data[li].uv=(.5+.45*math.cos(math.tau*j/sides),.5+.45*math.sin(math.tau*j/sides))
            elif min(columns)==0 and max(columns)==sides-1 and j==0:result.data.uv_layers.active.data[li].uv.x=1.
    return result

rod_records=[]
for name,sign,material in [('radius',-1,'Nib_Steel'),('ulna',1,'Nib_Brass')]:
    start=elbow+np.asarray((sign*.012,0,-.015));end=wrist+np.asarray((sign*.009,0,.004))
    obj=tube('Restorative connected '+name+' guide v1',[start,end],.005,material,'LowerArm_L',24)
    rod_records.append({'object':obj.name,'startMeters':start.tolist(),'endMeters':end.tolist(),
                        'wristCenterDistanceMeters':float(np.linalg.norm(end-wrist))})

# A bearing centered at the anatomical wrist stays coincident under the
# distributed forearm twist and full hand rotation. It remains ordinary reach.
bpy.ops.mesh.primitive_uv_sphere_add(segments=32,ring_count=16,radius=.011,location=wrist)
bearing=bpy.context.object;bearing.name='Restorative anatomical wrist bearing v1'
for c in list(bearing.users_collection):c.objects.unlink(bearing)
collection.objects.link(bearing)
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
bearing.data.materials.append(bpy.data.materials['Nib_Brass'])
for p in bearing.data.polygons:p.use_smooth=True
bearing['variant']='grip';bearing['bone']='Hand_L';bearing.parent=rig
group=bearing.vertex_groups.new(name='Hand_L');group.add(list(range(len(bearing.data.vertices))),1,'REPLACE')
mod=bearing.modifiers.new('Portable wrist rotation','ARMATURE');mod.object=rig;mod.use_deform_preserve_volume=False
new.append(bearing)

# Existing palm top is below the wrist; this bearing mount bridges that 5 mm
# interface on the Hand side without moving palm or migrated digit surfaces.
tube('Restorative palm bearing mount v1',[wrist,wrist+np.asarray((.006,-.008,-.013))],[.009,.009],'Nib_Steel','Hand_L',24)
for sign in [-1,1]:
    start=center+np.asarray((sign*.017,.011,0))+axis*.004
    end=wrist+np.asarray((sign*.007,.003,.004))
    middle=(start+end)*.5+np.asarray((sign*.003,.009,0))
    path=[(1-t)**2*start+2*(1-t)*t*middle+t*t*end for t in np.linspace(0,1,17)]
    tube('Restorative continuous return cable '+str(sign)+' v1',path,.0024,'Nib_Dark','LowerArm_L',10)

archive=bpy.data.collections.new('PRESERVED Nib old disconnected socket wrist v1');scene.collection.children.link(archive)
prefixes=('Fitted prosthetic cuff','Restorative elbow spindle','Replacement radius piston','Replacement ulna piston','Restorative flexible cable')
old=[o for o in collection.objects if o.get('variant')=='grip' and o.name.startswith(prefixes)]
if len(old)!=6:raise RuntimeError('Unexpected old socket/rod/cable replacement scope '+str([o.name for o in old]))
archived_names=[o.name for o in old]
for obj in old:collection.objects.unlink(obj);archive.objects.link(obj);obj.hide_render=True;obj.hide_set(True)
archive.hide_render=True;archive.hide_viewport=True

# Pose only the unchanged rig. Compare the two independently transformed wrist
# frames through all clips, not just the rest state or one favorable view.
pose_checks=[];max_error=0
rest=Vector(wrist)
for name in canonical:
    action=bpy.data.actions[name];rig.animation_data.action=action
    start,end=map(float,action.frame_range)
    for phase in np.linspace(0,1,9):
        frame=start+(end-start)*float(phase);scene.frame_set(int(frame),subframe=frame%1);bpy.context.view_layer.update()
        forearm=rig.pose.bones['LowerArm_L'].matrix@rig.data.bones['LowerArm_L'].matrix_local.inverted()@rest
        hand=rig.pose.bones['Hand_L'].matrix@rig.data.bones['Hand_L'].matrix_local.inverted()@rest
        error=(forearm-hand).length;max_error=max(error,max_error)
        pose_checks.append({'action':name,'phase':float(phase),'wristCenterErrorMeters':error})
if max_error>2e-6:raise RuntimeError('Wrist bearing center separates under actual action '+str(max_error))
for name,digest in retained.items():
    if surface_hash(bpy.data.objects[name])!=digest:raise RuntimeError('Grip fitting altered existing source mesh '+name)
if rig_contract(rig)!=contract:raise RuntimeError('Grip fitting changed bind/action contract')
candidate_hashes={o.name:surface_hash(o) for o in new}
for obj in collection.objects:
    show=obj.get('variant','all') in ['all','organic','natural'];obj.hide_set(not show);obj.hide_render=not show
rig.animation_data.action=bpy.data.actions['Idle'];scene.frame_set(1)
scene['source_version']='Coherent Nib restorative socket/wrist v1; actual pose/likeness review pending'
scene['nib_restorative_socket']=json.dumps({'inputSha256':args.source_sha256,'naturalMeshesAndAllActionsUnchanged':True,'ordinaryRestorationOnly':True,'artisticAcceptance':False})
for p in [Path(__file__),HERE/'socket_geometry.py']:
    text=bpy.data.texts.new('Restorative socket v1 '+p.name);text.write(p.read_text())
target=args.output_dir/'Nib_Coherent_RestorativeSocket_v1.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(target),compress=True)
bpy.ops.wm.open_mainfile(filepath=str(target),load_ui=False)
if rig_contract(bpy.data.objects['Nib_Rig'])!=contract:raise RuntimeError('Saved source changed rig/actions')
for name,digest in {**retained,**candidate_hashes}.items():
    if surface_hash(bpy.data.objects[name])!=digest:raise RuntimeError('Saved source changed mesh '+name)
if sha(args.source)!=args.source_sha256:raise RuntimeError('Pinned input changed')
report={'status':'Actual saved/reopened socket and wrist fit; actual posed review pending','source':str(args.source),
        'sourceSha256':args.source_sha256,'candidate':str(target),'candidateSha256':sha(target),'savedSourceReopened':True,
        'preservedRig':contract,'retainedMeshHashes':retained,'candidateMeshHashes':candidate_hashes,
        'socket':fit['report'],'socketSkinMaxInfluences':max_influences,'socketMorphExtentMeters':socket_shape_extents,
        'newParts':list(candidate_hashes),'archivedParts':archived_names,'guideRods':rod_records,
        'wristCenterPoseMaxErrorMeters':max_error,'wristCenterPoseSamples':pose_checks,
        'codeSha256':{p.name:sha(p) for p in [Path(__file__),HERE/'socket_geometry.py',HERE/'contracts.py']},
        'sharedChanged':False,'artisticAcceptance':False,'pending':['Actual socket cut coverage in neutral/Shoot',
        'Ordinary palm, joint and curled-digit contact','Axilla, garments, face, ears and groom remain unaccepted']}
(args.output_dir/'source.json').write_text(json.dumps(report,indent=2)+'\n',newline='\n')
print('NIB_RESTORATIVE_SOCKET_SAVED_AND_REOPENED',flush=True)
