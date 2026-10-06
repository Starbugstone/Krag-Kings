"""Require copied card atlases to match the actual connected source image bytes."""
import hashlib
from pathlib import Path

import bpy

from bake_fields import sha


def verify_card_source_images(material, contract, texture_directory):
    expected = {}
    for channel in ['baseColor','normal','roughness','metallic']:
        relative = Path(contract[channel])
        if relative.is_absolute() or len(relative.parts)!=2 or relative.parts[0]!='textures':
            raise RuntimeError('Card map is not a portable textures/filename path')
        source = Path(texture_directory)/relative.name
        if not source.is_file():
            raise RuntimeError('Missing supplied original card map: '+str(source))
        expected[relative.name] = sha(source)
    outputs = [node for node in material.node_tree.nodes if node.type=='OUTPUT_MATERIAL' and node.is_active_output]
    if len(outputs)!=1:
        raise RuntimeError('Masked source must have one active material output')
    pending = [link.from_node for link in outputs[0].inputs['Surface'].links]
    seen = set()
    found = []
    while pending:
        node = pending.pop()
        if node.name in seen:
            continue
        seen.add(node.name)
        if node.type=='GROUP':
            raise RuntimeError('Nested masked shader needs explicit source-image mapping: '+material.name)
        if node.type=='TEX_IMAGE':
            if node.image is None:
                raise RuntimeError('Connected card image node has no image')
            path = Path(bpy.path.abspath(node.image.filepath, library=node.image.library)).resolve()
            if path.name not in expected:
                raise RuntimeError('Source card shader image is absent from portable contract: '+str(path))
            if node.image.packed_file:
                checksum = hashlib.sha256(node.image.packed_file.data).hexdigest()
                storage = 'packed source image bytes'
            else:
                if not path.is_file():
                    raise RuntimeError('Connected source card image is unresolved: '+str(path))
                checksum = sha(path)
                storage = 'resolved source image file'
            if checksum != expected[path.name]:
                raise RuntimeError('Supplied card atlas differs from actual shader image: '+path.name)
            found.append({'node':node.name,'image':node.image.name,'resolvedSource':str(path),
                          'storage':storage,'sha256':checksum,'contractFile':path.name})
        for socket in node.inputs:
            pending.extend(link.from_node for link in socket.links)
    if not found:
        raise RuntimeError('Masked source has no connected image atlas to verify')
    return {'sourceConnectedImages':found,'providedContractMapHashes':expected,
            'copiedAtlasesMatchSourceShader':True}
