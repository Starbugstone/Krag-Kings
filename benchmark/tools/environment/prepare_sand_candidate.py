"""Isolated material candidate for the existing dunes; never changes shared assets.

Run in guarded Blender. Retains the original geometry/UVs and derives portable
PBR maps from the retained CC0 Sand 03 scan with quieter procedural wind ripples.
An actual engine comparison is required before promotion.
"""
import hashlib
import json
from pathlib import Path
import shutil

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
REFERENCE = ROOT / 'benchmark/art/environment/reference-materials/sand_03'
BASELINE = ROOT / 'benchmark/shared/environment'
OUTPUT = ROOT / 'benchmark/local/candidates/sand-scan-v2'
SOURCE = ROOT / 'benchmark/art/environment/Dunes.blend'
OUTPUT.mkdir(parents=True, exist_ok=True)
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
provenance = json.loads((REFERENCE / 'source.json').read_text())
for item in provenance['files']:
    if sha(REFERENCE / item['file']) != item['sha256']:
        raise RuntimeError('Retained scan differs from source receipt: ' + item['file'])

bpy.ops.wm.open_mainfile(filepath=str(SOURCE), load_ui=False)

def pixels(path, color):
    image = bpy.data.images.load(str(path), check_existing=False)
    image.colorspace_settings.name = 'sRGB' if color else 'Non-Color'
    width, height = image.size
    values = np.empty(width * height * 4, dtype=np.float32)
    image.pixels.foreach_get(values)
    values = values.reshape(height, width, 4)
    # Blender 5.2's loaded byte-image pixels preserve the encoded file values
    # (verified against a Windows bitmap read). Decode before color filtering.
    if color:
        values[:, :, :3] = srgb_to_linear(values[:, :, :3])
    return values

def srgb_to_linear(values):
    values = np.asarray(values, dtype=np.float32)
    return np.where(values <= .04045, values / 12.92, ((values + .055) / 1.055) ** 2.4)

def linear_to_srgb(values):
    values = np.clip(values, 0, 1)
    return np.where(values <= .0031308, values * 12.92, 1.055 * values ** (1 / 2.4) - .055)

def repeat_scan(values):
    # The retained scan covers 2m. Existing mesh UVs cover 4m, so downsample
    # linearly to 1K and repeat twice in each dimension in the final 2K map.
    if values.shape[:2] != (2048, 2048):
        raise RuntimeError('Expected the retained 2K scan')
    smaller = values.reshape(1024, 2, 1024, 2, 4).mean(axis=(1, 3))
    return np.tile(smaller, (2, 2, 1))

base = repeat_scan(pixels(REFERENCE / 'sand_03_diff_2k.jpg', True))
# V1 source review showed convincing grains but grey/damp color. Preserve the
# scan's local variation while fitting a proposed dry, warm desert palette.
target_srgb = np.array([.69, .57, .405], dtype=np.float32)
scan_median = np.median(base[:, :, :3], axis=(0, 1))
base[:, :, :3] = np.clip(base[:, :, :3] * (srgb_to_linear(target_srgb) / scan_median), 0, 1)
rough = repeat_scan(pixels(REFERENCE / 'sand_03_rough_2k.jpg', False))[:, :, 0]
scan_normal = repeat_scan(pixels(REFERENCE / 'sand_03_nor_gl_2k.jpg', False))[:, :, :3] * 2 - 1
old_normal = pixels(BASELINE / 'Sand_Normal.png', False)[:, :, :3] * 2 - 1
# Small-angle tangent-space slope addition keeps the scan grains and reduces
# the original repeating ridge field. This adds no geometry or shader samples.
normal = np.empty_like(scan_normal)
normal[:, :, :2] = .45 * scan_normal[:, :, :2] + .12 * old_normal[:, :, :2]
normal[:, :, 2] = scan_normal[:, :, 2] * old_normal[:, :, 2]
normal /= np.maximum(np.linalg.norm(normal, axis=2, keepdims=True), 1e-6)
normal = np.dstack((normal * .5 + .5, np.ones_like(rough)))
mask = np.dstack((np.zeros_like(rough), np.ones_like(rough), np.ones_like(rough), 1 - rough))
rough_map = np.dstack((rough, rough, rough, np.ones_like(rough)))

def save_map(name, values, color=False):
    image = bpy.data.images.new(name + '_ScanCandidate', width=2048, height=2048, alpha=True)
    image.colorspace_settings.name = 'sRGB' if color else 'Non-Color'
    values = values.astype(np.float32).copy()
    if color:
        values[:, :, :3] = linear_to_srgb(values[:, :, :3])
    image.pixels.foreach_set(values.ravel())
    image.filepath_raw = str(OUTPUT / (name + '.png'))
    image.file_format = 'PNG'
    image.save()
    return image

maps = {
    'Sand_BaseColor': save_map('Sand_BaseColor', base, True),
    'Sand_Normal': save_map('Sand_Normal', normal),
    'Sand_Roughness': save_map('Sand_Roughness', rough_map),
    'Sand_MaskHDRP': save_map('Sand_MaskHDRP', mask),
}
for material in bpy.data.materials:
    if not material.use_nodes:
        continue
    for node in material.node_tree.nodes:
        if node.type == 'TEX_IMAGE' and node.image:
            stem = Path(bpy.path.abspath(node.image.filepath)).stem
            if stem in maps:
                node.image = maps[stem]
shutil.copy2(BASELINE / 'Dunes.fbx', OUTPUT / 'Dunes.fbx')
manifest = json.loads((BASELINE / 'manifest.json').read_text())
manifest['materialRecipe'] = {
    'source': provenance,
    'runtimeTextureSize': 2048,
    'scanRepeatAcrossFourMeterTile': 2,
    'scanNormalSlopeGain': .45,
    'baselineRippleSlopeGain': .12,
    'colorAdjustment': 'Explicit sRGB decode, linear box filter, median-based dry-sand tint, explicit sRGB encode',
    'proposedMedianColorSRGB': target_srgb.tolist(),
    'sourceMedianLinear': scan_median.tolist(),
    'status': 'Candidate only; actual engine review pending',
}
(OUTPUT / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', newline='\n')
source_copy = OUTPUT / 'Dunes_ScanCandidate.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(source_copy), compress=True)
for image in maps.values():
    image.filepath = bpy.path.relpath(image.filepath)
bpy.ops.wm.save_as_mainfile(filepath=str(source_copy), compress=True)
receipt = {
    'status': 'Isolated material candidate; not promoted or visually accepted',
    'originalTerrainSourceSha256': sha(SOURCE),
    'geometryUnchangedSha256': sha(BASELINE / 'Dunes.fbx'),
    'filesSha256': {p.name: sha(p) for p in OUTPUT.iterdir() if p.name != 'candidate-receipt.json' and p.suffix in {'.png', '.fbx', '.blend', '.json'}},
}
(OUTPUT / 'candidate-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n', newline='\n')
print('SAND_SCAN_CANDIDATE_READY', OUTPUT)
