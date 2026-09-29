"""Rigid phalanx shells, in UE centimetres, inside each joint's stable span.

Flexible native-weighted mail covers joints; rigid noses must not cross pivots.
"""
import math
import numpy as np
from mathutils import Vector
import build_metal_gauntlet_sample as s


def radial_fit(section, head, trees, angles=None):
    axis, dorsal, across = (s.unit(section[k]) for k in ('axis', 'dorsal', 'across'))
    length = section['length']
    ts = np.linspace(.12 * length, .88 * length, 7)
    if angles is None:
        angles = np.linspace(-math.radians(65), math.radians(65), 15)
    rings = []
    for t in ts:
        row = []
        for angle in angles:
            radial = dorsal * math.cos(angle) + across * math.sin(angle)
            center = head + axis * t
            distances = []
            for tree in trees:
                hit, _, _, _ = tree.ray_cast(Vector(center + radial * 6), Vector(-radial), 12.)
                if hit is not None:
                    distance = float((np.asarray(hit) - center) @ radial)
                    if distance > 0:
                        distances.append(distance)
            row.append(max(distances) if distances else section['radius'])
        rings.append(row)
    # Fair the skin samples into a manufactured shell; retain the measured
    # clearance instead of shrinking the finger to a narrow dorsal rectangle.
    rings = np.asarray(rings)
    basis = np.array([np.ones_like(ts), ts / length, (ts / length) ** 2]).T
    fits = np.linalg.lstsq(basis, rings, rcond=None)[0]
    lift = np.maximum(0., np.max(rings - basis @ fits, axis=0))
    def radii(t):
        q = np.clip(t / length, .08, .94)
        values = np.array([1., q, q*q]) @ fits + lift + .08
        values[1:-1] = values[1:-1] * .6 + .2 * (values[:-2] + values[2:])
        return values
    return angles, radii, (axis, dorsal, across)


def finger_shell(section, head, trees, terminal=False, thumb_base=False, outward=None):
    angles = None
    bone=section['bone'];segment=int(bone.split('_')[1])
    pinky=bone.startswith('pinky_')
    ring=bone.startswith('ring_')
    if pinky or ring:
        sign=1. if np.asarray(section['across'])@outward>0 else -1.
        # Outside edge keeps broad coverage. The edge facing the neighbouring
        # finger ends above the shared skin-contact corridor.
        inner,outer=(14.,65.) if pinky else (62.,44.)
        angles=np.linspace(-math.radians(inner if sign>0 else outer),math.radians(outer if sign>0 else inner),15)
    if thumb_base:
        # The thumb metacarpal sits below the palm plate. Put its guard on the
        # exposed outer side, not on the inward dorsal sector under that plate.
        sign = 1. if np.asarray(section['across']) @ outward > 0 else -1.
        center = sign * math.radians(42)
        angles = np.linspace(center-math.radians(38), center+math.radians(38), 17)
    angles, radii, (axis, dorsal, across) = radial_fit(section, head, trees, angles)
    length = section['length']
    rows = []
    start = length * (.28 if thumb_base else .26 if pinky and segment==1 else .16)
    end = length * (.79 if thumb_base else .87 if terminal else .84)
    for t in np.linspace(start, end, 11):
        ring = radii(t)
        offset=.15 if pinky and segment==1 else .035
        rows.append([head + axis*t + (dorsal*math.cos(a) + across*math.sin(a))*r+dorsal*offset
                     for a, r in zip(angles, ring)])
    # No synthetic cap curls down into the native fingertip or finger pad.
    # The native-weighted mail protects the final contact edge instead.
    return np.asarray(rows), (angles, radii, axis, dorsal, across)


def knuckle_hood(section, head, fit, parent_tree):
    angles, radii, axis, dorsal, across = fit
    ring = radii(0.) + .23
    reach = min(.90, section['radius'] * .76)
    rows = []
    for phi in np.radians([-53, -39, -25, -12, 0, 12, 25, 39, 53, 67]):
        row = []
        for a, r in zip(angles, ring):
            radial = dorsal*math.cos(a) + across*math.sin(a)
            point = head + axis*(reach*math.sin(phi)) + radial*(r*math.cos(phi))
            # Nest the rear skirt over the finished palm plate. Both pieces
            # belong to hand, so their shared seam cannot shear under flexion.
            if phi <= 0:
                hit, _, _, _ = parent_tree.ray_cast(Vector(point + dorsal*6), Vector(-dorsal), 12.)
                if hit is not None:
                    height = float((np.asarray(hit)-point) @ dorsal) + .115
                    point += dorsal * max(0., height)
            row.append(point)
        rows.append(row)
    return np.asarray(rows)
