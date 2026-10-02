"""Author V7 closed-fist idle and bilateral distance-phase locomotion.

Production source generation only. Camera +X forward, +Y right, +Z up (cm).
The staff V16 free-left shoulder, wrist and elbow timing supplies the gait.
Both arms are solved on their native lengths and elbow hinge. Right-hand
orientation is transferred through native palm semantics and a camera-space
reflection; no reflected bone transform or negative mesh scale is published.
"""
import importlib.util
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation

P = Path(__file__).resolve().parent
ROOT = P.parents[1]
SOURCE = ROOT / 'SourceAssets/UnarmedIdle20261001/full-pose.json'
GAIT_SOURCE = ROOT / 'SourceAssets/ApprenticeStaff20260927/LeftGaitV16/left-gait.json'
HEADER = ROOT / 'Source/FPSGAME/Weapons/Unarmed/UnarmedAuthoredLocomotion20261001.h'
REVISION = 2026100101
SAMPLES = 32
PERIOD = 4.2
SIDES = ('l', 'r')
REFLECTION = np.diag([1., -1., 1.])

# The historical author modules are read-only inputs for this new source.
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location('idle_author_source', SOURCE.parent / 'author_idle.py')
idle_author = importlib.util.module_from_spec(spec)
spec.loader.exec_module(idle_author)
unit = idle_author.unit
frame = idle_author.limb_frame


def native_arm(rest, parent, names, anatomy, fist_local, side, shoulder, wrist,
               pole, preferred_lower, wrist_turn):
    """Two-bone geometry, native hinge flex, then axial forearm roll."""
    suffix = '_' + side
    clavicle, upper, lower, hand = [n + suffix for n in ('clavicle', 'upperarm', 'lowerarm', 'hand')]
    local = {n: np.linalg.inv(rest[parent[n]]) @ rest[n] for n in names}
    upper_rest = rest[lower][:3, 3] - rest[upper][:3, 3]
    lower_rest = rest[hand][:3, 3] - rest[lower][:3, 3]
    plane_rest = unit(np.cross(upper_rest, lower_rest))
    elbow = idle_author.solve_elbow(shoulder, wrist, pole,
                                    np.linalg.norm(upper_rest), np.linalg.norm(lower_rest))
    upper_axis, lower_axis = unit(elbow - shoulder), unit(wrist - elbow)
    plane = unit(np.cross(upper_axis, lower_axis))
    upper_rotation = frame(upper_axis, plane) @ frame(upper_rest, plane_rest).T @ rest[upper][:3, :3]
    hinge = rest[upper][:3, :3].T @ plane_rest
    flex = (math.acos(np.clip(upper_axis @ lower_axis, -1., 1.))
            - math.acos(np.clip(unit(upper_rest) @ unit(lower_rest), -1., 1.)))
    neutral = upper_rotation @ Rotation.from_rotvec(hinge * flex).as_matrix() @ local[lower][:3, :3]
    across = unit(rest['index_metacarpal' + suffix][:3, 3] - rest['pinky_metacarpal' + suffix][:3, 3])
    current = neutral @ rest[lower][:3, :3].T @ across
    goal = preferred_lower @ rest[lower][:3, :3].T @ across
    current = unit(current - lower_axis * (current @ lower_axis))
    goal = unit(goal - lower_axis * (goal @ lower_axis))
    roll = math.atan2(lower_axis @ np.cross(current, goal), current @ goal)
    # Gait palm orientation is carried by the forearm. The wrist only retains
    # the source's small passive flex/deviation, rather than compensating for
    # a different elbow plane with a new, large independent wrist turn.
    forearm_axis = unit(rest[lower][:3, :3].T @ lower_rest)
    lower_rotation = neutral @ Rotation.from_rotvec(forearm_axis * roll).as_matrix()
    lower_deformation = lower_rotation @ rest[lower][:3, :3].T
    world = {n: m.copy() for n, m in rest.items()}
    world[clavicle][:3, 3] = shoulder - rest[clavicle][:3, :3] @ local[upper][:3, 3]
    world[upper][:3, :3], world[upper][:3, 3] = upper_rotation, shoulder
    world[lower][:3, :3], world[lower][:3, 3] = lower_rotation, elbow
    world[hand] = world[lower] @ local[hand]
    world[hand][:3, :3] = lower_deformation @ wrist_turn @ rest[hand][:3, :3]
    for n in names:
        if not n.endswith(suffix) or n in (clavicle, upper, lower, hand):
            continue
        relative = fist_local[n] if n.startswith(('index_', 'middle_', 'ring_', 'pinky_', 'thumb_')) else local[n]
        world[n] = world[parent[n]] @ relative
    record = dict(shoulder_cm=shoulder.tolist(), wrist_cm=world[hand][:3, 3].tolist(),
                  elbow_cm=elbow.tolist(), elbow_pole_cm=pole.tolist(),
                  elbow_flexion_offset_radians=flex, forearm_roll_radians=roll)
    return {n: world[n] for n in names if n.endswith(suffix)}, record


def packet(world, rest, parent, names, role, joints):
    return dict(name=role, local={n: (np.linalg.inv(world[parent[n]]) @ world[n]).tolist() for n in names},
                component={n: world[n].tolist() for n in names}, anatomy=joints)


def header(data):
    def numbers(v):
        return ','.join(f'{float(x):.10f}' for x in v)
    def quat(matrix):
        return 'FQuat(' + numbers(Rotation.from_matrix(matrix).as_quat()) + ')'
    def pose_lines(pose):
        lines = ['{ // ' + pose['name']]
        for n in data['order']:
            m = np.asarray(pose['local'][n])
            lines.append('{' + quat(m[:3, :3]) + ',FVector(' + numbers(m[:3, 3]) + ')},')
        return lines + ['},']
    lines = ['// Generated by SourceAssets/UnarmedLocomotion20261001/author_locomotion.py.',
             '// Complete native LOCAL pose; Position divided by native parent ref scale at runtime.',
             '// Lowerarm interpolation uses weighted flex/roll scalars, then the native hinge assembly.',
             '#pragma once', '#include "CoreMinimal.h"', 'namespace UnarmedAuthoredLocomotion20261001 {',
             f'inline constexpr int32 Revision={REVISION};',
             f'inline constexpr int32 BoneCount={len(data["order"])}, Samples={SAMPLES}, IdleKeyCount=2;',
             f'inline constexpr float PeriodSeconds={PERIOD:.10f}f;',
             'struct FBone { FQuat Rotation; FVector Position; };',
             'struct FJoint { double Flex; double Roll; };',
             'struct FJointDefinition { FQuat LowerRestRotation; FVector ElbowHinge; FVector ForearmAxis; };',
             '// Side 0=left, 1=right. Cycle 0=Walk, 1=Run; right already offset by PI.',
             'inline const TCHAR* Names[BoneCount]={']
    lines += [f'TEXT("{n}"),' for n in data['order']]
    lines += ['};', 'inline const FJointDefinition JointDefinitions[2]={']
    for s in SIDES:
        j = data['joint_definitions'][s]
        lines += ['{' + quat(np.asarray(j['lower_rest_rotation'])) + ',FVector(' + numbers(j['elbow_hinge'])
                  + '),FVector(' + numbers(j['forearm_axis']) + ')},']
    lines += ['};', 'inline const FBone Idle[IdleKeyCount][BoneCount]={']
    for p in data['idle']:
        lines += pose_lines(p)
    lines += ['};', 'inline const FBone Cycles[2][Samples][BoneCount]={']
    for role in ('Walk', 'Run'):
        lines += ['{ // ' + role]
        for p in data['cycles'][role]:
            lines += pose_lines(p)
        lines += ['},']
    lines += ['};', 'inline const FJoint IdleJoints[IdleKeyCount][2]={']
    for p in data['idle']:
        lines += ['{' + ','.join('{' + f'{p["anatomy"][s]["elbow_flexion_offset_radians"]:.10f},{p["anatomy"][s]["forearm_roll_radians"]:.10f}' + '}' for s in SIDES) + '},']
    lines += ['};', 'inline const FJoint CycleJoints[2][Samples][2]={']
    for role in ('Walk', 'Run'):
        lines += ['{ // ' + role]
        for p in data['cycles'][role]:
            lines += ['{' + ','.join('{' + f'{p["anatomy"][s]["elbow_flexion_offset_radians"]:.10f},{p["anatomy"][s]["forearm_roll_radians"]:.10f}' + '}' for s in SIDES) + '},']
        lines += ['},']
    return '\n'.join(lines + ['};', '}', ''])


def author():
    old = json.loads(SOURCE.read_text(encoding='utf-8-sig'))
    gait = json.loads(GAIT_SOURCE.read_text(encoding='utf-8-sig'))
    anatomy = json.loads(idle_author.ANATOMY.read_text(encoding='utf-8-sig'))['anatomy']
    rest = {n: np.asarray(m, dtype=float) for n, m in old['rest'].items()}
    names, parents = old['order'], old['parent']
    profile = old['fist_profile']
    fist_local = idle_author.make_fists(rest, parents, names, anatomy, profile)
    placement = {s: dict(old['placement'][s]) for s in SIDES}
    for s in SIDES:
        placement[s]['wrist_cm'] = list(placement[s]['wrist_cm'])
        placement[s]['wrist_cm'][0] -= 5.
    exhale, idle_records = {n: m.copy() for n, m in rest.items()}, {}
    for s in SIDES:
        arm, record = idle_author.author_arm(rest, parents, names, anatomy, fist_local, s, placement[s])
        exhale.update(arm)
        idle_records[s] = record
    inhale = {n: m.copy() for n, m in exhale.items()}
    turn = Rotation.from_rotvec([0., -math.radians(.18), 0.]).as_matrix()
    shift = np.asarray([.18, 0., .14])
    for s in SIDES:
        pivot = np.asarray(placement[s]['shoulder_cm'])
        for n in names:
            if n.endswith('_' + s):
                inhale[n][:3, :3] = turn @ exhale[n][:3, :3]
                inhale[n][:3, 3] = pivot + turn @ (exhale[n][:3, 3] - pivot) + shift
    idle = [packet(exhale, rest, parents, names, 'Exhale', idle_records),
            packet(inhale, rest, parents, names, 'Inhale', idle_records)]
    palms = {s: idle_author.semantic_palm(rest, anatomy, s) for s in SIDES}
    palm_transfer = palms['r'] @ palms['l'].T
    cycles = {}
    for role in ('Walk', 'Run'):
        frames = []
        for sample in range(SAMPLES):
            world = {n: m.copy() for n, m in rest.items()}
            records = {}
            for s in SIDES:
                i = sample if s == 'l' else (sample + SAMPLES // 2) % SAMPLES
                src = {n: np.asarray(m) for n, m in gait['cycles'][role][i]['component'].items()}
                shoulder, elbow, wrist = [src[n + '_l'][:3, 3] for n in ('upperarm', 'lowerarm', 'hand')]
                lower_deformation = src['lowerarm_l'][:3, :3] @ rest['lowerarm_l'][:3, :3].T
                hand_deformation = src['hand_l'][:3, :3] @ rest['hand_l'][:3, :3].T
                wrist_turn = lower_deformation.T @ hand_deformation
                preferred = src['lowerarm_l'][:3, :3]
                if s == 'r':
                    shoulder, elbow, wrist = [REFLECTION @ v for v in (shoulder, elbow, wrist)]
                    # Reflection in camera space combined with the native
                    # opposite palm frame gives a proper right-arm rotation.
                    deformation = REFLECTION @ lower_deformation @ palms['l'] @ palms['r'].T
                    preferred = deformation @ rest['lowerarm_r'][:3, :3]
                    wrist_turn = palm_transfer @ wrist_turn @ palm_transfer.T
                arm, record = native_arm(rest, parents, names, anatomy, fist_local, s,
                                         shoulder, wrist, elbow, preferred, wrist_turn)
                world.update(arm)
                records[s] = record
            frames.append(packet(world, rest, parents, names, f'{role}_{sample:02d}', records))
        # Represent the axial angle on a continuous branch through the stride
        # and near the idle branch; weighted scalar interpolation must never
        # turn a harmless +/-PI representation boundary into an arm flip.
        for s in SIDES:
            rolls = np.unwrap([p['anatomy'][s]['forearm_roll_radians'] for p in frames])
            offset = math.tau * round((idle_records[s]['forearm_roll_radians'] - float(np.mean(rolls))) / math.tau)
            for p, roll in zip(frames, rolls + offset):
                p['anatomy'][s]['forearm_roll_radians'] = float(roll)
        cycles[role] = frames
    definitions = {}
    for s in SIDES:
        upper, lower, hand = ['upperarm_' + s, 'lowerarm_' + s, 'hand_' + s]
        u = rest[lower][:3, 3] - rest[upper][:3, 3]
        l = rest[hand][:3, 3] - rest[lower][:3, 3]
        definitions[s] = dict(lower_rest_rotation=(rest[upper][:3, :3].T @ rest[lower][:3, :3]).tolist(),
                              elbow_hinge=(rest[upper][:3, :3].T @ unit(np.cross(u, l))).tolist(),
                              forearm_axis=unit(rest[lower][:3, :3].T @ l).tolist())
    data = dict(revision=REVISION, role='UnarmedClosedFistLocomotion', units='normalized native UE camera cm',
                source=SOURCE.relative_to(ROOT).as_posix(), gait_source=GAIT_SOURCE.relative_to(ROOT).as_posix(),
                order=names, parent=parents, rest=old['rest'], idle=idle, cycles=cycles,
                period_seconds=PERIOD, samples_per_stride=SAMPLES, placement=placement,
                previous_idle_wrist_cm={s: old['placement'][s]['wrist_cm'] for s in SIDES},
                new_idle_wrist_cm={s: placement[s]['wrist_cm'] for s in SIDES},
                joint_definitions=definitions, fist_profile=profile,
                phase_clock='UFPSFootstepAudioComponent::GetStridePhaseRadians',
                right_phase_offset_radians=math.pi,
                right_arm_transfer='Camera Y reflection + native palm semantic frame, native right hinge/lengths, PI phase offset',
                helper_contract='Complete native rest-local for all upper/lower twist helpers',
                lowerarm_interpolation='Weighted flex/roll then Q(hinge,flex)*LowerRest*Q(forearmAxis,roll)',
                other_bone_interpolation='Shortest-path quaternion normalized lerp and local position lerp',
                gait_sampling='fractional = positive_mod(phase/TAU,1)*Samples; a=floor, b=(a+1)%Samples; alpha=frac',
                pose_weights='Idle*(1-Move) + Walk*Move*(1-Run) + Run*Move*Run; each cycle sampled at the same stride phase',
                skin='Accepted BarePalmV7/M4, native bind and skin retained',
                bone_scaling=False, skin_changed=False, ue_animation_import_required=False,
                rendered=False, runtime_tested=False)
    (P / 'full-pose.json').write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    parameters = {k: data[k] for k in ('revision', 'source', 'gait_source', 'period_seconds', 'samples_per_stride',
                 'placement', 'previous_idle_wrist_cm', 'new_idle_wrist_cm', 'joint_definitions', 'phase_clock',
                 'right_phase_offset_radians', 'right_arm_transfer', 'helper_contract', 'lowerarm_interpolation',
                 'other_bone_interpolation', 'gait_sampling', 'pose_weights', 'rendered', 'runtime_tested')}
    (P / 'authored-parameters.json').write_text(json.dumps(parameters, indent=2) + '\n', encoding='utf-8')
    HEADER.parent.mkdir(parents=True, exist_ok=True)
    HEADER.write_text(header(data), encoding='utf-8')
    print('SAVED_UNARMED_LOCOMOTION_SOURCE', REVISION, len(names), 'bones; 2 idle endpoints, 2 x 32 bilateral gait poses.', flush=True)
    print('AUTHORING_IDLE_WRISTS', json.dumps(data['new_idle_wrist_cm']), flush=True)


if __name__ == '__main__':
    author()
