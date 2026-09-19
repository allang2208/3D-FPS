"""Solver that moves the charged attack's left-arm twist from the elbow to the shoulder.

The grip fixes the hand, hence the forearm, hence the axial difference across
the elbow. The only joint that can carry that difference is the shoulder, so
this rolls ``upperarm_l`` about its own axis until the elbow's axial
difference is zero, leaving the forearm, the hand, the sword and the wrist
exactly as authored.

The roll is solved per frame with a secant iteration because the relation is
not 1:1 (the rig's rest pose is not a straight arm), and the root is tracked
from the previous frame so the solution stays continuous.
"""
import math
from mathutils import Matrix, Quaternion, Vector

UP = 'upperarm_l'
LO = 'lowerarm_l'
HAND = 'hand_l'


def ease(value):
    value = max(0.0, min(1.0, value))
    return value * value * value * (value * (value * 6.0 - 15.0) + 10.0)


def envelope(clip, seconds, source_time=None):
    """Zero at every seam with a clip that keeps the authored pose."""
    if clip == 'HeavyCharge':
        return ease(seconds / 0.10)
    if clip == 'HeavyRelease':
        return 1.0 - ease((seconds - 0.85) / 0.15)
    if clip == 'Slash1':
        charge_time = (source_time(seconds) if source_time else seconds) * 0.65 / 0.17
        return ease(charge_time / 0.10) * (1.0 - ease((seconds - 0.65) / 0.20))
    raise ValueError('unsupported clip ' + clip)


def elbow_roll(pose, rest):
    """Axial difference of the forearm relative to the upper arm (project metric)."""
    axis = (pose[HAND].translation - pose[LO].translation).normalized()
    rest_fore = (rest[HAND].translation - rest[LO].translation).normalized()
    up_delta = pose[UP].to_quaternion() @ rest[UP].to_quaternion().inverted()
    fore_delta = pose[LO].to_quaternion() @ rest[LO].to_quaternion().inverted()
    no_roll = (up_delta @ rest_fore).rotation_difference(axis) @ up_delta
    relative = fore_delta @ no_roll.inverted()
    vector = Vector((relative.x, relative.y, relative.z))
    angle = 2.0 * math.atan2(vector.dot(axis), relative.w)
    return math.degrees((angle + math.pi) % (2.0 * math.pi) - math.pi)


def humerus_axis(pose):
    return (pose[LO].translation - pose[UP].translation).normalized()


def rolled_humerus(pose, rest, roll_deg):
    axis = humerus_axis(pose)
    scale = pose[UP].decompose()[2]
    return Matrix.LocRotScale(
        pose[UP].translation,
        Quaternion(axis, math.radians(roll_deg)) @ pose[UP].to_quaternion(),
        scale)


def solve_roll(pose, rest, cap=95.0, step=1.0, previous=None, slack=1.0):
    """Roll (degrees, |roll| <= cap) that minimises the elbow's axial difference.

    The metric is periodic and not monotone in the roll, so this scans the
    allowed range and refines the best sample instead of chasing a root. The
    authored pose (roll 0) is inside the range, so the result is never worse
    than the source. ``slack`` keeps the chosen solution near the previous
    frame among candidates that are within that many degrees of the best.
    """

    def metric(roll):
        modified = dict(pose)
        modified[UP] = rolled_humerus(pose, rest, roll)
        return elbow_roll(modified, rest)

    samples = []
    roll = -cap
    while roll <= cap + 1e-9:
        samples.append((abs(metric(roll)), roll))
        roll += step
    best_value = min(value for value, _ in samples)
    candidates = [roll for value, roll in samples if value <= best_value + slack]
    if previous is None:
        chosen = min(candidates, key=lambda r: (abs(r), r))
    else:
        chosen = min(candidates, key=lambda r: abs(r - previous))

    # Local golden-section style refinement around the chosen sample.
    low, high = chosen - step, chosen + step
    for _ in range(60):
        a = low + (high - low) * 0.382
        b = low + (high - low) * 0.618
        if abs(metric(a)) <= abs(metric(b)):
            high = b
        else:
            low = a
    refined = max(-cap, min(cap, (low + high) / 2.0))
    if abs(metric(refined)) > best_value:
        refined = chosen
    return refined, metric(refined), humerus_axis(pose)
