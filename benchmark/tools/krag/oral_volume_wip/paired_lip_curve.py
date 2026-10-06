"""Broad lower oral arc with a finite, supported commissure tangent."""
import numpy as np


def lower_arc(u, bottom_z, corner_z, old_u, old_z):
    u = np.clip(np.asarray(u, float), 0., 1.)
    transition = .78
    height = corner_z-bottom_z
    base = bottom_z+height*(1-np.maximum(1-u*u, 0)**.25)
    start = bottom_z+height*(1-(1-transition*transition)**.25)
    start_slope = height*.5*transition/(1-transition*transition)**.75
    old_u, old_z = np.asarray(old_u), np.asarray(old_z)
    support = (old_u >= .88) & (old_u <= 1)
    if support.sum() < 3:
        raise RuntimeError('Actual oral rim lacks a resolved commissure neighborhood')
    # Preserve the existing finite tissue exit direction rather than the
    # infinite derivative of a superellipse at u=1. The angle is measured
    # from this same saved rim; it is not an enlarged displacement allowance.
    slope = float(np.polyfit(old_u[support], old_z[support], 1)[0])
    if not 0 < slope < .45:
        raise RuntimeError('Actual oral commissure tangent needs inspection: '+str(slope))
    t = np.clip((u-transition)/(1-transition), 0, 1)
    end = (2*t**3-3*t*t+1)*start + (t**3-2*t*t+t)*(1-transition)*start_slope
    end += (-2*t**3+3*t*t)*corner_z+(t**3-t*t)*(1-transition)*slope
    return np.where(u > transition, end, base), dict(transitionFraction=transition,
        savedCommissureSlopeMetersPerFraction=slope, startSlopeMetersPerFraction=float(start_slope),
        finiteEndpointTangent=True)
