"""Prepared actual neutral/back/Shoot cloth review; no source writes."""
import argparse,hashlib,json,sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE=Path(__file__).parent;ROOT=HERE.parents[3];BASE=ROOT/'benchmark/art/nib/garment-study/v2'
parser=argparse.ArgumentParser();parser.add_argument('--stage',choices=['shirt-straps','full'],default='shirt-straps')
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
SOURCE=BASE/('Nib_ShirtStrapsStudy_v2.blend' if args.stage=='shirt-straps' else 'Nib_GarmentStudy_v1.blend')
OUT=BASE/('shirt-straps-actual-views' if args.stage=='shirt-straps' else 'actual-views')
REPORT_PATH=BASE/('shirt-straps-source.json' if args.stage=='shirt-straps' else 'source.json')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
expected=json.loads(REPORT_PATH.read_text())['outputSha256']
if sha(SOURCE)!=expected:raise RuntimeError('Garment source/report mismatch')
if OUT.exists():raise RuntimeError('Preserve existing actual garment views')
OUT.mkdir(parents=True)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE),load_ui=False)
scene=bpy.context.scene;rig=bpy.data.objects['Nib_Rig'];collection=bpy.data.collections['Nib_Authored_Components']
for obj in collection.objects:
    visible=obj.get('variant','all') in ['all','natural','organic'];obj.hide_render=not visible;obj.hide_viewport=not visible
for track in rig.animation_data.nla_tracks:track.mute=True
scene.render.engine='BLENDER_WORKBENCH';scene.render.resolution_x=1000;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.use_compositing=False;scene.render.use_sequencer=False;scene.render.film_transparent=False
shade=scene.display.shading;shade.light='STUDIO';shade.color_type='SINGLE';shade.single_color=(.54,.54,.54);shade.show_shadows=True;shade.show_cavity=True;shade.cavity_type='BOTH';shade.background_type='WORLD'
scene.world.color=(.065,.065,.065);scene.display.render_aa='16';camera=scene.camera;camera.data.type='ORTHO';camera.data.ortho_scale=.88
report={'status':'Actual cloth diagnostics; concept/material/motion/contact acceptance pending','source':str(SOURCE),'sourceSha256':expected,'codeSha256':sha(Path(__file__)),'poses':[],'artisticAcceptance':False,'sharedChanged':False,'stage':args.stage,'inheritedScarf':'Retained unchanged and unaccepted' if args.stage=='shirt-straps' else 'New unaccepted garment'}
def surface(name):
    obj=bpy.data.objects[name];evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=evaluated.to_mesh()
    try:
        points=np.asarray([tuple(evaluated.matrix_world@v.co) for v in mesh.vertices]);mesh.calc_loop_triangles();triangles=np.asarray([t.vertices[:] for t in mesh.loop_triangles],dtype=np.int32)
    finally:evaluated.to_mesh_clear()
    if not np.isfinite(points).all():raise RuntimeError('Nonfinite posed cloth/anatomy')
    return points,triangles
for label,clip,phase,offset in [('Front','Idle',0,(0,-3,.08)),('Back','Idle',0,(0,3,.12)),('Shoot','Shoot',.46,(1.8,-3,.20))]:
    action=bpy.data.actions[clip];rig.animation_data.action=action;first,last=map(float,action.frame_range);frame=first+(last-first)*phase
    scene.frame_set(int(frame),subframe=frame%1);bpy.context.view_layer.update()
    p,t=surface('Continuous Nib anatomy organic');body=BVHTree.FromPolygons(p,t,all_triangles=True)
    metrics={}
    for name in ['Sleeveless dust undershirt','Nib v5 layered desert scarf','Overalls draped bib']:
        points,triangles=surface(name);areas=np.linalg.norm(np.cross(points[triangles[:,1]]-points[triangles[:,0]],points[triangles[:,2]]-points[triangles[:,0]]),axis=1)
        sampled=np.linspace(0,len(points)-1,min(1200,len(points)),dtype=int);distances=[]
        for index in sampled:
            hit,normal,_,distance=body.find_nearest(Vector(points[index]));signed=float((Vector(points[index])-hit).dot(normal));distances.append((signed,int(index),distance))
        distances.sort();metrics[name]={'vertices':len(points),'triangles':len(triangles),'zeroAreaTriangles':int(np.count_nonzero(areas<=1e-12)),
            'bodyClosestNormalSignedDistanceMinMeters':distances[0][0],
            'samplesBelowMinus1mm':sum(d<-.001 for d,_,_ in distances),'sampleCount':len(sampled),
            'worstSamples':[{'signedMeters':d,'vertex':i,'nearestDistanceMeters':near} for d,i,near in distances[:8]],
            'distanceInterpretation':'Closest-normal diagnostic, not proof of complete watertight collision absence'}
    target=Vector((0,-.015,.905));camera.location=target+Vector(offset);camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
    image=OUT/(label+'.png');scene.render.filepath=str(image);bpy.ops.render.render(write_still=True)
    report['poses'].append({'view':label,'clip':clip,'normalizedTime':phase,'frame':frame,'geometry':metrics,'image':str(image),'imageSha256':sha(image)})
    (OUT/'review.json').write_text(json.dumps(report,indent=2)+'\n',newline='\n')
if sha(SOURCE)!=expected:raise RuntimeError('Read-only garment review changed source')
print('NIB_SEWN_GARMENT_V2_REVIEW_COMPLETE',flush=True)
