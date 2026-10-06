"""Read CMU's original ASF/AMC into metric, +Z-up/-Y-forward joint samples.

Format interpretation follows CMU's linked ASF/AMC specification:
https://research.cs.wisc.edu/graphics/Courses/cs-838-1999/Jeff/ASF-AMC.html
Column-vector equivalent of the documented local transform: B C M C^-1.
No Blender dependency; this module does not execute downloaded source code.
"""
import argparse
import json
import math
from pathlib import Path

IDENTITY = [[1., 0., 0.], [0., 1., 0.], [0., 0., 1.]]
CANONICAL = [[1., 0., 0.], [0., 0., -1.], [0., 1., 0.]]


def multiply(a, b):
    return [[sum(a[i][k]*b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def transform(m, v):
    return [sum(row[k]*v[k] for k in range(3)) for row in m]


def transpose(m):
    return [list(row) for row in zip(*m)]


def rotation(axis, degrees):
    angle = math.radians(degrees)
    c, s = math.cos(angle), math.sin(angle)
    if axis == 'x': return [[1, 0, 0], [0, c, -s], [0, s, c]]
    if axis == 'y': return [[c, 0, s], [0, 1, 0], [-s, 0, c]]
    if axis == 'z': return [[c, -s, 0], [s, c, 0], [0, 0, 1]]
    raise ValueError(axis)


def compose(channels, values):
    result = IDENTITY
    for channel, value in zip(channels, values):
        if channel.lower().startswith('r'):
            result = multiply(rotation(channel[-1].lower(), value), result)
    return result


def read_skeleton(path):
    bones, hierarchy, root, units = {}, {}, {}, {}
    section, current = '', None
    for line in Path(path).read_text().splitlines():
        words = line.strip().split()
        if not words or words[0].startswith('#'): continue
        if words[0].startswith(':'):
            section = words[0][1:]; continue
        key, values = words[0], words[1:]
        if section == 'units': units[key] = values
        elif section == 'root': root[key] = values
        elif section == 'bonedata':
            if key == 'begin': current = {}
            elif key == 'end': bones[current['name'][0]] = current
            elif current is not None: current[key] = values
        elif section == 'hierarchy' and key not in ('begin', 'end'):
            hierarchy[key] = values
    if units.get('angle') != ['deg']: raise ValueError('Unsupported angular unit')
    scale = .0254/float(units['length'][0])
    result = {}
    for name, bone in bones.items():
        angles = list(map(float, bone['axis'][:3]))
        order = bone['axis'][3].lower()
        axis_values = dict(zip('xyz', angles))
        c = compose(['r'+axis for axis in order], [axis_values[a] for a in order])
        result[name] = {'length': float(bone['length'][0])*scale,
                        'direction': list(map(float, bone['direction'])),
                        'channels': bone.get('dof', []), 'basis': c}
    for parent, children in hierarchy.items():
        for child in children: result[child]['parent'] = parent
    return {'bones': result, 'hierarchy': hierarchy, 'root': root, 'scale': scale}


def read_frames(path):
    frames, current = [], None
    for line in Path(path).read_text().splitlines():
        words = line.strip().split()
        if not words or words[0].startswith(('#', ':')): continue
        if len(words) == 1 and words[0].isdigit():
            current = {'frame': int(words[0]), 'channels': {}}; frames.append(current)
        else:
            if current is None: raise ValueError('AMC channel without a frame')
            current['channels'][words[0]] = list(map(float, words[1:]))
    return frames


def evaluate(skeleton, frame):
    raw = frame['channels']; root_order = skeleton['root']['order']
    channels = dict(zip([x.lower() for x in root_order], raw['root']))
    root_position = [channels['t'+a]*skeleton['scale'] for a in 'xyz']
    root_rotation = compose(root_order, raw['root'])
    # Official selected skeletons have no additional root origin/orientation.
    for field in ('position', 'orientation'):
        if any(float(x) != 0 for x in skeleton['root'][field]):
            raise ValueError('Nonzero ASF root reference requires explicit support')
    heads, tails, rotations = {'root': root_position}, {'root': root_position}, {'root': root_rotation}
    def visit(parent):
        for name in skeleton['hierarchy'].get(parent, []):
            bone = skeleton['bones'][name]
            values = raw.get(name, [])
            if len(values) != len(bone['channels']): raise ValueError('AMC channel mismatch '+name)
            local = multiply(multiply(bone['basis'], compose(bone['channels'], values)), transpose(bone['basis']))
            global_rotation = multiply(rotations[parent], local)
            head = tails[parent]
            offset = transform(global_rotation, [v*bone['length'] for v in bone['direction']])
            heads[name] = head
            tails[name] = [head[i]+offset[i] for i in range(3)]
            rotations[name] = global_rotation
            visit(name)
    visit('root')
    return {'frame': frame['frame'], 'heads': {k: transform(CANONICAL, v) for k, v in heads.items()},
            'tails': {k: transform(CANONICAL, v) for k, v in tails.items()},
            'rotations': {k: multiply(multiply(CANONICAL, v), transpose(CANONICAL)) for k, v in rotations.items()}}


def load(asf, amc):
    skeleton = read_skeleton(asf)
    return skeleton, [evaluate(skeleton, frame) for frame in read_frames(amc)]


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--asf', type=Path, required=True)
    parser.add_argument('--amc', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists(): raise RuntimeError('Preserve prior output')
    skeleton, samples = load(args.asf, args.amc)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({'sourceFps': 120, 'canonicalAxes': '+Z up, -Y forward at zero root yaw',
                                     'skeleton': skeleton, 'samples': samples}, separators=(',', ':'))+'\n')
    print(json.dumps({'samples': len(samples), 'output': str(args.output)}))
