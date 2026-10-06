"""Prepared actual UV/alpha audit and tiny source-card/patch comparison.

No source saves or atlas edits. A single real ear card and its actual nearest
neighbours are copied with exact UVs into a small contrasting diagnostic scene.
"""
import argparse,hashlib,json,sys,math
from pathlib import Path
import bpy,numpy as np
from mathutils import Matrix,Vector
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--source-sha256',required=True);p.add_argument('--output-dir',type=Path,required=True);args=p.parse_args(sys.argv[sys.argv.index('--')+1:])
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if sha(args.source)!=args.source_sha256:raise RuntimeError('Exact actual layered source required')
if args.output_dir.exists():raise RuntimeError('Preserve prior tuft diagnostic')
bpy.ops.wm.open_mainfile(filepath=str(args.source),load_ui=False);scene=bpy.context.scene;rig=bpy.data.objects['Nib_Rig'];obj=bpy.data.objects['Nib layered alpha ear_locks_L'];material=obj.data.materials[0]
rig.animation_data.action=None
for t in rig.animation_data.nla_tracks:t.mute=True
for b in rig.pose.bones:b.matrix_basis=Matrix.Identity(4)
scene.frame_set(1);bpy.context.view_layer.update();deps=bpy.context.evaluated_depsgraph_get();evaluated=obj.evaluated_get(deps);mesh=evaluated.to_mesh(preserve_all_data_layers=True,depsgraph=deps)
positions=np.asarray([tuple(obj.matrix_world@v.co)for v in mesh.vertices],float)
if len(positions)%21:raise RuntimeError('Unexpected actual card topology')
roots=positions.reshape((-1,21,3))[:,1,:]
# Median-height anterior rim card, chosen from actual saved geometry rather
# than a newly generated ideal tuft. Its twelve closest real neighbours retain
# their original positions/UVs; the single-card panel differs only by inclusion.
center=np.median(roots,axis=0);chosen=int(np.argmin(np.linalg.norm(roots-center,axis=1)))
near=np.argsort(np.linalg.norm(roots-roots[chosen],axis=1))[:12].tolist()
card=positions[chosen*21:(chosen+1)*21];origin=card.mean(axis=0);up=Vector(card[-2]-card[1]).normalized();right=Vector(card[2]-card[0]).normalized();normal=right.cross(up).normalized();right=up.cross(normal).normalized();frame=np.asarray([right,up,normal],float)
uv_layers=[{'name':u.name,'activeRender':u.active_render,'activeClone':getattr(u,'active_clone',None)}for u in mesh.uv_layers]
# Texture Coordinate -> UV samples the active render layer, which can differ
# from the authoring selection. Preserve the actual renderer's layer.
uv=next((u for u in mesh.uv_layers if u.active_render),mesh.uv_layers.active)
if uv is None:raise RuntimeError('Actual evaluated groom lacks UVs')
faces=[tuple(p.vertices)for p in mesh.polygons];loop_uv={}
for poly in mesh.polygons:
    for li in poly.loop_indices:
        vi=mesh.loops[li].vertex_index;value=tuple(uv.data[li].uv)
        if vi in loop_uv and loop_uv[vi]!=value:raise RuntimeError('Unexpected split UV inside isolated card')
        loop_uv[vi]=value

def value(v):
    if isinstance(v,(bool,int,float,str)):return v
    try:return list(v)
    except TypeError:return str(v)
node_rows=[]
for n in material.node_tree.nodes:
    node_rows.append({'name':n.name,'type':n.bl_idname,'operation':getattr(n,'operation',None),'image':n.image.name if n.type=='TEX_IMAGE'and n.image else None,
                     'inputs':{s.name:value(s.default_value)for s in n.inputs if hasattr(s,'default_value')},'uvMap':getattr(n,'uv_map',None),'interpolation':getattr(n,'interpolation',None)})
links=[{'fromNode':l.from_node.name,'fromSocket':l.from_socket.name,'toNode':l.to_node.name,'toSocket':l.to_socket.name}for l in material.node_tree.links]
image_rows=[];base=None
for n in material.node_tree.nodes:
    if n.type!='TEX_IMAGE'or not n.image:continue
    image=n.image;size=list(image.size);pixels=np.empty(size[0]*size[1]*4,np.float32);image.pixels.foreach_get(pixels);pixels=pixels.reshape((size[1],size[0],4))
    path=Path(bpy.path.abspath(image.filepath));entry={'node':n.name,'name':image.name,'path':str(path),'sha256':sha(path),'size':size,'channels':image.channels,'alphaMode':image.alpha_mode,'colorSpace':image.colorspace_settings.name,'alphaRange':[float(pixels[:,:,3].min()),float(pixels[:,:,3].max())],'coverageAbove045':float(np.mean(pixels[:,:,3]>.45))}
    if 'BaseColor'in image.name:base=(image,pixels.copy())
    image_rows.append(entry)
if base is None:raise RuntimeError('Actual card lacks base-color texture')
image,pixels=base
actual_uv=np.asarray([loop_uv[i]for i in range(chosen*21,(chosen+1)*21)],float);low=actual_uv.min(axis=0);high=actual_uv.max(axis=0)
x,y=np.meshgrid(np.linspace(low[0],high[0],129),np.linspace(low[1],high[1],129));px=x*(pixels.shape[1])-0.5;py=y*(pixels.shape[0])-0.5
ix=np.floor(px).astype(int);iy=np.floor(py).astype(int);fx=px-ix;fy=py-iy;ix=np.clip(ix,0,pixels.shape[1]-2);iy=np.clip(iy,0,pixels.shape[0]-2)
a=pixels[iy,ix,3]*(1-fx)*(1-fy)+pixels[iy,ix+1,3]*fx*(1-fy)+pixels[iy+1,ix,3]*(1-fx)*fy+pixels[iy+1,ix+1,3]*fx*fy
report={'status':'Actual assigned/evaluated source audit; tiny source geometry diagnostic follows','sourceSha256':args.source_sha256,'object':obj.name,'material':material.name,'selectedCard':chosen,'neighbourCards':near,'uvLayers':uv_layers,'activeUV':uv.name,'selectedUvBounds':[low.tolist(),high.tolist()],'bilinearSelectedUvCoverageAbove045':float(np.mean(a>.45)),'selectedTopRowsCoverageAbove045':float(np.mean(a[-8:]>.45)),'selectedRootRowsCoverageAbove045':float(np.mean(a[:8]>.45)),'images':image_rows,'nodes':node_rows,'links':links,'originalCycles':{k:value(getattr(scene.cycles,k,None))for k in ['samples','use_denoising','max_bounces','transparent_max_bounces','pixel_filter_type','filter_width']},'sourceUnchanged':True,'artisticAcceptance':False}
args.output_dir.mkdir(parents=True)
(args.output_dir/'audit-before-render.json').write_text(json.dumps(report,indent=2)+'\n',newline='\n')
print('NIB_ACTUAL_TUFT_SOURCE_AUDIT',json.dumps({'card':chosen,'uv':uv.name,'coverage':report['bilinearSelectedUvCoverageAbove045'],'tipCoverage':report['selectedTopRowsCoverageAbove045'],'bounces':report['originalCycles']['transparent_max_bounces']}),flush=True)
# Preserve exact evaluated positions/UVs in the copy. Only a rigid orthonormal
# frame and the two panel offsets change. The input scene is never saved.
for original in scene.objects:original.hide_render=True
probe_collection=bpy.data.collections.new('ACTUAL tuft diagnostic');scene.collection.children.link(probe_collection)
for label,indices,offset in [('single',[chosen],-.036),('actual_neighbours',near,.036)]:
    ids=[j for i in indices for j in range(i*21,(i+1)*21)];mapping={v:i for i,v in enumerate(ids)}
    selected=[f for f in faces if all(v in mapping for v in f)]
    q=(positions[ids]-origin)@frame.T;q[:,0]+=offset
    data=bpy.data.meshes.new('Actual copied '+label);data.from_pydata(q.tolist(),[],[tuple(mapping[v]for v in f)for f in selected]);data.update();layer=data.uv_layers.new(name=uv.name)
    for loop in data.loops:layer.data[loop.index].uv=loop_uv[ids[loop.vertex_index]]
    for poly in data.polygons:poly.use_smooth=True
    # Transport the actual evaluated corner normals under the same rigid frame.
    normal_matrix=np.asarray(obj.matrix_world.to_3x3().inverted().transposed(),float)
    original_normals=np.asarray([n.vector[:]for n in mesh.corner_normals])@normal_matrix.T
    original_normals/=np.linalg.norm(original_normals,axis=1,keepdims=True)
    normals=[]
    selected_set=set(ids)
    for poly in mesh.polygons:
        if all(v in selected_set for v in poly.vertices):
            for li in poly.loop_indices:normals.append((frame@original_normals[li]).tolist())
    data.normals_split_custom_set(normals);data.materials.append(material)
    copy=bpy.data.objects.new('Actual '+label,data);probe_collection.objects.link(copy)
evaluated.to_mesh_clear()
background=bpy.data.materials.new('Contrasting diagnostic checker');background.use_nodes=True;nodes=background.node_tree.nodes;nodes.clear();out=nodes.new('ShaderNodeOutputMaterial');emission=nodes.new('ShaderNodeEmission');checker=nodes.new('ShaderNodeTexChecker');coordinates=nodes.new('ShaderNodeTexCoord')
checker.inputs['Color1'].default_value=(.008,.038,.045,1);checker.inputs['Color2'].default_value=(.12,.020,.018,1);checker.inputs['Scale'].default_value=16
background.node_tree.links.new(coordinates.outputs['Generated'],checker.inputs['Vector']);background.node_tree.links.new(checker.outputs['Color'],emission.inputs['Color']);background.node_tree.links.new(emission.outputs[0],out.inputs['Surface'])
plane=bpy.data.meshes.new('Backdrop');plane.from_pydata([(-.16,-.12,-.045),(.16,-.12,-.045),(.16,.12,-.045),(-.16,.12,-.045)],[],[(0,1,2,3)]);plane.materials.append(background);back=bpy.data.objects.new('Contrasting background',plane);probe_collection.objects.link(back)
cam_data=bpy.data.cameras.new('Tuft camera');cam=bpy.data.objects.new('Tuft camera',cam_data);probe_collection.objects.link(cam);cam.location=(0,.005,.20);cam.rotation_euler=(0,0,0);cam_data.type='ORTHO';cam_data.ortho_scale=.145;scene.camera=cam
light_data=bpy.data.lights.new('Tuft area','AREA');light_data.energy=5;light_data.shape='DISK';light_data.size=.12;light=bpy.data.objects.new('Tuft area',light_data);probe_collection.objects.link(light);light.location=(-.04,.06,.14);light.rotation_euler=(Vector((0,0,0))-light.location).to_track_quat('-Z','Y').to_euler()
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.render.threads_mode='FIXED';scene.render.threads=4;scene.render.resolution_x=1200;scene.render.resolution_y=800;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.render.use_sequencer=False;scene.render.use_compositing=False
report['probes']=[]
# Change exactly one renderer control per comparison. A different sample count
# at the same time as denoising/bounces would not attribute the square ends.
original_bounces=report['originalCycles']['transparent_max_bounces']
probes=[('matched24',24,True,original_bounces),('raw24',24,False,original_bounces)]
if original_bounces!=32:probes.append(('raw24_bounces32',24,False,32))
for label,samples,denoise,bounces in probes:
    scene.cycles.samples=samples;scene.cycles.use_denoising=denoise;scene.cycles.transparent_max_bounces=bounces
    path=args.output_dir/(label+'.png');scene.render.filepath=str(path);bpy.ops.render.render(write_still=True)
    report['probes'].append({'image':path.name,'sha256':sha(path),'samples':samples,'denoising':denoise,'transparentMaxBounces':bounces,'left':'one actual source card','right':'same card plus eleven actual nearest source neighbours'})
if sha(args.source)!=args.source_sha256:raise RuntimeError('Read-only tuft study changed source')
report['scriptSha256']=sha(Path(__file__));(args.output_dir/'audit.json').write_text(json.dumps(report,indent=2)+'\n',newline='\n');print('NIB_ACTUAL_TUFT_AUDIT_COMPLETE',flush=True)
