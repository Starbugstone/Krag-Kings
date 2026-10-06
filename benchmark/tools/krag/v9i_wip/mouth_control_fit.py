"""Prepared true-rim control/soft-tissue fit; not integrated or rendered.

The old +/-0.043 m control positions and +/-0.040 m expression centers came
from an earlier head. This derives the two commissures from the actual
retained source topology instead of guessing new creature proportions.
"""
import json
import numpy as np


def configure(head, context, fit):
    mesh = head.data
    position = mesh.attributes.get('krag_reference_position')
    face_sets = mesh.attributes.get('.sculpt_face_set')
    if position is None or face_sets is None:
        raise RuntimeError('Mouth controls require preserved source anatomy domains')
    raw = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
    position.data.foreach_get('vector', raw); raw = raw.reshape(-1, 3)
    tags = np.zeros(len(raw), dtype=np.uint64)
    for polygon, tag in zip(mesh.polygons, face_sets.data):
        tags[list(polygon.vertices)] |= np.uint64(1) << np.uint64(tag.value)
    member = lambda tag: (tags & (np.uint64(1) << np.uint64(tag))) != 0
    corners = raw[member(7) & member(24) & member(33)]
    if len(corners) != 2 or not (corners[:, 0].min() < 0 < corners[:, 0].max()):
        raise RuntimeError('Expected exactly two retained true oral commissures')
    centers = {}
    previous = {}
    for side, sign in [('L', 1), ('R', -1)]:
        source = corners[np.argmax(corners[:, 0] * sign)]
        centers[side] = source.astype(float)
        name = 'MouthCorner_' + side
        previous[name] = list(context['continuous_head_landmarks'][name])
        context['continuous_head_landmarks'][name] = tuple(fit([source])[0])
    head['krag_fitted_face_landmarks'] = json.dumps(context['continuous_head_landmarks'])
    context['mouth_control_refit'] = {'status': 'Prepared anatomical control fit; actual expressions require review',
        'sourceCorners': {side: p.tolist() for side, p in centers.items()},
        'previousFittedControls': previous,
        'fittedControls': {name: list(context['continuous_head_landmarks'][name]) for name in previous}}
    return centers


def expression_delta(raw, name, centers, fit, head_transform, original):
    if not name.startswith(('Smile_', 'Frown_')):
        return original(raw, name)
    side = name.rsplit('_', 1)[1]; sign = 1 if side == 'L' else -1
    center = np.asarray(centers[side]); smile = name.startswith('Smile_')
    radius = np.asarray((.012, .045, .015))
    front = np.clip((-raw[:, 1] - .025) / .055, 0, 1)
    field = np.exp(-np.sum(((raw - center) / radius) ** 2, axis=1)) * front
    delta = np.zeros_like(raw)
    delta[:, 2] = (.0036 if smile else -.0042) * field
    delta[:, 0] = sign * (.0018 if smile else -.0006) * field
    # Soft adjoining cheek follows the actual corner; retained amplitude is
    # intentionally modest for serious Krag acting, not a playful smile.
    cheek = center + np.asarray((sign * .016, .024, .025))
    support = np.exp(-np.sum(((raw - cheek) / np.asarray((.016, .065, .024))) ** 2, axis=1)) * front
    delta[:, 2] += (.0014 if smile else -.0007) * support
    return head_transform(fit(raw + delta)) - head_transform(fit(raw))
