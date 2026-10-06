"""Copy only nine Shoot rotation-value arrays into preserved baseline FBXs.

Uses Blender's installed FBX parser/writer. Skeleton rest transforms and times
must match. Every other raw-tree property is verified byte-identical after
serialization, including mesh/morph coordinates, weights, normals and UVs.
"""
import argparse, array, gc, hashlib, importlib, json, shutil, sys, types
from pathlib import Path

BONES=('UpperArm_R','LowerArm_R','Hand_R')
METHODS={'Z':'add_int8','Y':'add_int16','I':'add_int32','L':'add_int64',
 'B':'add_bool','C':'add_char','F':'add_float32','D':'add_float64',
 'R':'add_bytes','S':'add_string','i':'add_int32_array','l':'add_int64_array',
 'f':'add_float32_array','d':'add_float64_array','b':'add_bool_array','c':'add_byte_array'}

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def child(node,name):return next(n for n in node.elems if n.id==name)
def label(node):return node.props[1].split(b'\0')[0]
def same_properties(a,b):
    if a.id!=b.id or a.props_type!=b.props_type or len(a.props)!=len(b.props):return False
    for x,y in zip(a.props,b.props):
        if hasattr(x,'tobytes'):
            if not hasattr(y,'tobytes') or x.tobytes()!=y.tobytes():return False
        elif x!=y:return False
    return True

def same_tree(a,b,path=(),allowed=None,observed=None):
    """Only explicitly identified KeyValueFloat paths may differ."""
    if len(a.elems)!=len(b.elems):raise AssertionError('Child count changed at '+str(path))
    if not same_properties(a,b):
        if allowed is None or path not in allowed:raise AssertionError('Unapproved FBX change at '+str(path))
        if a.id!=b'KeyValueFloat' or a.props_type!=b.props_type:raise AssertionError('Unexpected allowed payload type')
        if observed is not None:observed.add(path)
    for i,(x,y) in enumerate(zip(a.elems,b.elems)):same_tree(x,y,path+(i,),allowed,observed)

def index(root):
    objects=child(root,b'Objects');nodes={n.props[0]:n for n in objects.elems}
    connections=[n.props for n in child(root,b'Connections').elems if n.id==b'C']
    models={label(n):n for n in objects.elems if n.id==b'Model'}
    stacks=[n.props[0] for n in objects.elems if n.id==b'AnimationStack' and label(n).endswith(b'Shoot')]
    if len(stacks)!=1:raise ValueError('Expected exactly one Shoot stack')
    layers={e[1] for e in connections if e[2]==stacks[0] and nodes.get(e[1],None) and nodes[e[1]].id==b'AnimationLayer'}
    curve_nodes={e[1] for e in connections if e[2] in layers and nodes.get(e[1],None) and nodes[e[1]].id==b'AnimationCurveNode'}
    curves={}
    for edge in connections:
        if edge[0]!=b'OP' or edge[1] not in curve_nodes or edge[3]!=b'Lcl Rotation':continue
        bone=nodes[edge[2]]
        if label(bone).decode() not in BONES:continue
        for row in connections:
            if row[0]==b'OP' and row[2]==edge[1] and nodes[row[1]].id==b'AnimationCurve':
                curves[(label(bone).decode(),row[3][-1:].decode())]=nodes[row[1]]
    if set(curves)!={(b,a) for b in BONES for a in 'XYZ'}:raise ValueError('Nine rotation curves not found')
    return models,curves

def transform_values(model):
    # Model defaults may describe the currently selected action, not BindPose.
    # Compare the invariant Euler basis here and actual rest matrices below.
    names={b'PreRotation':(0.,0.,0.),b'PostRotation':(0.,0.,0.),b'RotationOrder':(0,),
           b'RotationPivot':(0.,0.,0.),b'ScalingPivot':(0.,0.,0.),b'InheritType':(0,)}
    properties={n.props[0]:tuple(n.props[4:]) for n in child(model,b'Properties70').elems if n.id==b'P'}
    return {name:properties.get(name,default) for name,default in names.items()}

def bind_matrices(root):
    objects=child(root,b'Objects')
    names={n.props[0]:label(n) for n in objects.elems if n.id==b'Model'}
    poses=[n for n in objects.elems if n.id==b'Pose' and n.props[2]==b'BindPose']
    if not poses:raise ValueError('No explicit BindPose')
    result={}
    # Existing assembled exports include a one-mesh pose and a full skin pose.
    # Merge their named entries, rejecting any contradictory duplicate matrix.
    for pose in poses:
        for node in pose.elems:
            if node.id!=b'PoseNode':continue
            name=names[child(node,b'Node').props[0]];matrix=child(node,b'Matrix').props[0]
            if name in result and result[name].tobytes()!=matrix.tobytes():raise ValueError('Contradictory bind poses '+name.decode())
            result[name]=matrix
    return result

def load_modules(addons):
    if 'io_scene_fbx' not in sys.modules:
        module=types.ModuleType('io_scene_fbx');module.__path__=[str(addons/'io_scene_fbx')];sys.modules['io_scene_fbx']=module
    return importlib.import_module('io_scene_fbx.parse_fbx'),importlib.import_module('io_scene_fbx.encode_bin')

def patch(source,destination,donor_root,parse,encode,require_change=True):
    root,version=parse.parse(str(source));models,curves=index(root);donor_models,donor_curves=index(donor_root)
    source_bind,donor_bind=bind_matrices(root),bind_matrices(donor_root)
    for name,values in donor_bind.items():
        if name not in source_bind:
            if name.startswith(b'AnimationBindMesh'):continue
            raise ValueError('Donor bind node absent from target '+name.decode())
        if values.tobytes()!=source_bind[name].tobytes():raise ValueError('Actual BindPose mismatch '+name.decode())
    for name,model in models.items():
        if name not in donor_models:continue # Assembled character mesh has no donor counterpart.
        a,b=transform_values(model),transform_values(donor_models[name])
        for key in a:
            if len(a[key])!=len(b[key]) or max(abs(x-y) for x,y in zip(a[key],b[key]))>1e-7:
                raise ValueError('Donor rest transform mismatch: '+name.decode()+' '+key.decode())
    object_index=root.elems.index(child(root,b'Objects'));objects=child(root,b'Objects')
    old_payloads={};allowed=set();changes=[];time_offsets=[];time_residuals=[]
    for key,curve in curves.items():
        donor=donor_curves[key]
        old=child(curve,b'KeyValueFloat');new=child(donor,b'KeyValueFloat')
        target_times=child(curve,b'KeyTime').props[0];donor_times=child(donor,b'KeyTime').props[0]
        # Blender's embedded takes start at tick zero; standalone clips start
        # one frame later. Require identical relative sample times and retain
        # every original target KeyTime value verbatim.
        residual=max(abs((t-target_times[0])-(d-donor_times[0])) for t,d in zip(target_times,donor_times))
        # FBX integer-tick conversion rounds the two absolute origins slightly
        # differently: one tick is 21.65 picoseconds. No target times are edited.
        if len(target_times)!=len(donor_times) or residual>1:
            raise ValueError('Relative animation sample times differ '+str(key))
        time_residuals.append(residual)
        time_offsets.append(int(donor_times[0]-target_times[0]))
        if old.props_type!=new.props_type or len(old.props[0])!=len(new.props[0]):raise ValueError('Animation value type/count changed')
        old_payloads[key]=old
        path=(object_index,objects.elems.index(curve),curve.elems.index(old));allowed.add(path)
        curve.elems[curve.elems.index(old)]=new
        difference=max(abs(x-y) for x,y in zip(old.props[0],new.props[0]))
        changes.append({'bone':key[0],'axis':key[1],'keys':len(new.props[0]),
                        'stack':'Shoot','channel':'Lcl Rotation','property':'KeyValueFloat',
                        'rawTreeChildIndexPath':list(path),'curveObjectId':curve.props[0],
                        'maxEulerValueChangeDegrees':difference})
    if require_change and not any(c['maxEulerValueChangeDegrees']>1e-3 for c in changes):raise ValueError('Donor contains no meaningful repair')
    def convert(node):
        output=encode.FBXElem(node.id)
        for kind,value in zip(node.props_type,node.props):getattr(output,METHODS[chr(kind)])(value)
        output.elems=[convert(n) for n in node.elems];return output
    destination.parent.mkdir(parents=True,exist_ok=True)
    temporary=destination.with_suffix('.fbx.curves.tmp');encoded=convert(root)
    encode.write(str(temporary),encoded,version);del encoded;gc.collect()
    reread,new_version=parse.parse(str(temporary))
    if version!=new_version:raise AssertionError('Serialized FBX version changed')
    same_tree(root,reread)
    # Restore the in-memory original, then independently compare only the nine
    # allowed value nodes against the serialized candidate.
    for key,curve in curves.items():curve.elems[curve.elems.index(child(curve,b'KeyValueFloat'))]=old_payloads[key]
    observed=set();same_tree(root,reread,allowed=allowed,observed=observed)
    temporary.replace(destination)
    result={'source':str(source),'sourceSha256':sha(source),'target':str(destination),'targetSha256':sha(destination),
            'changedRotationArrays':len(observed),'allowedRotationArrays':9,'changes':changes,
            'unchangedAllOtherTreeProperties':True,'unchangedGeometryMorphsUVNormalsWeightsBindAndOtherTakes':True,
            'sourceAndDonorBindMatricesByteIdentical':True,'sourceAndDonorRotationBasisMatch':True,
            'targetSampleTimesPreservedByteIdentical':True,
            'donorRelativeSampleTimeMaxResidualTicks':max(time_residuals),
            'donorRelativeSampleTimeMaxResidualSeconds':max(time_residuals)/46186158000,
            'donorAbsoluteTimeOffsetTicks':sorted(set(time_offsets))}
    print(json.dumps(result),flush=True);return result

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--source-dir',type=Path,required=True)
    parser.add_argument('--candidate-dir',type=Path,required=True);parser.add_argument('--donor',type=Path,required=True)
    parser.add_argument('--addons',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--identity-test',action='store_true')
    args=parser.parse_args();parse,encode=load_modules(args.addons);donor,version=parse.parse(str(args.donor))
    if args.source_dir.resolve()==args.candidate_dir.resolve():raise ValueError('Source must remain preserved')
    args.candidate_dir.mkdir(parents=True,exist_ok=True)
    if not args.identity_test:shutil.copytree(args.source_dir,args.candidate_dir,dirs_exist_ok=True)
    paths=['animations/Shoot.fbx'] if args.identity_test else ['Krag_Natural.fbx','Krag_Crusher.fbx','Krag_IronJaw.fbx','Krag_Piston.fbx','animations/Shoot.fbx']
    results=[]
    for relative in paths:
        results.append(patch(args.source_dir/relative,args.candidate_dir/relative,donor,parse,encode,not args.identity_test));gc.collect()
    report={'donor':str(args.donor),'donorSha256':sha(args.donor),'files':results,
            'identityTestOnly':args.identity_test,'artisticAcceptance':False,
            'status':'Raw property preservation passed; actual Blender roundtrip/grip review required separately'}
    args.output.write_text(json.dumps(report,indent=2)+'\n',newline='\n')
    print('KRAG_SHOOT_CURVES_PATCHED',flush=True)

if __name__=='__main__':main()
