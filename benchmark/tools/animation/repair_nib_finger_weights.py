"""Isolated anatomical proximal-digit weighting study on unchanged source skin.

No shape, bind or action changes. Proximal seeds use the original licensed hand
coordinates, with harmonic transition through the MCP and interdigital webs.
"""
import argparse,hashlib,json,sys
from pathlib import Path
import bpy
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(Path(__file__).parent),str(ROOT/'tools/nib/v5_wip'),str(ROOT/'tools/nib/restorative_wip')]
from nib_hand_v5 import SOURCE_CHAINS
from contracts import rig_contract,surface_hash
import hand_skin_domains as domains
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--source-sha256',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
if sha(a.source)!=a.source_sha256:raise RuntimeError('Pinned source changed')
if a.output.exists():raise RuntimeError('Preserve previous source and evidence')
a.output.mkdir(parents=True)
bpy.ops.wm.open_mainfile(filepath=str(a.source),load_ui=False)
rig=bpy.data.objects['Nib_Rig']; hand=bpy.data.objects['Nib v5 coherent hand L'];mesh=hand.data
before_rig=rig_contract(rig);retained={o.name:surface_hash(o) for o in bpy.data.objects if o.type=='MESH' and o!=hand}
geometry=np.asarray([v.co[:] for v in mesh.vertices],np.float32);faces=[list(p.vertices) for p in mesh.polygons]
original=mesh.attributes.get('Nib_OriginalHandCoordinate')
if original is None or original.data_type!='FLOAT_VECTOR':raise RuntimeError('Exact original reference coordinate missing')
points=np.empty((len(mesh.vertices),3),np.float32);original.data.foreach_get('vector',points.ravel())
fields,field_report=domains.solve(points,faces,source_cage=True,proximal_chains=SOURCE_CHAINS)
names,weights,weight_report=domains.weights(points,fields,SOURCE_CHAINS,side='L',joint_half_width=.008)
old=[{hand.vertex_groups[g.group].name:g.weight for g in v.groups} for v in mesh.vertices]
hand.vertex_groups.clear()
for name in names:hand.vertex_groups.new(name=name)
for index,row in enumerate(weights):
 for column in np.flatnonzero(row>1e-8):hand.vertex_groups[int(column)].add([index],float(row[column]),'REPLACE')
for index,digit in enumerate(domains.DIGITS+['Palm']):
 attribute=mesh.attributes.get('Nib_HandDomain_'+digit)
 if attribute is None:raise RuntimeError('Hand semantic field missing '+digit)
 attribute.data.foreach_set('value',np.asarray(fields[:,index],np.float32))
measure={}
for digit in domains.DIGITS:
 start,end=np.asarray(SOURCE_CHAINS[digit][:2]);v=end-start;length=np.linalg.norm(v);t=(points-start)@v/(length*length);distance=np.linalg.norm(points-start-t[:,None]*v,axis=1)
 mask=(t>.35)&(t<.65)&(distance<.008/.43);ids=np.flatnonzero(mask);cols=[i for i,name in enumerate(names) if name.startswith(digit)]
 measure[digit]={'sampleVertices':len(ids),'beforePalmRange':[min(old[i].get('Hand_L',0) for i in ids),max(old[i].get('Hand_L',0) for i in ids)],'afterPalmRange':[float(weights[mask,0].min()),float(weights[mask,0].max())],'beforeOwnDigitMean':float(np.mean([sum(w for n,w in old[i].items() if n.startswith(digit)) for i in ids])),'afterOwnDigitMean':float(weights[mask][:,cols].sum(axis=1).mean())}
assert np.array_equal(geometry,np.asarray([v.co[:] for v in mesh.vertices],np.float32))
hand_name=hand.name;new_hash=surface_hash(hand);output=a.output/'Nib_ProximalFingerWeights_v1.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(output),compress=True)
bpy.ops.wm.open_mainfile(filepath=str(output),load_ui=False)
if rig_contract(bpy.data.objects['Nib_Rig'])!=before_rig:raise RuntimeError('Saved source changed bind/actions')
for name,digest in retained.items():
 if surface_hash(bpy.data.objects[name])!=digest:raise RuntimeError('Saved source altered unrelated mesh '+name)
if surface_hash(bpy.data.objects[hand_name])!=new_hash:raise RuntimeError('Saved hand weights changed')
if sha(a.source)!=a.source_sha256:raise RuntimeError('Input source changed')
r={'source':str(a.source),'sourceSha256':a.source_sha256,'output':str(output),'outputSha256':sha(output),'recipeSha256':sha(Path(__file__)),'domainRecipeSha256':sha(Path(domains.__file__)),'status':'Actual proximal weighting candidate, pose and contact review required','savedSourceReopened':True,'preservedOtherMeshCount':len(retained),'bindAndActionContractPreserved':True,'handGeometryPreserved':True,'handPayloadSha256':new_hash,'domain':field_report,'weights':weight_report,'proximalSamples':measure,'maximumInfluences':int(np.max(np.count_nonzero(weights>1e-8,axis=1))),'sharedAssetsChanged':False,'engineExported':False,'artisticAcceptance':False}
(a.output/'finger-weights.json').write_text(json.dumps(r,indent=2)+'\n');print('NIB_PROXIMAL_FINGER_WEIGHTS_COMPLETE',flush=True)
