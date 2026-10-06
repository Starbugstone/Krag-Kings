"""Prepared installed Hair Curves authoring/Alembic fixture, not character art.

Three separate regional ABCs avoid assuming generic curve-attribute export in
Blender5.2. Exact native arrays/attributes remain in the editable .blend and
JSON sidecar; Unreal must independently validate import and width conversion.
"""
import argparse,hashlib,json,sys
from pathlib import Path
import bpy,numpy as np

p=argparse.ArgumentParser();p.add_argument('--output-dir',type=Path,required=True)
args=p.parse_args(sys.argv[sys.argv.index('--')+1:])
if args.output_dir.exists():raise RuntimeError('Preserve prior native groom fixture')
args.output_dir.mkdir(parents=True);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1.;scene.render.fps=30
api={'version':bpy.app.version_string,'buildHash':bpy.app.build_hash.decode(),
     'hairCurvesCollection':hasattr(bpy.data,'hair_curves'),'alembicBuild':bpy.app.build_options.alembic,
     'alembicExportProperties':list(bpy.ops.wm.alembic_export.get_rna_type().properties.keys())}
(args.output_dir/'api.json').write_text(json.dumps(api,indent=2)+'\n',newline='\n')
if not api['hairCurvesCollection'] or not api['alembicBuild']:raise RuntimeError('Installed native curves/Alembic capability missing')
fixtures=[]
for group,name in enumerate(['CreamHead','PinkEarWisps','TawnyEarOuter']):
    data=bpy.data.hair_curves.new('Native '+name)
    data.add_curves([9,9,9,9]);data.set_types(type='POLY')
    obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj)
    xyz=[];radii=[];colors=[]
    for strand in range(4):
        for point in range(9):
            t=point/8
            xyz.append((group*.025+strand*.002+.003*np.sin(t*2.7),.004*t*t,.02*t))
            radii.append((.000040+strand*.000005)*(1-.96*t)**.65)
            colors.append((.54+.22*t,.32+.36*t,.15+.44*t))
    position=data.attributes['position'];position.data.foreach_set('vector',np.asarray(xyz,np.float32).ravel())
    radius=data.attributes.get('radius') or data.attributes.new('radius','FLOAT','POINT');radius.data.foreach_set('value',radii)
    group_attr=data.attributes.new('groom_group_id','INT','CURVE');group_attr.data.foreach_set('value',[group]*4)
    uv=data.attributes.new('groom_root_uv','FLOAT2','CURVE');uv.data.foreach_set('vector',np.asarray([(i/3,group/2)for i in range(4)],np.float32).ravel())
    color=data.attributes.new('groom_color','FLOAT_VECTOR','POINT');color.data.foreach_set('vector',np.asarray(colors,np.float32).ravel())
    data['groom_version_major']=1;data['groom_version_minor']=5
    fixtures.append({'name':name,'group':group,'curveCount':4,'pointCount':36,'curveOffsets':[0,9,18,27,36],
                     'pointsBlenderMeters':xyz,'radiusMeters':radii,'rootUv':[(i/3,group/2)for i in range(4)],
                     'colorLinearRgb':colors,'attributes':[{'name':a.name,'domain':a.domain,'type':a.data_type}for a in data.attributes]})
native=args.output_dir/'NativeHairCurves_Fixture.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(native),compress=True)
exports=[]
for f in fixtures:
    bpy.ops.object.select_all(action='DESELECT');obj=bpy.data.objects[f['name']];obj.select_set(True);bpy.context.view_layer.objects.active=obj
    path=args.output_dir/(f['name']+'.abc')
    kwargs={'filepath':str(path),'start':1,'end':1,'selected':True,'flatten':False,
            'curves_as_mesh':False,'export_hair':True,'export_particles':False,'as_background_job':False,'global_scale':1.}
    unsupported=set(kwargs)-set(api['alembicExportProperties'])
    if unsupported:raise RuntimeError('Installed export API differs '+str(unsupported))
    result=bpy.ops.wm.alembic_export(**kwargs)
    if 'FINISHED'not in result or not path.is_file() or path.stat().st_size<100:
        raise RuntimeError('Native regional Alembic export failed')
    exports.append({'region':f['name'],'path':path.name,'sha256':sha(path),'bytes':path.stat().st_size})
(args.output_dir/'fixture-exported.json').write_text(json.dumps({'status':'Native export written; readback pending',
    'api':api,'editableSourceSha256':sha(native),'fixtures':fixtures,'exports':exports,
    'unrealImported':False,'characterGroomCreated':False},indent=2)+'\n',newline='\n')
# Reopen the editable source and inspect actual data, not just successful save.
bpy.ops.wm.open_mainfile(filepath=str(native),load_ui=False)
for f in fixtures:
    obj=bpy.data.objects[f['name']];data=obj.data
    actual=np.empty(len(data.points)*3,np.float32);data.attributes['position'].data.foreach_get('vector',actual)
    expected=np.asarray(f['pointsBlenderMeters'],np.float32).ravel()
    if obj.type!='CURVES' or not np.array_equal(actual,expected):raise RuntimeError('Saved native curve positions differ')
    r=np.empty(len(data.points),np.float32);data.attributes['radius'].data.foreach_get('value',r)
    if not np.array_equal(r,np.asarray(f['radiusMeters'],np.float32)):raise RuntimeError('Saved native curve radius differs')
roundtrips=[]
for e,f in zip(exports,fixtures):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    result=bpy.ops.wm.alembic_import(filepath=str(args.output_dir/e['path']),as_background_job=False)
    imported=[o for o in bpy.context.scene.objects if o.type in ['CURVES','CURVE']]
    row={'region':e['region'],'operatorResult':list(result),'objects':[{'name':o.name,'type':o.type}for o in imported]}
    if len(imported)!=1 or imported[0].type!='CURVES':
        raise RuntimeError('Expected one modern Hair Curves readback '+json.dumps(row))
    data=imported[0].data;actual=np.empty(len(data.points)*3,np.float32);data.attributes['position'].data.foreach_get('vector',actual)
    expected=np.asarray(f['pointsBlenderMeters'],np.float32).ravel()
    error=float(np.max(np.abs(actual-expected)))if actual.shape==expected.shape else None
    row.update({'curveCount':len(data.curves),'pointCount':len(data.points),'maximumPositionComponentErrorMeters':error,
                'attributes':[{'name':a.name,'domain':a.domain,'type':a.data_type}for a in data.attributes]})
    if error is None or error>1e-7 or len(data.curves)!=4:raise RuntimeError('Native ABC position/count readback differs '+json.dumps(row))
    radius=data.attributes.get('radius')
    if radius is None:raise RuntimeError('Native ABC lost standard widths/radius')
    r=np.empty(len(data.points),np.float32);radius.data.foreach_get('value',r)
    row['maximumRadiusErrorMeters']=float(np.max(np.abs(r-np.asarray(f['radiusMeters'],np.float32))))
    if row['maximumRadiusErrorMeters']>1e-9:raise RuntimeError('Native ABC radius readback differs')
    roundtrips.append(row)
report={'status':'Actual native fixture only; Unreal import and character grooming pending','api':api,
        'editableSourceSha256':sha(native),'sourceSavedAndReopened':True,'fixtures':fixtures,'exports':exports,'blenderRoundtrips':roundtrips,
        'alembicAxes':'Blender metres(x,y,z) maps to native ABC(x,z,-y); standard widths are2*radius in metres',
        'expected52Limitation':'Native generic groom_group_id/root_uv/color attributes are not exported by5.2; region files and exact sidecar retained',
        'unrealImported':False,'characterGroomCreated':False,'artisticAcceptance':False,'sharedChanged':False,
        'recipeSha256':sha(Path(__file__))}
(args.output_dir/'fixture.json').write_text(json.dumps(report,indent=2)+'\n',newline='\n')
print('NIB_NATIVE_HAIR_CURVES_FIXTURE_COMPLETE',flush=True)
