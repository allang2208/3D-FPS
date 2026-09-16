"""Spread the Inspect's forearm pronation along the forearm instead of the elbow.

What the shipped Inspect does (measured, probe_limb_twist.json):

* ``upperarm_r``'s local rotation is a constant -51.9 deg twist and
  ``upperarm_l``'s a constant +45.5 deg for the whole 2.90 s clip: the
  shoulders are never animated, so the arms swing from the clavicles.
* ``upperarm_twist_01/02_*`` and ``lowerarm_twist_01/02_*`` are pinned at
  0.00 deg, i.e. none of the four bones per arm that hold nearly all of the
  arm skin (1099 / 1005 / 589 / 1047 dominant vertices) ever rotates.
* ``lowerarm_r`` therefore carries up to 177.4 deg of twist about the forearm
  axis on its own, and ``lowerarm_l`` up to -99.3 deg, each on a 159-vertex
  elbow cap.  All of that has to be absorbed by the skin at the elbow seam:
  the candy-wrapper shear the user keeps reporting.

The fix rebuilds each forearm as a cumulative roll profile in rig space, so
there is no +-180 reference-frame wrap (the failure mode the skill records for
the earlier sword attempts):

    station                        authored   target
    lowerarm_*    (elbow cap, 0.0)      T      0.000 T
    lowerarm_twist_02_*  (0.274)        T      0.274 T
    lowerarm_twist_01_*  (0.863)        T      0.863 T
    hand_*        (wrist, 1.0)          T      1.000 T

The profile is interpolated between the authored and target shapes by the
envelope, so weight 0 reproduces the source pose exactly.  ``hand_*`` keeps its
authored world orientation, so the grip, the sword, the silhouette and the
timing do not move, and every bone head keeps its position.
"""
import math
from mathutils import Matrix, Quaternion, Vector

# Cumulative profile, elbow cap to wrist.  Positions are the measured median
# axis position of each bone's dominant vertices (probe_skin_axis.json).
STATIONS = (0.0, 0.2739, 0.8634, 1.0)


def bones(side):
    return {
        'up': 'upperarm_' + side,
        'lo': 'lowerarm_' + side,
        'lo_t1': 'lowerarm_twist_01_' + side,
        'lo_t2': 'lowerarm_twist_02_' + side,
        'hand': 'hand_' + side,
    }


SIDES = ('r', 'l')


def chain(side):
    names = bones(side)
    return (names['lo'], names['lo_t2'], names['lo_t1'], names['hand'])


def build_rig():
    """Per-side profile entries and parent map, so callers stay simple."""
    profile = {}
    parents = {}
    edited = []
    for side in SIDES:
        names = bones(side)
        profile[side] = tuple(zip(chain(side), STATIONS))
        parents[side] = {names['lo']: names['up'], names['lo_t2']: names['lo'],
                         names['lo_t1']: names['lo'], names['hand']: names['lo']}
        edited.extend(chain(side))
    return profile, parents, tuple(edited)


PROFILE, PARENT, EDITED = build_rig()
PARENT_OF = {name: parents for side in SIDES for name, parents in PARENT[side].items()}


def smoothstep(value):
    value = max(0.0, min(1.0, value))
    return value * value * value * (value * (value * 6.0 - 15.0) + 10.0)


def envelope(seconds, rise=(0.0, 0.25), fall=(2.65, 2.90)):
    """Zero at both idle seams, one through the working range."""
    return smoothstep((seconds - rise[0]) / (rise[1] - rise[0])) * (
        1.0 - smoothstep((seconds - fall[0]) / (fall[1] - fall[0])))


def limb_axis_local(rest, lower, upper, name):
    """The forearm axis expressed in this bone's own rest frame.

    The rig's bones do not point along a fixed local component, so the axis is
    taken from the joint positions instead of assumed.
    """
    direction = (rest[upper].translation - rest[lower].translation).normalized()
    return (rest[name].to_3x3().inverted() @ direction).normalized()


def twist_angle(delta, axis):
    """Signed twist of a rest-space rotation about ``axis``, in degrees."""
    q = delta.to_quaternion()
    if q.w < 0.0:
        q.negate()
    return math.degrees(2.0 * math.atan2(Vector((q.x, q.y, q.z)).dot(axis), q.w))


def local_delta(rest_local, world, parent_world):
    """Pose rotation of a bone expressed in the bone's own rest frame."""
    return rest_local.inverted() @ (parent_world.inverted() @ world)


def authored_profile(pose, rest_local, rest, side):
    names = bones(side)
    local = {}
    cumulative = {}
    running = 0.0
    for name, _ in PROFILE[side]:
        axis = limb_axis_local(rest, names['lo'], names['hand'], name)
        angle = twist_angle(local_delta(rest_local[name], pose[name],
                                        pose[PARENT[side][name]]), axis)
        local[name] = angle
        running += angle
        cumulative[name] = running
    return local, cumulative


def build(pose, rest_local, rest, weight):
    """World matrices for both forearm chains at envelope ``weight``.

    Every forearm bone keeps its authored position and receives only a twist
    about the forearm axis, moving its cumulative roll from the authored
    profile (all of it on the elbow cap) to the target ramp.  ``hand_*`` is
    left untouched, which is what preserves the grip and the sword.
    """
    result = {}
    report = {}
    for side in SIDES:
        names = bones(side)
        local, cumulative = authored_profile(pose, rest_local, rest, side)
        total = cumulative[names['hand']]
        axis = (pose[names['hand']].translation
                - pose[names['lo']].translation).normalized()
        applied = {}
        after = {}
        for name, station in PROFILE[side]:
            if name == names['hand']:
                result[name] = pose[name].copy()
                applied[name] = 0.0
            else:
                delta = weight * (station * total - cumulative[name])
                _, rotation, scale = pose[name].decompose()
                result[name] = Matrix.LocRotScale(
                    pose[name].translation,
                    Quaternion(axis, math.radians(delta)) @ rotation,
                    scale)
                applied[name] = delta
            after[name] = cumulative[name] + applied[name]
        report[side] = {'elbow_twist_before': local[names['lo']],
                        'elbow_twist_after': after[names['lo']],
                        'profile_before': dict(cumulative),
                        'profile_after': dict(after),
                        'applied_twist': applied, 'total': total}
    return result, report
