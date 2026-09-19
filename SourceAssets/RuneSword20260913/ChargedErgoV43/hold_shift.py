"""Bring the charged hold closer to the body so the left elbow can bend.

The posed arm is 96.7% extended because the pommel sits at almost the left
arm's full reach. Moving the whole hold (sword and both hands) along the line
from the left wrist to the left shoulder shortens that reach without touching
the grips: every hand keeps its position and orientation relative to the
hilt, and both arms are re-solved with a two-bone IK that keeps each elbow on
its authored side.
"""
import math
from mathutils import Matrix, Quaternion, Vector

UP = {False: 'upperarm_l', True: 'upperarm_r'}
LO = {False: 'lowerarm_l', True: 'lowerarm_r'}
HAND = {False: 'hand_l', True: 'hand_r'}
SWORD = 'WPN_root'


def ease(value):
    value = max(0.0, min(1.0, value))
    return value * value * value * (value * (value * 6.0 - 15.0) + 10.0)


def envelope(clip, seconds, source_time=None):
    if clip == 'HeavyCharge':
        return ease(seconds / 0.10)
    if clip == 'HeavyRelease':
        return 1.0 - ease((seconds - 0.85) / 0.15)
    if clip == 'Slash1':
        charge_time = (source_time(seconds) if source_time else seconds) * 0.65 / 0.17
        return ease(charge_time / 0.10) * (1.0 - ease((seconds - 0.65) / 0.20))
    raise ValueError('unsupported clip ' + clip)


def solve_arm(pose, right, offset):
    """Two-bone IK for one arm with the authored elbow kept as the pole."""
    up, lo, hand = UP[right], LO[right], HAND[right]
    S = pose[up].translation
    E = pose[lo].translation
    W = pose[hand].translation
    a = (E - S).length
    b = (W - E).length
    target = W + offset
    delta = target - S
    d = delta.length
    limit = a + b - 1e-4
    if d > limit:
        target = S + delta.normalized() * limit
        delta = target - S
        d = limit
    u = delta.normalized()
    pole = (E - S) - u * ((E - S).dot(u))
    if pole.length < 1e-5:
        pole = Vector((0.0, 0.0, -1.0)) - u * (-u.z)
    pole.normalize()
    cos_alpha = max(-1.0, min(1.0, (a * a + d * d - b * b) / (2.0 * a * d)))
    alpha = math.acos(cos_alpha)
    E2 = S + (u * math.cos(alpha) + pole * math.sin(alpha)) * a
    upper_rot = ((E - S).normalized().rotation_difference((E2 - S).normalized())
                 @ pose[up].to_quaternion())
    fore_rot = ((W - E).normalized().rotation_difference((target - E2).normalized())
                @ pose[lo].to_quaternion())
    return {
        up: Matrix.LocRotScale(S, upper_rot, pose[up].decompose()[2]),
        lo: Matrix.LocRotScale(E2, fore_rot, pose[lo].decompose()[2]),
        hand: Matrix.LocRotScale(target, pose[hand].to_quaternion(), pose[hand].decompose()[2]),
    }, {
        'reach_before_m': d - offset.length if False else (W - S).length,
        'reach_after_m': d,
        'elbow_bone_angle_before': math.degrees((E - S).normalized().angle((W - E).normalized())),
        'elbow_bone_angle_after': math.degrees((E2 - S).normalized().angle((target - E2).normalized())),
    }


def build(pose, weight, distance, rest=None, roll_solver=None):
    """Return the target world matrices for the moved hold."""
    if weight <= 0.0:
        return {}, {}
    S = pose[UP[False]].translation
    W = pose[HAND[False]].translation
    direction = (S - W).normalized()
    offset = direction * (distance * weight)
    targets = {SWORD: Matrix.LocRotScale(pose[SWORD].translation + offset,
                                         pose[SWORD].to_quaternion(),
                                         pose[SWORD].decompose()[2])}
    stats = {}
    for right in (False, True):
        solved, info = solve_arm(pose, right, offset)
        targets.update(solved)
        stats['left' if not right else 'right'] = info
    if rest is not None and roll_solver is not None:
        modified = dict(pose)
        modified.update(targets)
        roll, residual, _ = roll_solver(modified, rest)
        if roll:
            base = targets[UP[False]]
            axis = (targets[LO[False]].translation - base.translation).normalized()
            targets[UP[False]] = Matrix.LocRotScale(
                base.translation, Quaternion(axis, math.radians(roll)) @ base.to_quaternion(),
                base.decompose()[2])
        stats['left']['shoulder_roll_deg'] = roll
        stats['left']['elbow_metric_after_deg'] = residual
    return targets, stats
