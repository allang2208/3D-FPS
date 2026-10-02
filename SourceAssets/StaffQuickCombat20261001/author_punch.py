"""Author the staff free-left-hand quick straight punch on the native V7 rig.

Production only: saves a complete left-chain local pose table and editable
parameters. No render, UE import, compiler, game launch or acceptance test.
Coordinates are camera-space UE centimetres (+X forward, +Y right, +Z up).
The right hand and staff remain the existing V14 carry.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation, Slerp

P = Path(__file__).resolve().parent
ROOT = P.parents[1]
SOURCE = ROOT / 'SourceAssets/ApprenticeStaff20260927/RightCarryV14/full-pose.json'
ANATOMY = ROOT / 'SourceAssets/ModularOutfit20260924/OriginalShapeBareM4/BareUpperArmsV6/M4_bare_shape.json'
HEADER = ROOT / 'Source/FPSGAME/Weapons/Staff/StaffAuthoredQuickPunch20261001.h'
sys.path.insert(0, str(P / 'FixV2'))
from fit_v7_fist import closed_pose
source = json.loads(SOURCE.read_text(encoding='utf-8'))
anatomy = json.loads(ANATOMY.read_text(encoding='utf-8'))['anatomy']['l']
rest = {n: np.asarray(m, dtype=float) for n, m in source['rest'].items()}
parent = source['parent']
order = [n for n in source['order'] if n.endswith('_l')]
native_local = {n: np.linalg.inv(rest[parent[n]]) @ rest[n] for n in order}
idle = source['poses']['false'][0]
idle_local = {n: np.asarray(idle['local'][n], dtype=float) for n in order}
REVISION = 2026100102
SOURCE_TIMES = [0., .055, .115, .20, .24, .32, .44, .58]
# Only Ready -> Contact is accelerated. Preparation and every recovery span
# keep their existing durations; contact-dependent gameplay uses these times.
CONTACT = .115 + (.20 - .115) / 1.5
ADVANCE = .20 - CONTACT
TIMES = [0., .055, .115, CONTACT] + [t - ADVANCE for t in SOURCE_TIMES[4:]]
NAMES = ['Idle', 'Collect', 'Ready', 'Contact', 'ShortRebound', 'Retract', 'Relax', 'IdleReturn']

# Cumulative palm directions from the accepted free-fist family, adapted on the
# actual native V7 skin. The opposed thumb has an explicit nail/pad direction;
# bending it like a fifth index finger leaves its pad facing out of the fist.
FIST_PROFILE = json.loads((P / 'FixV2/fist-profile-v2.json').read_text(encoding='utf-8'))


def unit(v):
    v = np.asarray(v, dtype=float)
    return v / np.linalg.norm(v)


def matrix(rotation, position):
    m = np.eye(4)
    m[:3, :3] = rotation
    m[:3, 3] = position
    return m


def frame(forward, across):
    x = unit(forward)
    y = unit(across - x * np.dot(x, across))
    return np.column_stack((x, y, np.cross(x, y)))


def swing(a, b):
    a, b = unit(a), unit(b)
    v = np.cross(a, b)
    s = np.linalg.norm(v)
    return np.eye(3) if s < 1.e-9 else Rotation.from_rotvec(
        v / s * math.atan2(s, np.dot(a, b))).as_matrix()


def mix_local(a, b, u):
    m = np.eye(4)
    m[:3, :3] = Slerp([0., 1.], Rotation.from_matrix([a[:3, :3], b[:3, :3]]))([u]).as_matrix()[0]
    m[:3, 3] = a[:3, 3] * (1. - u) + b[:3, 3] * u
    return m


fist_world = closed_pose(rest, parent, order, FIST_PROFILE)
fist_local = {n: np.linalg.inv(fist_world[parent[n]]) @ fist_world[n] for n in order}
upper_rest = rest['lowerarm_l'][:3, 3] - rest['upperarm_l'][:3, 3]
lower_rest = rest['hand_l'][:3, 3] - rest['lowerarm_l'][:3, 3]
upper_length = np.linalg.norm(upper_rest)
lower_length = np.linalg.norm(lower_rest)

# The chamber is behind/below the left edge of the camera: the fist first
# enters from the near-left edge, then travels forward in one brief stroke.
# Shoulder and elbow support are authored together; full native helpers follow
# their segment, with no wrist-only twist, finger translation, scale or stretch.
TRACK = [
    None,
    {'shoulder': [-8.8, -20.2, -23.2], 'wrist': [-1.5, -28., -29.],
     'pole': [-23., -44., -42.], 'closed': .76, 'thumb_closed': .22, 'roll': .64},
    {'shoulder': [-11., -20.8, -23.0], 'wrist': [1.5, -25., -18.5],
     'pole': [-26., -44., -37.], 'closed': 1., 'thumb_closed': 1., 'roll': 1.},
    {'shoulder': [-4., -18.7, -22.5], 'wrist': [45., -8., -8.],
     'pole': [18., -32., -24.], 'closed': 1., 'thumb_closed': 1., 'roll': 1.},
    {'shoulder': [-4.2, -18.9, -22.6], 'wrist': [43., -8.5, -9.],
     'pole': [16., -32.5, -25.], 'closed': 1., 'thumb_closed': 1., 'roll': 1.},
    {'shoulder': [-5., -19.3, -23.0], 'wrist': [24., -13., -22.],
     'pole': [6., -35., -38.], 'closed': .94, 'thumb_closed': .90, 'roll': .84},
    {'shoulder': [-5.2, -19.1, -23.0], 'wrist': [19., -18., -32.],
     'pole': [2., -35., -44.], 'closed': .30, 'thumb_closed': .14, 'roll': .30},
    None,
]
idle_lower_delta = np.asarray(idle['component']['lowerarm_l'])[:3, :3] @ rest['lowerarm_l'][:3, :3].T
idle_across = unit(idle_lower_delta @ np.asarray(anatomy['across']))


def author(i):
    if TRACK[i] is None:
        return {'name': NAMES[i], 'time': TIMES[i],
                'local': {n: idle_local[n].tolist() for n in order},
                'component': {n: idle['component'][n] for n in order}}
    key = TRACK[i]
    shoulder, wrist, pole = [np.asarray(key[n], dtype=float) for n in ('shoulder', 'wrist', 'pole')]
    reach = wrist - shoulder
    distance = np.linalg.norm(reach)
    axis = unit(reach)
    along = (upper_length ** 2 - lower_length ** 2 + distance ** 2) / (2. * distance)
    bend = unit(pole - shoulder - axis * np.dot(pole - shoulder, axis))
    elbow = shoulder + axis * along + bend * math.sqrt(upper_length ** 2 - along ** 2)
    across = unit(idle_across * (1. - key['roll']) + np.asarray([0., 0., 1.]) * key['roll'])
    lower_delta = frame(wrist - elbow, across) @ frame(lower_rest, np.asarray(anatomy['across'])).T
    upper_delta = swing(lower_delta @ upper_rest, elbow - shoulder) @ lower_delta
    world = {n: m.copy() for n, m in rest.items()}
    world['clavicle_l'] = np.asarray(idle['component']['clavicle_l']).copy()
    world['upperarm_l'] = matrix(upper_delta @ rest['upperarm_l'][:3, :3], shoulder)
    world['lowerarm_l'] = matrix(lower_delta @ rest['lowerarm_l'][:3, :3], elbow)
    # The hand inherits the complete native forearm segment. There is no extra
    # wrist flexion or a hand-only twist layer on the forward punch.
    world['hand_l'] = matrix(lower_delta @ rest['hand_l'][:3, :3], wrist)
    world['clavicle_l'][:3, 3] = shoulder - world['clavicle_l'][:3, :3] @ native_local['upperarm_l'][:3, 3]
    for n in order:
        if n in ('clavicle_l', 'upperarm_l', 'lowerarm_l', 'hand_l'):
            continue
        closed = key['thumb_closed'] if n.startswith('thumb_') else key['closed']
        relative = (mix_local(idle_local[n], fist_local[n], closed)
                    if 'twist' not in n else native_local[n])
        world[n] = world[parent[n]] @ relative
    local = {n: np.linalg.inv(world[parent[n]]) @ world[n] for n in order}
    return {'name': NAMES[i], 'time': TIMES[i],
            'local': {n: m.tolist() for n, m in local.items()},
            'component': {n: world[n].tolist() for n in order}}


poses = [author(i) for i in range(len(TIMES))]
data = {'revision': REVISION, 'role': 'StaffFreeLeftQuickPunch',
        'units': 'UE cm, normalized native local transforms',
        'source': '../ApprenticeStaff20260927/RightCarryV14/full-pose.json',
        'source_solver': '../ApprenticeStaff20260927/LeftGaitV16/author_gait.py',
        'order': order, 'parent': parent, 'rest': source['rest'],
        'duration_seconds': TIMES[-1], 'contact_seconds': CONTACT,
        'times': TIMES, 'poses': poses, 'track': TRACK,
        'finger_profile_cumulative_palm_degrees': FIST_PROFILE,
        'fist_profile_source': 'FixV2/fist-profile-v2.json',
        'fist_reference': '../LeftHandPowerFist20260923/fist_profile_v2.json',
        'thumb_surface_authoring': 'FixV2/fist-authoring-result.json',
        'thumb_opposition': 'native nail faces exterior; distal pad covers index/middle outside',
        'close_sequence': 'four digits collect first; thumb opposes over their exterior before Ready',
        'clock_mapping': {'source_seconds': SOURCE_TIMES, 'authored_seconds': TIMES,
                          'forward_stroke_speed_multiplier': 1.5,
                          'forward_stroke_source_seconds': [.115, .20],
                          'recovery_span_durations_unchanged': True},
        'interpolation': 'local quaternion slerp and position lerp with quintic segment easing',
        'bone_scaling': False, 'right_carry': 'V14 false Idle; unchanged right-arm/staff contact',
        'rendered': False, 'runtime_tested': False}
(P / 'full-pose.json').write_text(json.dumps(data, indent=2), encoding='utf-8')


def numbers(values):
    return ','.join(f'{float(v):.10f}' for v in values)


lines = ['// Generated by SourceAssets/StaffQuickCombat20261001/author_punch.py.',
         '// Native LOCAL transforms, normalized UE centimetres. Divide position by parent reference scale.',
         '#pragma once', '#include "CoreMinimal.h"', 'namespace StaffAuthoredQuickPunch20261001 {',
         f'inline constexpr int32 Revision={REVISION};',
         f'inline constexpr int32 KeyCount=8, BoneCount={len(order)};',
         'inline constexpr float Times[KeyCount]={' + ','.join(f'{t:.10f}f' for t in TIMES) + '};',
         'struct FBone { FQuat Rotation; FVector Position; };',
         'inline const TCHAR* Names[BoneCount]={']
lines += [f'TEXT("{n}"),' for n in order]
lines += ['};', 'inline const FBone Poses[KeyCount][BoneCount]={']
for pose in poses:
    lines += ['{ // ' + pose['name'] + ', ' + str(pose['time']) + ' s']
    for n in order:
        m = np.asarray(pose['local'][n])
        lines += ['{FQuat(' + numbers(Rotation.from_matrix(m[:3, :3]).as_quat())
                  + '),FVector(' + numbers(m[:3, 3]) + ')},']
    lines += ['},']
lines += ['};', '}']
HEADER.write_text('\n'.join(lines) + '\n', encoding='utf-8')
print(f'Saved staff quick punch V2 source and native local table: 8 keys, {len(order)} left-chain bones, contact {CONTACT:.9f} s, duration {TIMES[-1]:.9f} s; forward stroke speed 1.5x.', flush=True)
