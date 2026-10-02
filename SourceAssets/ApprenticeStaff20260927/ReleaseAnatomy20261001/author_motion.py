"""Author a continuous staff release from the anatomical settled charge.

Preserve accepted carry/run, four grasps and all native bindings. Arm endpoints
are solved before writing parent-local transforms; no independent hand pivot or
skin-weight compensation is used. This script makes data, not game tests.
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
CHARGE = P.parent / 'ChargeFlow20261001/full-pose.json'
HEADER = PROJECT / 'Source/FPSGAME/Weapons/Staff/StaffAuthoredReleaseAnatomy20261001.h'
REVISION = 2026100101
KEY_NAMES = ['Idle', 'Raised', 'Windup', 'Release', 'Follow', 'Run']
VARIANT_NAMES = ['false', 'alloy_grip', 'pine_grip', 'sandalwood_grip']
CAST_KEYS = [
    ('Windup', [47., 27., -7.], [.44, -.12, .890], [-9., 16., -14.]),
    ('Release', [55., 21., -12.], [.940, -.080, .332], [0., 16., -14.]),
    ('Follow', [53., 19., -16.], [.960, -.100, .262], [-1., 16., -14.]),
]


def unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def limb_frame(direction, normal):
    x = unit(direction)
    z = unit(normal - x * (normal @ x))
    return np.column_stack((x, np.cross(z, x), z))


def contact_frame(point, axis):
    # FRotationMatrix::MakeFromZX(axis, ForwardVector): camera +X forward.
    z = unit(axis)
    x = unit(np.array([1., 0., 0.]) - z * z[0])
    result = np.eye(4)
    result[:3, :3] = np.column_stack((x, np.cross(z, x), z))
    result[:3, 3] = point
    return result


def solve_elbow(shoulder, wrist, pole, upper_length, lower_length):
    delta = wrist - shoulder
    distance = np.linalg.norm(delta)
    direction = unit(delta)
    along = (upper_length**2 - lower_length**2 + distance**2) / (2 * distance)
    radius = math.sqrt(upper_length**2 - along**2)
    side = unit(pole - shoulder - direction * ((pole - shoulder) @ direction))
    return shoulder + along * direction + radius * side


def author():
    source = json.loads(SOURCE.read_text(encoding='utf-8-sig'))
    charge = json.loads(CHARGE.read_text(encoding='utf-8-sig'))
    rest = {n: np.array(m, float) for n, m in source['rest'].items()}
    parent, names = source['parent'], source['order']
    right_names = [n for n in names if n.endswith('_r')]
    ref_local = {n: np.linalg.inv(rest[parent[n]]) @ rest[n] for n in names}
    ref_upper = rest['lowerarm_r'][:3, 3] - rest['upperarm_r'][:3, 3]
    ref_lower = rest['hand_r'][:3, 3] - rest['lowerarm_r'][:3, 3]
    ref_plane = unit(np.cross(ref_upper, ref_lower))
    hinge = rest['upperarm_r'][:3, :3].T @ ref_plane
    forearm_axis = unit(rest['lowerarm_r'][:3, :3].T @ ref_lower)
    ref_flexion = math.acos(unit(ref_upper) @ unit(ref_lower))
    palm_width = unit(rest['index_metacarpal_r'][:3, 3] - rest['pinky_metacarpal_r'][:3, 3])
    upper_length, lower_length = np.linalg.norm(ref_upper), np.linalg.norm(ref_lower)
    poses, parameters = {}, []

    for variant in VARIANT_NAMES:
        # The complete idle and run rows are preserved, not regenerated.
        clips = copy.deepcopy(source['poses'][variant])
        grasp = np.array(source['variants'][variant]['hand'])
        idle = dict(rest, **{n: np.array(m) for n, m in clips[0]['component'].items()})
        carry_wrist = idle['lowerarm_r'][:3, :3].T @ idle['hand_r'][:3, :3]
        settled = charge['poses'][variant][-1]
        # Right chain is byte-for-value identical to the latest charge endpoint.
        clips[1]['local'].update(copy.deepcopy(settled['local']))
        clips[1]['component'].update(copy.deepcopy(settled['component']))
        for field in ('contact', 'elbow_flexion_offset_radians', 'forearm_roll_radians', 'elbow_pole_camera_cm'):
            clips[1][field] = copy.deepcopy(settled[field])
        clips[1]['charge_source_revision'] = charge['revision']
        previous_upper = np.array(settled['component']['upperarm_r'])[:3, :3]

        for index, (name, point, axis, anchor) in enumerate(CAST_KEYS, start=2):
            contact = contact_frame(point, axis)
            hand = contact @ grasp
            shoulder, wrist = np.array(anchor), hand[:3, 3]
            # The accepted carry wrist determines the preferred forearm, so
            # changing shaft tilt cannot abruptly pick another elbow side.
            preferred_lower = hand[:3, :3] @ carry_wrist.T
            pole = wrist - preferred_lower @ rest['lowerarm_r'][:3, :3].T @ ref_lower
            # A horizontal shaft makes the unconstrained carry-wrist pole pick
            # the opposite anatomical bend plane: the upper segment rolls 125
            # degrees, leaving roughly 139 degrees in the wrist after pronation
            # is limited. Resolve this on the same native elbow circle. Choose
            # its nearest natural wrist/previous-upper orientation together;
            # this retains contact and reach without a camera-fixed elbow pole.
            reach_direction = unit(wrist - shoulder)
            pole_side = unit(pole - shoulder - reach_direction * ((pole - shoulder) @ reach_direction))
            best = None
            for swivel_degrees in np.arange(-180., 180.001, .25):
                candidate_pole = shoulder + R.from_rotvec(reach_direction * math.radians(swivel_degrees)).apply(pole_side) * lower_length
                candidate_elbow = solve_elbow(shoulder, wrist, candidate_pole, upper_length, lower_length)
                upper_direction, lower_direction = unit(candidate_elbow - shoulder), unit(wrist - candidate_elbow)
                plane = unit(np.cross(upper_direction, lower_direction))
                candidate_upper = limb_frame(upper_direction, plane) @ limb_frame(ref_upper, ref_plane).T @ rest['upperarm_r'][:3, :3]
                candidate_flexion = math.acos(np.clip(upper_direction @ lower_direction, -1., 1.)) - ref_flexion
                lower_neutral = candidate_upper @ R.from_rotvec(hinge * candidate_flexion).as_matrix() @ ref_local['lowerarm_r'][:3, :3]
                current_width = lower_neutral @ rest['lowerarm_r'][:3, :3].T @ palm_width
                goal_width = hand[:3, :3] @ rest['hand_r'][:3, :3].T @ palm_width
                current_width = unit(current_width - lower_direction * (current_width @ lower_direction))
                goal_width = unit(goal_width - lower_direction * (goal_width @ lower_direction))
                candidate_raw_roll = math.atan2(lower_direction @ np.cross(current_width, goal_width), current_width @ goal_width)
                candidate_roll = float(np.clip(candidate_raw_roll, -math.radians(45.), math.radians(45.)))
                candidate_lower = lower_neutral @ R.from_rotvec(forearm_axis * candidate_roll).as_matrix()
                wrist_angle = R.from_matrix(candidate_lower.T @ hand[:3, :3] @ carry_wrist.T).magnitude()
                upper_angle = R.from_matrix(candidate_upper @ previous_upper.T).magnitude()
                score = wrist_angle**2 + upper_angle**2
                candidate = (score, candidate_pole, candidate_elbow, candidate_upper, candidate_lower,
                    candidate_flexion, candidate_roll, candidate_raw_roll, swivel_degrees, wrist_angle, upper_angle)
                if best is None or score < best[0]:
                    best = candidate
            _, pole, elbow, upper_rotation, lower_rotation, flexion, roll, raw_roll, swivel_degrees, wrist_angle, upper_angle = best
            previous_upper = upper_rotation
            world = dict(rest, **{n: np.array(m) for n, m in clips[index]['component'].items()})
            world['clavicle_r'] = idle['clavicle_r'].copy()
            world['clavicle_r'][:3, 3] = shoulder - world['clavicle_r'][:3, :3] @ ref_local['upperarm_r'][:3, 3]
            world['upperarm_r'][:3, :3], world['upperarm_r'][:3, 3] = upper_rotation, shoulder
            world['lowerarm_r'][:3, :3], world['lowerarm_r'][:3, 3] = lower_rotation, elbow
            world['hand_r'] = hand
            for n in right_names:
                if n in ('clavicle_r', 'upperarm_r', 'lowerarm_r', 'hand_r'):
                    continue
                relative = np.array(source['variants'][variant]['fingers'][n]) if n in source['variants'][variant]['fingers'] else ref_local[n]
                world[n] = world[parent[n]] @ relative
            # Left chain has the original cast locals; only the right chain is
            # rebuilt. Twist helper translations/rotations remain native locals.
            clips[index].update(name=name, contact=contact.tolist(),
                elbow_flexion_offset_radians=flexion, forearm_roll_radians=roll,
                elbow_pole_camera_cm=pole.tolist(),
                local={n: (np.linalg.inv(world[parent[n]]) @ world[n]).tolist() for n in names},
                component={n: world[n].tolist() for n in names})
            parameters.append(dict(variant=variant, key=name,
                shoulder_camera_cm=shoulder.tolist(), elbow_camera_cm=elbow.tolist(), wrist_camera_cm=wrist.tolist(),
                shoulder_wrist_reach_cm=float(np.linalg.norm(wrist - shoulder)),
                total_elbow_flexion_degrees=math.degrees(ref_flexion + flexion),
                forearm_roll_degrees=math.degrees(roll), unclamped_forearm_roll_degrees=math.degrees(raw_roll),
                pole_swivel_from_carry_degrees=float(swivel_degrees),
                wrist_rotation_from_carry_degrees=math.degrees(wrist_angle), upper_rotation_from_previous_key_degrees=math.degrees(upper_angle)))
        poses[variant] = clips

    data = dict(revision=REVISION, units='normalized UE camera cm',
        source=str(SOURCE.relative_to(PROJECT)), charge_source=str(CHARGE.relative_to(PROJECT)), charge_revision=charge['revision'],
        order=names, rest=source['rest'], parent=parent, variants=source['variants'], key_names=KEY_NAMES, poses=poses,
        native_lengths_cm=dict(upper=upper_length, lower=lower_length), authored_parameters=parameters,
        elbow_contract=dict(hinge_upper_local=hinge.tolist(), lower_rest_rotation=ref_local['lowerarm_r'].tolist(),
            forearm_axis_lower_local=forearm_axis.tolist(), rest_elbow_flexion_degrees=math.degrees(ref_flexion),
            max_forearm_roll_degrees=45.,
            pole_contract='Actual hand and accepted carry wrist seed the native-length elbow circle; resolve its swivel with joint wrist/previous-upper orientation energy instead of allowing a bend-plane inversion',
            runtime_interpolation='Positive local-transform weights, lowerarm flexion/pronation scalars reconstructed around a fixed native hinge; Idle/Run entry blended once'),
        contact_contract='All cast camera offsets are already applied once. Raised is the current anatomical charge endpoint. Shaft is always derived from whole-arm FK.',
        helper_contract='All four right upper/lower twist helpers retain their full rest-local transforms and follow their segment',
        retained_contract='Complete Idle/Run rows, grasp fingers, hand-in-grip, native bind and left arm cast keys are preserved',
        duration_contract=dict(swing_seconds=.28, anticipation_seconds=.035, contact_seconds=.18, hold_seconds=.10, recover_seconds=.42),
        rendered=False, runtime_tested=False, ue_animation_import_required=False)
    (P / 'full-pose.json').write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    HEADER.write_text(header(data), encoding='utf-8')
    (P / 'authored-parameters.json').write_text(json.dumps(dict(revision=REVISION, native_lengths_cm=data['native_lengths_cm'], rows=parameters), indent=2) + '\n', encoding='utf-8')
    print('SAVED_STAFF_RELEASE_ANATOMY', REVISION, '4 grips x 6 keys; complete charge endpoint and carry/run retained.', flush=True)
    for row in parameters:
        print(row['variant'], row['key'], 'flex', round(row['total_elbow_flexion_degrees'], 3), 'roll', round(row['forearm_roll_degrees'], 3), 'elbow', [round(x, 3) for x in row['elbow_camera_cm']], flush=True)


def header(data):
    def numbers(values):
        return ','.join(f'{v:.10f}' for v in values)
    def transform(value):
        m = np.array(value)
        return 'FTransform(FQuat(' + numbers(R.from_matrix(m[:3, :3]).as_quat()) + '),FVector(' + numbers(m[:3, 3]) + '))'
    lines = ['// Generated by ReleaseAnatomy20261001/author_motion.py; anatomical staff charge-to-release chain.',
        '#pragma once', '#include "CoreMinimal.h"', 'namespace StaffAuthoredReleaseAnatomy20261001 {',
        f'inline constexpr int32 Revision={REVISION}, PoseCount=6, VariantCount=4, BoneCount={len(data["order"])};',
        'struct FBone { const TCHAR* Name; FQuat Rotation; FVector Position; };',
        'inline const TCHAR* VariantNames[]={' + ','.join('TEXT("' + n + '")' for n in VARIANT_NAMES) + '};',
        'inline const TCHAR* KeyNames[]={' + ','.join('TEXT("' + n + '")' for n in KEY_NAMES) + '};',
        'inline const FTransform HandInGrip[VariantCount]={']
    lines += [transform(data['variants'][n]['hand']) + ',' for n in VARIANT_NAMES]
    lines += ['};', 'inline const FQuat LowerRestRotation=' + transform(data['elbow_contract']['lower_rest_rotation']) + '.GetRotation();',
        'inline const FVector ForearmAxisLocal=FVector(' + numbers(data['elbow_contract']['forearm_axis_lower_local']) + ');',
        'inline constexpr double ElbowAngles[VariantCount][PoseCount][2]={']
    for variant in VARIANT_NAMES:
        rows = [[c['elbow_flexion_offset_radians'], c['forearm_roll_radians']] if k in (1, 2, 3, 4) else [0., 0.] for k, c in enumerate(data['poses'][variant])]
        lines.append('{' + ','.join('{' + numbers(row) + '}' for row in rows) + '},')
    lines += ['};', 'inline const FTransform Contacts[VariantCount][PoseCount]={']
    for variant in VARIANT_NAMES:
        lines.append('{ // ' + variant)
        lines += [transform(c['contact']) + ',' for c in data['poses'][variant]]
        lines.append('},')
    lines += ['};', 'inline const FBone Poses[VariantCount][PoseCount][BoneCount]={']
    for variant in VARIANT_NAMES:
        lines.append('{ // ' + variant)
        for clip in data['poses'][variant]:
            lines.append('{ // ' + clip['name'])
            for name in data['order']:
                m = np.array(clip['local'][name])
                lines.append('{TEXT("' + name + '"),FQuat(' + numbers(R.from_matrix(m[:3, :3]).as_quat()) + '),FVector(' + numbers(m[:3, 3]) + ')},')
            lines.append('},')
        lines.append('},')
    return '\n'.join(lines + ['};', '}', ''])


if __name__ == '__main__':
    author()
