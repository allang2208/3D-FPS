"""Author a free-left-arm stride on the existing V7 staff skeleton.

Camera coordinates are UE centimetres (+X forward, +Y screen right, +Z up).
Right-hand contact and V14 presentation are not authored by this script.
The shoulder is anchored behind the camera; elbow/wrist tracks preserve native
segment lengths. Production export only: no render or runtime test.
"""
import json
import math
from pathlib import Path

import numpy as np
from scipy.interpolate import CubicSpline
from scipy.spatial.transform import Rotation

P = Path(__file__).resolve().parent
ROOT = P.parents[2]
source = json.loads((P.parent / 'RightCarryV14/full-pose.json').read_text())
anatomy = json.loads((ROOT / 'SourceAssets/ModularOutfit20260924/OriginalShapeBareM4/BareUpperArmsV6/M4_bare_shape.json').read_text())['anatomy']['l']
rest = {n: np.array(m) for n, m in source['rest'].items()}
parent = source['parent']
order = [n for n in source['order'] if n.endswith('_l')]
local = {n: np.linalg.inv(rest[parent[n]]) @ rest[n] for n in order}
digits = {d['bone']: d for d in anatomy['digits']}
SAMPLES = 32


def unit(v):
    return np.asarray(v) / np.linalg.norm(v)


def matrix(rotation, position):
    m = np.eye(4)
    m[:3, :3] = rotation
    m[:3, 3] = position
    return m


def frame(x, across):
    x = unit(x)
    y = unit(across - x * np.dot(x, across))
    return np.column_stack((x, y, np.cross(x, y)))


def swing(a, b):
    a, b = unit(a), unit(b)
    v = np.cross(a, b)
    s = np.linalg.norm(v)
    return np.eye(3) if s < 1.e-9 else Rotation.from_rotvec(v / s * math.atan2(s, np.dot(a, b))).as_matrix()


# Gentle, unequal finger flexion: relaxed walk, a little more collected in run.
# These are offsets from this native skeleton, not a copied opposite-hand pose.
CURL = {'index': (12, 22, 12), 'middle': (17, 28, 16),
        'ring': (23, 34, 20), 'pinky': (29, 39, 24), 'thumb': (4, 12, 8)}
CURL_SWING = {'index': (3.6, 5.2, 2.8), 'middle': (4.2, 6., 3.3),
              'ring': (4.6, 6.6, 3.7), 'pinky': (5., 7., 4.), 'thumb': (1.3, 2., 1.1)}
DIGIT_LAG = {'index': .43, 'middle': .55, 'ring': .68, 'pinky': .82, 'thumb': .37}
# Unequal forward/back timing and different vertical/lateral extrema produce
# a relaxed loop rather than translating a frozen hand along a single sine.
KNOTS = [0., .18, .43, .58, .78, 1.]
WRIST_PATH = {
    False: CubicSpline(KNOTS, [[18,-25,-37], [23,-25.5,-33.5], [33.5,-22,-23],
                              [32,-20.5,-20.5], [22,-22,-29.5], [18,-25,-37]], bc_type='periodic'),
    True: CubicSpline(KNOTS, [[14,-28,-38], [22,-27,-31], [36,-20,-18],
                             [34,-17.8,-14.8], [21,-22,-27], [14,-28,-38]], bc_type='periodic')}
native_across = np.array(anatomy['across'])
native_dorsal = np.array(anatomy['dorsal'])
wrist_flex_sign = np.sign(np.dot(np.cross(native_across, anatomy['forward']), -native_dorsal))
upper_rest = rest['lowerarm_l'][:3, 3] - rest['upperarm_l'][:3, 3]
lower_rest = rest['hand_l'][:3, 3] - rest['lowerarm_l'][:3, 3]


def author(phase, running):
    # Right foot contacts at PI in GetStridePhaseRadians. The left hand leads
    # on that footfall with a small arm lag; no separate animation clock.
    theta = phase - .18
    wrist = WRIST_PATH[running]((theta / math.tau) % 1.)
    # Shoulder leads the free hand. The elbow plane follows with less delay
    # than the wrist; its excursion stays below/outside the view.
    shoulder_phase = phase + .12
    elbow_phase = phase - .08
    if running:
        shoulder = np.array([-5 - .62 * math.cos(shoulder_phase),
                             -19 - .4 * math.sin(shoulder_phase),
                             -23 - .24 * math.cos(2 * shoulder_phase - .3)])
        pole = np.array([6 + 1.8 * math.sin(elbow_phase),
                         -35.5 + 1.4 * math.cos(elbow_phase - .3),
                         -43 + 1.8 * math.sin(elbow_phase - .3)])
    else:
        shoulder = np.array([-5 - .38 * math.cos(shoulder_phase),
                             -19 - .25 * math.sin(shoulder_phase),
                             -23 - .15 * math.cos(2 * shoulder_phase - .3)])
        pole = np.array([5 + 1.1 * math.sin(elbow_phase),
                         -35 + .85 * math.cos(elbow_phase - .3),
                         -45 + 1.15 * math.sin(elbow_phase - .3)])
    reach = wrist - shoulder
    length = np.linalg.norm(reach)
    axis = unit(reach)
    along = (np.dot(upper_rest, upper_rest) - np.dot(lower_rest, lower_rest) + length * length) / (2 * length)
    bend = unit(pole - shoulder - axis * np.dot(pole - shoulder, axis))
    elbow = shoulder + axis * along + bend * math.sqrt(np.dot(upper_rest, upper_rest) - along * along)
    # Small forearm roll and wrist flexion are distinct movements. Helpers
    # follow their complete native segment; no fractional twist compensation.
    across = np.array([.06 * math.sin(phase - .48), .10 * math.sin(phase - .68), 1.])
    lower_delta = frame(wrist - elbow, across) @ frame(lower_rest, np.array(anatomy['across'])).T
    upper_delta = swing(lower_delta @ upper_rest, elbow - shoulder) @ lower_delta
    wrist_flex = (5.5 if running else 4.) * math.sin(phase - .58) + .8 * math.sin(2 * phase - .55)
    wrist_deviation = (1.9 if running else 1.4) * math.sin(phase - .85)
    wrist_turn = (Rotation.from_rotvec(unit(native_across) * wrist_flex_sign * math.radians(wrist_flex)).as_matrix()
                  @ Rotation.from_rotvec(unit(native_dorsal) * math.radians(wrist_deviation)).as_matrix())
    world = {n: m.copy() for n, m in rest.items()}
    world['upperarm_l'] = matrix(upper_delta @ rest['upperarm_l'][:3, :3], shoulder)
    world['lowerarm_l'] = matrix(lower_delta @ rest['lowerarm_l'][:3, :3], elbow)
    world['hand_l'] = matrix(lower_delta @ wrist_turn @ rest['hand_l'][:3, :3], wrist)
    world['clavicle_l'][:3, 3] = shoulder - world['clavicle_l'][:3, :3] @ local['upperarm_l'][:3, 3]
    for n in order:
        if n in ('clavicle_l', 'upperarm_l', 'lowerarm_l', 'hand_l'):
            continue
        world[n] = world[parent[n]] @ local[n]
        if n in digits:
            d = digits[n]
            across = np.array(d['across'])
            sign = np.sign(np.dot(np.cross(across, d['axis']), -np.array(d['dorsal'])))
            # One passive follow-through per stride, with progressively later
            # PIP/DIP response. Ulnar fingers have slightly more movement.
            # Run starts more collected but has less finger flutter than walk.
            digit, joint = d['digit'], d['segment'] - 1
            digit_phase = phase - DIGIT_LAG[digit] - joint * .09
            follow = -.84 * math.cos(digit_phase) + .16 * math.sin(2 * digit_phase - .25)
            degrees = (CURL[digit][joint] * (1.18 if running else 1.)
                       + CURL_SWING[digit][joint] * follow * (.8 if running else 1.))
            parent_delta = world[parent[n]][:3, :3] @ rest[parent[n]][:3, :3].T
            turn = Rotation.from_rotvec(unit(parent_delta @ across) * sign * math.radians(degrees)).as_matrix()
            world[n][:3, :3] = turn @ world[n][:3, :3]
    authored_local = {n: np.linalg.inv(world[parent[n]]) @ world[n] for n in order}
    return {'local': {n: m.tolist() for n, m in authored_local.items()},
            'component': {n: world[n].tolist() for n in order}}


cycles = {name: [author(math.tau * i / SAMPLES, running) for i in range(SAMPLES)]
          for name, running in [('Walk', False), ('Run', True)]}
data = {'revision': 16, 'samples_per_stride': SAMPLES, 'units': 'UE cm, normalized native local transforms',
        'source': '../RightCarryV14/full-pose.json', 'order': order, 'parent': parent,
        'phase_clock': 'UFPSFootstepAudioComponent::GetStridePhaseRadians',
        'right_foot_phase': math.pi, 'arm_lag_radians': .18,
        'finger_lag_radians': DIGIT_LAG, 'finger_flex_swing_degrees': CURL_SWING,
        'runtime_variation': 'amplitude only, 0.71 and 1.13 rad/s; never changes footstep phase',
        'cycles': cycles, 'rendered': False, 'runtime_tested': False}
(P / 'left-gait.json').write_text(json.dumps(data, indent=2), encoding='utf-8')


def numbers(values):
    return ','.join(f'{v:.10f}' for v in values)


lines = ['// Generated by LeftGaitV16/author_gait.py. Full arm with delayed wrist/finger motion.',
         '#pragma once', '#include "CoreMinimal.h"', 'namespace StaffLeftGaitV16 {',
         f'inline constexpr int32 Samples={SAMPLES}, BoneCount={len(order)};',
         'struct FLocal { FQuat Rotation; FVector Position; };',
         'inline const TCHAR* Names[]={']
lines += [f'TEXT("{n}"),' for n in order]
lines += ['};', 'inline const FLocal Cycles[2][Samples][BoneCount]={']
for name, frames in cycles.items():
    lines += ['{ // ' + name]
    for i, pose in enumerate(frames):
        lines += ['{ // Stride sample ' + str(i)]
        for n in order:
            m = np.array(pose['local'][n])
            lines += ['{FQuat(' + numbers(Rotation.from_matrix(m[:3, :3]).as_quat()) + '),FVector(' + numbers(m[:3, 3]) + ')},']
        lines += ['},']
    lines += ['},']
lines += ['};', '}']
(ROOT / 'Source/FPSGAME/Weapons/Staff/StaffAuthoredLeftGaitV16.h').write_text('\n'.join(lines) + '\n', encoding='utf-8')
print(f'Saved Walk/Run left-arm cycles: {SAMPLES} stride samples, {len(order)} native bones; no render or runtime test.', flush=True)
