"""Read-only source skin/strand attribution before a native groom appearance pass."""
import argparse
import json
import math
import sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from strand_contract import sha


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--source-sha256', required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    if sha(args.source) != args.source_sha256 or args.output.exists():
        raise RuntimeError('Pinned source changed or audit already exists')
    report = json.loads(args.report.read_text())
    if report['candidateSha256'] != args.source_sha256:
        raise RuntimeError('Native source report mismatch')
    bpy.ops.wm.open_mainfile(filepath=str(args.source), load_ui=False)
    rig = bpy.data.objects['Nib_Rig']
    rig.animation_data.action = None
    for track in rig.animation_data.nla_tracks:
        track.mute = True
    for bone in rig.pose.bones:
        bone.matrix_basis = Matrix.Identity(4)
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()
    results = []
    def make_tree(obj):
        obj.data.calc_loop_triangles()
        world = [obj.matrix_world @ v.co for v in obj.data.vertices]
        return BVHTree.FromPolygons(world, [tuple(t.vertices) for t in obj.data.loop_triangles], all_triangles=True)
    for region in report['regions']:
        surface = bpy.data.objects[region['sourceSurfaceObject']]
        tree = make_tree(surface)
        occluders = {surface.name: tree}
        # The visible pink lining and basal ridges are separate retained meshes.
        # Checking only the closed outer shell can miss the actual hair occluder.
        if region['name'].startswith('Ear'):
            side = 'L' if region['name'].endswith('_L') else 'R'
            for obj in bpy.data.collections['Nib_Authored_Components'].objects:
                if (obj.type != 'MESH' or obj.get('variant', 'all') not in ['all', 'natural', 'organic']
                        or obj.get('bone') != 'Ear_' + side):
                    continue
                if obj.name.startswith(('Ear inner velvet', 'Rounded auricle cartilage rim', 'Auricle basal cartilage fold')):
                    occluders[obj.name] = make_tree(obj)
        data = bpy.data.objects['Nib native ' + region['name']].data
        positions = np.empty(len(data.points) * 3, np.float32)
        data.attributes['position'].data.foreach_get('vector', positions)
        positions = positions.reshape(-1, 9, 3)
        entry = {'name': region['name'], 'parts': []}
        offset = 0
        for part in region['parts']:
            count = part['rootSamples']
            strands = positions[offset:offset + count]
            lengths = np.linalg.norm(np.diff(strands, axis=1), axis=2).sum(axis=1)
            dz = strands[:, -1, 2] - strands[:, 0, 2]
            signed = []
            blocked = {'Neutral': 0, 'Profile': 0}
            first_owners = {'Neutral': {}, 'Profile': {}}
            root_owners = {}
            samples = 0
            worst = []
            for i in range(0, count, max(1, count // 160)):
                root = Vector(strands[i, 0])
                hits = []
                for owner, candidate in occluders.items():
                    _, _, _, hit = candidate.ray_cast(root + Vector((0, -3, 0)), Vector((0, 1, 0)), 3)
                    if hit is not None and hit < 3 - .0005:
                        hits.append((hit, owner))
                if hits:
                    owner = min(hits)[1]
                    root_owners[owner] = root_owners.get(owner, 0) + 1
                for j in [2, 4, 6, 8]:
                    point = Vector(strands[i, j])
                    nearest, normal, triangle, distance = tree.find_nearest(point)
                    value = float((point - nearest).dot(normal))
                    signed.append(value)
                    if value < -.0005:
                        worst.append({'curve': offset + i, 'point': j, 'signedNearestMeters': value,
                                      'position': list(point), 'nearestTriangle': triangle})
                    for view, direction in [('Neutral', Vector((.35, -3, .16)).normalized()),
                                            ('Profile', Vector((1, 0, .005)).normalized())]:
                        camera = point + direction * 3
                        hits = []
                        for owner, candidate in occluders.items():
                            _, _, _, hit = candidate.ray_cast(camera, -direction, 3)
                            if hit is not None and hit < 3 - .0005:
                                hits.append((hit, owner))
                        if hits:
                            blocked[view] += 1
                            hit, owner = min(hits)
                            first_owners[view][owner] = first_owners[view].get(owner, 0) + 1
                            if view == 'Neutral' and owner != surface.name:
                                worst.append({'curve': offset + i, 'point': j,
                                    'signedNearestMeters': value, 'position': list(point),
                                    'firstVisibleOccluder': owner, 'cameraRayBurialMeters': 3 - hit})
                    samples += 1
            entry['parts'].append({'region': part['region'], 'curves': count,
                'arcLengthMeters': {'min': float(lengths.min()), 'median': float(np.median(lengths)), 'max': float(lengths.max())},
                'tipDeltaZMedianMeters': float(np.median(dz)),
                'sampledNonRootPoints': samples,
                'nearestSurfaceSignedMeters': {'min': min(signed), 'median': float(np.median(signed)),
                    'negativeBeyond0_5mm': sum(x < -.0005 for x in signed)},
                'sourceSurfaceOccludedPoints': blocked,
                'actualFirstOccluderCounts': first_owners,
                'rootFrontOccluderCounts': root_owners,
                'actualOccluders': list(occluders),
                'worstNearestSamples': sorted(worst, key=lambda r: r['signedNearestMeters'])[:12]})
            offset += count
        results.append(entry)
    if sha(args.source) != args.source_sha256:
        raise RuntimeError('Read-only audit changed source')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({'source': str(args.source), 'sourceSha256': args.source_sha256,
        'sourceReportSha256': sha(args.report), 'recipeSha256': sha(Path(__file__)), 'regions': results,
        'interpretation': 'Nearest signed distances and camera occlusion are attribution only; rear-facing hair is naturally occluded. Inspect actual sampled locations before correcting flow.',
        'sourceChanged': False, 'artisticAcceptance': False}, indent=2) + '\n', newline='\n')
    print('NIB_NATIVE_FLOW_AUDIT_COMPLETE', flush=True)


if __name__ == '__main__':
    main()
