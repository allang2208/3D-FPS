"""Native staff charge flow with an anatomical elbow and complete arm helpers.

Author only: local FK segments drive the shaft contact. Runtime duration, entry
capture, locomotion and effect timing belong to the integration code. No tests,
asset import, rendering or UE launch are performed by this script.
"""
import copy
import json
import math
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation as R

P = Path(__file__).resolve().parent
PROJECT = P.parents[2]
SOURCE = P.parent / 'CastElbowRepair20260930/full-pose.json'
HEADER = PROJECT / 'Source/FPSGAME/Weapons/Staff/StaffAuthoredChargeFlow20261001.h'
REVISION = 2026100102
TIMES = [.18, .43, .70, .88, 1.]
KEY_NAMES = ['Coil', 'LiftLow', 'LiftHigh', 'Compress', 'RaisedSettled']
VARIANT_NAMES = ['false', 'alloy_grip', 'pine_grip', 'sandalwood_grip']


def unit(v):
    return np.asarray(v, float) / np.linalg.norm(v)


def limb_frame(direction, normal):
    x = unit(direction)
    z = unit(normal - x*(normal @ x))
    return np.column_stack((x, np.cross(z, x), z))


def solve_elbow(shoulder, wrist, pole, upper_length, lower_length):
    delta = wrist - shoulder
    distance = np.linalg.norm(delta)
    direction = unit(delta)
    along = (upper_length**2 - lower_length**2 + distance**2)/(2*distance)
    radius = math.sqrt(upper_length**2 - along**2)
    side = unit(pole - shoulder - direction*((pole-shoulder) @ direction))
    return shoulder + along*direction + radius*side


def author():
    source = json.loads(SOURCE.read_text(encoding='utf-8-sig'))
    # Immutable landmarks from the previous trial retain the user's staff path
    # and grasp. They are inputs, not an output fed back into the next bake.
    landmarks = json.loads((P/'BeforeElbowRepair/full-pose.json').read_text(encoding='utf-8-sig'))
    rest = {n: np.array(m, float) for n, m in source['rest'].items()}
    parent = source['parent']
    names = [n for n in source['order'] if n.endswith('_r')]

    def locals_from_world(world):
        complete = dict(rest, **world)
        return {n: np.linalg.inv(complete[parent[n]]) @ world[n] for n in names}

    ref_local = {n: np.linalg.inv(rest[parent[n]]) @ rest[n] for n in names}
    ref_upper = rest['lowerarm_r'][:3, 3] - rest['upperarm_r'][:3, 3]
    ref_lower = rest['hand_r'][:3, 3] - rest['lowerarm_r'][:3, 3]
    ref_plane = unit(np.cross(ref_upper, ref_lower))
    hinge = rest['upperarm_r'][:3, :3].T @ ref_plane
    forearm_axis = unit(rest['lowerarm_r'][:3, :3].T @ ref_lower)
    ref_flexion = math.acos(unit(ref_upper) @ unit(ref_lower))
    palm_width = unit(rest['index_metacarpal_r'][:3, 3] - rest['pinky_metacarpal_r'][:3, 3])
    shoulders = [[-6., 24., -26.], [-8., 21., -23.],
                 [-10., 17., -16.], [-9., 16., -14.], [-9., 16., -14.]]
    poses, entries = {}, {}
    for variant in VARIANT_NAMES:
        grasp = np.array(source['variants'][variant]['hand'])
        idle = dict(rest, **{n: np.array(m) for n, m in landmarks['default_entry'][variant]['component'].items()})
        carry_wrist = idle['lowerarm_r'][:3, :3].T @ idle['hand_r'][:3, :3]
        clips = []
        entries[variant] = copy.deepcopy(landmarks['default_entry'][variant])
        for key, phase, anchor, old_clip in zip(KEY_NAMES, TIMES, shoulders, landmarks['poses'][variant]):
            contact = np.array(old_clip['contact'])
            hand = contact @ grasp
            shoulder, wrist = np.array(anchor), hand[:3, 3]
            # A camera-fixed outward pole would bend this accepted staff wrist
            # sideways. Aim the elbow towards the carry forearm extrapolated
            # from the actual hand, then solve the native-length elbow circle.
            preferred_lower = hand[:3, :3] @ carry_wrist.T
            pole = wrist - preferred_lower @ rest['lowerarm_r'][:3, :3].T @ ref_lower
            elbow = solve_elbow(shoulder, wrist, pole, np.linalg.norm(ref_upper), np.linalg.norm(ref_lower))
            upper_direction, lower_direction = unit(elbow-shoulder), unit(wrist-elbow)
            plane = unit(np.cross(upper_direction, lower_direction))
            upper_rotation = limb_frame(upper_direction, plane) @ limb_frame(ref_upper, ref_plane).T @ rest['upperarm_r'][:3, :3]
            flexion = math.acos(np.clip(upper_direction @ lower_direction, -1., 1.)) - ref_flexion
            hinge_rotation = R.from_rotvec(hinge*flexion).as_matrix()
            lower_neutral = upper_rotation @ hinge_rotation @ ref_local['lowerarm_r'][:3, :3]
            # Wrist extension must not masquerade as elbow twist. Derive
            # pronation from actual palm width projected around the forearm.
            current_width = lower_neutral @ rest['lowerarm_r'][:3, :3].T @ palm_width
            goal_width = hand[:3, :3] @ rest['hand_r'][:3, :3].T @ palm_width
            current_width = unit(current_width - lower_direction*(current_width @ lower_direction))
            goal_width = unit(goal_width - lower_direction*(goal_width @ lower_direction))
            pronation = math.atan2(lower_direction @ np.cross(current_width, goal_width), current_width @ goal_width)
            pronation = float(np.clip(pronation, -math.radians(45.), math.radians(45.)))
            lower_rotation = lower_neutral @ R.from_rotvec(forearm_axis*pronation).as_matrix()
            world = {n:m.copy() for n,m in rest.items()}
            world['clavicle_r'] = idle['clavicle_r'].copy()
            world['clavicle_r'][:3, 3] = shoulder - world['clavicle_r'][:3, :3] @ ref_local['upperarm_r'][:3, 3]
            world['upperarm_r'][:3, :3], world['upperarm_r'][:3, 3] = upper_rotation, shoulder
            world['lowerarm_r'][:3, :3], world['lowerarm_r'][:3, 3] = lower_rotation, elbow
            world['hand_r'] = hand
            for n in names:
                if n in ('clavicle_r', 'upperarm_r', 'lowerarm_r', 'hand_r'):
                    continue
                # All native upper/lower helpers retain their full rest-local
                # transform; both endpoint helpers move with their main segment.
                relative = np.array(source['variants'][variant]['fingers'][n]) if n in source['variants'][variant]['fingers'] else ref_local[n]
                world[n] = world[parent[n]] @ relative
            local = locals_from_world(world)
            clips.append(dict(name=key, phase_normalized=phase,
                elbow_flexion_offset_radians=flexion, forearm_roll_radians=pronation,
                elbow_pole_camera_cm=pole.tolist(),
                local={n:m.tolist() for n,m in local.items()},
                component={n:world[n].tolist() for n in names}, contact=contact.tolist()))
        poses[variant] = clips

    data = dict(revision=REVISION, units='normalized UE camera cm', source=str(SOURCE.relative_to(PROJECT)),
        order=names, rest=source['rest'], parent=parent, variants=source['variants'],
        phase_normalized=TIMES, key_names=KEY_NAMES, poses=poses, default_entry=entries,
        raised_contract=dict(contact_cm=[49., 26., -8.], axis=[.52, -.10, .848],
            presentation_offset_cm=[0., 4., 0.], charge_offset_cm=[10., 0., 0.], offsets_already_applied=True),
        driver='Native anatomical two-bone controls; constant elbow hinge, bounded palm-derived forearm pronation; exact prior grip landmarks',
        helper_contract='All upperarm/lowerarm twist helpers keep full rest-local transforms and follow their segment',
        elbow_contract=dict(hinge_upper_local=hinge.tolist(), lower_rest_rotation=ref_local['lowerarm_r'].tolist(),
            forearm_axis_lower_local=forearm_axis.tolist(),
            pole_contract='Per-control forearm extrapolation from accepted carry wrist; anatomical bend plane with native-length reach',
            shoulder_keys_camera_cm=shoulders, max_forearm_roll_degrees=45.,
            runtime_interpolation='Weighted flexion/pronation scalars, then hinge * lower_rest * forearm_roll; captured entry blended once'),
        duration_contract='Phase fractions only; unchanged runtime charge duration; editable standard take 0.95s',
        rendered=False, runtime_tested=False, ue_animation_import_required=False)
    (P/'full-pose.json').write_text(json.dumps(data, indent=2)+'\n', encoding='utf-8')
    HEADER.write_text(header(data), encoding='utf-8')
    print('SAVED_CHARGE_ELBOW_REPAIR revision', REVISION, '4 grips x 5 anatomical arm controls; prior hand/shaft landmarks retained.', flush=True)


def header(data):
    def numbers(values):
        return ','.join(f'{v:.10f}' for v in values)
    def transform(value):
        m = np.array(value)
        return 'FTransform(FQuat('+numbers(R.from_matrix(m[:3,:3]).as_quat())+'),FVector('+numbers(m[:3,3])+'))'
    lines = ['// Generated by ChargeFlow20261001/author_motion.py; V7 anatomical elbow, current grip landmarks.',
        '#pragma once', '#include "CoreMinimal.h"', 'namespace StaffAuthoredChargeFlow20261001 {',
        f'inline constexpr int32 Revision={REVISION}, KeyCount=5, VariantCount=4, BoneCount={len(data["order"])};',
        'inline constexpr float PhaseNormalized[]={'+','.join(f'{t:.10f}f' for t in TIMES)+'};',
        'inline const TCHAR* VariantNames[]={'+','.join('TEXT("'+n+'")' for n in VARIANT_NAMES)+'};',
        'inline const TCHAR* KeyNames[]={'+','.join('TEXT("'+n+'")' for n in KEY_NAMES)+'};',
        'inline const TCHAR* Names[BoneCount]={'+','.join('TEXT("'+n+'")' for n in data['order'])+'};',
        'struct FBone { FQuat Rotation; FVector Position; };',
        'inline const FTransform HandInGrip[VariantCount]={']
    lines += [transform(data['variants'][n]['hand'])+',' for n in VARIANT_NAMES]
    lines += ['};', 'inline const FQuat LowerRestRotation='+transform(data['elbow_contract']['lower_rest_rotation'])+'.GetRotation();',
        'inline const FVector ForearmAxisLocal=FVector('+numbers(data['elbow_contract']['forearm_axis_lower_local'])+');',
        'inline constexpr double ElbowAngles[VariantCount][KeyCount][2]={']
    for variant in VARIANT_NAMES:
        lines.append('{'+','.join('{'+numbers([c['elbow_flexion_offset_radians'], c['forearm_roll_radians']])+'}' for c in data['poses'][variant])+'},')
    lines += ['};', 'inline const FTransform Contacts[VariantCount][KeyCount]={']
    for variant in VARIANT_NAMES:
        lines.append('{ // '+variant)
        lines += [transform(c['contact'])+',' for c in data['poses'][variant]]
        lines.append('},')
    lines += ['};', 'inline const FBone Poses[VariantCount][KeyCount][BoneCount]={']
    for variant in VARIANT_NAMES:
        lines.append('{ // '+variant)
        for clip in data['poses'][variant]:
            lines.append('{ // '+clip['name'])
            for n in data['order']:
                m = np.array(clip['local'][n])
                lines.append('{FQuat('+numbers(R.from_matrix(m[:3,:3]).as_quat())+'),FVector('+numbers(m[:3,3])+')},')
            lines.append('},')
        lines.append('},')
    return '\n'.join(lines+['};','}',''])


if __name__ == '__main__':
    author()
