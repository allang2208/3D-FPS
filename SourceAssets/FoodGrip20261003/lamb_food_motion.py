"""Lamb-specific camera-space approach; preserve each food's transaction clock.

UE coordinates are centimetres, X forward / Y right / Z up. Keys describe the
real meat edge. Derive the hand's grip from that edge and the original mesh so
changing a grasp cannot silently leave the old bread trajectory in place.
"""
import math
import json
from pathlib import Path


def rotate(point, euler):
    pitch, yaw, roll = map(math.radians, euler)
    x, y, z = point
    y, z = math.cos(roll)*y + math.sin(roll)*z, -math.sin(roll)*y + math.cos(roll)*z
    x, z = math.cos(pitch)*x - math.sin(pitch)*z, math.sin(pitch)*x + math.cos(pitch)*z
    return [math.cos(yaw)*x - math.sin(yaw)*y, math.sin(yaw)*x + math.cos(yaw)*y, z]


def apply_lamb_motion(motion, large=False, apply_grasp=True):
    """Called after the authored grasp and approved per-food times are set."""
    if large:
        # The meat edge faces the mouth; the long rib row stays horizontal.
        # Swapping the mesh-side grips with the half turn keeps left/right hands
        # on their own sides rather than crossing them in front of the camera.
        palm = motion['grip_in_palm']
        motion.update(two_handed=True, object_rotation=[0, -90, 0],
                      grip_in_object=[9.0, 1.0, 4.0],
                      right_grip_in_object=[-6.2, 1.0, 4.0],
                      right_grip_in_palm=[palm[0], -palm[1], palm[2]], grip_height=4.0)
        points = [
            [30, 0, -38], [30, 0, -38], [29, -.3, -19], [26, 0, -4],
            [22, 0, -4.7], [21, 0, -5], [19, -.15, -5.3], [17, .1, -5.8],
            [13, -.1, -6.2], [4.2, 0, -7.25], [4.2, 0, -12], [4.2, 0, -30],
            [4.2, 0, -48], [4.2, 0, -48],
        ]
        pitches = [5, 5, 10, 18, 24, 26, 27.5, 28, 29.2, 30, 30, 30, 30, 30]
    else:
        points = [
            [27, -14, -36], [27, -14, -36], [26, -10, -22], [25, -5, -2.5],
            [22, -2, -3], [21, -1.5, -3.2], [19, -1, -3.6], [17, -.4, -4.2],
            [13, -.2, -5.5], [4.2, 0, -7.25], [15, -1, -8], [25, -8, -24],
            [27, -14, -36], [27, -14, -36],
        ]
        pitches = [5, 5, 12, 32, 42, 44, 45, 46, 48, 50, 42, 18, 5, 5]
    if apply_grasp:
        # These thumb-only corrections include the mixed palm/forearm skin at
        # the thumb root. The rack's two asymmetric ends use independent poses.
        profiles = json.loads(Path(__file__).with_name('lamb_thumb_profiles.json').read_text(encoding='utf-8'))
        grasp = profiles['roasted_large_lamb' if large else 'roasted_lamb_ribs']
        motion['digits']['thumb'] = grasp['l']['thumb']
        motion['grip_in_palm'] = grasp['l']['grip_in_palm']
        if large:
            motion['right_thumb'] = grasp['r']['thumb']
            motion['right_grip_in_palm'] = grasp['r']['grip_in_palm']
    # Keep the established uneven timing, but never inherit the bread's 65deg
    # drinking angle or compensate a large rack behind the camera.
    times = motion['times']
    key_times = [0, times['grab'], times['duration']/6, times['duration']*.275,
                 times['duration']*.375, times['drink_start'], times['duration']*.5375,
                 times['duration']*.625, times['duration']*(17/24), times['contact'],
                 times['duration']*(49/60), times['duration']*(53/60),
                 times['release'], times['duration']]
    delta = [b-g for b, g in zip(motion['bite_in_object'], motion['grip_in_object'])]
    local_bite = rotate(delta, motion['object_rotation'])
    keys = []
    for i, (time, point, pitch) in enumerate(zip(key_times, points, pitches)):
        rotation = [pitch, -.25 if i == 6 else .2 if i == 7 else 0, .25 if i == 7 else 0]
        offset = rotate(local_bite, rotation)
        keys.append({'time': time, 'grip': [round(p-d, 6) for p, d in zip(point, offset)],
                     'rotation': rotation})
    motion['keys'] = keys
    if large:
        # Finish the bite before lowering vertically at the same camera depth.
        # A duplicate bite key stops the incoming Hermite tangent from producing
        # a small forward/back overshoot during the downward exit.
        finish=dict(keys[9]);finish['time']=times['drink_end']
        keys.insert(10,finish)
    motion['authoring'] = ('LambThumbClose20261015: original mesh, V7 hand dimensions, '
                           'closer food-specific lift; independent thumbs and thumb-root clearance; real meat-edge target, '
                           'unchanged duration/contact/release. ' +
                           ('Two hands hold opposite sides; meat faces the mouth.' if large else
                            'Single hand retains the authored bone-end grasp.'))
    if large and apply_grasp:
        # Preserve the independently authored palms and all five support digits
        # when the original lamb source is regenerated. No food-path changes.
        grasp = json.loads(Path(__file__).with_name("large_lamb_natural_grasp.json").read_text(encoding="utf-8"))
        for key, value in grasp.items():
            motion[key] = value
        motion.pop("right_thumb", None)
    return motion
