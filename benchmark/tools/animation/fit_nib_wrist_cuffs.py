"""Fit proximal natural hand cuffs into the actual oblique forearm openings.

The original uniform hand fit preserves digit proportions but places the cuff
lateral/posterior to the anatomical forearm. Correct only its proximal skin and
attached glove details, leaving finger surfaces, bind and all actions intact.
"""
import argparse, collections, hashlib, json, sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector
from bpy_extras.anim_utils import action_get_channelbag_for_slot
sys.path.insert(0,str(Path(__file__).parent))
from export_contract import CLIPS,select_action
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if a.output.exists():raise RuntimeError('Preserve previous cuff source')
a.output.mkdir(parents=True);source_hash=sha(a.source);bpy.ops.wm.open_mainfile(filepath=str(a.source),load_ui=False)
rig=bpy.data.objects['Nib_Rig'];collection=bpy.data.collections['Nib_Authored_Components'];body=bpy.data.objects['Continuous Nib anatomy organic']
bind={b.name:[list(row) for row in b.matrix_local] for b in rig.data.bones}
def digest_actions():
 result={}
 for name in CLIPS:
  action=bpy.data.actions[name];select_action(bpy,rig,action);bag=action_get_channelbag_for_slot(action,rig.animation_data.action_slot)
  rows=[(c.data_path,c.array_index,[(list(k.co),list(k.handle_left),list(k.handle_right),k.interpolation,k.handle_left_type,k.handle_right_type) for k in c.keyframe_points]) for c in bag.fcurves]
  result[name]=hashlib.sha256(json.dumps(sorted(rows),sort_keys=True).encode()).hexdigest()
 return result
clips=digest_actions();select_action(bpy,rig,None)
for track in rig.animation_data.nla_tracks:track.mute=True
bpy.context.scene.frame_set(1);bpy.context.view_layer.update()
points=[body.matrix_world@v.co for v in body.data.vertices]
edges=collections.Counter(tuple(sorted((x,y))) for face in body.data.polygons for x,y in zip(list(face.vertices),list(face.vertices)[1:]+list(face.vertices)[:1]))
adj=collections.defaultdict(set)
for (x,y),count in edges.items():
 if count==1:adj[x].add(y);adj[y].add(x)
unseen=set(adj);loops=[]
while unseen:
 stack=[unseen.pop()];component=[]
 while stack:
  x=stack.pop();component.append(x);near=adj[x]&unseen;unseen-=near;stack.extend(near)
 loops.append(component)
report={'source':str(a.source),'sourceSha256':source_hash,'recipeSha256':sha(Path(__file__)),
 'status':'Actual proximal hand cuff fitting; posed union/body fit review required','sides':{},'sharedAssetsChanged':False,'engineExported':False,'artisticAcceptance':False}
for side,sign in [('L',1),('R',-1)]:
 candidates=[loop for loop in loops if .15<sign*sum(points[i].x for i in loop)/len(loop)<.26 and .60<sum(points[i].z for i in loop)/len(loop)<.66]
 if len(candidates)!=1:raise RuntimeError('Actual wrist boundary is ambiguous '+side)
 loop=candidates[0];target=sum((points[i] for i in loop),Vector())/len(loop)
 forearm=rig.data.bones['LowerArm_'+side];axis=(forearm.tail_local-forearm.head_local).normalized()
 hand=bpy.data.objects['Nib v5 coherent hand '+side]
 sample=[hand.matrix_world@v.co for v in hand.data.vertices if .630<(hand.matrix_world@v.co).z<.638]
 if len(sample)<40:raise RuntimeError('Missing actual proximal hand cross-section '+side)
 measured=Vector(np.median(np.array(sample),axis=0));desired=target+axis*((measured.z-target.z)/axis.z)
 delta=desired-measured;delta.z=0
 if delta.length>.035:raise RuntimeError('Unexpected proximal cuff mismatch')
 touched=[]
 for obj in list(collection.objects):
  if obj.type!='MESH' or obj.get('bone')!='Hand_'+side or obj.get('variant','all') not in ['natural','all']:continue
  if 'carbine' in obj.name.lower():continue
  if obj.data.shape_keys:raise RuntimeError('Explicit cuff shape transfer needed '+obj.name)
  inverse=obj.matrix_world.inverted();count=0;maximum=0.;digit_changed=0
  for vertex in obj.data.vertices:
   point=obj.matrix_world@vertex.co
   t=max(0.,min(1.,(point.z-.608)/(.635-.608)));t=t*t*(3-2*t)
   offset=delta*t
   if offset.length>1e-10:
    vertex.co=inverse@(point+offset);count+=1;maximum=max(maximum,offset.length)
    if point.z<=.608:digit_changed+=1
  if count:obj.data.update();touched.append({'object':obj.name,'verticesChanged':count,'maxDisplacementMeters':maximum,'verticesAtOrBelowDigitCutChanged':digit_changed})
 if not touched or any(row['verticesAtOrBelowDigitCutChanged'] for row in touched):raise RuntimeError('Invalid cuff scope')
 report['sides'][side]={'actualBodyWristBoundaryVertices':len(loop),'actualBodyBoundaryMean':list(target),'actualHandProximalSampleMedian':list(measured),
  'fittedProximalCenter':list(desired),'maximumTranslation':list(delta),'blendRangeZ':[.608,.635],'meshes':touched}
select_action(bpy,rig,bpy.data.actions['Idle']);bpy.context.scene.frame_set(1)
out=a.output/'Nib_FittedWristCuffs_Study_v1.blend';bpy.ops.wm.save_as_mainfile(filepath=str(out),compress=True)
bpy.ops.wm.open_mainfile(filepath=str(out),load_ui=False);rig=bpy.data.objects['Nib_Rig']
if bind!={b.name:[list(row) for row in b.matrix_local] for b in rig.data.bones}:raise RuntimeError('Cuff source changed bind')
if clips!=digest_actions():raise RuntimeError('Cuff source changed actions')
if any(not bpy.data.actions[n].use_fake_user for n in CLIPS):raise RuntimeError('Canonical action retention lost')
if sha(a.source)!=source_hash:raise RuntimeError('Cuff patch changed input')
report.update({'output':str(out),'outputSha256':sha(out),'reopenedSavedFile':True,'exactBindPreserved':True,'canonicalActionHashes':clips})
(a.output/'wrist-fit.json').write_text(json.dumps(report,indent=2)+'\n');print('NIB_WRIST_CUFF_FIT_COMPLETE',flush=True)
