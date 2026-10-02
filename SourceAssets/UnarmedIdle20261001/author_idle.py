"""Author low, closed V7 fists with a quiet continuous breathing cycle.

Camera coordinates are UE centimetres: +X forward, +Y screen right, +Z up.
The left fist is the accepted staff punch V2 profile. Right digit rotations
are conjugated through the actual native palm semantic frames; native local
translations, bind transforms and skin are retained on both sides.
This script only produces the complete local table and editable source data.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation

P = Path(__file__).resolve().parent
ROOT = P.parents[1]
SOURCE = ROOT / 'SourceAssets/ApprenticeStaff20260927/RightCarryV14/full-pose.json'
ANATOMY = ROOT / 'SourceAssets/ModularOutfit20260924/OriginalShapeBareM4/BareUpperArmsV6/M4_bare_shape.json'
FIST_DIR = ROOT / 'SourceAssets/StaffQuickCombat20261001/FixV2'
HEADER = ROOT / 'Source/FPSGAME/Weapons/Unarmed/UnarmedAuthoredIdle20261001.h'
REVISION = 2026100101
PERIOD = 4.2

sys.path.insert(0, str(FIST_DIR))
from fit_v7_fist import closed_pose


def unit(value):
    return np.asarray(value, dtype=float) / np.linalg.norm(value)


def limb_frame(direction, normal):
    x = unit(direction)
    z = unit(normal - x * (normal @ x))
    return np.column_stack((x, np.cross(z, x), z))


def semantic_palm(rest, anatomy, side):
    # Anatomical forward/radial/dorsal are a semantic frame. Its determinant
    # differs across hands; use it only to conjugate a proper rotation.
    # Never put its reflection into a bone transform or a mesh scale.
    origin = rest['hand_' + side][:3, 3]
    forward = unit(rest['middle_01_' + side][:3, 3] - origin)
    radial = rest['index_01_' + side][:3, 3] - rest['pinky_01_' + side][:3, 3]
    radial = unit(radial - forward * (radial @ forward))
    dorsal = unit(np.cross(forward, radial))
    if dorsal @ np.asarray(anatomy[side]['dorsal']) < 0:
        dorsal *= -1.
    return np.column_stack((forward, radial, dorsal))


def solve_elbow(shoulder, wrist, pole, upper_length, lower_length):
    reach = wrist - shoulder
    distance = np.linalg.norm(reach)
    axis = unit(reach)
    along = (upper_length ** 2 - lower_length ** 2 + distance ** 2) / (2. * distance)
    side = unit(pole - shoulder - axis * ((pole - shoulder) @ axis))
    return shoulder + along * axis + math.sqrt(upper_length ** 2 - along ** 2) * side


def make_fists(rest, parents, names, anatomy, profile):
    left_names = [n for n in names if n.endswith('_l')]
    left = closed_pose(rest, parents, left_names, profile)
    left_frame = semantic_palm(rest, anatomy, 'l')
    right_frame = semantic_palm(rest, anatomy, 'r')
    palm_transfer = right_frame @ left_frame.T
    right = {n: m.copy() for n, m in rest.items()}
    for name in names:
        if not name.endswith('_r'):
            continue
        parent = parents[name]
        local = np.linalg.inv(rest[parent]) @ rest[name]
        right[name] = right[parent] @ local
        if name.startswith(('index_', 'middle_', 'ring_', 'pinky_', 'thumb_')):
            left_name = name[:-1] + 'l'
            deformation = left[left_name][:3, :3] @ rest[left_name][:3, :3].T
            right[name][:3, :3] = (palm_transfer @ deformation @ palm_transfer.T
                                     @ rest[name][:3, :3])
    world = {**rest, **{n: left[n] for n in left_names},
             **{n: right[n] for n in names if n.endswith('_r')}}
    return {n: np.linalg.inv(world[parents[n]]) @ world[n] for n in names}


def author_arm(rest, parent, names, anatomy, fist_local, side, placement):
    suffix = '_' + side
    clavicle, upper, lower, hand = [n + suffix for n in ('clavicle', 'upperarm', 'lowerarm', 'hand')]
    local = {n: np.linalg.inv(rest[parent[n]]) @ rest[n] for n in names}
    upper_rest = rest[lower][:3, 3] - rest[upper][:3, 3]
    lower_rest = rest[hand][:3, 3] - rest[lower][:3, 3]
    plane_rest = unit(np.cross(upper_rest, lower_rest))
    shoulder = np.asarray(placement['shoulder_cm'], dtype=float)
    wrist = np.asarray(placement['wrist_cm'], dtype=float)

    preferred = (limb_frame(placement['preferred_palm_forward'], placement['preferred_dorsal'])
                 @ limb_frame(anatomy[side]['forward'], anatomy[side]['dorsal']).T)
    pole = wrist - preferred @ lower_rest
    elbow = solve_elbow(shoulder, wrist, pole,
                        np.linalg.norm(upper_rest), np.linalg.norm(lower_rest))
    upper_axis, lower_axis = unit(elbow - shoulder), unit(wrist - elbow)
    plane = unit(np.cross(upper_axis, lower_axis))
    upper_rotation = (limb_frame(upper_axis, plane) @ limb_frame(upper_rest, plane_rest).T
                      @ rest[upper][:3, :3])
    hinge = rest[upper][:3, :3].T @ plane_rest
    flexion = (math.acos(np.clip(upper_axis @ lower_axis, -1., 1.))
               - math.acos(unit(upper_rest) @ unit(lower_rest)))
    lower_neutral = upper_rotation @ Rotation.from_rotvec(hinge * flexion).as_matrix() @ local[lower][:3, :3]
    palm_width = unit(rest['index_metacarpal' + suffix][:3, 3] - rest['pinky_metacarpal' + suffix][:3, 3])
    current_width = lower_neutral @ rest[lower][:3, :3].T @ palm_width
    goal_width = preferred @ palm_width
    current_width = unit(current_width - lower_axis * (current_width @ lower_axis))
    goal_width = unit(goal_width - lower_axis * (goal_width @ lower_axis))
    roll = math.atan2(lower_axis @ np.cross(current_width, goal_width), current_width @ goal_width)
    forearm_axis = unit(rest[lower][:3, :3].T @ lower_rest)
    lower_rotation = lower_neutral @ Rotation.from_rotvec(forearm_axis * roll).as_matrix()

    world = {n: m.copy() for n, m in rest.items()}
    # The shoulder remains behind the eye. The clavicle-to-shoulder vector is
    # the native one; translating the clavicle positions the complete arm.
    world[clavicle][:3, 3] = shoulder - rest[clavicle][:3, :3] @ local[upper][:3, 3]
    world[upper][:3, :3], world[upper][:3, 3] = upper_rotation, shoulder
    world[lower][:3, :3], world[lower][:3, 3] = lower_rotation, elbow
    # The fist inherits the complete native wrist relation. Its actual forward
    # direction comes from the low supported forearm, rather than forcing the
    # wrist sideways to match a separate hand-only camera rotation.
    world[hand] = world[lower] @ local[hand]
    for n in names:
        if not n.endswith(suffix) or n in (clavicle, upper, lower, hand):
            continue
        relative = fist_local[n] if n.startswith(('index_', 'middle_', 'ring_', 'pinky_', 'thumb_')) else local[n]
        world[n] = world[parent[n]] @ relative
    lower_deformation = lower_rotation @ rest[lower][:3, :3].T
    record = dict(shoulder_cm=shoulder.tolist(), wrist_cm=world[hand][:3, 3].tolist(),
                  elbow_cm=elbow.tolist(), elbow_pole_camera_cm=pole.tolist(),
                  upper_length_cm=float(np.linalg.norm(upper_rest)),
                  lower_length_cm=float(np.linalg.norm(lower_rest)),
                  hinge_upper_local=hinge.tolist(), elbow_flexion_offset_radians=flexion,
                  forearm_roll_radians=roll,
                  actual_palm_forward=(lower_deformation @ np.asarray(anatomy[side]['forward'])).tolist(),
                  actual_dorsal=(lower_deformation @ np.asarray(anatomy[side]['dorsal'])).tolist(),
                  wrist_contract='Unmodified native hand-to-lowerarm local transform')
    return {n: world[n] for n in names if n.endswith(suffix)}, record


def author():
    source = json.loads(SOURCE.read_text(encoding='utf-8-sig'))
    rest = {n: np.asarray(m, dtype=float) for n, m in source['rest'].items()}
    anatomy = json.loads(ANATOMY.read_text(encoding='utf-8-sig'))['anatomy']
    parent, names = source['parent'], source['order']
    profile = json.loads((FIST_DIR / 'fist-profile-v2.json').read_text(encoding='utf-8-sig'))
    fist_local = make_fists(rest, parent, names, anatomy, profile)
    placement = {
        'l': dict(shoulder_cm=[-7., -21., -26.], wrist_cm=[34., -15., -18.],
                  preferred_palm_forward=[.97, .08, .30], preferred_dorsal=[-.25, -.93, .28]),
        'r': dict(shoulder_cm=[-7., 21., -26.], wrist_cm=[35., 16., -19.],
                  preferred_palm_forward=[.97, -.08, .30], preferred_dorsal=[-.25, .93, .28])}
    exhale, anatomy_contract = {n: m.copy() for n, m in rest.items()}, {}
    for side in ('l', 'r'):
        arm, record = author_arm(rest, parent, names, anatomy, fist_local, side, placement[side])
        exhale.update(arm)
        anatomy_contract[side] = record
    inhale = {n: m.copy() for n, m in rest.items()}
    rotation = Rotation.from_rotvec(np.asarray([0., -math.radians(.18), 0.])).as_matrix()
    translation = np.asarray([.18, 0., .14])
    for side in ('l', 'r'):
        pivot = np.asarray(placement[side]['shoulder_cm'])
        for n in names:
            if not n.endswith('_' + side):
                continue
            inhale[n][:3, :3] = rotation @ exhale[n][:3, :3]
            inhale[n][:3, 3] = pivot + rotation @ (exhale[n][:3, 3] - pivot) + translation
    clips = []
    for name, seconds, world in [('Exhale', 0., exhale), ('Inhale', PERIOD * .5, inhale)]:
        local = {n: np.linalg.inv(world[parent[n]]) @ world[n] for n in names}
        clips.append(dict(name=name, time_seconds=seconds,
                          local={n: m.tolist() for n, m in local.items()},
                          component={n: world[n].tolist() for n in names}))
    data = dict(revision=REVISION, role='UnarmedClosedFistIdle', units='normalized native UE camera cm',
                source=SOURCE.relative_to(ROOT).as_posix(), skin='BarePalmV7/M4',
                order=names, parent=parent, rest=source['rest'], poses=clips,
                period_seconds=PERIOD, key_names=['Exhale', 'Inhale'], placement=placement,
                anatomy_contract=anatomy_contract,
                fist_profile=profile, fist_profile_source=(FIST_DIR / 'fist-profile-v2.json').relative_to(ROOT).as_posix(),
                right_fist_transfer='Left deformation conjugated through native forward/radial/dorsal palm frames; right local lengths retained',
                helper_contract='All upper/lower twist helpers retain complete native rest-local transforms',
                breathing=dict(weight='0.5 - 0.5*cos(2*pi*t/4.2)',
                               whole_chain_translation_cm=translation.tolist(),
                               whole_chain_pitch_degrees=-.18, pivot='Each native shoulder',
                               interpolation='UE shortest-path quaternion normalized lerp and position lerp'),
                bone_scaling=False, skin_changed=False, ue_animation_import_required=False,
                runtime_tested=False, rendered=False)
    (P / 'full-pose.json').write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    HEADER.parent.mkdir(parents=True, exist_ok=True)
    HEADER.write_text(header(data), encoding='utf-8')
    print('SAVED_UNARMED_IDLE_SOURCE', REVISION, len(names), 'bones, 2 endpoints, 4.2 second continuous breathing.', flush=True)
    print('AUTHORING_PLACEMENT', json.dumps(anatomy_contract), flush=True)


def header(data):
    def numbers(values):
        return ','.join(f'{float(v):.10f}' for v in values)
    lines = ['// Generated by SourceAssets/UnarmedIdle20261001/author_idle.py.',
             '// Complete native LOCAL transforms in normalized UE camera centimetres.',
             '// Runtime divides Position by the native parent reference scale.',
             '#pragma once', '#include "CoreMinimal.h"', 'namespace UnarmedAuthoredIdle20261001 {',
             f'inline constexpr int32 Revision={REVISION};',
             f'inline constexpr int32 KeyCount=2, BoneCount={len(data["order"])};',
             f'inline constexpr float PeriodSeconds={PERIOD:.10f}f;',
             'struct FBone { FQuat Rotation; FVector Position; };',
             'inline const TCHAR* Names[BoneCount]={']
    lines += [f'TEXT("{n}"),' for n in data['order']]
    lines += ['};', 'inline const FBone Poses[KeyCount][BoneCount]={']
    for pose in data['poses']:
        lines.append('{ // ' + pose['name'])
        for n in data['order']:
            m = np.asarray(pose['local'][n])
            lines.append('{FQuat(' + numbers(Rotation.from_matrix(m[:3, :3]).as_quat())
                         + '),FVector(' + numbers(m[:3, 3]) + ')},')
        lines.append('},')
    return '\n'.join(lines + ['};', '}', ''])


if __name__ == '__main__':
    author()
