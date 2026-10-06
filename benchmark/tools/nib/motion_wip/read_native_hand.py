"""Read-only actual saved hand extraction without launching Blender.

Reads the file's own DNA offsets and Blender's installed header decoder. The
input is never modified; decompression is streamed into an ignored local file.
This does not evaluate animation or Blender modifiers: the saved hand already
has its construction subdivision applied and portable LBS weights stored.
"""
import argparse,hashlib,importlib.util,json,mmap,re,struct,subprocess,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True);parser.add_argument('--mesh-name',default='Nib v5 coherent hand L');args=parser.parse_args()
source=args.source.resolve();expected=hashlib.sha256(source.read_bytes()).hexdigest()
header_path=Path('/mnt/d/Program Files/Blender Foundation/Blender 5.2/5.2/scripts/modules/_blendfile_header.py')
spec=importlib.util.spec_from_file_location('_blendfile_header',header_path);module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
temporary=ROOT/'benchmark/local/nib-native-hand-readonly.blend'
marker=temporary.with_suffix('.source-sha256')
if not temporary.exists() or not marker.exists() or marker.read_text()!=expected:
    subprocess.run(['zstd','-q','-d','-f',str(source),'-o',str(temporary)],check=True)
    marker.write_text(expected)
file_stream=temporary.open('rb');stream=mmap.mmap(file_stream.fileno(),0,access=mmap.ACCESS_READ);header=module.BlendFileHeader(stream);block_header=header.create_block_header_struct();blocks=[];addresses={};scopes={};owner=None;active_scope={}
while True:
    block=module.BlockHeader(stream,block_header)
    if block.code==b'ENDB':break
    entry={'code':block.code,'offset':stream.tell(),'size':block.size,'address':block.addr_old,'dna':block.sdna_index,'count':block.count}
    if block.code!=b'DATA':owner=block.addr_old;scopes[owner]={}
    entry['owner']=owner;blocks.append(entry);addresses[block.addr_old]=entry
    scopes[owner][block.addr_old]=entry;stream.seek(block.size,1)
data=stream
dna=next(b for b in blocks if b['code']==b'DNA1');at=dna['offset']
def expect(value):
    global at
    if data[at:at+len(value)]!=value:raise RuntimeError('Invalid saved DNA section')
    at+=len(value)
def u32():
    global at
    value=struct.unpack_from('<I',data,at)[0];at+=4;return value
def strings():
    global at
    values=[]
    for _ in range(u32()):
        end=data.find(b'\0',at);values.append(data[at:end].decode('utf8'));at=end+1
    at=dna['offset']+((at-dna['offset']+3)&~3);return values
expect(b'SDNANAME');names=strings();expect(b'TYPE');types=strings();expect(b'TLEN')
sizes=struct.unpack_from('<'+'H'*len(types),data,at);at+=len(types)*2;at=dna['offset']+((at-dna['offset']+3)&~3);expect(b'STRC')
schemas=[];by_type={}
for _ in range(u32()):
    type_index,count=struct.unpack_from('<HH',data,at);at+=4;fields={};offset=0
    for _ in range(count):
        t,n=struct.unpack_from('<HH',data,at);at+=4;raw_name=names[n];pointer='*' in raw_name
        counts=[int(v) for v in re.findall(r'\[(\d+)\]',raw_name)];length=1
        for c in counts:length*=c
        name=re.sub(r'\[.*','',raw_name).lstrip('*').strip('()');size=(header.pointer_size if pointer else sizes[t])*length
        fields[name]={'type':types[t],'offset':offset,'size':size,'pointer':pointer,'count':length,'raw':raw_name};offset+=size
    schema={'name':types[type_index],'size':sizes[type_index],'computedSize':offset,'fields':fields};schemas.append(schema);by_type[schema['name']]=schema

def block_for(address):return active_scope.get(address,addresses.get(address))

def record(address,type_name=None):
    block=block_for(address)
    if block is None:raise RuntimeError('Missing saved pointer '+hex(address))
    typ=type_name or schemas[block['dna']]['name'];schema=by_type[typ]
    if schema['computedSize']!=schema['size']:raise RuntimeError('DNA size mismatch in '+typ)
    return block['offset'],typ
def info(rec,name):return by_type[rec[1]]['fields'][name]
def field(rec,name):
    item=info(rec,name);offset=rec[0]+item['offset']
    if item['pointer']:return struct.unpack_from('<Q',data,offset)[0]
    if item['type']=='char':return data[offset:offset+item['size']].split(b'\0')[0].decode('utf8',errors='replace')
    if item['type'] in ['int','float','short','uint64_t','int8_t','int64_t']:
        fmt={'int':'i','float':'f','short':'h','uint64_t':'Q','int8_t':'b','int64_t':'q'}[item['type']];values=struct.unpack_from('<'+fmt*item['count'],data,offset)
        return values[0] if len(values)==1 else list(values)
    return offset,item['type']
def linked(listbase,type_name):
    pointer=field(listbase,'first');seen=set()
    while pointer:
        if pointer in seen:raise RuntimeError('Cyclic saved list')
        seen.add(pointer);item=record(pointer,type_name);yield item;pointer=field(item,'next')
def array(pointer,type_name,count):
    if count==0:return []
    base=record(pointer,type_name)[0];size=by_type[type_name]['size'];block=block_for(pointer)
    if block['size']>=count*size:return [(base+i*size,type_name) for i in range(count)]
    return [record(pointer+i*size,type_name) for i in range(count)]

# DATA pointer maps are scoped to their owning ID, as in Blender's reader.
# A global DATA map alone resolves reused serialization addresses incorrectly.
objects={}
for block in blocks:
    if block['code']!=b'OB':continue
    obj=(block['offset'],'Object');name=field(field(obj,'id'),'name')[2:];objects[name]=obj
hand=objects[args.mesh_name];mesh=record(field(hand,'data'),'Mesh');rig=objects['Nib_Rig']
active_scope=scopes[block_for(field(hand,'data'))['owner']]
mesh_fields=by_type['Mesh']['fields']
report={'status':'Read-only saved DNA extraction; no animation evaluation or authoring',
    'source':str(source),'sourceSha256':expected,'installedHeaderReaderSha256':hashlib.sha256(header_path.read_bytes()).hexdigest(),
    'meshFieldNames':list(mesh_fields),'meshTypeSizeVerified':True,'meshObject':args.mesh_name,'objectTransform':{k:field(hand,k) for k in ['loc','size','rot','quat','rotmode']}}
args.output.parent.mkdir(parents=True,exist_ok=True)

# During schema bring-up write only known actual field names, never guess an
# offset. Full extraction continues once the actual saved schema is recognized.
vertex_count=field(mesh,'verts_num' if 'verts_num' in mesh_fields else 'totvert')
corner_count=field(mesh,'corners_num' if 'corners_num' in mesh_fields else 'totloop')
face_count=field(mesh,'faces_num' if 'faces_num' in mesh_fields else 'totpoly')
def layers(custom):
    result={}
    for layer in array(field(custom,'layers'),'CustomDataLayer',field(custom,'totlayer')):
        result[field(layer,'name')]={'type':field(layer,'type'),'pointer':field(layer,'data')}
    return result
vertex_layers=layers(field(mesh,'vert_data' if 'vert_data' in mesh_fields else 'vdata'));corner_layers=layers(field(mesh,'corner_data' if 'corner_data' in mesh_fields else 'ldata'))

storage=field(mesh,'attribute_storage')

attribute_block=block_for(field(storage,'dna_attributes'))
report['attributeCountSavedDeclared']=field(storage,'dna_attributes_num')
report['attributeCountSerialized']=attribute_block['count']
if report['attributeCountSavedDeclared']!=report['attributeCountSerialized']:raise RuntimeError('Unexpected saved attribute count mismatch')
if schemas[attribute_block['dna']]['name']!='Attribute':raise RuntimeError('Wrong serialized attribute type')
for attr in array(field(storage,'dna_attributes'),'Attribute',attribute_block['count']):
    address=field(attr,'name');block=block_for(address);name=data[block['offset']:block['offset']+block['size']].split(b'\0')[0].decode()
    value={'type':field(attr,'data_type'),'domain':field(attr,'domain'),'storage':field(attr,'storage_type'),'pointer':field(attr,'data')}
    pointed=block_for(value['pointer']);value['savedDataType']=schemas[pointed['dna']]['name']
    wrapped=record(value['pointer'],value['savedDataType']);value['pointer']=field(wrapped,'data')
    if value['savedDataType']=='AttributeArray':value['count']=field(wrapped,'size')
    if value['domain']==0:vertex_layers[name]=value
    elif value['domain']==3:corner_layers[name]=value
report['vertexLayers']={k:v['type'] for k,v in vertex_layers.items()};report['cornerLayers']={k:v['type'] for k,v in corner_layers.items()}
def numeric(pointer,fmt,count):
    block=block_for(pointer)
    if block is None or struct.calcsize(fmt)*count>block['size']:raise RuntimeError('Invalid saved numeric payload '+str({'pointer':pointer,'requestedBytes':struct.calcsize(fmt)*count,'block':block}))
    return list(struct.unpack_from('<'+fmt*count,data,block['offset']))
raw=numeric(vertex_layers['position']['pointer'],'f',vertex_count*3);points=[raw[i:i+3] for i in range(0,len(raw),3)]
corners=numeric(corner_layers['.corner_vert']['pointer'],'i',corner_count)
offsets=numeric(field(mesh,'face_offset_indices' if 'face_offset_indices' in mesh_fields else 'poly_offset_indices'),'i',face_count+1);faces=[corners[offsets[i]:offsets[i+1]] for i in range(face_count)]
groups=[field(group,'name') for group in linked(field(mesh,'vertex_group_names'),'bDeformGroup')]
deform=next(v for v in vertex_layers.values() if v['type']==2)
weights=[]
for vertex in array(deform['pointer'],'MDeformVert',vertex_count):
    count=field(vertex,'totweight');row=[]
    if count:
        for w in array(field(vertex,'dw'),'MDeformWeight',count):row.append([groups[field(w,'def_nr')],field(w,'weight')])
    weights.append(row)
active_scope=scopes[block_for(field(rig,'data'))['owner']]
armature=record(field(rig,'data'),'bArmature');bones={}
def bone_tree(listbase):
    for bone in linked(listbase,'Bone'):
        name=field(bone,'name')
        if name.endswith('_L') and name.startswith(('Hand','Thumb','Index','Middle','Ring','Little')):
            bones[name]={'head':field(bone,'arm_head'),'tail':field(bone,'arm_tail'),'matrix':field(bone,'arm_mat')}
        bone_tree(field(bone,'childbase'))
bone_tree(field(armature,'bonebase'))
report.update({'vertices':points,'polygons':faces,'weights':weights,'bones':bones,'vertexCount':vertex_count,'faceCount':face_count,
    'codeSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'sharedChanged':False})
args.output.write_text(json.dumps(report,separators=(',',':'))+'\n',newline='\n')
if hashlib.sha256(source.read_bytes()).hexdigest()!=expected:raise RuntimeError('Read-only extraction changed source')
data.close();file_stream.close();temporary.unlink();marker.unlink(missing_ok=True)
print(json.dumps({'output':str(args.output),'vertices':vertex_count,'faces':face_count,'bones':list(bones)}))
