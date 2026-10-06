"""Prepare the proven cleaned Natural target; stage only after the fixture run closes."""
import argparse,hashlib,json,shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
TOOLS=Path(__file__).resolve().parent
PILOT=ROOT/'benchmark/local/unity-strand-hair-pilot'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--stage',action='store_true');args=parser.parse_args()
    delivery_path=ROOT/'benchmark/art/nib/groom-study/native-filtered-target-v1/delivery.json'
    if sha(delivery_path)!='4e7b430b9c850aa469f8ede96bf70fd99c612866c26ab963414f4f51c2d8e0a6':raise RuntimeError('Frozen common target delivery changed')
    delivery=json.loads(delivery_path.read_text())
    for key in ('fbx','manifest','sourceReport','nativeGroomReport'):
        row=delivery[key]
        if sha(ROOT/row['path'])!=row['sha256']:raise RuntimeError('Common target drift: '+key)
    source=json.loads((ROOT/delivery['sourceReport']['path']).read_text())
    manifest=json.loads((ROOT/delivery['manifest']['path']).read_text())
    groom_path=ROOT/delivery['nativeGroomReport']['path'];groom=json.loads(groom_path.read_text())
    out=PILOT/'prepared-character-v1'
    if out.exists():raise RuntimeError('Preserve prior character preparation')
    out.mkdir();files=[]
    def copy(src,name):
        dst=out/name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
        files.append({'path':'Assets/NativeGroom/Character/'+name,'sha256':sha(dst)})
    copy(ROOT/delivery['fbx']['path'],'Nib_Natural.fbx')
    regions=[]
    for region in groom['regions']:
        for stream in ('positions','radii','curveCounts','rootUv','colorLinearRgb','rootWeightOffsets','rootBoneIndices','rootBoneWeights'):
            row=region['files'][stream];src=groom_path.parent/region['dataDirectory']/row['path']
            if sha(src)!=row['sha256'] or src.stat().st_size!=row['bytes']:raise RuntimeError('Authored groom stream drift: '+str(src))
            copy(src,'Strands/'+region['name']+'.'+stream+'.bytes')
        regions.append({'name':region['name'],'prefix':'Assets/NativeGroom/Character/Strands/'+region['name'],'curves':region['curveCount'],'points':region['pointCount']})
    anchors=[{'name':name,'source':row['headBlenderWorldMeters']} for name,row in source['coordinateContract']['restAnchors'].items()]
    config={'fbx':'Assets/NativeGroom/Character/Nib_Natural.fbx','sourceSha256':delivery['filteredSource']['sha256'],'anchors':anchors,'files':files,'regions':regions,'bones':manifest['bones'],'expectedTriangles':manifest['variants'][0]['triangles']}
    (out/'config.json').write_text(json.dumps(config,indent=2)+'\n')
    receipt={'status':'Prepared exact character streams; actual Unity coordinate fit and asset build pending','commonDeliverySha256':sha(delivery_path),'configSha256':sha(out/'config.json'),'files':files,'engineTransformAssumed':False,'characterBindingVerified':False,'materialsStaged':False}
    (out/'preparation.json').write_text(json.dumps(receipt,indent=2)+'\n')
    if args.stage:
        destination=PILOT/'project/Assets/NativeGroom/Character'
        if destination.exists():raise RuntimeError('Preserve existing staged character')
        shutil.copytree(out,destination)
        for name in ('CharacterImportProbe.cs','NativeBinaryCurveProvider.cs'):
            dst=PILOT/'project/Assets/Editor'/name
            if dst.exists():raise RuntimeError('Preserve existing character source')
            shutil.copyfile(TOOLS/name,dst)
    print('NATIVE_CHARACTER_PREPARED',out,'staged=',args.stage)
if __name__=='__main__':main()
