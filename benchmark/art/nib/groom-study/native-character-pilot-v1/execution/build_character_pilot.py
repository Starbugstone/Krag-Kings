"""Isolated e1cdbd native strand pilot. No simulation, card generation or export promotion."""
import argparse,hashlib,json,math,random,sys
from pathlib import Path
import bpy,numpy as np
from mathutils import Matrix,Vector,Quaternion

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sys.path[:0]=[str(HERE),str(HERE.parent/'restorative_wip'),str(HERE.parent/'macroface_wip'),str(HERE.parent/'surface_layers_wip'),str(HERE.parent/'v5_wip')]
from contracts import rig_contract,surface_hash
from native_surface import surface_copy,Sampler,native_deformer
from strand_contract import write_region,sha
from source_image_archive import remap_verified_images
from flow_guides import make as make_guide,head_selector
from nib_groom_v5 import ear_coordinates,configure_goggle_envelopes,avoid_goggles,GOGGLE_ENVELOPES

p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--source-sha256',required=True);p.add_argument('--output-dir',type=Path,required=True)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
if sha(a.source)!=a.source_sha256:raise RuntimeError('Pinned integrated source changed')
if a.source_sha256!='e1cdbd030b8b4de9abd073807e93c40e9d69348e5bcf97c519656f5e3599804b':raise RuntimeError('First pilot requires matching frozen canonical79')
if a.output_dir.exists():raise RuntimeError('Preserve previous native pilot output')
a.output_dir.mkdir(parents=True)
bpy.ops.wm.open_mainfile(filepath=str(a.source),load_ui=False)
scene=bpy.context.scene;rig=bpy.data.objects['Nib_Rig'];authored=bpy.data.collections['Nib_Authored_Components']
canonical=['Idle','Walk','Run','Melee','Shoot','Hit','FacePerformance']
for name in canonical:
    if name not in bpy.data.actions:raise RuntimeError('Canonical action missing '+name)
    bpy.data.actions[name].use_fake_user=True
contract=rig_contract(rig)
if len(contract['bones'])!=79 or np.max(abs(np.asarray(rig.matrix_world)-np.eye(4)))>1e-7:raise RuntimeError('Expected canonical79 identity armature')
retained={o.name:surface_hash(o)for o in bpy.data.objects if o.type=='MESH'}
prior_images=json.loads((ROOT/'benchmark/art/nib/groom-study/fine-strands-v1/source.json').read_text())['reopenedImages']
expected={x['name']:{'sha256':x['sha256'],'colorspace':x['colorSpace']}for x in prior_images}
images=remap_verified_images(bpy,ROOT,ROOT/'benchmark/art/nib/source-textures/macroface-regional-ed53df/manifest.json',expected)
inherited=json.loads((a.source.parent/'source.json').read_text())
groom=bpy.data.collections.new('Nib_Native_Groom_Pilot');scene.collection.children.link(groom)
support_collection=bpy.data.collections.new('Nib_Native_Groom_Attachment');scene.collection.children.link(support_collection)

def rest():
    rig.animation_data.action=None
    for track in rig.animation_data.nla_tracks:track.mute=True
    for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
    scene.frame_set(1);bpy.context.view_layer.update()
rest();configure_goggle_envelopes(authored)
head=bpy.data.objects['Nib v5 fitted animation face']
surfaces={'Head':head}
for side in ['L','R']:
    surfaces['Ear_'+side]=next(o for o in authored.objects if o.name.startswith('Fennec cupped ear ')and o.get('bone')=='Ear_'+side)
supports={name:surface_copy(obj,support_collection)for name,obj in surfaces.items()}
bpy.context.view_layer.update()

def head_clear(point):
    # Fine roots need no former broad-card footprint. Keep the actual strand
    # center outside goggles; later guide samples are also envelope checked.
    return (avoid_goggles(point)-point).length<1e-6

def ear_select(region,point,normal,hint):
    t,u=ear_coordinates(point)
    if not .045<t<.982:return False
    if region=='ear_exterior':return normal.y>.12
    if normal.y>-.15:return False
    if region=='ear_undercoat':return abs(u)>.53 or t<.24
    return (.60<abs(u)<.96 and t<.90)or(t<.25 and abs(u)<.55)

def hair_material(name,color):
    material=bpy.data.materials.new(name);material.use_nodes=True;nodes=material.node_tree.nodes;nodes.clear()
    out=nodes.new('ShaderNodeOutputMaterial');hair=nodes.new('ShaderNodeBsdfHairPrincipled');hair.parametrization='COLOR'
    hair.inputs['Color'].default_value=(*color,1);hair.inputs['Roughness'].default_value=.36
    if 'Radial Roughness'in hair.inputs:hair.inputs['Radial Roughness'].default_value=.45
    attribute=nodes.new('ShaderNodeAttribute');attribute.attribute_name='groom_color'
    material.node_tree.links.new(attribute.outputs['Color'],hair.inputs['Color']);material.node_tree.links.new(hair.outputs[0],out.inputs['Surface'])
    material.diffuse_color=(*color,1);return material

materials={'cream':hair_material('Nib_NativeCreamHair',(.46,.34,.21)),
           'tawny':hair_material('Nib_NativeTawnyHair',(.25,.105,.036))}
# Budgets are first-render proposals, not quality/performance acceptance.
definitions=[('HeadCream','Head','cream',[('undercoat',4000),('crown',1700),('fringe',1000),('temple_L',1000),('temple_R',1000),('nape',1300)])]
for side in ['L','R']:
    definitions.extend([(f'EarInnerCream_{side}','Ear_'+side,'cream',[('ear_locks',2200),('ear_undercoat',1300)]),
                        (f'EarOuterTawny_{side}','Ear_'+side,'tawny',[('ear_exterior',4500)])])
bone_names=list(rig.data.bones.keys());groups=[];native_objects=[];native_payload={};seed=621600
for name,surface_name,color_region,parts in definitions:
    obj=surfaces[surface_name];support=supports[surface_name];all_roots=[];all_positions=[];all_radii=[];all_colors=[];part_reports=[]
    side=1 if surface_name.endswith('_L')else-1
    for region,count in parts:
        def select(point,normal,hint):
            if surface_name=='Head':
                if not head_selector(region,point,normal,hint):return False
                if region in ['fringe','undercoat']and abs(hint.x)<.018 and hint.z<.353:return False
                return head_clear(point)
            return ear_select(region,point,normal,hint)
        sampler=Sampler(obj,support,select)
        roots,audit=sampler.sample(count,seed,head_clear if surface_name=='Head'else None)
        # Regional guides establish small coherent clumps. The remaining roots
        # are actual independent surface samples, not coincident card centers.
        guide_count=min(180,max(40,count//22));guide_roots,_=sampler.sample(guide_count,seed+719,head_clear if surface_name=='Head'else None)
        guides=[make_guide(region,Vector(r['point']),Vector(r['normal']),Vector(r['sourceHint']),seed+i,side)for i,r in enumerate(guide_roots)]
        guide_xyz=np.asarray([r['point']for r in guide_roots],float)
        for index,root in enumerate(roots):
            rng=random.Random(seed*100003+index);point=Vector(root['point']);normal=Vector(root['normal'])
            closest=int(np.argmin(np.sum((guide_xyz-np.asarray(root['point']))**2,axis=1)));guide=guides[closest]
            anchor=Vector(guide['root']);guide_normal=Vector(guide['normal']);rotation=guide_normal.rotation_difference(normal)
            middle=rotation@(Vector(guide['middle'])-anchor);tip=rotation@(Vector(guide['tip'])-anchor)
            length=rng.uniform(.70,1.12);under=region in ['undercoat','ear_undercoat','ear_exterior']
            if under:length*=.83
            tangent=tip.normalized();across=tangent.cross(normal)
            if across.length<1e-7:across=normal.cross(Vector((1,0,0)))
            across.normalize();waviness=rng.uniform(.00010,.00045)if under else rng.uniform(.00020,.00080)
            phase=rng.uniform(0,math.tau);strand=[]
            radius=rng.uniform(.000027,.000045)if under else rng.uniform(.000034,.000061)
            base=np.array((.42,.28,.15)if color_region=='cream'else(.22,.085,.022),float)*rng.uniform(.74,1.22)
            end=np.array((.65,.53,.35)if color_region=='cream'else(.43,.22,.070),float)*rng.uniform(.86,1.10)
            for j in range(9):
                t=j/8;displacement=(middle*(2*(1-t)*t)+tip*t*t)*length
                wave=across*(waviness*math.sin(t*math.pi)*math.sin(t*math.tau*1.3+phase))
                pnt=point+displacement+wave
                if surface_name=='Head'and j:pnt=avoid_goggles(pnt)
                strand.append(list(pnt));all_radii.append(radius*(1-.995*t)**.66)
                all_colors.append(list(base*(1-t*.65)+end*(t*.65)))
            if min((Vector(v)-Vector(u)).length for u,v in zip(strand,strand[1:]))<1e-7:raise RuntimeError('Degenerate native strand segment')
            all_positions.extend(strand);all_roots.append(root)
        part_reports.append({'region':region,**audit,'guides':guide_count});seed+=10000
    positions=np.asarray(all_positions,np.float32);radii=np.asarray(all_radii,np.float32);counts=[9]*len(all_roots)
    data=bpy.data.hair_curves.new('Nib native '+name);data.add_curves(counts);data.set_types(type='POLY')
    curves=bpy.data.objects.new('Nib native '+name,data);groom.objects.link(curves);data.attributes['position'].data.foreach_set('vector',positions.ravel())
    for attr,typ,domain,prop,values in [('radius','FLOAT','POINT','value',radii),
        ('groom_color','FLOAT_VECTOR','POINT','vector',all_colors),
        ('surface_uv_coordinate','FLOAT2','CURVE','vector',[r['attachmentUv']for r in all_roots]),
        ('groom_root_uv','FLOAT2','CURVE','vector',[r['sourceUv']for r in all_roots])]:
        field=data.attributes.get(attr)or data.attributes.new(attr,typ,domain);field.data.foreach_set(prop,np.asarray(values,np.float32).ravel())
    data.materials.append(materials[color_region]);native_deformer(curves,support)
    curves['native_groom_region']=name;curves['variant']='all';curves['surfaceSource']=obj.name
    entry=write_region(a.output_dir/'strands',name,positions,radii,counts,all_roots,all_colors,obj.name,support.name,bone_names)
    entry['parts']=part_reports;entry['material']=materials[color_region].name
    groups.append(entry);native_objects.append(curves);native_payload[name]={'roots':all_roots,'positions':positions,'radii':radii,'surface':surface_name}
    print('NIB_NATIVE_REGION_AUTHORED',name,len(counts),flush=True)

hidden=[]
for obj in authored.objects:
    if obj.type=='MESH'and obj.name.startswith(('Nib v6 cards ','Nib v6 opaque accents '))and obj.get('bone')in ['Head','Ear_L','Ear_R']:
        hidden.append({'name':obj.name,'previousHideRender':obj.hide_render,'previousHideViewport':obj.hide_get()});obj.hide_render=True;obj.hide_set(True);obj['native_groom_replaced_visibility']=True
if not hidden:raise RuntimeError('No old head/ear groom control groups identified')

def inspect_roots(label):
    bpy.context.view_layer.update();deps=bpy.context.evaluated_depsgraph_get();reports=[]
    for curves,entry in zip(native_objects,groups):
        name=entry['name'];payload=native_payload[name];support=supports[payload['surface']]
        evaluated=support.evaluated_get(deps);mesh=evaluated.to_mesh();xyz=np.asarray([support.matrix_world@v.co for v in mesh.vertices],float)
        root_ids=np.asarray([r['vertices']for r in payload['roots']],int);weights=np.asarray([r['barycentric']for r in payload['roots']],float)
        expected=np.einsum('nij,ni->nj',xyz[root_ids],weights);evaluated.to_mesh_clear()
        current=curves.evaluated_get(deps).data;points=np.empty(len(current.points)*3,np.float32);current.attributes['position'].data.foreach_get('vector',points);points=points.reshape(-1,3)
        actual=points[::9];errors=np.linalg.norm(actual-expected,axis=1);maximum=float(errors.max())
        moved=np.linalg.norm(actual-payload['positions'][::9],axis=1)
        reports.append({'region':name,'rootCount':len(actual),'maximumRootErrorMeters':maximum,'maximumRootMovementMeters':float(moved.max()),'rmsRootErrorMeters':float(np.sqrt(np.mean(errors*errors)))})
        if maximum>1e-5:raise RuntimeError('Native surface attachment differs '+str((label,reports[-1])))
    return {'pose':label,'regions':reports}

poses=[];rest();poses.append(inspect_roots('BindRest'))
for action,frame in [('Idle',45),('Run',8),('FacePerformance',16),('FacePerformance',103)]:
    rig.animation_data.action=bpy.data.actions[action];scene.frame_set(frame);poses.append(inspect_roots(action+':'+str(frame)))
rest();rig.pose.bones['EarTip_L'].rotation_euler.z=.18;poses.append(inspect_roots('Diagnostic EarTip_L local Z +0.18rad; no action edited'))
if max(r['maximumRootMovementMeters']for r in poses[-1]['regions']if r['region'].endswith('_L'))<.0005:raise RuntimeError('Ear-tip diagnostic did not deform groom roots')
rest()
exports=[]
for curves,entry in zip(native_objects,groups):
    bpy.ops.object.select_all(action='DESELECT');curves.select_set(True);bpy.context.view_layer.objects.active=curves
    path=a.output_dir/(entry['name']+'.abc')
    result=bpy.ops.wm.alembic_export(filepath=str(path),start=1,end=1,selected=True,flatten=False,curves_as_mesh=False,export_hair=True,export_particles=False,as_background_job=False,global_scale=1.)
    if 'FINISHED'not in result:raise RuntimeError('Native groom ABC export did not finish')
    exports.append({'region':entry['name'],'path':path.name,'sha256':sha(path),'bytes':path.stat().st_size,'axes':'ABC(x,z,-y) from Blender(x,y,z)','units':'meters','standardWidth':'per-point diameter = 2*sidecar radius'})
for name,digest in retained.items():
    if surface_hash(bpy.data.objects[name])!=digest:raise RuntimeError('Native groom changed non-groom mesh '+name)
if rig_contract(rig)!=contract:raise RuntimeError('Native groom changed bind/actions')
scene['native_groom_pilot']=True;scene['source_version']='Native Hair Curves pilot on artistically unaccepted integrated e1cdbd; no simulation'
rig.animation_data.action=bpy.data.actions['Idle'];scene.frame_set(1)
target=a.output_dir/'Nib_NativeGroom_Pilot_v1.blend';bpy.ops.wm.save_as_mainfile(filepath=str(target),compress=True)
bpy.ops.wm.open_mainfile(filepath=str(target),load_ui=False)
if rig_contract(bpy.data.objects['Nib_Rig'])!=contract:raise RuntimeError('Saved native pilot lost rig/takes')
for name,digest in retained.items():
    if surface_hash(bpy.data.objects[name])!=digest:raise RuntimeError('Saved native pilot changed original mesh '+name)
for entry in groups:
    data=bpy.data.objects['Nib native '+entry['name']].data;actual=np.empty(len(data.points)*3,np.float32);data.attributes['position'].data.foreach_get('vector',actual)
    if not np.array_equal(actual.reshape(-1,3),native_payload[entry['name']]['positions']):raise RuntimeError('Saved native curve points changed')
    if not data.surface or data.surface_uv_map!='NativeGroomAttachment':raise RuntimeError('Saved surface attachment disappeared')
if sha(a.source)!=a.source_sha256:raise RuntimeError('Frozen source mutated')
roundtrips=[]
for entry,export in zip(groups,exports):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    result=bpy.ops.wm.alembic_import(filepath=str(a.output_dir/export['path']),as_background_job=False)
    objects=[o for o in bpy.context.scene.objects if o.type=='CURVES']
    if 'FINISHED'not in result or len(objects)!=1:raise RuntimeError('Expected one native curves object on character ABC readback')
    data=objects[0].data;values=np.empty(len(data.points)*3,np.float32);data.attributes['position'].data.foreach_get('vector',values)
    payload=native_payload[entry['name']];expected=payload['positions'];actual=values.reshape(-1,3)
    if actual.shape!=expected.shape or len(data.curves)!=entry['curveCount']:raise RuntimeError('Character ABC counts differ')
    position_error=float(np.max(abs(actual-expected)));radii=np.empty(len(data.points),np.float32)
    if not data.attributes.get('radius'):raise RuntimeError('Character ABC lost native widths')
    data.attributes['radius'].data.foreach_get('value',radii);radius_error=float(np.max(abs(radii-payload['radii'])))
    if position_error>2e-6 or radius_error>1e-9:raise RuntimeError('Character ABC neutral payload differs '+str((entry['name'],position_error,radius_error)))
    roundtrips.append({'region':entry['name'],'curveCount':len(data.curves),'pointCount':len(data.points),'maxPositionComponentErrorMeters':position_error,'maxRadiusErrorMeters':radius_error})
report={'status':'Actual native character source; Neutral/Profile appearance and engine imports pending',
    'source':str(a.source),'sourceSha256':a.source_sha256,'candidate':str(target),'candidateSha256':sha(target),'savedSourceReopened':True,
    'preservedRig':contract,'retainedMeshHashes':retained,'hiddenControlGroom':hidden,'regions':groups,'exports':exports,'posedRootChecks':poses,
    'boneNames':bone_names,'imagesRemappedExactly':images,'curveCount':sum(g['curveCount']for g in groups),'pointCount':sum(g['pointCount']for g in groups),'nativeAlembicRoundtrips':roundtrips,
    'simulation':False,'nativeSurfaceDeformation':True,'genericAlembicGroomAttributesExported':False,'artisticAcceptance':False,'engineImported':False,'sharedChanged':False,
    'retainedWarnings':['Underlying integrated face/ear/scarf art remains unaccepted','Existing fine face/body fuzz retained; head/ear cards hidden only','Simulation and runtime cost not established'],
    'inheritedPreRenderGate':inherited['preRenderGate'],'codeSha256':{f.name:sha(f)for f in [Path(__file__),HERE/'native_surface.py',HERE/'strand_contract.py']}}
(a.output_dir/'source.json').write_text(json.dumps(report,indent=2)+'\n',newline='\n')
print('NIB_NATIVE_CHARACTER_GROOM_SAVED_AND_REOPENED',flush=True)
