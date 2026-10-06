"""Bounded actual Blender/FBX fixture before retrying the full character export."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import bpy

ROOT=Path(__file__).resolve().parents[4]
HELPERS=ROOT/'benchmark/tools/nib/v5_wip'
sys.path.insert(0,str(HELPERS))
from triangulate_corners import triangulate
from preserve_fbx_point_payloads import preserve
from validate_triangulated_payload import compare


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--recipes',type=Path,required=True)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    pins=json.loads(args.recipes.read_text())
    def verify():
        for entry in pins['files']:
            if hashlib.sha256((ROOT/entry['path']).read_bytes()).hexdigest()!=entry['sha256']:
                raise RuntimeError('Frozen fixture recipe changed: '+entry['path'])
    verify()
    if args.out.exists():raise RuntimeError('Preserve previous fixture output')
    args.out.mkdir(parents=True)
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    mesh=bpy.data.meshes.new('Two hard-edged quads')
    mesh.from_pydata([(0,0,0),(1,0,0),(1,1,0),(0,1,0),(1,0,1),(1,1,1)],[],[(0,1,2,3),(1,4,5,2)])
    mesh.update()
    obj=bpy.data.objects.new('CornerContract',mesh);bpy.context.collection.objects.link(obj)
    obj.select_set(True);bpy.context.view_layer.objects.active=obj
    obj.shape_key_add(name='Basis');key=obj.shape_key_add(name='KnownDelta')
    key.data[3].co.z+=.03
    uv=mesh.uv_layers.new(name='UVMap')
    for loop,value in zip(uv.data,[(0,0),(1,0),(1,1),(0,1),(.2,.1),(.8,.1),(.8,.9),(.2,.9)]):loop.uv=value
    for name in ['FaceA','FaceB']:mesh.materials.append(bpy.data.materials.new(name))
    mesh.polygons[1].material_index=1
    def export(path):
        bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},
            axis_forward='-Z',axis_up='Y',use_mesh_modifiers=False,use_triangles=False,
            add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE')
    before=args.out/'source.fbx';after=args.out/'target.fbx';mapping=after.with_suffix('.corners.npz')
    export(before)
    native=triangulate(mesh,mapping)
    export(after)
    raw=preserve(before,after,Path(bpy.utils.system_resource('SCRIPTS'))/'addons_core',
        preserve_morphs=False,corner_map_path=mapping)
    result=compare(before,after)
    if not result['mappedNormalPayloadByteIdentical']:raise RuntimeError('Exact corner normal payload not retained')
    if not result['pointAndMorphPayloadsByteIdentical']:raise RuntimeError('Point/morph payload changed')
    report={'passed':True,'blender':bpy.app.version_string,'fixture':'Two quads sharing a hard edge with distinct UV/material corners and one nonzero morph',
        'nativeTriangulation':native,'rawPreservation':raw,'independentRawComparison':result,
        'fullCharacterExportVerified':False,'recipeSetSha256':hashlib.sha256(args.recipes.read_bytes()).hexdigest()}
    verify()
    (args.out/'result.json').write_text(json.dumps(report,indent=2)+'\n',newline='\n')
    print('NIB_CORNER_FIXTURE_COMPLETE',flush=True)


if __name__=='__main__':main()
