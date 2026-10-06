"""Read only FBX model metadata/connections; never load geometry arrays or an editor."""
import argparse
import hashlib
import json
from pathlib import Path
import struct


def inspect(path, wrapper='Nib_Rig', authored_root='Root'):
    with Path(path).open('rb') as stream:
        header=stream.read(27)
        if not header.startswith(b'Kaydara FBX Binary'):raise ValueError('Binary FBX required')
        version=struct.unpack_from('<I',header,23)[0]
        fmt,size=('<QQQB',25) if version>=7500 else ('<IIIB',13)
        def prop():
            kind=stream.read(1)
            scalar={b'Y':'<h',b'C':'<?',b'I':'<i',b'F':'<f',b'D':'<d',b'L':'<q'}
            if kind in scalar:
                pattern=scalar[kind];return struct.unpack(pattern,stream.read(struct.calcsize(pattern)))[0]
            if kind in (b'S',b'R'):
                value=stream.read(struct.unpack('<I',stream.read(4))[0])
                return value.decode('utf8','replace') if kind==b'S' else {'bytes':len(value)}
            if kind in (b'f',b'd',b'i',b'l',b'b',b'c'):
                count,encoding,length=struct.unpack('<III',stream.read(12));stream.seek(length,1)
                return {'arrayCount':count,'encoding':encoding}
            raise ValueError('Unsupported property type')
        def node(parent=''):
            raw=stream.read(size)
            if len(raw)!=size:return None
            end,count,_,length=struct.unpack(fmt,raw)
            if not end:return None
            name=stream.read(length).decode()
            if (not parent and name not in ('Objects','Connections','GlobalSettings')) or (parent=='Objects' and name!='Model'):
                stream.seek(end);return None
            result={'name':name,'props':[prop() for _ in range(count)],'children':[]}
            while stream.tell()<end-size:
                child=node(name)
                if child:result['children'].append(child)
            stream.seek(end);return result
        roots=[]
        while stream.tell()<Path(path).stat().st_size-size:
            position=stream.tell();item=node()
            if item:roots.append(item)
            if stream.tell()==position+size:break
    groups={item['name']:item for item in roots}
    models={item['props'][0]:item for item in groups['Objects']['children']}
    names={item['props'][1].split('\0')[0]:identifier for identifier,item in models.items()}
    edges=[item['props'] for item in groups['Connections']['children'] if item['name']=='C']
    def properties(item):
        group=next((child for child in item['children'] if child['name']=='Properties70'),None)
        return {child['props'][0]:child['props'][4:] for child in group['children'] if child['name']=='P'} if group else {}
    if wrapper not in names or authored_root not in names:raise ValueError('Exact wrapper/root not present')
    identifier=names[wrapper];root_id=names[authored_root]
    # OO links also connect bones to skin clusters; only Model/scene links define hierarchy.
    parents=[edge[2] for edge in edges if edge[0]=='OO' and edge[1]==identifier and (edge[2]==0 or edge[2] in models)]
    root_parents=[edge[2] for edge in edges if edge[0]=='OO' and edge[1]==root_id and (edge[2]==0 or edge[2] in models)]
    bone_names=sorted(name for name,index in names.items() if models[index]['props'][2]=='LimbNode')
    if models[identifier]['props'][2]!='Null' or parents!=[0] or root_parents!=[identifier]:
        raise ValueError('Wrapper classification requires attribution: '+repr({'wrapper':models[identifier]['props'],
            'parents':parents,'authoredRootParents':root_parents,'properties':properties(models[identifier])}))
    with Path(path).open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
    return {'fbx':str(path),'sha256':digest,'fbxVersion':version,'wrapper':wrapper,'modelType':'Null',
            'topLevelConnectionVerified':True,'authoredRoot':authored_root,'authoredRootParentVerified':True,
            'wrapperProperties':properties(models[identifier]),'globalSettings':properties(groups['GlobalSettings']),
            'authoredBoneNames':bone_names,'authoredBoneCount':len(bone_names),'geometryRead':False,
            'broadNameFilteringAllowed':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('fbx',type=Path);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();result=inspect(args.fbx);args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
