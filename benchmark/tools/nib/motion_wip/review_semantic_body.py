"""Bounded actual neutral/Shoot semantic shoulder and retained-clothing review."""
import argparse,hashlib,json,sys
from pathlib import Path
import bpy,numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,required=True);parser.add_argument('--report',type=Path,required=True);parser.add_argument('--output-dir',type=Path,required=True)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:]);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();expected=sha(args.source);source_report=json.loads(args.report.read_text())
if source_report.get('candidateSha256')!=expected or not source_report.get('savedSourceReopened'):raise RuntimeError('Require the actual reopened semantic source report')
if args.output_dir.exists():raise RuntimeError('Preserve previous actual body review')
args.output_dir.mkdir(parents=True);bpy.ops.wm.open_mainfile(filepath=str(args.source),load_ui=False);scene=bpy.context.scene;rig=bpy.data.objects['Nib_Rig'];camera=scene.camera
for track in rig.animation_data.nla_tracks:track.mute=True
for obj in bpy.data.collections['Nib_Authored_Components'].objects:
    visible=obj.get('variant','all') in ['all','organic','natural'];obj.hide_render=not visible;obj.hide_set(not visible);obj.color=(.58,.58,.56,1)
    if obj.name=='Continuous Nib anatomy organic':obj.color=(.20,.48,.30,1)
scene.render.engine='BLENDER_WORKBENCH';scene.render.resolution_x=1100;scene.render.resolution_y=1100;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.render.use_compositing=False;scene.render.use_sequencer=False;scene.render.film_transparent=False
shade=scene.display.shading;shade.light='STUDIO';shade.color_type='OBJECT';shade.show_shadows=True;shade.show_cavity=True;shade.cavity_type='BOTH';shade.background_type='WORLD';scene.world.color=(.065,.065,.065);scene.display.render_aa='16';camera.data.type='ORTHO';camera.data.ortho_scale=.86
body=bpy.data.objects['Continuous Nib anatomy organic'];records=[]
for name,action,phase,offset in [('Neutral','Idle',0.,(1.4,-3,.20)),('Shoot','Shoot',.46,(1.8,-3,.20)),('ShootSide','Shoot',.46,(3,-.3,.12))]:
    rig.animation_data.action=bpy.data.actions[action];a,b=map(float,rig.animation_data.action.frame_range);frame=a+(b-a)*phase;scene.frame_set(int(frame),subframe=frame%1);bpy.context.view_layer.update();graph=bpy.context.evaluated_depsgraph_get()
    evaluated=body.evaluated_get(graph);mesh=evaluated.to_mesh();points=[body.matrix_world@v.co for v in mesh.vertices];faces=[list(p.vertices) for p in mesh.polygons];tree=BVHTree.FromPolygons(points,faces);body_bounds=[np.asarray(points).min(0).tolist(),np.asarray(points).max(0).tolist()];evaluated.to_mesh_clear();contacts=[]
    for part_name in ['Sleeveless dust undershirt','Overalls draped bib']:
        part=bpy.data.objects.get(part_name)
        if not part:raise RuntimeError('Expected retained garment missing '+part_name)
        ev=part.evaluated_get(graph);m=ev.to_mesh();ids=np.linspace(0,len(m.vertices)-1,min(len(m.vertices),2000)).astype(int);signed=[]
        for i in ids:
            p=part.matrix_world@m.vertices[int(i)].co;hit,n,idx,dist=tree.find_nearest(p)
            if hit is not None:signed.append(float((p-hit).dot(n)))
        ev.to_mesh_clear();contacts.append({'name':part_name,'samples':len(signed),'nearestNormalSignedMinMeters':min(signed),'belowMinus1mm':sum(v<-.001 for v in signed),'belowMinus5mm':sum(v<-.005 for v in signed),'scope':'Nearest-surface normal samples, not a watertight collision proof'})
    target=Vector((0,-.015,.905));camera.location=target+Vector(offset);camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();image=args.output_dir/(name+'.png');scene.render.filepath=str(image);bpy.ops.render.render(write_still=True)
    records.append({'view':name,'action':action,'normalizedTime':phase,'frame':frame,'image':str(image),'imageSha256':sha(image),'bodyBounds':body_bounds,'garmentContacts':contacts})
if sha(args.source)!=expected:raise RuntimeError('Read-only review changed source')
report={'status':'Actual isolated posed surface review; no automatic visual acceptance','source':str(args.source),'sourceSha256':expected,'sourceReportSha256':sha(args.report),'codeSha256':sha(Path(__file__)),'bodyColor':'green for ownership, all other materials neutral grey','renderer':'Blender Workbench actual skinned mesh','poses':records,'artisticAcceptance':False,'sharedChanged':False};(args.output_dir/'review.json').write_text(json.dumps(report,indent=2)+'\n',newline='\n');print('NIB_SEMANTIC_BODY_ACTUAL_REVIEW_COMPLETE',flush=True)
