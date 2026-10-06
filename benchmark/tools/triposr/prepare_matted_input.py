"""Local foreground alpha only; preserve every crop RGB sample before compositing."""
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'benchmark/local/triposr-reference-v1'
PLAN = Path(__file__).with_name('krag-bust-matted-v2.plan.json')


def sha(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024), b''):
            result.update(block)
    return result.hexdigest()


def main():
    plan = json.loads(PLAN.read_text(encoding='utf-8'))
    source = BASE / 'input-krag-bust/cropped-original.png'
    if sha(source) != plan['input']['originalCropSha256']:
        raise RuntimeError('Approved original crop changed')
    cache = BASE / 'matte-model-download'
    model = cache / 'u2net.onnx'
    if sha(model) != plan['mattingModel']['sha256']:
        raise RuntimeError('Reviewed local matting-model hash changed')
    output = ROOT / plan['input']['outputDirectory']
    if output.exists():
        raise RuntimeError('Preserve an existing matting attempt')
    output.mkdir()
    os.environ.update({'U2NET_HOME':str(cache), 'OMP_NUM_THREADS':'2',
                       'NUMBA_CACHE_DIR':str(BASE/'cache/numba')})
    import numpy as np
    from PIL import Image
    from rembg import new_session
    session = new_session('u2net', providers=['CPUExecutionProvider'])
    with Image.open(source) as image:
        crop = image.convert('RGB')
    mask = session.predict(crop)[0].convert('L')
    rgba = crop.convert('RGBA')
    rgba.putalpha(mask)
    if np.array(rgba)[..., :3].tobytes() != np.array(crop).tobytes():
        raise RuntimeError('Matting changed original foreground RGB')
    rgba.save(output/'foreground-original-rgb.png')
    mask.save(output/'alpha-mask.png')
    canvas = Image.new('RGB', (512, 512), (128, 128, 128))
    offset = ((512-crop.width)//2, (512-crop.height)//2)
    composite = Image.composite(crop, Image.new('RGB', crop.size, (128,128,128)), mask)
    canvas.paste(composite, offset)
    canvas.save(output/'conditioning.png')
    mask_values = np.asarray(mask)
    if not (mask_values.min()==0 and mask_values.max()==255):
        raise RuntimeError('Matte lacks definite foreground or background')
    if sha(source) != plan['input']['originalCropSha256']:
        raise RuntimeError('Matting changed the original crop file')
    receipt={'planSha256':sha(PLAN), 'recipeSha256':sha(__file__),
             'originalCropSha256':sha(source), 'modelSha256':sha(model),
             'foregroundRGBExactlyPreservedInRGBA':True,
             'conditioning':'Original crop at identical512-square offset, alpha-composited over RGB128 gray. No crop resizing, inpainting or redesign.',
             'paddingOffsetXY':list(offset), 'cropDimensions':list(crop.size),
             'alphaCoverageAbove127':float((mask_values>127).mean()),
             'cpuProvider':session.inner_session.get_providers(),
             'outputs':{name:sha(output/name) for name in ['foreground-original-rgb.png','alpha-mask.png','conditioning.png']},
             'silhouetteVisuallyReviewed':False,'inferenceExecuted':False}
    (output/'input-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n', encoding='utf-8')
    print('TRIPOSR_MATTED_INPUT_COMPLETE', flush=True)


if __name__ == '__main__':
    main()
