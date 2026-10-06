"""One scoped fix for the actual Unity6 duplicate built-in keyword failure."""
from pathlib import Path
import copy,hashlib,json,shutil
REPO=Path(__file__).resolve().parents[4]
BASE=REPO/'benchmark/local/unity-strand-hair-pilot'
SRC=BASE/'source/Runtime/HairVertex.shadersubgraph'
GRAPH=BASE/'prepared-shader/NativeFurPhysical.shadergraph'
OUT=BASE/'prepared-shader-v2'
if OUT.exists():raise RuntimeError('Preserve previous repair preparation')
OUT.mkdir()
def read(path):
 s=path.read_text(encoding='utf-8-sig');d=json.JSONDecoder();out=[]
 while s.strip():
  s=s.lstrip();o,n=d.raw_decode(s);out.append(o);s=s[n:]
 return out
def write(path,objects):path.write_text('\n\n'.join(json.dumps(o,indent=4) for o in objects)+'\n')
objects=read(SRC);before=copy.deepcopy(objects)
keyword=next(o for o in objects if o['m_Type'].endswith('.ShaderKeyword') and o.get('m_OverrideReferenceName')=='PROCEDURAL_INSTANCING_ON')
if keyword['m_KeywordDefinition']!=1:raise RuntimeError('Unexpected upstream keyword definition')
keyword['m_KeywordDefinition']=2 # exact installed enum: Predefined; no emitted #pragma
keyword['m_GeneratePropertyBlock']=False
subgraph=OUT/'HairVertexHDRP174.shadersubgraph';write(subgraph,objects)
guid=hashlib.md5(b'KragKings.NativeHair.HDRP174.PredefinedInstancing.v2').hexdigest()
meta=(SRC.with_suffix(SRC.suffix+'.meta')).read_text();old_guid=next(x.split(': ',1)[1] for x in meta.splitlines() if x.startswith('guid: '))
subgraph.with_suffix(subgraph.suffix+'.meta').write_text(meta.replace('guid: '+old_guid,'guid: '+guid,1))
shader=read(GRAPH)
node=next(o for o in shader if o.get('m_Name')=='HairVertex' and o['m_Type'].endswith('.SubGraphNode'))
if old_guid not in node['m_SerializedSubGraph']:raise RuntimeError('Wrong shader provider link')
node['m_SerializedSubGraph']=node['m_SerializedSubGraph'].replace(old_guid,guid)
write(OUT/'NativeFurPhysical.shadergraph',shader)
(OUT/'preparation.json').write_text(json.dumps({'status':'Prepared candidate repair; actual renderer rerun pending','reason':'Actual first GPU attempt failed because PROCEDURAL_INSTANCING_ON is declared twice. Treat the built-in keyword as Predefined in a local subgraph copy. HDRP retains the native procedural instancing directive.','upstreamUnchanged':True,'sourceHashes':{str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (SRC,GRAPH)},'exactSubgraphChanges':{'keyword':keyword['m_ObjectId'],'m_KeywordDefinition':[1,2],'m_GeneratePropertyBlock':[True,False]},'newSubgraphGuid':guid,'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.iterdir() if p.is_file()}},indent=2)+'\n')
# Only the isolated project's own new shader is replaced; keep its .meta.
for p in OUT.iterdir():
 if p.suffix in ('.shadergraph','.shadersubgraph','.meta'):shutil.copy2(p,BASE/'project/Assets/NativeGroom'/p.name)
source=REPO/'benchmark/tools/unity/strand_pilot/RenderProbe.cs'
s=source.read_text().replace('fixture-render-v1','fixture-render-v2');source.write_text(s)
shutil.copy2(source,BASE/'project/Assets/Editor/RenderProbe.cs')
job=json.loads((source.parent/'render.job.json').read_text());job['name']='unity-native-strand-fixture-render-v2'
job['arguments']=[x.replace('fixture-render-v1.log','fixture-render-v2.log') for x in job['arguments']]
job['successLog']=job['successLog'].replace('fixture-render-v1.log','fixture-render-v2.log')
(source.parent/'render-v2.job.json').write_text(json.dumps(job,indent=2)+'\n')
print('NATIVE_KEYWORD_REPAIR_PREPARED',OUT)
