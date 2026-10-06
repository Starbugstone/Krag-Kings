"""Save a new portable texture root and prove paths/content after reopening it."""
import hashlib
from pathlib import Path
import bpy

CHANNELS = ('baseColor', 'normal', 'roughness', 'metallic')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def material_images():
    collection = bpy.data.collections['Nib_Authored_Components']
    materials = {m for obj in collection.objects if obj.type == 'MESH'
                 for m in obj.data.materials if m is not None}
    return materials, {node.image for material in materials if material.use_nodes
                       for node in material.node_tree.nodes
                       if node.type == 'TEX_IMAGE' and node.image}


def expected_maps(report):
    expected = {}
    for material in report['materials']:
        for channel in CHANNELS:
            relative = Path(material[channel])
            if relative.is_absolute() or len(relative.parts) != 2 or relative.parts[0] != 'textures':
                raise RuntimeError('Texture escapes portable root: ' + str(relative))
            value = {'sha256': material['mapHashes'][channel],
                     'colorSpace': 'sRGB' if channel == 'baseColor' else 'Non-Color'}
            if relative.name in expected and expected[relative.name] != value:
                raise RuntimeError('Inconsistent shared image contract: ' + relative.name)
            expected[relative.name] = value
    return expected


def validate_saved_pbr(target, report):
    target = Path(target).resolve()
    bpy.ops.wm.open_mainfile(filepath=str(target))
    materials, images = material_images()
    if {m.name for m in materials} != {m['name'] for m in report['materials']}:
        raise RuntimeError('Reopened material set differs from PBR report')
    expected = expected_maps(report)
    records = []
    for image in sorted(images, key=lambda item: item.name):
        if image.source != 'FILE':
            raise RuntimeError('Used image is not a portable file: ' + image.name)
        name = Path(image.filepath).name
        if name not in expected or image.filepath.replace('\\', '/') != '//textures/' + name:
            raise RuntimeError('Reopened image has wrong relative root: ' + image.filepath)
        actual = Path(bpy.path.abspath(image.filepath, library=image.library)).resolve()
        wanted = target.parent / 'textures' / name
        if actual != wanted or not actual.is_file():
            raise RuntimeError('Reopened image does not resolve inside saved PBR: ' + str(actual))
        if sha(actual) != expected[name]['sha256']:
            raise RuntimeError('Saved image content differs from bake: ' + name)
        if image.colorspace_settings.name != expected[name]['colorSpace']:
            raise RuntimeError('Saved image color space changed: ' + name)
        image.reload()
        width, height = image.size
        if width <= 0 or height <= 0 or not image.has_data:
            raise RuntimeError('Reopened image failed to decode: ' + name)
        records.append({'image': image.name, 'relativePath': 'textures/' + name,
                        'sha256': expected[name]['sha256'], 'width': width, 'height': height,
                        'channels': image.channels, 'colorSpace': image.colorspace_settings.name})
    missing = set(expected) - {Path(entry['relativePath']).name for entry in records}
    if missing:
        raise RuntimeError('Reported maps are not connected to actual materials: ' + str(sorted(missing)))
    return {'reopened': True, 'relativeRootCorrect': True, 'allMapsDecoded': True,
            'allBytesMatchBake': True, 'imageDatablocks': len(records),
            'uniqueTextureFiles': len(expected), 'images': records}


def save_and_validate_pbr(target, report):
    target = Path(target).resolve()
    expected = expected_maps(report)
    _, images = material_images()
    for image in images:
        name = Path(image.filepath).name
        local = target.parent / 'textures' / name
        if name not in expected or not local.is_file() or sha(local) != expected[name]['sha256']:
            raise RuntimeError('Image not covered by the portable content contract: ' + name)
        # The intended root belongs to target, not the still-current source file.
        image.filepath = '//textures/' + name
    bpy.ops.wm.save_as_mainfile(filepath=str(target), compress=True, relative_remap=False)
    return validate_saved_pbr(target, report)
