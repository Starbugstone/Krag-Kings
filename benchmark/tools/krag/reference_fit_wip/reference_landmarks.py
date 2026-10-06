"""Read-only visible-mass correspondence from the reviewed concept-derived bust.

Pixel selections are inspectable fitting proposals, not anatomical truth from
an inferred mesh. No rear, eye, mouth-cavity or tusk topology is transferred.
"""
from pathlib import Path
import hashlib
import json
import struct
import numpy as np

ROOT = Path(__file__).resolve().parents[4]
REFERENCE = ROOT/'benchmark/unreal/evidence/triposr-krag-bust-matted-v2'
SHA = 'f6513fa6cb0c50c07d9e1adad1a17e7c15a1f75bfa8dc0745593cb08ef5f0026'


def read_mesh():
    contract = json.loads((REFERENCE/'mesh-coordinate-contract.json').read_text())
    data = (ROOT/contract['meshPath']).read_bytes()
    if hashlib.sha256(data).hexdigest() != SHA:
        raise RuntimeError('Inspected reference GLB changed')
    if struct.unpack_from('<III', data) != (0x46546C67, 2, len(data)):
        raise RuntimeError('Unexpected GLB header')
    length, kind = struct.unpack_from('<II', data, 12)
    if kind != 0x4E4F534A:
        raise RuntimeError('Missing GLB JSON chunk')
    document = json.loads(data[20:20+length])
    offset = 20+length
    length, kind = struct.unpack_from('<II', data, offset)
    if kind != 0x004E4942:
        raise RuntimeError('Missing GLB binary chunk')
    blob = data[offset+8:offset+8+length]
    if any(any(key in node for key in ('matrix', 'rotation', 'translation', 'scale'))
           for node in document['nodes']):
        raise RuntimeError('Source node transforms need explicit evaluation')

    def accessor(index):
        item = document['accessors'][index]
        view = document['bufferViews'][item['bufferView']]
        if 'byteStride' in view or 'sparse' in item:
            raise RuntimeError('Unsupported packed source format')
        dtype = {5125: '<u4', 5126: '<f4', 5121: 'u1'}[item['componentType']]
        width = {'SCALAR': 1, 'VEC3': 3, 'VEC4': 4}[item['type']]
        start = view.get('byteOffset', 0)+item.get('byteOffset', 0)
        return np.frombuffer(blob, dtype, item['count']*width, start).reshape(-1, width).copy()

    primitives = [p for mesh in document['meshes'] for p in mesh['primitives']]
    if len(primitives) != 1 or primitives[0].get('mode', 4) != 4:
        raise RuntimeError('Expected reviewed single triangle mesh')
    primitive = primitives[0]
    return accessor(primitive['attributes']['POSITION']).astype(float), accessor(primitive['indices']).reshape(-1, 3), contract


def projection(points, contract):
    view = next(item for item in contract['views'] if item['path'] == 'Clay_QuarterPlusXMinusY.png')
    camera, target = np.asarray(view['cameraPosition']), np.asarray(contract['cameraTarget'])
    toward = target-camera
    toward /= np.linalg.norm(toward)
    right = np.cross(toward, (0., 0., 1.))
    right /= np.linalg.norm(right)
    up = np.cross(right, toward)
    scale = contract['cameraOrthoScale']
    relative = points-target
    return np.column_stack((320+(relative@right)*640/scale,
                            320-(relative@up)*640/scale)), (points-camera)@toward


def pick(points, triangles, pixels, depth, xy):
    projected = pixels[triangles]
    a = projected[:, 0]
    b, c, q = projected[:, 1]-a, projected[:, 2]-a, np.asarray(xy)-a
    det = b[:, 0]*c[:, 1]-b[:, 1]*c[:, 0]
    good = abs(det) > 1e-10
    u = np.divide(q[:, 0]*c[:, 1]-q[:, 1]*c[:, 0], det, out=np.zeros_like(det), where=good)
    v = np.divide(b[:, 0]*q[:, 1]-b[:, 1]*q[:, 0], det, out=np.zeros_like(det), where=good)
    hits = np.flatnonzero(good & (u >= 0) & (v >= 0) & (u+v <= 1))
    if not len(hits):
        raise RuntimeError('Reference landmark misses the actual surface: '+str(xy))
    bary = np.column_stack((1-u[hits]-v[hits], u[hits], v[hits]))
    index = int(np.argmin(np.einsum('ij,ij->i', depth[triangles[hits]], bary)))
    return {'pixel': list(xy), 'triangle': int(hits[index]), 'barycentric': bary[index].tolist(),
            'point': np.einsum('i,ij->j', bary[index], points[triangles[hits[index]]]).tolist()}


# These picks identify broad surfaces in the actual quarter clay view. Ocular
# picks establish a fitting frame only: the generated ocular mesh is excluded.
PICKS = {
    'ocular_left_frame': (287, 248), 'ocular_right_frame': (394, 239),
    'crown': (329, 85), 'forehead_center': (330, 168),
    'glabella_mass': (344, 238), 'glabella_furrow': (347, 213),
    'brow_left_crest': (290, 232), 'brow_right_crest': (388, 224),
    'brow_left_support': (286, 209), 'brow_right_support': (388, 202),
    'bridge': (344, 252), 'nose_tip': (339, 272),
    'nasal_left_ala': (307, 267), 'nasal_right_ala': (366, 264),
    'left_malar_crest': (252, 275), 'right_malar_crest': (411, 269),
    'left_malar_plane': (257, 308), 'right_malar_plane': (410, 301),
    'left_nasolabial': (290, 300), 'right_nasolabial': (392, 303),
    'upper_muzzle_left': (313, 302), 'upper_muzzle_right': (369, 300),
    'upper_lip_center': (346, 328), 'lower_lip_center': (345, 349),
    'mouth_left_corner': (291, 329), 'mouth_right_corner': (407, 330),
    'chin_center': (327, 391), 'chin_left_plane': (291, 374), 'chin_right_plane': (377, 374),
    'left_jaw_angle': (232, 328), 'right_jaw_angle': (414, 350),
}


def measure():
    points, triangles, contract = read_mesh()
    pixels, depth = projection(points, contract)
    landmarks = {name: pick(points, triangles, pixels, depth, xy) for name, xy in PICKS.items()}
    left, right = [np.asarray(landmarks[name]['point']) for name in ('ocular_left_frame', 'ocular_right_frame')]
    lateral = right-left
    lateral[2] = 0
    lateral /= np.linalg.norm(lateral)
    anterior = np.cross(lateral, (0., 0., 1.))
    center = (left+right)*.5
    if np.dot(np.asarray(landmarks['nose_tip']['point'])-center, anterior) < 0:
        anterior *= -1
    frame = np.asarray([lateral, -anterior, (0., 0., 1.)])
    for item in landmarks.values():
        item['faceFramePoint'] = ((np.asarray(item['point'])-center)@frame.T).tolist()
    return {'status': 'Actual saved reference surface picks only; constrained source fit not generated',
            'referenceSha256': SHA, 'referenceUnits': 'normalized generator units',
            'landmarkView': 'Clay_QuarterPlusXMinusY.png',
            'frameCenter': center.tolist(), 'rawToFaceFrameRows': frame.tolist(),
            'landmarks': landmarks, 'artisticAcceptance': False,
            'excluded': ['reference orbital and oral topology', 'tusks', 'inferred rear', 'surface noise']}


if __name__ == '__main__':
    result = measure()
    destination = ROOT/'benchmark/art/krag/reference-fit-study'
    destination.mkdir(exist_ok=True)
    (destination/'visible-reference-landmarks.json').write_text(json.dumps(result, indent=2)+'\n', newline='\n')
    print(json.dumps({key: value['faceFramePoint'] for key, value in result['landmarks'].items()}, indent=2))
