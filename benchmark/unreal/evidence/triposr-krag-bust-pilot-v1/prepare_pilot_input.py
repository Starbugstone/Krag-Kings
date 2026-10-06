"""Exact approved concept crop plus neutral padding for local model conditioning."""
import hashlib
import json
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
PLAN = Path(__file__).with_name('krag-bust-pilot.plan.json')
sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
plan = json.loads(PLAN.read_text())
source = ROOT / plan['input']['source']
if sha(source) != plan['input']['sourceSha256']:
    raise RuntimeError('Original concept sheet changed')
output = ROOT / plan['input']['outputDirectory']
if output.exists():
    raise RuntimeError('Preserve previous conditioning input')
output.mkdir(parents=True)
with Image.open(source) as sheet:
    if list(sheet.size) != plan['input']['sourceDimensions']:
        raise RuntimeError('Unexpected sheet dimensions')
    crop = sheet.convert('RGB').crop(tuple(plan['input']['cropXYXY']))
    crop.save(output/'cropped-original.png')
    canvas = Image.new('RGB', tuple(plan['input']['conditioningDimensions']), (128,128,128))
    offset = ((canvas.width-crop.width)//2, (canvas.height-crop.height)//2)
    canvas.paste(crop, offset)
    canvas.save(output/'conditioning.png')
    if canvas.crop((offset[0],offset[1],offset[0]+crop.width,offset[1]+crop.height)).tobytes()!=crop.tobytes():
        raise RuntimeError('Padding changed original crop pixels')
if sha(source) != plan['input']['sourceSha256']:
    raise RuntimeError('Preprocessing changed original sheet')
(output/'input-receipt.json').write_text(json.dumps({
    'planSha256':sha(PLAN), 'recipeSha256':sha(__file__), 'input':plan['input'],
    'cropDimensions':list(crop.size), 'paddingOffsetXY':list(offset),
    'originalCropPixelsUnchanged':True, 'sourceSheetUnchanged':True,
    'outputs':{name:sha(output/name) for name in ['cropped-original.png','conditioning.png']},
    'inferenceExecuted':False
},indent=2)+'\n')
print('TRIPOSR_CONDITIONING_INPUT_COMPLETE',flush=True)
