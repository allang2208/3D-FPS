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
upper_rest = rest['lowerarm_l'][:3, 3] - rest['upperarm_l'][:3, 3]
lower_rest = rest['hand_l'][:3, 3] - rest['lowerarm_l'][:3, 3]


def author(phase, running):
    # Right foot contacts at PI in GetStridePhaseRadians. The left hand leads
    # on that footfall with a small arm lag; no separate animation clock.
    theta = phase - .18
    forward = .5 - .5 * math.cos(theta)
    arc = math.sin(theta)
    if running:
        wrist = np.array([14 + 23 * forward, -28 + 9 * forward + 1.7 * arc,
                          -38 + 22 * forward + 1.8 * arc])
        shoulder = np.array([-5 + .55 * (2 * forward - 1), -19 - .35 * arc,
                             -23 - .25 * math.cos(2 * theta)])
        pole = np.array([6., -35.5, -43.])
    else:
        wrist = np.array([18 + 16 * forward, -25 + 4 * forward + 1.1 * arc,
                          -37 + 16 * forward + 1.1 * arc])
        shoulder = np.array([-5 + .30 * (2 * forward - 1), -19 - .20 * arc,
                             -23 - .15 * math.cos(2 * theta)])
        pole = np.array([5., -35., -45.])
    reach = wrist - shoulder
    length = np.linalg.norm(reach)
    axis = unit(reach)
    along = (np.dot(upper_rest, upper_rest) - np.dot(lower_rest, lower_rest) + length * length) / (2 * length)
    bend = unit(pole - shoulder - axis * np.dot(pole - shoulder, axis))
    elbow = shoulder + axis * along + bend * math.sqrt(np.dot(upper_rest, upper_rest) - along * along)
    # A softly changing roll plane follows the forearm. The wrist retains its
    # native relationship to the lower arm instead of independently twisting.
    across = np.array([.055 * math.sin(theta - .25), .075 * math.sin(theta - .35), 1.])
    lower_delta = frame(wrist - elbow, across) @ frame(lower_rest, np.array(anatomy['across'])).T
    upper_delta = swing(lower_delta @ upper_rest, elbow - shoulder) @ lower_delta
    world = {n: m.copy() for n, m in rest.items()}
    world['upperarm_l'] = matrix(upper_delta @ rest['upperarm_l'][:3, :3], shoulder)
    world['lowerarm_l'] = matrix(lower_delta @ rest['lowerarm_l'][:3, :3], elbow)
    world['hand_l'] = matrix(lower_delta @ rest['hand_l'][:3, :3], wrist)
    world['clavicle_l'][:3, 3] = shoulder - world['clavicle_l'][:3, :3] @ local['upperarm_l'][:3, 3]
    for n in order:
        if n in ('clavicle_l', 'upperarm_l', 'lowerarm_l', 'hand_l'):
            continue
        world[n] = world[parent[n]] @ local[n]
        if n in digits:
            d = digits[n]
            across = np.array(d['across'])
            sign = np.sign(np.dot(np.cross(across, d['axis']), -np.array(d['dorsal'])))
            degrees = CURL[d['digit']][d['segment'] - 1] * (1.22 if running else 1.)
            parent_delta = world[parent[n]][:3, :3] @ rest[parent[n]][:3, :3].T
            turn = Rotation.from_rotvec(unit(parent_delta @ across) * sign * math.radians(degrees)).as_matrix()
            world[n][:3, :3] = turn @ world[n][:3, :3]
    authored_local = {n: np.linalg.inv(world[parent[n]]) @ world[n] for n in order}
    return {'local': {n: m.tolist() for n, m in authored_local.items()},
            'component': {n: world[n].tolist() for n in order}}


cycles = {name: [author(math.tau * i / SAMPLES, running) for i in range(SAMPLES)]
          for name, running in [('Walk', False), ('Run', True)]}
data = {'revision': 15, 'samples_per_stride': SAMPLES, 'units': 'UE cm, normalized native local transforms',
        'source': '../RightCarryV14/full-pose.json', 'order': order, 'parent': parent,
        'phase_clock': 'UFPSFootstepAudioComponent::GetStridePhaseRadians',
        'right_foot_phase': math.pi, 'arm_lag_radians': .18,
        'cycles': cycles, 'rendered': False, 'runtime_tested': False}
(P / 'left-gait.json').write_text(json.dumps(data, indent=2), encoding='utf-8')


def numbers(values):
    return ','.join(f'{v:.10f}' for v in values)


lines = ['// Generated by LeftGaitV15/author_gait.py. Complete native left arm only.',
         '#pragma once', '#include "CoreMinimal.h"', 'namespace StaffLeftGaitV15 {',
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
(ROOT / 'Source/FPSGAME/Weapons/Staff/StaffAuthoredLeftGaitV15.h').write_text('\n'.join(lines) + '\n', encoding='utf-8')
print(f'Saved Walk/Run left-arm cycles: {SAMPLES} stride samples, {len(order)} native bones; no render or runtime test.', flush=True)
