"""Prepared native guide proposal; no scene mutation or artistic acceptance.

The frozen 26k pilot remains the engine control. This recipe is deliberately
separate and must follow an actual skin-clearance audit and two-view review.
"""
import math
import random
import sys
from pathlib import Path
from mathutils import Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'surface_layers_wip'))
from flow_guides import ear_frame


def tangent(direction, normal):
    value = direction - normal * direction.dot(normal)
    if value.length < 1e-6:
        value = normal.cross(Vector((1, 0, 0)))
    if value.length < 1e-6:
        raise RuntimeError('Native guide has no tangent')
    return value.normalized()


def make(region, root, normal, source, seed, side=1):
    """A curved tuft spine; all dimensions are provisional appearance tuning."""
    rng = random.Random(seed)
    if region.startswith('ear_'):
        along, across_fraction, axis, across, width = ear_frame(root, side)
        inward = across * -math.copysign(1, across_fraction)
        if region == 'ear_exterior':
            # Short tawny nap must also root on the outer/front rim, not only
            # the rear-facing surface invisible from the character camera.
            direction = axis + across * rng.uniform(-.30, .30)
            length = rng.uniform(.006, .013)
            lift = rng.uniform(.0020, .0040)
            tip_lift = rng.uniform(.0012, .0030)
        elif region == 'ear_undercoat':
            direction = inward * .82 + axis * rng.uniform(-.18, .48)
            length = rng.uniform(.013, .023)
            lift = rng.uniform(.004, .007)
            tip_lift = rng.uniform(.0025, .005)
        else:
            direction = inward * .90 + axis * rng.uniform(-.25, .42)
            if along < .24:
                direction = axis * .8 + inward * .4
            length = rng.uniform(.024, .047)
            # Keep the pink center open. This bounds the projected lock span,
            # not an arbitrary opaque card width.
            budget = max(.013, (abs(across_fraction) - .20) * width)
            projected = abs(tangent(direction, normal).dot(across))
            length = min(length, budget / max(.3, projected))
            lift = rng.uniform(.010, .018)
            tip_lift = rng.uniform(.005, .010)
    else:
        side = 1 if root.x >= 0 else -1
        if region == 'crown':
            direction = Vector((side * rng.uniform(.15, .7), rng.uniform(-.5, .15), .55))
            length = rng.uniform(.020, .040)
            lift = rng.uniform(.017, .029)
            tip_lift = rng.uniform(.010, .021)
        elif region == 'fringe':
            direction = Vector((side * .80, -.12, rng.uniform(-.45, -.18)))
            length = rng.uniform(.019, .033)
            lift = rng.uniform(.009, .016)
            tip_lift = rng.uniform(.005, .011)
        elif region.startswith('temple'):
            direction = Vector((side * .55, rng.uniform(.10, .48), rng.uniform(-.65, -.30)))
            length = rng.uniform(.020, .039)
            lift = rng.uniform(.011, .020)
            tip_lift = rng.uniform(.005, .014)
        elif region == 'nape':
            direction = Vector((side * rng.uniform(.25, .65), .35, rng.uniform(-.7, -.35)))
            length = rng.uniform(.018, .038)
            lift = rng.uniform(.009, .018)
            tip_lift = rng.uniform(.005, .012)
        else:
            direction = Vector((side * .25, -.10, -.40 if source.z < .35 else .25))
            length = rng.uniform(.006, .013)
            lift = rng.uniform(.002, .004)
            tip_lift = rng.uniform(.0010, .0025)
    direction = tangent(direction, normal)
    lateral = normal.cross(direction).normalized()
    curl = lateral * rng.uniform(-.006, .006)
    middle = root + direction * length * rng.uniform(.38, .55) + normal * lift + curl
    tip = root + direction * length + normal * tip_lift - curl * rng.uniform(.15, .40)
    return {'region': region, 'root': list(root), 'normal': list(normal),
            'middle': list(middle), 'tip': list(tip), 'seed': seed,
            'lengthProposalMeters': length, 'tipLiftProposalMeters': tip_lift,
            'undercoat': region in ['undercoat', 'ear_undercoat', 'ear_exterior']}


def strand_point(root, normal, guide, t, length_scale, curl_phase, undercoat=False):
    """Lifted spine with genuine local tip convergence, never coincident roots.

    The pilot translated every guide displacement to every independent root;
    that creates nearly parallel locks. This retains each root but bends toward
    a shared guide tip progressively, with finite clump attraction.
    """
    anchor = Vector(guide['root'])
    guide_normal = Vector(guide['normal'])
    rotation = guide_normal.rotation_difference(normal)
    middle = rotation @ (Vector(guide['middle']) - anchor)
    tip = rotation @ (Vector(guide['tip']) - anchor)
    displacement = (middle * (2 * (1 - t) * t) + tip * t * t) * length_scale
    anchor_offset = anchor - root
    anchor_offset -= normal * anchor_offset.dot(normal)
    # Limit convergence to a local 8mm neighborhood, avoiding long cross-scalp
    # seams when the nearest guide lies across a sparse region boundary.
    if anchor_offset.length > .008:
        anchor_offset *= .008 / anchor_offset.length
    attraction = .18 if undercoat else .52
    side = normal.cross(tip).normalized()
    wave = side * ((.00025 if undercoat else .0011) * math.sin(math.pi * t)
                   * math.sin(2 * math.pi * t + curl_phase))
    return root + displacement + anchor_offset * attraction * t * t + wave


def ear_selector(region, point, normal, source):
    """Concentrate cream on the border; retain the visible central membrane."""
    side = 1 if point.x >= 0 else -1
    along, across, _, _, _ = ear_frame(point, side)
    if not .045 < along < .975:
        return False
    if region == 'ear_exterior':
        return normal.y > .12 or (.80 < abs(across) < 1.04 and normal.y < .12)
    if normal.y > -.15:
        return False
    if region == 'ear_undercoat':
        return .55 < abs(across) < .92 or (along < .24 and abs(across) < .60)
    return (.63 < abs(across) < .91 and along < .91) or (along < .25 and abs(across) < .52)
