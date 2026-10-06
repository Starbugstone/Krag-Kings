"""Constrained coordinate proof from actual named rest-bone positions; no best-fit deformation."""
import itertools
import math


def apply_axes(point, axes):
    return [point[axis['sourceAxis']]*axis['sign']*100.0 for axis in axes]


def match_rest_positions(source_bones, imported_bones, tolerance_cm=0.001):
    """Find a unique signed axis permutation at fixed metres→centimetres scale.

    Source matrices are Blender column-vector matrices; imported matrices are
    Unreal row-vector component matrices. Bone-local orientation conventions may
    change through FBX, so this gate compares named origins and exact hierarchy.
    It does not claim full rotational bind parity by comparing origins alone.
    """
    imported = {bone['name']: bone for bone in imported_bones}
    if len(imported) != len(imported_bones) or set(imported) != set(source_bones):
        raise ValueError('Full named skeleton differs')
    pairs=[]
    for name, bone in source_bones.items():
        actual=imported[name]
        if (bone['parent'] or '') != actual['parent']:
            raise ValueError('Rest hierarchy differs: '+name)
        source=[bone['matrix'][row][3] for row in range(3)]
        target=actual['componentMatrixUnrealRowMajorCentimeters'][12:15]
        if len(target)!=3 or not all(math.isfinite(value) for value in source+target):
            raise ValueError('Invalid bind origin')
        pairs.append((name,source,target))
    candidates=[]
    for permutation in itertools.permutations(range(3)):
        for signs in itertools.product((-1,1),repeat=3):
            axes=[{'sourceAxis':axis,'sign':sign} for axis,sign in zip(permutation,signs)]
            errors=[max(abs(a-b) for a,b in zip(apply_axes(source,axes),target)) for _,source,target in pairs]
            candidates.append({'axes':axes,'maximumComponentErrorCentimeters':max(errors),
                               'meanComponentMaximumErrorCentimeters':sum(errors)/len(errors)})
    candidates.sort(key=lambda candidate:candidate['maximumComponentErrorCentimeters'])
    accepted=[candidate for candidate in candidates if candidate['maximumComponentErrorCentimeters']<=tolerance_cm]
    if len(accepted)!=1:
        raise ValueError('No unique fixed-scale axis conversion: '+str(candidates[:2]))
    result=accepted[0]
    result.update({'boneCount':len(pairs),'toleranceCentimeters':tolerance_cm,
                   'scaleCentimetersPerSourceMeter':100,'translationCentimeters':[0,0,0],
                   'fullRotationalBindParityClaimed':False})
    return result


def abc_conversion_basis(axes):
    """Destination columns for ABC(x,z,-y), with unit scale removed."""
    # ABC X=Blender X, ABC Y=Blender Z, ABC Z=negative Blender Y.
    return [[value/100.0 for value in apply_axes(point,axes)]
            for point in ((1,0,0),(0,0,1),(0,-1,0))]


if __name__=='__main__':
    source={}
    for index,point in enumerate(((0,0,0),(.7,.2,1.2),(-.3,.6,.8),(.1,-.4,.9))):
        matrix=[[float(row==col) for col in range(4)] for row in range(4)]
        for row in range(3):matrix[row][3]=point[row]
        source[str(index)]={'parent':None if index==0 else '0','matrix':matrix}
    for permutation in itertools.permutations(range(3)):
        for signs in itertools.product((-1,1),repeat=3):
            axes=[{'sourceAxis':axis,'sign':sign} for axis,sign in zip(permutation,signs)]
            imported=[]
            for name,bone in source.items():
                matrix=[float(row==col) for row in range(4) for col in range(4)]
                matrix[12:15]=apply_axes([bone['matrix'][row][3] for row in range(3)],axes)
                imported.append({'name':name,'parent':bone['parent'] or '',
                                 'componentMatrixUnrealRowMajorCentimeters':matrix})
            assert match_rest_positions(source,imported)['axes']==axes
    broken=[dict(item) for item in imported]
    broken[1]['parent']='wrong'
    try:match_rest_positions(source,broken)
    except ValueError:pass
    else:raise AssertionError('Hierarchy mismatch was accepted')
    for item in broken:item['parent']=source[item['name']]['parent'] or ''
    broken[1]['componentMatrixUnrealRowMajorCentimeters']=list(broken[1]['componentMatrixUnrealRowMajorCentimeters'])
    broken[1]['componentMatrixUnrealRowMajorCentimeters'][12]+=0.02
    try:match_rest_positions(source,broken)
    except ValueError:pass
    else:raise AssertionError('Non-axis displacement was accepted')
    print('48 signed-axis cases and hierarchy/non-axis displacement rejection pass; no native import claimed')
