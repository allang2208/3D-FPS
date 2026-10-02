"""Reuse the photographed guard with increased whole-arm sway, then recover.

The existing four-finger fist and neutral wrist remain copied; the three
thumb locals use the wrist/thumb revision. The shoulder and elbow are authored
together on native lengths and hinge, with palm roll carried by the forearm.
The exact complete current Prepare is copied at both hold endpoints.
Between them only the clavicle root translates: shoulder, elbow, wrist and
fist move as one rigid chain without changing any wrist or finger local.
There is no forward shove, contact brake or rebound pose.
Production only: no render, runtime test, engine launch or asset import.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation

sys.dont_write_bytecode = True
P = Path(__file__).resolve().parent
ROOT = P.parents[1]
REVISION = 2026100212
HEADER = ROOT / 'Source/FPSGAME/Movement/DoorPushAuthored20261002.h'
INPUT = ROOT / 'SourceAssets/StaffQuickCombat20261001/full-pose.json'
EXAMPLE_INPUT = ROOT / 'SourceAssets/UnarmedLocomotion20261001/full-pose.json'
GUARD_INPUT = P / 'GuardWristThumbV8_20261002/authored-guard.json'
TIMES = [0., .06, .1225, .185, .2475, .31, .507]
KEY_NAMES = ['CapturedEntryExample', 'Prepare', 'GuardSwayRight', 'GuardSwayLift',
             'GuardSwayLeft', 'GuardHoldEnd', 'CurrentGripExample']
SOURCE_KEYS = ['idle[0]'] + ['GuardWristThumbV8::Prepare'] * 5 + ['idle[0]']
SWAY_OFFSETS = [[0., 0., 0.], [0., 0., 0.], [0., .56, .20],
                [0., .08, .40], [0., -.32, .16], [0., 0., 0.], [0., 0., 0.]]
GUARD = dict(shoulder_cm=[-9., -20.8, -23.], wrist_cm=[23., -14., -5.],
             elbow_pole_cm=[12., -24., -47.], palm_normal_toward_camera=[-1., 0., 0.])
PHOTO = 'SourceAssets/DoorPush20261002/GuardPoseV4_20261002/Reference/user-left-fist-guard.jpg'


def unit(v):
    v = np.asarray(v, dtype=float)
    return v / np.linalg.norm(v)


def rigid_guard_sway(guard_local, guard_world, names, offset):
    """Translate the complete existing chain; preserve all child locals.

    Derive the actual clavicle-parent component transform from the copied
    key, so camera translation is converted into the correct parent space.
    No hinge solve, wrist turn, helper adjustment or bone scaling occurs.
    """
    offset = np.asarray(offset, dtype=float)
    local = {n: m.copy() for n, m in guard_local.items()}
    world = {n: guard_world[n].copy() for n in names}
    parent_world = guard_world['clavicle_l'] @ np.linalg.inv(guard_local['clavicle_l'])
    local['clavicle_l'][:3, 3] += np.linalg.solve(parent_world[:3, :3], offset)
    for n in names:
        world[n][:3, 3] += offset
    return local, world


def limb_frame(forward, across):
    x = unit(forward)
    y = unit(across - x * np.dot(x, across))
    return np.column_stack((x, y, np.cross(x, y)))


def raised_guard(rest, parent, names, ready, joint):
    """New whole-arm placement, existing native closed hand without refitting.

    The geometry and joint assembly follow UnarmedLocomotion's native_arm.
    Only clavicle/upper/lower arm locals change. The original Ready hand,
    all four native twist helpers and all 19 fist bones remain copied.
    The required palm-facing roll is on lowerarm_l, not an extra wrist turn.
    """
    local = {n: np.asarray(ready['local'][n], dtype=float).copy() for n in names}
    ready_world = {n: np.asarray(ready['component'][n], dtype=float) for n in names}
    shoulder = np.asarray(GUARD['shoulder_cm'])
    wrist = np.asarray(GUARD['wrist_cm'])
    pole = np.asarray(GUARD['elbow_pole_cm'])
    upper_rest = rest['lowerarm_l'][:3, 3] - rest['upperarm_l'][:3, 3]
    lower_rest = rest['hand_l'][:3, 3] - rest['lowerarm_l'][:3, 3]
    upper_length, lower_length = np.linalg.norm(upper_rest), np.linalg.norm(lower_rest)
    reach = wrist - shoulder
    distance, axis = np.linalg.norm(reach), unit(reach)
    along = (upper_length**2 - lower_length**2 + distance**2) / (2. * distance)
    bend = unit(pole - shoulder - axis * np.dot(pole - shoulder, axis))
    elbow = shoulder + axis * along + bend * math.sqrt(upper_length**2 - along**2)
    upper_axis, lower_axis = unit(elbow - shoulder), unit(wrist - elbow)
    plane_rest = unit(np.cross(upper_rest, lower_rest))
    plane = unit(np.cross(upper_axis, lower_axis))
    upper_rotation = (limb_frame(upper_axis, plane) @ limb_frame(upper_rest, plane_rest).T
                      @ rest['upperarm_l'][:3, :3])
    hinge, forearm_axis = np.asarray(joint['elbow_hinge']), np.asarray(joint['forearm_axis'])
    flex = (math.acos(np.clip(upper_axis @ lower_axis, -1., 1.))
            - math.acos(np.clip(unit(upper_rest) @ unit(lower_rest), -1., 1.)))
    native_lower_rotation = np.asarray(joint['lower_rest_rotation'])
    neutral = upper_rotation @ Rotation.from_rotvec(hinge * flex).as_matrix() @ native_lower_rotation

    # Frame the complete forearm/neutral hand by the photographed palm side.
    ready_axis = unit(ready_world['hand_l'][:3, 3] - ready_world['lowerarm_l'][:3, 3])
    ready_normal = np.asarray(contact(ready_world, rest)['palm_normal'])
    preferred = (limb_frame(lower_axis, np.asarray(GUARD['palm_normal_toward_camera']))
                 @ limb_frame(ready_axis, ready_normal).T @ ready_world['lowerarm_l'][:3, :3])
    across = unit(rest['index_metacarpal_l'][:3, 3] - rest['pinky_metacarpal_l'][:3, 3])
    current = neutral @ rest['lowerarm_l'][:3, :3].T @ across
    goal = preferred @ rest['lowerarm_l'][:3, :3].T @ across
    current = unit(current - lower_axis * (current @ lower_axis))
    goal = unit(goal - lower_axis * (goal @ lower_axis))
    roll = math.atan2(lower_axis @ np.cross(current, goal), current @ goal)
    lower_local = (Rotation.from_rotvec(hinge * flex).as_matrix() @ native_lower_rotation
                   @ Rotation.from_rotvec(forearm_axis * roll).as_matrix())
    world = {n: m.copy() for n, m in rest.items()}
    clavicle_rotation = ready_world['clavicle_l'][:3, :3]
    clavicle_position = shoulder - clavicle_rotation @ local['upperarm_l'][:3, 3]
    clavicle_world = np.eye(4)
    clavicle_world[:3, :3], clavicle_world[:3, 3] = clavicle_rotation, clavicle_position
    local['clavicle_l'] = np.linalg.inv(rest[parent['clavicle_l']]) @ clavicle_world
    local['upperarm_l'][:3, :3] = clavicle_rotation.T @ upper_rotation
    local['lowerarm_l'][:3, :3] = lower_local
    for n in names:
        world[n] = world[parent[n]] @ local[n]
    record = dict(GUARD)
    record.update(elbow_cm=world['lowerarm_l'][:3, 3].tolist(),
                  actual_wrist_cm=world['hand_l'][:3, 3].tolist(),
                  elbow_flexion_offset_radians=flex, forearm_roll_radians=roll,
                  authored_geometry='Native two-bone length and fixed hinge; forearm carries palm-facing roll',
                  unchanged_local_bones=[n for n in names if n not in ('clavicle_l','upperarm_l','lowerarm_l')])
    return local, world, record


def describe_lower(local, joint):
    """Describe, never replace, the existing source's lower-arm rotation.

    A best fit to the existing native hinge/roll model records its residual.
    The staff action is not constrained to that model. Its complete source
    rotation remains authoritative and is interpolated directly by slerp.
    """
    target = local['lowerarm_l'][:3, :3]
    hinge = np.asarray(joint['elbow_hinge'])
    axis = np.asarray(joint['forearm_axis'])
    rest = np.asarray(joint['lower_rest_rotation'])

    def residual(x):
        fitted = (Rotation.from_rotvec(hinge*x[0]).as_matrix() @ rest
                  @ Rotation.from_rotvec(axis*x[1]).as_matrix())
        return Rotation.from_matrix(fitted.T @ target).as_rotvec()

    fit = least_squares(residual, [0., 0.])
    return dict(elbow_flexion_offset_radians=float(fit.x[0]),
                forearm_roll_radians=float(fit.x[1]),
                native_hinge_model_residual_radians=float(np.linalg.norm(fit.fun)),
                source_local_rotation_authoritative=True,
                lowerarm_interpolation='Direct shortest-path source-local quaternion slerp')


def contact(world, rest):
    origin = rest['hand_l'][:3, 3]
    forward = unit(rest['middle_01_l'][:3, 3] - origin)
    normal = unit(np.cross(rest['index_01_l'][:3, 3] - origin,
                           rest['pinky_01_l'][:3, 3] - origin))
    deform = world['hand_l'][:3, :3] @ rest['hand_l'][:3, :3].T
    return dict(shoulder_cm=world['upperarm_l'][:3, 3].tolist(),
                wrist_cm=world['hand_l'][:3, 3].tolist(),
                elbow_pole_cm=world['lowerarm_l'][:3, 3].tolist(),
                elbow_cm=world['lowerarm_l'][:3, 3].tolist(),
                palm_forward=(deform @ forward).tolist(),
                palm_normal=(deform @ normal).tolist(),
                hand_rotation_xyzw=Rotation.from_matrix(world['hand_l'][:3, :3]).as_quat().tolist())


def header(data):
    def numbers(v):
        return ','.join(f'{float(x):.10f}' for x in v)
    def vec(v):
        return 'FVector(' + numbers(v) + ')'
    def quat(q):
        return 'FQuat(' + numbers(q) + ')'
    j = data['joint_definition']
    lines = ['// Generated by SourceAssets/DoorPush20261002/author_motion.py.',
             '// Existing raised guard, 250ms increased rigid whole-arm sway, then current live grip recovery.',
             '// Camera keys use UE centimetres (+X forward, +Y right, +Z up).',
             '// Raised guard authored offline on native hinge/lengths. No runtime IK or hand-shape reconstruction.',
             '// Runtime captures live entry and live recovery.',
             '#pragma once', '#include "CoreMinimal.h"',
             'namespace DoorPushAuthored20261002 {',
             f'inline constexpr int32 Revision={REVISION};',
             f'inline constexpr int32 KeyCount={len(TIMES)}, BoneCount={len(data["order"])};',
             'inline constexpr float DurationSeconds=.507f, PrepareSeconds=.06f, ContactSeconds=.31f;',
             'inline constexpr float HoldSeconds=.25f, PushStartSeconds=.31f;',
             'inline constexpr float ContactBrakeSeconds=.31f, ReboundSeconds=.0f;',
             'inline constexpr float RecoverStartSeconds=.31f, RecoverySeconds=.197f, BlendInSeconds=.06f;',
             'inline constexpr float FistCloseStartSeconds=.0f, FistCloseEndSeconds=.06f;',
             'inline constexpr bool FistUsesUnarmedIdleLocal=false;',
             'inline constexpr bool FullActionUsesStaffQuickCombat=true;',
             'inline constexpr bool PrepareUsesPhotoRaisedGuard=true;',
             'inline constexpr bool UsesForwardPush=false, UsesContactBrake=false, UsesShortRebound=false;',
             'inline constexpr bool UsesWholeArmGuardSway=true;',
             'inline constexpr float GuardSwaySideMaxCm=.56f, GuardSwayUpMaxCm=.40f;',
             'inline constexpr bool LowerUsesNativeJointScalars=false;',
             '// Joints are source diagnostics; source lower-arm locals include another swing component.',
             '// Never reconstruct this action from the hinge/roll approximation.',
             'struct FContact { FVector Shoulder,Wrist,Pole,PalmForward,PalmNormal; FQuat HandRotation; };',
             'struct FBone { FQuat Rotation; FVector Position; };',
             'struct FJoint { double Flex,Roll; };',
             'inline constexpr float Times[KeyCount]={' + ','.join(f'{t:.10f}f' for t in TIMES) + '};',
             'inline const TCHAR* KeyNames[KeyCount]={']
    lines += ['TEXT("' + n + '"),' for n in KEY_NAMES]
    lines += ['};', 'inline const FContact Contacts[KeyCount]={']
    for p in data['poses']:
        c = p['contact']
        lines += ['{' + ','.join(vec(c[n]) for n in ('shoulder_cm','wrist_cm','elbow_pole_cm','palm_forward','palm_normal'))
                  + ',' + quat(c['hand_rotation_xyzw']) + '},']
    lines += ['};',
              'inline const FQuat LowerRestRotation=' + quat(Rotation.from_matrix(j['lower_rest_rotation']).as_quat()) + ';',
              'inline const FVector ElbowHinge=' + vec(j['elbow_hinge']) + ';',
              'inline const FVector ForearmAxis=' + vec(j['forearm_axis']) + ';',
              'inline const FJoint Joints[KeyCount]={']
    for p in data['poses']:
        a = p['anatomy']
        lines += ['{' + f'{a["elbow_flexion_offset_radians"]:.10f},{a["forearm_roll_radians"]:.10f}' + '},']
    lines += ['};', 'inline constexpr double LowerSourceResidualRadians[KeyCount]={']
    lines += [f'{p["anatomy"]["native_hinge_model_residual_radians"]:.10f},' for p in data['poses']]
    lines += ['};', 'inline const TCHAR* Names[BoneCount]={']
    lines += ['TEXT("' + n + '"),' for n in data['order']]
    lines += ['};', 'inline const FBone Poses[KeyCount][BoneCount]={']
    for p in data['poses']:
        lines += ['{ // ' + p['name'] + ': ' + p['source_key']]
        for n in data['order']:
            m = np.asarray(p['local'][n])
            lines += ['{' + quat(Rotation.from_matrix(m[:3, :3]).as_quat()) + ',' + vec(m[:3, 3]) + '},']
        lines += ['},']
    lower_index = data['order'].index('lowerarm_l')
    lines += ['};',
              'inline float Ease(float T) {T=FMath::Clamp(T,0.f,1.f);return T*T*T*(T*(T*6.f-15.f)+10.f);}',
              '// Entry, gentle whole-arm sway and recovery use quintic interpolation.',
              'inline float SegmentBlend(int32 Segment,float T) {',
              ' T=FMath::Clamp(T,0.f,1.f);',
              ' return Ease(T);', '}',
              'inline float MotionBlend(float Age) {',
              ' if(Age<=Times[0]) return 0.f;',
              ' if(Age>=Times[KeyCount-1]) return float(KeyCount-1);',
              ' for(int32 A=0;A<KeyCount-1;++A) if(Age<Times[A+1])',
              '  return float(A)+SegmentBlend(A,(Age-Times[A])/(Times[A+1]-Times[A]));',
              ' return float(KeyCount-1);', '}',
              'inline FQuat LowerRotation(int32 A,int32 B,float Alpha) {',
              f' return FQuat::Slerp(Poses[A][{lower_index}].Rotation,Poses[B][{lower_index}].Rotation,Alpha).GetNormalized();',
              '}', '}', '']
    return '\n'.join(lines)


def author():
    source = json.loads(INPUT.read_text(encoding='utf-8'))
    example = json.loads(EXAMPLE_INPUT.read_text(encoding='utf-8'))
    rest = {n: np.asarray(m, dtype=float) for n, m in source['rest'].items()}
    parent, names = source['parent'], source['order']
    idle = example['idle'][0]
    entry_world = {n: m.copy() for n, m in rest.items()}
    entry_world.update({n: np.asarray(m, dtype=float) for n, m in idle['component'].items()})
    by_name = {p['name']: p for p in source['poses']}
    joint = example['joint_definitions']['l']
    # Preserve the exact current pose, including every helper and finger local.
    # Sway the complete current guard without solving/refitting wrist or fist.
    previous = json.loads(GUARD_INPUT.read_text(encoding='utf-8'))
    guard = next(p for p in previous['poses'] if p['name'] == 'Prepare')
    guard_local = {n: np.asarray(guard['local'][n], dtype=float).copy() for n in names}
    guard_world = {n: np.asarray(guard['component'][n], dtype=float).copy() for n in names}
    guard_record = previous['photo_guard']
    poses = []
    for name, age, source_key, sway_offset in zip(KEY_NAMES, TIMES, SOURCE_KEYS, SWAY_OFFSETS):
        if source_key == 'idle[0]':
            local = {n: np.asarray(idle['local'][n], dtype=float).copy() for n in names}
            world = {n: entry_world[n].copy() for n in names}
        elif source_key == 'GuardWristThumbV8::Prepare':
            local, world = rigid_guard_sway(guard_local, guard_world, names, sway_offset)
        record = describe_lower(local, joint)
        c = contact(world, rest)
        record.update({k: c[k] for k in ('shoulder_cm', 'wrist_cm', 'elbow_cm', 'elbow_pole_cm')})
        poses.append(dict(name=name, time_seconds=age, source_key=source_key,
                          guard_sway_camera_offset_cm=sway_offset,
                          local={n: m.tolist() for n, m in local.items()},
                          component={n: m.tolist() for n, m in world.items()},
                          contact=c, anatomy=record))
    fist_names = [n for n in names if n.startswith(('index_', 'middle_', 'ring_', 'pinky_', 'thumb_'))]
    ready = by_name['Ready']
    data = dict(revision=REVISION, role='DoorPushLeftClosedFist',
                units='normalized native UE camera centimetres',
                source=INPUT.relative_to(ROOT).as_posix(), source_revision=source['revision'],
                skin='BarePalmV7/M4; existing bind and skin preserved',
                order=names, parent=parent, rest=source['rest'], poses=poses,
                all_order=example['order'],
                example_base_component={n: m.tolist() for n, m in entry_world.items()},
                times=TIMES, key_names=KEY_NAMES, source_keys=SOURCE_KEYS,
                duration_seconds=.507, prepare_seconds=.06, hold_seconds=.25,
                push_start_seconds=.31, contact_seconds=.31, contact_brake_seconds=.31,
                rebound_seconds=.0, recover_start_seconds=.31,
                recovery_seconds=.197, blend_in_seconds=.06,
                uses_forward_push=False, uses_contact_brake=False, uses_short_rebound=False,
                guard_pose_source=GUARD_INPUT.relative_to(ROOT).as_posix() + '::Prepare',
                guard_pose_source_revision=previous['revision'],
                photo_guard=guard_record, reference_photo=PHOTO,
                guard_sway=dict(enabled=True, hold_start_seconds=.06, hold_end_seconds=.31,
                                times_seconds=TIMES[1:-1],
                                offsets_camera_cm=SWAY_OFFSETS[1:-1],
                                side_max_cm=.56, up_max_cm=.40, forward_max_cm=0.,
                                rotation_degrees=0.,
                                method='Camera-space rigid translation at clavicle root; entire left arm moves together',
                                unchanged_child_locals=[n for n in names if n != 'clavicle_l'],
                                root_rotation_unchanged=True, bone_length_unchanged=True,
                                wrist_rotation_unchanged=True, helper_locals_unchanged=True,
                                finger_locals_unchanged=True, endpoints_zero_offset=True),
                reference_interpretation='Left closed fist raised in front of body; palm/curl side faces player, fingers fully collected, thumb over index/middle exterior, neutral wrist and elbow down',
                joint_definition=joint, lower_uses_native_joint_scalars=False,
                fist_source='Existing complete 27-bone guard with revised three-bone thumb opposition and neutral hand_l; clavicle-only rigid sway',
                fist_source_json=GUARD_INPUT.relative_to(ROOT).as_posix() + '::poses[Prepare]',
                fist_source_revision=source['revision'], fist_bones=fist_names,
                fist_local={n: guard['local'][n] for n in fist_names},
                thumb_opposition=previous['thumb_opposition'],
                door_guard_thumb_patch=previous['door_guard_thumb_patch'],
                helper_contract='Original complete source upper/lower twist-helper local and CS transforms copied with their parent chain',
                wrist_contract='Original StaffQuickCombat hand_l local copied at each source key; guard palm-facing rotation carried by the complete forearm, no independent wrist turn',
                lowerarm_interpolation='Direct source-local shortest-path quaternion slerp; Joints are only a best-fit diagnostic and are not reconstructed',
                other_bone_interpolation='Prepare/recover quintic ease; hold sway changes only clavicle translation; source-local quaternion slerp and position lerp, one FK',
                segment_curve=['quintic_ease'] + ['quintic_rigid_guard_sway'] * 4 + ['quintic_recover'],
                entry_contract='Runtime captures current weapon or unarmed left chain; key zero is only a copied editable UnarmedLocomotion idle example',
                recovery_contract='Recover directly from the unchanged guard chain to the current live grip during .31-.507s; no frozen entry reapplication',
                fist_clock=dict(close_start=.0, close_end=.06,
                                source='Photo-raised whole-arm guard; revised thumb opposition, existing four-finger fist, neutral wrist and native helpers',
                                hold='.06 to .31: raised guard held for a full .25 seconds with doubled rigid whole-arm lateral/vertical sway',
                                recovery='Recover whole copied source chain to current live pose during .197s'),
                impact_contract='At .31s one door transition after a full .25s raised guard hold; no forward movement, braking or rebound pose; existing contact audio and camera shake share this runtime clock',
                forward_wrist_displacement_cm=0.,
                full_action_transfer='Existing complete raised guard and rigid sway with revised three-bone thumb opposition; direct recovery to current live grip',
                fist_acceptance='Existing game staff quick-punch source reused; this door adaptation has not been user-tested or newly accepted',
                reference_url='https://www.bilibili.com/video/BV17HSbBvE3M/',
                bone_scaling=False, skin_changed=False, runtime_tested=False, rendered=False)
    (P / 'full-pose.json').write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    (P / 'authored-parameters.json').write_text(json.dumps({k: v for k, v in data.items()
                                                           if k not in ('rest','parent','poses','example_base_component')}, indent=2) + '\n', encoding='utf-8')
    HEADER.write_text(header(data), encoding='utf-8')
    for p in poses:
        print('AUTHORED_DOOR_PUSH_REUSED_KEY', p['name'], p['time_seconds'], p['source_key'],
              'wrist', p['contact']['wrist_cm'],
              'source_lower_hinge_fit_residual', p['anatomy']['native_hinge_model_residual_radians'], flush=True)
    print('DOOR_PUSH_FULL_ACTION_SOURCE_SAVED', REVISION, len(names), 'native left bones', len(poses), 'keys', flush=True)


if __name__ == '__main__':
    author()
