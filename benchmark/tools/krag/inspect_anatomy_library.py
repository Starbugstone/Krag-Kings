"""Read-only inventory of the official CC0 base-mesh bundle.

Does not alter the library or current Krag sources/exports. Raw low-resolution
topology dumps allow anatomical landmark review before any adaptation.
"""
import bpy, json, hashlib
from pathlib import Path
from mathutils import Vector
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
LIBRARY = ROOT / 'benchmark/art/reference-anatomy/blender-studio-human-base-meshes/source/human-base-meshes-bundle-v1.4.1/human_base_meshes_bundle.blend'
OUT = ROOT / 'benchmark/art/krag/anatomy-study'
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(LIBRARY), load_ui=False)
report = {'source': str(LIBRARY), 'sourceSha256': hashlib.sha256(LIBRARY.read_bytes()).hexdigest(),
          'status': 'Reference inventory only; no topology adopted into Krag',
          'texts': {t.name: t.as_string() for t in bpy.data.texts}, 'objects': []}
for obj in bpy.data.objects:
    if obj.type != 'MESH':
        continue
    bounds = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    entry = {'name': obj.name, 'vertices': len(obj.data.vertices), 'polygons': len(obj.data.polygons),
             'matrixWorld': [list(row) for row in obj.matrix_world],
             'worldBounds': {'min': [min(v[a] for v in bounds) for a in range(3)],
                             'max': [max(v[a] for v in bounds) for a in range(3)]},
             'modifiers': [{'name': m.name, 'type': m.type,
                            **({k: getattr(m,k) for k in ['levels','render_levels']} if m.type == 'SUBSURF' else {})}
                           for m in obj.modifiers],
             'vertexGroups': [g.name for g in obj.vertex_groups],
             'collections': [c.name for c in obj.users_collection]}
    if obj.asset_data:
        entry['asset'] = {key: getattr(obj.asset_data, key, '') for key in ['author','description','copyright','license','catalog_id']}
    report['objects'].append(entry)
    label = obj.name.lower()
    selected = 'hand' in label or ('body' in label and 'male' in label and 'female' not in label) or ('head' in label and 'anim' in label)
    if 'realistic' in label and selected and 'primitive' not in label:
        path = OUT / (obj.name.replace('/', '_') + '.npz')
        np.savez_compressed(path, vertices=np.array([tuple(v.co) for v in obj.data.vertices], dtype=np.float32),
                            polygons=np.array([tuple(p.vertices) for p in obj.data.polygons], dtype=object),
                            world_matrix=np.array(obj.matrix_world, dtype=np.float64))
        entry['rawTopologyDump'] = path.name
(OUT / 'library-inventory.json').write_text(json.dumps(report, indent=2))
print('REFERENCE INVENTORY:', len(report['objects']), 'meshes;', len(report['texts']), 'text blocks', flush=True)
