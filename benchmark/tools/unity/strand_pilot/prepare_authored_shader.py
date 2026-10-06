"""Unity-only graph derivative reading actual linear strand colors/diameters.

Uses one small float texture per unresampled, sequentially ordered region.
This preparation does not establish GPU correctness or performance.
"""
from pathlib import Path
import copy,hashlib,json,uuid

ROOT=Path(__file__).resolve().parents[4]
PILOT=ROOT/'benchmark/local/unity-strand-hair-pilot'
BASE=PILOT/'prepared-shader-v2/NativeFurPhysical.shadergraph'
VERTEX=PILOT/'prepared-shader-v2/HairVertexHDRP174.shadersubgraph'
PHYSICAL=ROOT/'benchmark/unity/Library/PackageCache/com.unity.render-pipelines.high-definition@4509f627d0da/Runtime/RenderPipelineResources/ShaderGraph/Hair Physical.shadergraph'

def read(path):
    text=path.read_text(encoding='utf-8-sig');decoder=json.JSONDecoder();objects=[]
    while text.strip():
        text=text.lstrip();obj,n=decoder.raw_decode(text);objects.append(obj);text=text[n:]
    return objects
def ident(name):return uuid.uuid5(uuid.NAMESPACE_URL,'krag-kings-unity-authored-strand-data-v1/'+name).hex

def main():
    out=PILOT/'prepared-authored-shader-v2'
    if out.exists():raise RuntimeError('Preserve prior authored shader preparation')
    objects=read(BASE);official=read(PHYSICAL);vertex=read(VERTEX)
    graph=objects[0];by={o['m_ObjectId']:o for o in objects};ob={o['m_ObjectId']:o for o in official}
    hair=next(o for o in objects if o.get('m_Name')=='HairVertex')
    function=copy.deepcopy(next(o for o in vertex if o.get('m_FunctionName')=='Instancing'))
    function.update(m_ObjectId=ident('function'),m_Name='Authored Strand Data',m_FunctionName='KKAuthoredStrand',m_Precision=1)
    function['m_FunctionBody']='''uint width, height;
Data.tex.GetDimensions(width, height);
uint strand = min((uint)round(StrandIndex), height - 1);
float curvePoint = saturate(SurfaceUV.y) * (width - 1);
uint lo = (uint)floor(curvePoint);
uint hi = min(lo + 1, width - 1);
float4 value = lerp(Data.tex.Load(int3(lo, strand, 0)), Data.tex.Load(int3(hi, strand, 0)), frac(curvePoint));
Color = value.rgb;
WidthCm = value.a * 100.0;'''
    prop=copy.deepcopy(next(o for o in official if o['m_Type'].endswith('Texture2DShaderProperty')))
    original_prop_id=prop['m_ObjectId']
    prop.update(m_ObjectId=ident('property'),m_Guid={'m_GuidSerialized':str(uuid.UUID(ident('property-guid')))},m_Name='Authored Strand Data',m_RefNameGeneratedByDisplayName='Authored Strand Data',m_DefaultReferenceName='_AuthoredStrandData',m_OverrideReferenceName='_AuthoredStrandData',m_Value={'m_SerializedTexture':'{"texture":{"instanceID":0}}','m_Guid':''},useTilingAndOffset=False,useTexelSize=True)
    property_node=copy.deepcopy(next(o for o in official if o['m_Type'].endswith('.PropertyNode') and o.get('m_Property',{}).get('m_Id')==original_prop_id))
    texture_slot=copy.deepcopy(ob[property_node['m_Slots'][0]['m_Id']]);texture_slot.update(m_ObjectId=ident('texture-out'),m_DisplayName='Data')
    property_node.update(m_ObjectId=ident('property-node'),m_Property={'m_Id':prop['m_ObjectId']},m_Slots=[{'m_Id':texture_slot['m_ObjectId']}])
    slots=[]
    def slot(template,name,index,output=False):
        result=copy.deepcopy(template);result.update(m_ObjectId=ident('slot-'+name),m_Id=index,m_DisplayName=name,m_ShaderOutputName=name,m_SlotType=int(output),m_StageCapability=3)
        slots.append(result);return result
    texture_input=slot(texture_slot,'Data',0)
    one=next(o for o in objects if o['m_Type'].endswith('.Vector1MaterialSlot'))
    two=next(o for o in objects if o['m_Type'].endswith('.Vector2MaterialSlot'))
    three=next(o for o in objects if o['m_Type'].endswith('.Vector3MaterialSlot'))
    strand=slot(one,'StrandIndex',1);uv=slot(two,'SurfaceUV',2);color=slot(three,'Color',3,True);width=slot(one,'WidthCm',4,True)
    function['m_Slots']=[{'m_Id':s['m_ObjectId']} for s in slots]
    objects.extend([prop,property_node,texture_slot,function]+slots)
    graph['m_Properties'].append({'m_Id':prop['m_ObjectId']});graph['m_Nodes'].extend([{'m_Id':property_node['m_ObjectId']},{'m_Id':function['m_ObjectId']}])
    def edge(a,port,b,input_port):return {'m_OutputSlot':{'m_Node':{'m_Id':a['m_ObjectId']},'m_SlotId':port},'m_InputSlot':{'m_Node':{'m_Id':b['m_ObjectId']},'m_SlotId':input_port}}
    base_color=next(o for o in objects if o.get('m_Name')=='SurfaceDescription.BaseColor')
    line_width=next(o for o in objects if o.get('m_Name')=='VertexDescription.Width')
    graph['m_Edges']=[e for e in graph['m_Edges'] if e['m_InputSlot']['m_Node']['m_Id'] not in (base_color['m_ObjectId'],line_width['m_ObjectId'])]
    graph['m_Edges'].extend([edge(property_node,0,function,0),edge(hair,9,function,1),edge(hair,11,function,2),edge(function,3,base_color,0),edge(function,4,line_width,0)])
    assert len({o['m_ObjectId'] for o in objects})==len(objects)
    out.mkdir();path=out/'NativeFurAuthored.shadergraph';path.write_text('\n\n'.join(json.dumps(o,indent=4) for o in objects)+'\n')
    receipt={'status':'Prepared Unity-only authored color/diameter graph; not imported or rendered','inputs':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (BASE,VERTEX,PHYSICAL)},'outputSha256':hashlib.sha256(path.read_bytes()).hexdigest(),'layout':'Texture width=points per curve; height=curve count; linear float RGBA=(authored R,G,B,diameter metres)','requirements':['uniform points per curve','sequential unchanged strand ordering','no curve resampling or cluster reordering','native vertex positions/tangents retained'],'limitations':['Direct authored diameter replaces stock fitted taper; automatic LOD width compensation is not retained in this diagnostic','Actual GPU endpoint widths/colors and frame time remain unverified']}
    (out/'preparation.json').write_text(json.dumps(receipt,indent=2)+'\n');print('AUTHORED_SHADER_PREPARED',path)
if __name__=='__main__':main()
