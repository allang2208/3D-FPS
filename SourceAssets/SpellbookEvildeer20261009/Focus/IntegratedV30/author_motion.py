"""Author V30 from the accepted V24 pose path. No renders or runtime tests.

Outputs native local-pose keys, closing-only finger rotations and editable data.
The hand release frame and final reading pose remain at the accepted endpoints.
"""
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R, Slerp

OUT = Path(__file__).resolve().parent
P = OUT.parent
ROOT = P.parents[2]
DEST = ROOT / 'Source/FPSGAME/Weapons/Spellbook'
settings = json.loads((OUT / 'motion-settings.json').read_text())
source = json.loads((P / 'PalmUpOpeningV24/candidate.json').read_text())
native = json.loads((ROOT / 'SourceAssets/ModularOutfit20260925/BarePalmV7/M4_original.json').read_text())['bones']
names = source['arm_order']
by_index = {bone['index']: name for name, bone in native.items()}
parents = {name: by_index.get(native[name]['parent']) for name in names}
held = {name: np.array(value) for name, value in source['poses'][54]['local'].items()}
opened = {name: np.array(value) for name, value in source['poses'][75]['local'].items()}
outer = np.array(source['poses'][54]['component']['clavicle_l']) @ np.linalg.inv(held['clavicle_l'])
digits = tuple(settings['digit_offsets'])
is_finger = [name.startswith(tuple(d + '_' for d in digits)) for name in names]


def ease(a, b, value):
    t = float(np.clip((value-a)/(b-a), 0., 1.))
    return t*t*t*(t*(t*6.-15.)+10.)


def pulse(a, peak, b, value):
    return ease(a, peak, value) * (1.-ease(peak, b, value))


def mix_rotation(a, b, weight):
    return Slerp([0., 1.], R.from_matrix([a, b]))([weight]).as_matrix()[0]


def sample_source(age):
    frame = min(age*source['fps'], len(source['poses'])-1.)
    a = min(int(frame), len(source['poses'])-2)
    weight = frame-a
    local = {}
    for name in names:
        first = np.array(source['poses'][a]['local'][name])
        second = np.array(source['poses'][a+1]['local'][name])
        value = np.eye(4)
        value[:3, :3] = mix_rotation(first[:3, :3], second[:3, :3], weight)
        value[:3, 3] = first[:3, 3]*(1.-weight)+second[:3, 3]*weight
        local[name] = value
    return local


def component_pose(local):
    world = {}
    for name in names:
        world[name] = (world[parents[name]] if parents[name] in world else outer) @ local[name]
    return world


def swing(a, b):
    a, b = a/np.linalg.norm(a), b/np.linalg.norm(b)
    cross = np.cross(a, b)
    # These small support adjustments stay near the accepted bent-arm frame.
    return R.from_quat(np.r_[cross, 1.+np.dot(a, b)]).as_matrix()


def support_pose(local, age):
    if age <= .86 or age >= 1.62:
        return local
    world = component_pose(local)
    old_shoulder = world['upperarm_l'][:3, 3].copy()
    old_elbow = world['lowerarm_l'][:3, 3].copy()
    old_wrist = world['hand_l'][:3, 3].copy()
    old_drop = -10.*ease(1.14, 1.62, age)
    settle = pulse(.86, .93, 1.10, age)
    shoulder_delta = np.array(settings['shoulder_settle_cm'])*settle
    shoulder_delta[2] += -10.*ease(*settings['shoulder_lower_window'], age)-old_drop
    wrist_delta = np.array(settings['wrist_arc_cm'])*pulse(.95, 1.24, 1.62, age)
    wrist_delta[2] += -10.*ease(*settings['wrist_lower_window'], age)-old_drop
    shoulder = old_shoulder+shoulder_delta
    wrist = old_wrist+wrist_delta
    upper_length = np.linalg.norm(old_elbow-old_shoulder)
    lower_length = np.linalg.norm(old_wrist-old_elbow)
    axis = wrist-shoulder
    distance = np.linalg.norm(axis)
    axis /= distance
    along = (upper_length**2-lower_length**2+distance**2)/(2.*distance)
    radius = np.sqrt(max(0., upper_length**2-along**2))
    lead = np.array(settings['elbow_lead_cm'])*pulse(.88, 1.10, 1.50, age)
    pole = old_elbow+shoulder_delta+lead-shoulder
    pole -= axis*np.dot(pole, axis)
    pole /= np.linalg.norm(pole)
    elbow = shoulder+axis*along+pole*radius
    targets = {name: world[name].copy() for name in ('clavicle_l', 'upperarm_l', 'lowerarm_l', 'hand_l')}
    targets['clavicle_l'][:3, 3] += shoulder_delta
    targets['upperarm_l'][:3, 3] = shoulder
    targets['lowerarm_l'][:3, 3] = elbow
    targets['hand_l'][:3, 3] = wrist
    targets['upperarm_l'][:3, :3] = swing(old_elbow-old_shoulder, elbow-shoulder) @ world['upperarm_l'][:3, :3]
    targets['lowerarm_l'][:3, :3] = swing(old_wrist-old_elbow, wrist-elbow) @ world['lowerarm_l'][:3, :3]
    rebuilt = {}
    result = {}
    for name in names:
        parent = rebuilt[parents[name]] if parents[name] in rebuilt else outer
        rebuilt[name] = targets[name] if name in targets else parent @ local[name]
        result[name] = np.linalg.inv(parent) @ rebuilt[name]
    return result


def finger_weight(name, age, returning):
    digit, part, *_ = name.split('_')
    offset = settings['digit_offsets'][digit]
    joint = max(0, int(part)-1) if part.isdigit() else 0
    lag = joint*settings['joint_lag_seconds']
    if returning:
        contact = 1.045+offset*.35+lag*.5
        end = 1.235+offset*.18+lag*.25
        fraction = settings['closing_contact_fraction']
        # Descending source time: approach -> surface contact -> final squeeze.
        # The final pose never closes beyond the accepted grip.
        return fraction*ease(.95, contact, age)+(1.-fraction)*ease(contact, end, age)
    start = settings['finger_release_start']+offset+lag
    end = start+settings['finger_release_span']
    unload = settings['unload_fraction']
    return unload*ease(.90, start, age)+(1.-unload)*ease(start, end, age)


fps = settings['source_fps']
times = sorted(set([round(i/fps, 9) for i in range(round(1.95*fps)+1)] + [.86, .90, .93, .95, 1.10, 1.12, 1.14, 1.17, 1.25, 1.28, 1.62]))
poses, closing = [], []
for age in times:
    local = support_pose(sample_source(age), age)
    return_rotations = {}
    for name, finger in zip(names, is_finger):
        if finger and age >= .90:
            local[name][:3, :3] = mix_rotation(held[name][:3, :3], opened[name][:3, :3], finger_weight(name, age, False))
            close = mix_rotation(held[name][:3, :3], opened[name][:3, :3], finger_weight(name, age, True))
        else:
            close = local[name][:3, :3]
        return_rotations[name] = R.from_matrix(close).as_quat().tolist()
    poses.append({name: value.tolist() for name, value in local.items()})
    closing.append(return_rotations)


def numbers(values):
    return ','.join(f'{value:.10f}' for value in values)


header = ['#pragma once', '#include "SpellbookAuthoredGrip.h"',
          '// Generated by Focus/IntegratedV30/author_motion.py; accepted V24 endpoints.',
          'namespace SpellbookAuthoredFocus {', f'inline constexpr int32 KeyCount={len(times)};',
          'inline constexpr float Times[]={'+','.join(f'{t:.9f}f' for t in times)+'};',
          'struct FKeyBone { double Rotation[4]; double Position[3]; };',
          'inline constexpr bool FingerBone[]={'+','.join('true' if finger else 'false' for finger in is_finger)+'};',
          'inline constexpr FKeyBone Poses[KeyCount][SpellbookAuthoredGrip::BoneCount]={']
for pose in poses:
    header.append('{')
    for name in names:
        value = np.array(pose[name])
        header.append('    {{'+numbers(R.from_matrix(value[:3, :3]).as_quat())+'},{'+numbers(value[:3, 3])+'}},')
    header.append('},')
header += ['};', 'inline constexpr double ReturnRotations[KeyCount][SpellbookAuthoredGrip::BoneCount][4]={']
for pose in closing:
    header += ['{']+['    {'+numbers(pose[name])+'},' for name in names]+['},']
header += ['};', '}']
(DEST / 'SpellbookAuthoredFocus.h').write_text('\n'.join(header)+'\n', encoding='utf-8')
clock = ['#pragma once', '// Generated from IntegratedV30/motion-settings.json.', 'namespace SpellbookFocusPolish {']
for symbol, key in [('PlaybackRate', 'playback_rate'), ('AuthoredLength', 'authored_length'), ('RecoveryBlendSeconds', 'recovery_blend_seconds')]:
    clock.append(f'inline constexpr float {symbol}={settings[key]:.9f}f;')
for symbol, key in [('AgeKeys', 'age_keys'), ('SourceKeys', 'source_keys'), ('Rates', 'source_rates')]:
    clock.append(f'inline constexpr float {symbol}[]={{'+','.join(f'{v:.9f}f' for v in settings[key])+'};')
clock += ['}']
(DEST / 'SpellbookFocusPolish.h').write_text('\n'.join(clock)+'\n', encoding='utf-8')
(OUT / 'motion.json').write_text(json.dumps({'revision':30, 'times':times, 'arm_order':names, 'poses':poses, 'return_rotations':closing,
    'settings':settings, 'source':'PalmUpOpeningV24/candidate.json', 'runtime_tested':False}, separators=(',', ':')), encoding='utf-8')
print(f'SPELLBOOK_V30_AUTHORED keys={len(times)} opening=1.12 recover=1.12')
