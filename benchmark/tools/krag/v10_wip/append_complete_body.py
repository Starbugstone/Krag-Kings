"""Append a hidden editable cinematic body without replacing runtime modules.

This is a separate source study. It does not export FBX or change the shared
package, skeleton, existing mesh, material, shape target or action data.
"""
from pathlib import Path
import argparse,hashlib,json,sys
from collections import Counter
import bpy,numpy as np
from mathutils import Vector
folder=Path(__file__).resolve().parent;root=folder.parents[3]
sys.path.insert(0,str(folder.parent));sys.path.insert(0,str(folder))
from complete_body_fit import fit,lower_weights,smooth
import krag_anatomy,krag_face

parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--report',type=Path,required=True)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
if args.source.resolve()==args.output.resolve():raise ValueError('Preserve the input master')
source_hash=hashlib.sha256(args.source.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(args.source))
rig=bpy.data.objects['Krag_Rig'];bones={b.name:(b.head_local.copy(),b.tail_local.copy()) for b in rig.data.bones}
library=root/'benchmark/art/reference-anatomy/blender-studio-human-base-meshes/source/human-base-meshes-bundle-v1.4.1/human_base_meshes_bundle.blend'
with bpy.data.libraries.load(str(library),link=False) as (available,loaded):loaded.objects=['GEO-body_male_realistic']
reference=loaded.objects[0];original=reference.data
raw=np.asarray([tuple(v.co) for v in original.vertices],dtype=float)
faces=[list(p.vertices) for p in original.polygons if all(raw[i,2]<1.445 for i in p.vertices)]
used=sorted({i for p in faces for i in p});index={old:new for new,old in enumerate(used)}
polygons=[[index[i] for i in face] for face in faces];raw=raw[used];points=fit(raw)
edge_count=Counter(tuple(sorted((a,b))) for face in polygons for a,b in zip(face,face[1:]+face[:1]))
neck_boundary={i for edge,count in edge_count.items() if count==1 for i in edge if points[i,2]>1.70}
for i in neck_boundary:points[i,2]=1.840
collar=np.clip((points[:,2]-1.68)/.17,0,1)*np.clip((.24-np.abs(points[:,0]))/.09,0,1)
points[:,0]*=1+.11*collar;points[:,1]=.016+(points[:,1]-.016)*(1+.10*collar)
if not np.isfinite(points).all():raise AssertionError('Non-finite organic fit')
mesh=bpy.data.meshes.new('Krag complete organic editable cage');mesh.from_pydata(points,[],polygons);mesh.update()
mesh.materials.append(bpy.data.materials['Krag_SandstoneSkin'])
for polygon in mesh.polygons:polygon.use_smooth=True
attribute=mesh.attributes.new('krag_complete_body_source_position','FLOAT_VECTOR','POINT');attribute.data.foreach_set('vector',raw.astype(np.float32).ravel())
attribute=mesh.attributes.new('krag_complete_body_source_vertex','INT','POINT');attribute.data.foreach_set('value',np.asarray(used,dtype=np.int32))
collection=bpy.data.collections.new('CINEMATIC complete organic anatomy study');bpy.context.scene.collection.children.link(collection)
obj=bpy.data.objects.new('CINEMATIC Krag complete organic body',mesh);collection.objects.link(obj)
obj['cinematic_only']=True;obj['runtime_export']=False
obj['anatomical_status']='Provisional complete hidden organic anatomy; source and posed review required; unaccepted'
obj['anatomical_source']='Blender Studio Human Base Meshes 1.4.1 / GEO-body_male_realistic / CC0'
obj['anatomical_source_sha256']=hashlib.sha256(library.read_bytes()).hexdigest()
# There is intentionally no module property: existing runtime variant recipes
# select only their explicit modular objects and cannot ingest this hidden body.
groups={name:obj.vertex_groups.new(name=name) for name in bones}
max_influences=0;max_sum_error=0
for vertex,source_point in zip(mesh.vertices,raw):
    upper=krag_anatomy.anatomical_weights(vertex.co,bones)
    lower=lower_weights(vertex.co)
    amount=float(smooth((vertex.co.z-.980)/.140))
    if abs(source_point[0])>.240 and source_point[2]>.650:amount=1
    weights={}
    for name,value in upper:weights[name]=weights.get(name,0)+value*amount
    for name,value in lower:weights[name]=weights.get(name,0)+value*(1-amount)
    values=sorted(((n,w) for n,w in weights.items() if w>1e-7),key=lambda item:item[1],reverse=True)[:8]
    total=sum(w for n,w in values)
    if total<=0:raise AssertionError('Unweighted organic vertex')
    values=[(n,w/total) for n,w in values]
    for name,value in values:groups[name].add([vertex.index],value,'REPLACE')
    max_influences=max(max_influences,len(values));max_sum_error=max(max_sum_error,abs(sum(w for n,w in values)-1))
# Keep correctives on the low cage, before skeletal deformation and subdivision.
obj.shape_key_add(name='Basis',from_mix=False)
for name in krag_face.BODY:
    region='BioArm_L' if ('Shoulder' in name or 'Elbow' in name) else 'Garments'
    delta=krag_face.deform(region,points,name)
    key=obj.shape_key_add(name=name,from_mix=False);key.data.foreach_set('co',(points+delta).astype(np.float32).ravel())
for definition in krag_face.driver_manifest()['drivers']:
    if definition['kind']!='body':continue
    key=mesh.shape_keys.key_blocks[definition['morph']];driver=key.driver_add('value').driver;driver.type='SCRIPTED'
    for axis in 'xyz':
        variable=driver.variables.new();variable.name=axis;variable.type='TRANSFORMS';target=variable.targets[0];target.id=rig;target.bone_target=definition['bone'];target.transform_space='LOCAL_SPACE';target.transform_type='ROT_'+axis.upper()
    angle='2*acos(min(1,abs(cos(x/2)*cos(y/2)*cos(z/2)+sin(x/2)*sin(y/2)*sin(z/2))))*57.2957795131'
    driver.expression=f'min(1,max(0,(({angle})-{definition["start"]})/{definition["end"]-definition["start"]}))'
obj.parent=rig
armature=obj.modifiers.new('Organic body skeletal deformation','ARMATURE');armature.object=rig
subdivision=obj.modifiers.new('Editable cinematic anatomical surface','SUBSURF');subdivision.levels=2;subdivision.render_levels=3
# Editable UVs are retained for later real skin/merchandise texturing; this
# source uses the same object-coordinate skin recipe as the current master.
bpy.ops.object.select_all(action='DESELECT');obj.hide_set(False);obj.select_set(True);bpy.context.view_layer.objects.active=obj
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=1.1519,island_margin=.02);bpy.ops.object.mode_set(mode='OBJECT')
obj.hide_render=True;obj.hide_set(True)
collection['status']='Hidden authoring study. Hide runtime Body/arm modules and clothing, then show this body for anatomical review; do not export until approved.'
bpy.data.objects.remove(reference,do_unlink=True)
if original.users==0:bpy.data.meshes.remove(original)
for path in [Path(__file__),folder/'complete_body_fit.py']:
    text=bpy.data.texts.get(path.name) or bpy.data.texts.new(path.name);text.clear();text.write(path.read_text())
args.output.parent.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(args.output),compress=True)
receipt={'inputMaster':str(args.source),'inputSha256':source_hash,'outputMaster':str(args.output),'outputSha256':hashlib.sha256(args.output.read_bytes()).hexdigest(),'status':'Hidden complete-body study generated; no visual or posed anatomical acceptance','cageVertices':len(mesh.vertices),'cagePolygons':len(mesh.polygons),'neckBoundaryVertices':len(neck_boundary),'weights':{'maximumInfluences':max_influences,'maximumSumError':max_sum_error},'correctiveNames':krag_face.BODY,'liveModifiers':['Armature','Subdivision viewport2/render3'],'runtimeModulesChanged':False,'skeletonChanged':False,'notes':['Full feet/toes are provisional under-clothing anatomy.','Foot control rest height .24m is retained; actual ankle bending and ground contact must be reviewed, not inferred from weights.','Separate continuous head remains attached visually through the neck overlap; neck seam deformation must be reviewed.']}
args.report.write_text(json.dumps(receipt,indent=2)+'\n',newline='\n')
print('KRAG_COMPLETE_ORGANIC_STUDY_SAVED',flush=True)
