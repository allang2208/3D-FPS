"""RSH-only shoulder/elbow support for the existing perforated-grip contact.

Input and output are armature-space matrices. The grasp, fingers and weapon
stay fixed; only the chain supporting that grasp and the wrist local rotation
change. This is an offline authoring operation, not a runtime IK layer.
"""
import math
from mathutils import Matrix, Vector, Quaternion

WRIST_SWING_DEGREES = 18.0


def contact_weight(kind, time, duration):
    def smooth(value):
        value = max(0.0, min(1.0, value))
        return value * value * (3.0 - 2.0 * value)
    if kind.startswith(('single_', 'speed_')):
        return 1.0-smooth(time/.18) if time < .18 else smooth((time-(duration-.30))/.30)
    if kind == 'quickcombat':
        return 1.0-smooth(time/.09) if time < .09 else smooth((time-(duration-.16))/.16)
    if kind.startswith('equip'):
        return smooth((time-(duration-.30))/.30)
    return 1.0


def _project(vector, axis):
    return vector-axis*vector.dot(axis)


def _frame(direction, normal):
    x = direction.normalized()
    y = _project(normal, x).normalized()
    return Matrix((x, y, x.cross(y).normalized())).transposed().to_quaternion()


def _signed_angle(a, b, axis):
    return math.atan2(axis.dot(a.cross(b)), max(-1.0, min(1.0, a.dot(b))))


def support_arm(pose, rest, weight):
    if weight <= 0.0:
        return set()
    old = {name: value.copy() for name, value in pose.items()}
    shoulder = old['upperarm_l'].translation.copy()
    elbow = old['lowerarm_l'].translation.copy()
    wrist = old['hand_l'].translation.copy()
    upper = elbow-shoulder
    lower = wrist-elbow
    l1, l2 = upper.length, lower.length
    neutral = (old['hand_l'].to_quaternion() @ rest['hand_l'].to_quaternion().inverted()
               @ (rest['hand_l'].translation-rest['lowerarm_l'].translation).normalized()).normalized()

    # Find the closest reachable elbow with a modest wrist swing. If the
    # original shoulder cannot support it, translate the whole shoulder girdle
    # by the minimum required amount. Do not stretch either arm segment.
    reach_axis = (wrist-shoulder).normalized()
    swing = neutral.rotation_difference(reach_axis)
    fraction = min(1.0, math.radians(WRIST_SWING_DEGREES)/max(1e-7, swing.angle))
    relaxed_direction = Quaternion().slerp(swing, fraction) @ neutral
    relaxed_elbow = wrist-relaxed_direction*l2
    shoulder_to_elbow = relaxed_elbow-shoulder
    shift = shoulder_to_elbow.normalized()*max(0.0, shoulder_to_elbow.length-l1)
    new_shoulder = shoulder+shift*weight

    # Rebuild the exact two-bone circle. Rotate continuously from the existing
    # elbow plane toward the least-bent wrist, including release/return frames.
    line = wrist-new_shoulder
    distance = line.length
    axis = line.normalized()
    along = (l1*l1-l2*l2+distance*distance)/(2.0*distance)
    radius = math.sqrt(max(0.0, l1*l1-along*along))
    old_pole = _project(upper, axis).normalized()
    desired_pole = _project(wrist-neutral*l2-new_shoulder, axis)
    if desired_pole.length < 1e-7:
        desired_pole = old_pole.copy()
    desired_pole.normalize()
    angle = _signed_angle(old_pole, desired_pole, axis)
    pole = Quaternion(axis, angle*weight) @ old_pole
    new_elbow = new_shoulder+axis*along+pole*radius
    new_upper, new_lower = new_elbow-new_shoulder, wrist-new_elbow

    # Transport the actual elbow flexion plane, not just the two direction
    # vectors. This keeps the humerus and elbow crease aligned after reposing.
    normal = upper.cross(lower).normalized()
    new_normal = new_upper.cross(new_lower).normalized()
    for name, before, after, location in (
            ('upperarm_l', upper, new_upper, new_shoulder),
            ('lowerarm_l', lower, new_lower, new_elbow)):
        rotation = _frame(after, new_normal) @ _frame(before, normal).inverted()
        pose[name] = Matrix.LocRotScale(location, rotation @ old[name].to_quaternion(), old[name].to_scale())
    pose['clavicle_l'] = old['clavicle_l'].copy()
    pose['clavicle_l'].translation += new_shoulder-shoulder
    changed = {'clavicle_l', 'upperarm_l', 'lowerarm_l', 'hand_l'}

    # The wrist stays in place. Spread palm roll through the forearm's existing
    # two skinning stations instead of concentrating it at the wrist seam.
    lower_axis = new_lower.normalized()
    neutral_hand = (pose['lowerarm_l'].to_quaternion()
                    @ rest['lowerarm_l'].to_quaternion().inverted()
                    @ rest['hand_l'].to_quaternion())
    difference = old['hand_l'].to_quaternion() @ neutral_hand.inverted()
    twist = 2.0*math.atan2(Vector((difference.x, difference.y, difference.z)).dot(lower_axis), difference.w)
    twist = (twist+math.pi) % (2.0*math.pi)-math.pi
    for name in old:
        if not name.endswith('_l') or not name.startswith(('upperarm_twist', 'lowerarm_twist')):
            continue
        owner = 'upperarm_l' if name.startswith('upperarm') else 'lowerarm_l'
        carried = pose[owner] @ old[owner].inverted() @ old[name]
        if owner == 'lowerarm_l':
            station = .95 if name == 'lowerarm_twist_01_l' else .55
            rest_frame = pose[owner] @ rest[owner].inverted() @ rest[name]
            target_rotation = Quaternion(lower_axis, twist*station) @ rest_frame.to_quaternion()
            carried = Matrix.LocRotScale(carried.translation,
                                        carried.to_quaternion().slerp(target_rotation, weight),
                                        old[name].to_scale())
        pose[name] = carried
        changed.add(name)
    # hand_l needs a new LOCAL rotation because its parent changed; its
    # component transform and all finger local rotations remain the input ones.
    return changed
