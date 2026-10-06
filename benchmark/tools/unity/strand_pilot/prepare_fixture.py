"""Flatten actual Blender fixture streams for Unity; no invented strand data."""
from pathlib import Path
import hashlib,json
REPO=Path(__file__).resolve().parents[4]
src=REPO/'benchmark/art/nib/groom-study/native-hair-fixture-v1/fixture.json'
report=json.loads(src.read_text());sha=hashlib.sha256(src.read_bytes()).hexdigest()
out=REPO/'benchmark/local/unity-strand-hair-pilot/prepared-fixture'
if out.exists():raise RuntimeError('Preserve prior fixture conversion')
out.mkdir()
files=[]
for item in report['fixtures']:
 p=item['pointsBlenderMeters'];r=item['radiusMeters'];offsets=item['curveOffsets'];uv=item['rootUv']
 assert len(p)==len(r)==offsets[-1] and len(uv)==len(offsets)-1
 d={'region':item['name'],'coordinates':'Unity metres (Blender x,z,y)','sourceSha256':sha,
    'counts':[b-a for a,b in zip(offsets,offsets[1:])],
    'positions':[v for x,y,z in p for v in (x,z,y)],'radii':r,'rootUV':[v for pair in uv for v in pair]}
 dst=out/(item['name']+'.json');dst.write_text(json.dumps(d,indent=2)+'\n')
 files.append({'name':dst.name,'sha256':hashlib.sha256(dst.read_bytes()).hexdigest(),'curves':len(d['counts']),'points':len(r)})
(out/'conversion.json').write_text(json.dumps({'status':'Prepared actual-fixture conversion; Unity ingest pending','source':str(src.relative_to(REPO)),'sourceSha256':sha,'transform':'x,z,y in metres; handedness reflection matches the intended Unity coordinate system, to be checked against imported character before binding','radius':'retained in metres; provider supplies diameter=2*radius','files':files},indent=2)+'\n')
print('NATIVE_FIXTURE_CONVERTED',out)
