"""Redistribute the left forearm's axial rotation along the forearm.

The authored charged attack stores the whole forearm pronation on
``lowerarm_l``, so every forearm vertex rotates rigidly with it and the shear
lands on the elbow seam. This module rebuilds that rotation as a linear
gradient over the three bones that actually hold forearm skin:

    lowerarm_l            x ~ 0.00   elbow cap            (68 dominant vertices)
    lowerarm_twist_02_l   x ~ 0.29   elbow-side forearm   (988)
    lowerarm_twist_01_l   x ~ 0.86   wrist-side forearm   (589)
    hand_l                x ~ 1.0    hand

Only the roll of those bones about the forearm axis changes. Bone positions,
bone directions, the hand's world orientation (grip), the sword, the right arm
and the timing are all preserved bit-exactly.
"""
import math
from mathutils import Matrix, Quaternion, Vector

LO = 'lowerarm_l'
TWIST_01 = 'lowerarm_twist_01_l'
TWIST_02 = 'lowerarm_twist_02_l'
HAND = 'hand_l'
UP = 'upperarm_l'

# Median position of each bone's dominant vertices along the forearm axis.
AXIS_POSITION = {LO: 0.0, TWIST_02: 0.286, TWIST_01: 0.859}
EDITED = (LO, TWIST_01, TWIST_02, HAND)


def ease(value):
    value = max(0.0, min(1.0, value))
    return value * value * value * (value * (value * 6.0 - 15.0) + 10.0)


def clamp01(value):
    return max(0.0, min(1.0, value))


def envelope(clip, seconds, source_time=None):
    """How much of the elbow's rotation is moved into the forearm.

    Zero at every seam with a clip that keeps the authored profile (idle at
    both ends of the charge and of Slash1) and one through the working range.
    Slash1 follows the same charge clock the runtime uses for an early release
    (charge .65 s maps to Slash1 .17 s), so the two clips still agree there.
    """
    if clip == 'HeavyCharge':
        return ease(seconds / 0.10)
    if clip == 'HeavyRelease':
        return 1.0 - ease((seconds - 0.85) / 0.15)
    if clip == 'Slash1':
        charge_time = (source_time(seconds) if source_time else seconds) * 0.65 / 0.17
        return ease(charge_time / 0.10) * (1.0 - ease((seconds - 0.65) / 0.20))
    raise ValueError('unsupported clip ' + clip)


def forearm_roll(pose, rest):
    """Project-style axial difference of the forearm relative to the upper arm."""
    up = pose[UP]
    fore = pose[LO]
    hand = pose[HAND]
    axis = (hand.translation - fore.translation).normalized()
    rest_fore = (rest[HAND].translation - rest[LO].translation).normalized()
    rest_dirs = {
        LO: (rest[HAND].translation - rest[LO].translation).normalized(),
        TWIST_01: (rest[TWIST_01].translation - rest[LO].translation).normalized(),
        TWIST_02: (rest[TWIST_02].translation - rest[LO].translation).normalized(),
        HAND: rest_fore,
    }
    up_delta = up.to_quaternion() @ rest[UP].to_quaternion().inverted()
    fore_delta = fore.to_quaternion() @ rest[LO].to_quaternion().inverted()
    no_roll = (up_delta @ rest_fore).rotation_difference(axis) @ up_delta
    relative = fore_delta @ no_roll.inverted()
    vector = Vector((relative.x, relative.y, relative.z))
    roll = 2.0 * math.atan2(vector.dot(axis), relative.w)
    roll = (roll + math.pi) % (2.0 * math.pi) - math.pi
    return {'axis': axis, 'no_roll': no_roll, 'roll': roll, 'rest_dirs': rest_dirs}


def rebuild(pose, rest, weight):
    """Return pose matrices for the edited bones with the roll redistributed."""
    if weight <= 0.0:
        return {}
    info = forearm_roll(pose, rest)
    axis = info['axis']
    no_roll = info['no_roll']
    roll = info['roll']
    result = {}
    for bone, position in AXIS_POSITION.items():
        remaining = roll * (1.0 - weight * (1.0 - position))
        matrix = pose[bone]
        scale = matrix.decompose()[2]
        result[bone] = Matrix.LocRotScale(
            matrix.translation,
            Quaternion(axis, remaining) @ no_roll @ rest[bone].to_quaternion(),
            scale)
    # The hand keeps its authored world orientation, which is what preserves
    # the grip; its local rotation is rebuilt against the new parent.
    result[HAND] = pose[HAND].copy()
    return result


def verify_decomposition(pose, rest):
    """Check that roll(phi) composed with the transport frame rebuilds the pose."""
    info = forearm_roll(pose, rest)
    rebuilt = Quaternion(info['axis'], info['roll']) @ info['no_roll'] @ rest[LO].to_quaternion()
    error = pose[LO].to_quaternion().rotation_difference(rebuilt)
    return math.degrees(2.0 * math.atan2(math.sqrt(error.x ** 2 + error.y ** 2 + error.z ** 2),
                                         abs(error.w)))
