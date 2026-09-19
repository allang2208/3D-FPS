"""Natural wrist/arm solver copied from the current ASH-12 authoring baseline.
Only the reload author uses this frozen helper; no mesh/rest/weight edits.
"""
import math
from mathutils import Matrix, Quaternion, Vector

def shift_arm_natural(pose, side, pole_hint=None, hand_target=None, natural_blend=0.8,
                      shoulder_shift=None, *, rest, hand_subtree):
    """Keep the accepted hand on the gun, but solve the arm like WristNatural.

    The old pole solver left the hand orientation untouched while it swung the
    forearm to a new elbow, so the whole correction landed on the wrist and the
    twist helper bones were reset to rest.  This ports the accepted foregrip
    fix instead: keep the hand world matrix, let the elbow move toward the
    pole, derive the natural forearm direction from that hand orientation, and
    distribute the remaining roll across the two forearm twist bones (the
    0.55 / 0.95 shares from the accepted WristNatural pass).
    """
    upper, lower, hand = "upperarm_" + side, "lowerarm_" + side, "hand_" + side
    old_upper = pose[upper].copy()
    old_lower = pose[lower].copy()
    old_hand = pose[hand].copy()
    old_pose = {name: matrix.copy() for name, matrix in pose.items()}
    H = hand_target.copy() if hand_target is not None else old_hand.copy()
    A = old_upper.translation.copy()
    if shoulder_shift is not None:
        # Root clearance for the ADS eye (see RIGHT_SHOULDER_SHIFT): applied
        # before the IK so the elbow re-solves from the moved root and the
        # overreach guard below never has to trigger.
        A += shoulder_shift
    target = H.translation.copy()
    l1 = (rest[lower].translation - rest[upper].translation).length
    l2 = (rest[hand].translation - rest[lower].translation).length
    axis = (target - A).normalized()
    reach = (target - A).length
    if reach > l1 + l2 - 0.015:
        shift = axis * (reach - (l1 + l2 - 0.015))
        A += shift
        clavicle = "clavicle_" + side
        if clavicle in pose:
            pose[clavicle] = Matrix.Translation(shift) @ pose[clavicle]
    dist = (target - A).length
    axis = (target - A).normalized()
    pole = Vector(pole_hint) if pole_hint is not None else (old_lower.translation - A)
    pole -= axis * pole.dot(axis)
    if pole.length < 1e-6:
        pole = (old_lower.translation - A) - axis * (old_lower.translation - A).dot(axis)
    pole.normalize()
    desired = (H.to_3x3() @ rest[hand].to_3x3().inverted()
               @ (rest[hand].translation - rest[lower].translation).normalized())
    natural = target - desired * l2 - A
    natural -= axis * natural.dot(axis)
    if natural.length > 1e-6 and natural_blend > 0.0:
        pole = pole.lerp(natural.normalized(), natural_blend).normalized()
    along = (l1 * l1 - l2 * l2 + dist * dist) / (2.0 * dist)
    elbow = A + axis * along + pole * math.sqrt(max(0.0, l1 * l1 - along * along))
    u = (elbow - A).normalized()
    v = (target - elbow).normalized()
    ou = (old_lower.translation - old_upper.translation).normalized()
    ov = (old_hand.translation - old_lower.translation).normalized()
    pose[upper] = Matrix.LocRotScale(A, ou.rotation_difference(u) @ old_upper.to_quaternion(),
                                     old_upper.to_scale())
    pose[lower] = Matrix.LocRotScale(elbow, ov.rotation_difference(v) @ old_lower.to_quaternion(),
                                     old_lower.to_scale())
    # Preserve the accepted upper-arm twist instead of resetting the helpers
    # to rest (the old solver's visible skin twist).
    for name in ("upperarm_twist_01_" + side, "upperarm_twist_02_" + side):
        if name in pose:
            pose[name] = pose[upper] @ old_upper.inverted() @ old_pose[name]
    # Move the residual forearm roll off the wrist and onto the two twist bones.
    neutral = (pose[lower].to_quaternion() @ rest[lower].to_quaternion().inverted()
               @ rest[hand].to_quaternion())
    q = H.to_quaternion() @ neutral.inverted()
    twist = 2.0 * math.atan2(Vector((q.x, q.y, q.z)).dot(v), q.w)
    twist = (twist + math.pi) % (2.0 * math.pi) - math.pi
    for name, share in (("lowerarm_twist_02_" + side, 0.55), ("lowerarm_twist_01_" + side, 0.95)):
        if name in pose:
            m = pose[lower] @ rest[lower].inverted() @ rest[name]
            pose[name] = Matrix.LocRotScale(m.translation,
                                            Quaternion(v, twist * share) @ m.to_quaternion(),
                                            m.to_scale())
    # Put the hand/finger subtree back on the target without changing its grip.
    rigid = H @ old_hand.inverted()
    for name in hand_subtree(side):
        if name in old_pose:
            pose[name] = rigid @ old_pose[name]
