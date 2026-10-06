"""Explicit, byte-verified legacy source texture remapping for isolated views.

No shared files or source blend are written. Callers supply the source's own
saved image receipt; an archive from another source is usable only if every
requested image has the exact same recorded bytes and color space.
"""
import hashlib
import json
from pathlib import Path


def remap_verified_images(bpy, root, archive_path, expected_images):
    root = Path(root).resolve()
    archive_path = Path(archive_path).resolve()
    archive = json.loads(archive_path.read_text())
    prepared = []
    for name, expected in expected_images.items():
        entry = archive['images'].get(name)
        image = bpy.data.images.get(name)
        if entry is None or image is None:
            raise RuntimeError('Missing declared source image ' + name)
        path = (root / entry['relativePath']).resolve()
        if not path.is_relative_to(root / 'benchmark/art/nib/source-textures'):
            raise RuntimeError('Image archive leaves the owned source dependency directory')
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != expected['sha256'] or digest != entry['sha256']:
            raise RuntimeError('Historical image bytes differ: ' + name)
        if image.colorspace_settings.name != expected['colorspace'] or entry['colorspace'] != expected['colorspace']:
            raise RuntimeError('Historical image color space differs: ' + name)
        prepared.append((name, image, path, digest))
    # Resolve all dependencies before changing any in-memory image path.
    result = {}
    for name, image, path, digest in prepared:
        old_path = image.filepath
        image.filepath = str(path)
        image.reload()
        size = list(image.size)  # Force lazy decoding before has_data.
        if not image.has_data or min(size) <= 0:
            raise RuntimeError('Historical source image did not decode: ' + name)
        result[name] = {'previousPath': old_path, 'archivePath': str(path), 'sha256': digest, 'size': size, 'colorspace': image.colorspace_settings.name}
    return result
