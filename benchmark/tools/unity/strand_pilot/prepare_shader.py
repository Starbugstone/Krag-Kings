"""Prepare a native-strand Hair Physical graph using installed/official nodes.
This generates Unity-only derived shader data, not a third-party renderer fork.
"""
from pathlib import Path
import copy,hashlib,json
REPO=Path(__file__).resolve().parents[4]
BASE=REPO/'benchmark/local/unity-strand-hair-pilot'
SRC=BASE/'source/Runtime/HairMaterialDefaultLitSRP.shadergraph'
PHYS=REPO/'benchmark/unity/Library/PackageCache/com.unity.render-pipelines.high-definition@4509f627d0da/Runtime/RenderPipelineResources/ShaderGraph/Hair Physical.shadergraph'
def read(path):
 s=path.read_text(encoding='utf-8-sig');d=json.JSONDecoder();out=[]
 while s.strip():
  s=s.lstrip();o,n=d.raw_decode(s);out.append(o);s=s[n:]
 return out
obs=read(SRC);phys=read(PHYS);graph=obs[0];by={o['m_ObjectId']:o for o in obs}
get=lambda suffix:next(o for o in obs if o['m_Type'].endswith(suffix))
# Keep the package's real GPU vertex/width/velocity path, change only the
# HDRP surface model to physical hair with strand geometry.
get('.HDLitSubTarget')['m_Type']='UnityEditor.Rendering.HighDefinition.ShaderGraph.HairSubTarget'
old=get('.HDLitData');hair=copy.deepcopy(next(o for o in phys if o['m_Type'].endswith('.HairData')))
hair['m_ObjectId']=old['m_ObjectId'];hair.update(m_MaterialType=1,m_GeometryType=1,m_DirectionalFractionMode=1,m_EnvironmentSamples=0,m_AreaLightSamples=0)
obs[obs.index(old)]=hair
system=get('.SystemData');system.update(m_SurfaceType=1,m_RenderingPass=3,m_AlphaTest=False,m_DoubleSidedMode=1)
target=get('.HDTarget');target['m_SupportLineRendering']=True
graph['m_ActiveTargets']=[{'m_Id':target['m_ObjectId']}]
graph['m_Path']='Krag Kings/Native Groom'
# The package's default is a debug rainbow. Replace that connection with a
# real exposed regional fur color. Retain the source shader's other graph IDs.
prop=copy.deepcopy(next(o for o in phys if o.get('m_Name')=='Root Color' and o['m_Type'].endswith('ColorShaderProperty')))
prop['m_OverrideReferenceName']='_FurColor';prop['m_Name']='Fur Color';prop['isMainColor']=True
node=copy.deepcopy(next(o for o in phys if o['m_Type'].endswith('.PropertyNode') and o.get('m_Property',{}).get('m_Id')==prop['m_ObjectId']))
slots=[copy.deepcopy(next(o for o in phys if o['m_ObjectId']==s['m_Id'])) for s in node['m_Slots']]
for o in [prop,node]+slots:
 if o['m_ObjectId'] in by:raise RuntimeError('Unexpected cross-graph ID collision')
obs.extend([prop,node]+slots);graph['m_Properties'].append({'m_Id':prop['m_ObjectId']});graph['m_Nodes'].append({'m_Id':node['m_ObjectId']})
base=next(o for o in obs if o.get('m_Name')=='SurfaceDescription.BaseColor')
graph['m_Edges']=[e for e in graph['m_Edges'] if e['m_InputSlot']['m_Node']['m_Id']!=base['m_ObjectId']]
graph['m_Edges'].append({'m_OutputSlot':{'m_Node':{'m_Id':node['m_ObjectId']},'m_SlotId':slots[0]['m_Id']},'m_InputSlot':{'m_Node':{'m_Id':base['m_ObjectId']},'m_SlotId':0}})
# Unsupported metallic/occlusion ports are removed; no discarded surface
# output is allowed to obscure which material is actually being tested.
remove=set()
for o in obs:
 if o.get('m_Name') in ('SurfaceDescription.Metallic','SurfaceDescription.Occlusion','SurfaceDescription.BentNormal'):
  remove.add(o['m_ObjectId']);remove.update(s['m_Id'] for s in o['m_Slots'])
obs=[o for o in obs if o['m_ObjectId'] not in remove]
graph['m_Nodes']=[n for n in graph['m_Nodes'] if n['m_Id'] not in remove]
graph['m_FragmentContext']['m_Blocks']=[n for n in graph['m_FragmentContext']['m_Blocks'] if n['m_Id'] not in remove]
graph['m_Edges']=[e for e in graph['m_Edges'] if e['m_InputSlot']['m_Node']['m_Id'] not in remove and e['m_OutputSlot']['m_Node']['m_Id'] not in remove]
out=BASE/'prepared-shader';out.mkdir(exist_ok=True)
dst=out/'NativeFurPhysical.shadergraph'
if dst.exists():raise RuntimeError('Preserve prior graph preparation')
dst.write_text('\n\n'.join(json.dumps(o,indent=4) for o in obs)+'\n')
(out/'preparation.json').write_text(json.dumps({'status':'Prepared graph only; Unity import and actual rendering pending','sourceShaders':{str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (SRC,PHYS)},'outputSha256':hashlib.sha256(dst.read_bytes()).hexdigest(),'shader':'Physical Hair / Strands / HDRP High Quality Lines; official HairVertex GPU provider; regional _FurColor; shadow-map directional fraction; no cinematic multiple-scattering volume'},indent=2)+'\n')
print('NATIVE_HAIR_GRAPH_PREPARED',dst)
