"""Remove only named old groom controls from the proven PBR derivative.

This is a distinct engine pilot source, not a shared asset replacement. Original
canonical79 bind, clips, every retained mesh/UV/morph/weight and maps are exact.
"""
import argparse,json,sys
from pathlib import Path
import bpy,numpy as np
from mathutils import Matrix
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sys.path[:0]=[str(HERE),str(HERE.parent/'restorative_wip')]
from contracts import rig_contract,surface_hash
from strand_contract import sha

p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--source-sha256',required=True)
p.add_argument('--groom-report',type=Path,required=True);p.add_argument('--groom-report-sha256',required=True);p.add_argument('--output-dir',type=Path,required=True)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
if sha(a.source)!=a.source_sha256 or a.source_sha256!='fee71393f1a41355e309994118656494b320f1284f995259a5362fa82db0b4b1':raise RuntimeError('Frozen proven PBR source differs')
if sha(a.groom_report)!=a.groom_report_sha256:raise RuntimeError('Actual native groom receipt changed')
if a.output_dir.exists():raise RuntimeError('Preserve prior filtered source')
groom=json.loads(a.groom_report.read_text());names=[x['name']for x in groom['hiddenControlGroom']]
if len(names)!=22 or len(set(names))!=22:raise RuntimeError('Expected exact22 old groom objects')
bpy.ops.wm.open_mainfile(filepath=str(a.source),load_ui=False);scene=bpy.context.scene;rig=bpy.data.objects['Nib_Rig'];collection=bpy.data.collections['Nib_Authored_Components']
contract=rig_contract(rig)
if contract!=groom['preservedRig']:raise RuntimeError('Proven PBR and native groom bind/actions differ')
old={o.name:surface_hash(o)for o in bpy.data.objects if o.type=='MESH'}
def color_contract(obj):
    attrs=obj.data.color_attributes;layers={}
    for layer in attrs:
        values=np.empty(len(layer.data)*4,np.float32);layer.data.foreach_get('color',values)
        layers[layer.name]={'type':layer.data_type,'domain':layer.domain,'valuesSha256':__import__('hashlib').sha256(values.tobytes()).hexdigest()}
    return {'layers':layers,'activeIndex':attrs.active_color_index,'renderIndex':attrs.render_color_index}
old_colors={o.name:color_contract(o)for o in collection.objects if o.type=='MESH'}
if any(name not in collection.objects for name in names):raise RuntimeError('Named removed groom is not an authored component')
rig.animation_data.action=None
for track in rig.animation_data.nla_tracks:track.mute=True
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
scene.frame_set(1);bpy.context.view_layer.update()
if np.max(abs(np.asarray(rig.matrix_world)-np.eye(4)))>1e-7:raise RuntimeError('Canonical rest world/armature identity required')
roots=[]
for region in groom['regions']:
    obj=bpy.data.objects[region['sourceSurfaceObject']]
    def array(key):
        e=region['files'][key];path=a.groom_report.parent/region['dataDirectory']/e['path']
        if sha(path)!=e['sha256']:raise RuntimeError('Native sidecar bytes changed '+key)
        return np.fromfile(path,dtype='<i4'if e['dtype']=='int32-le'else'<f4').reshape(e['shape'])
    points=array('positions');counts=array('curveCounts');starts=np.r_[0,np.cumsum(counts)[:-1]]
    ids=array('rootTriangleVertexIndices');weights=array('rootBarycentrics')
    mesh_points=np.asarray([obj.matrix_world@v.co for v in obj.data.vertices],float)
    expected=np.einsum('nij,ni->nj',mesh_points[ids],weights.astype(float));error=np.linalg.norm(expected-points[starts],axis=1)
    if float(error.max())>1e-6:raise RuntimeError('Native roots do not match proven PBR source topology '+region['name'])
    roots.append({'region':region['name'],'surface':obj.name,'rootCount':len(counts),'maximumSourceCorrespondenceErrorMeters':float(error.max()),'sourceVertices':len(mesh_points)})
removed=[]
for name in names:
    obj=bpy.data.objects[name]
    if not obj.name.startswith(('Nib v6 cards ','Nib v6 opaque accents '))or obj.get('bone')not in ['Head','Ear_L','Ear_R']:raise RuntimeError('Removal list contains non-head/ear groom '+name)
    removed.append({'name':name,'surfaceSha256':old[name],'triangles':sum(len(p.vertices)-2 for p in obj.data.polygons),'vertices':len(obj.data.vertices),'materials':[m.name for m in obj.data.materials]})
    bpy.data.objects.remove(obj,do_unlink=True)
retained={k:v for k,v in old.items()if k not in names}
binding_skin={r['sourceSurfaceObject']for r in groom['regions']};binding_attribute=[]
for obj in collection.objects:
    if obj.type!='MESH':continue
    attrs=obj.data.color_attributes
    if 'KKGroomBindable'in attrs:raise RuntimeError('Binding pilot attribute already exists')
    before=old_colors[obj.name];values=np.zeros((len(obj.data.vertices),4),np.float32)
    if obj.name in binding_skin:values[:,3]=1
    layer=attrs.new(name='KKGroomBindable',type='FLOAT_COLOR',domain='POINT');layer.data.foreach_set('color',values.ravel())
    if before['layers']:
        attrs.active_color_index=before['activeIndex'];attrs.render_color_index=before['renderIndex']
    after=color_contract(obj)
    if any(after['layers'].get(n)!=v for n,v in before['layers'].items()):raise RuntimeError('Existing vertex color changed '+obj.name)
    binding_attribute.append({'object':obj.name,'eligible':obj.name in binding_skin,'vertices':len(values),'originalColorLayers':before})
used={m.name:m for o in collection.objects if o.type=='MESH'for m in o.data.materials if m}
old_card_contract=json.loads(scene.get('nib_groom_material_contract','[]'))
scene['nib_groom_material_contract']=json.dumps([m for m in old_card_contract if m['name']in used])
texture_dir=a.source.parent/'textures';texture_hashes={f.name:sha(f)for f in texture_dir.glob('*')if f.is_file()}
connected_images={}
for material in used.values():
    for node in material.node_tree.nodes if material.use_nodes else []:
        if node.type!='TEX_IMAGE'or not node.image:continue
        image=node.image;original=Path(bpy.path.abspath(image.filepath));target=texture_dir/original.name
        if not target.is_file()or (original.is_file()and sha(original)!=sha(target)):raise RuntimeError('Durable PBR image path/hash differs '+image.name)
        image.filepath=str(target);image.reload();size=list(image.size)
        if not image.has_data or min(size)<=0:raise RuntimeError('Connected PBR image failed decode')
        connected_images[image.name]={'path':str(target),'sha256':sha(target),'colorspace':image.colorspace_settings.name,'size':size}
for name,digest in retained.items():
    if surface_hash(bpy.data.objects[name])!=digest:raise RuntimeError('Filtered target changed retained mesh '+name)
if rig_contract(rig)!=contract:raise RuntimeError('Filtering changed original bind/actions')
anchors={n:{'headBlenderWorldMeters':list(rig.matrix_world@rig.data.bones[n].head_local),'tailBlenderWorldMeters':list(rig.matrix_world@rig.data.bones[n].tail_local)}for n in ['Root','Pelvis','Head','Eye_L','Eye_R','Ear_L','Ear_R','Hand_L','Hand_R','Foot_L','Foot_R','WeaponMuzzle','WeaponAim']}
scene['native_groom_removed_control_names']=json.dumps(names);scene['source_version']='Isolated native groom engine target; exact proven PBR minus named22 control groom meshes'
rig.animation_data.action=bpy.data.actions['Idle'];scene.frame_set(1);a.output_dir.mkdir(parents=True)
target=a.output_dir/'Nib_NativeGroom_FilteredTarget_PBR.blend';bpy.ops.wm.save_as_mainfile(filepath=str(target),compress=True)
bpy.ops.wm.open_mainfile(filepath=str(target),load_ui=False)
if rig_contract(bpy.data.objects['Nib_Rig'])!=contract:raise RuntimeError('Saved filtered target lost bind/actions')
if any(name in bpy.data.objects for name in names):raise RuntimeError('Saved filtered target retained old groom objects')
for name,digest in retained.items():
    if surface_hash(bpy.data.objects[name])!=digest:raise RuntimeError('Saved filtered source changed retained mesh '+name)
for entry in binding_attribute:
    obj=bpy.data.objects[entry['object']];current=color_contract(obj);before=entry['originalColorLayers']
    if any(current['layers'].get(n)!=v for n,v in before['layers'].items()):raise RuntimeError('Saved existing color payload changed')
    data=obj.data.color_attributes['KKGroomBindable'].data;values=np.empty((len(data),4),np.float32);data.foreach_get('color',values.ravel())
    if np.any(values[:,:3]!=0)or np.any(values[:,3]!=(1 if entry['eligible']else 0)):raise RuntimeError('Saved binding eligibility differs')
for name,e in connected_images.items():
    image=bpy.data.images[name];path=Path(bpy.path.abspath(image.filepath));size=list(image.size)
    if sha(path)!=e['sha256']or image.colorspace_settings.name!=e['colorspace']or not image.has_data or size!=e['size']:raise RuntimeError('Saved portable image differs '+name)
if sha(a.source)!=a.source_sha256:raise RuntimeError('Frozen PBR input mutated')
shared=ROOT/'benchmark/shared/characters/nib/Nib_Natural.fbx'
report={'status':'Actual filtered native-groom target source; isolated FBX export/import pending','source':str(a.source),'sourceSha256':a.source_sha256,
    'candidate':str(target),'candidateSha256':sha(target),'savedSourceReopened':True,'nativeGroomSourceSha256':groom['candidateSha256'],'nativeGroomReportSha256':a.groom_report_sha256,
    'removed':removed,'retainedMeshHashes':retained,'preservedRig':contract,'nativeRootCorrespondence':roots,'connectedImages':connected_images,'textureDirectory':str(texture_dir),'textureHashes':texture_hashes,
    'coordinateContract':{'units':'meters','sourceAxes':{'right':'+X','up':'+Z','characterForward':'-Y','handedness':'right'},'armatureWorldIsIdentity':True,'restAnchors':anchors,'fbxAxisForward':'-Z','fbxAxisUp':'Y','fbxScaleOptions':'FBX_SCALE_UNITS','currentSharedNaturalFbxSha256':sha(shared),'engineActorMappingVerified':False,'requiredEngineGate':'Fit/check actual imported canonical anchors against these source values; do not assume a Unity or Unreal handedness flip'},
    'addedBindingAttribute':{'name':'KKGroomBindable','type':'FLOAT_COLOR','domain':'POINT','rgb':[0,0,0],'eligibleAlpha':1,'otherAlpha':0,'objects':binding_attribute,'existingColorPayloadsExact':True,'unrealImported':False},
    'artisticAcceptance':False,'sharedChanged':False,'existingFaceBodyFuzzRetained':True,'sourceReceiptKind':'filtered exact matching PBR source with additive binding mask','codeSha256':sha(Path(__file__))}
(a.output_dir/'source.json').write_text(json.dumps(report,indent=2)+'\n',newline='\n');print('NIB_NATIVE_FILTERED_TARGET_SAVED_AND_REOPENED',flush=True)
