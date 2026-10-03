"""Restore the weight-transfer and fast crossing of the real HundredEyed sweep.

The real Epic Rampage Attack_Biped_Melee_A is the motion reference used by
HundredEyedSlag's formal AttackSweep_R. Its windup, shoulder/elbow/wrist arc,
body rotation and follow-through are sampled, time-shaped and adapted to the
original M07's 83 fixed-length bones. The original Meshy geometry, UVs, skin
and reference pose are retained here; the separate V16 arm solve owns skin.
Only two animation FBXs are exported. No UE/game/render/test is launched.
"""
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Quaternion, Vector

PROJECT = Path('D:/FPS3D/FPSGAME')
ROOT = PROJECT/'SourceAssets/BlindSupplicantM07Meshy20261001'
OUT = ROOT/'ArmSweepV16/Motion'
MASTER = ROOT/'MotionRecoveryV15/LocomotionDeath/M07_Original_LocomotionDeath_V15.blend'
CAST_MASTER = ROOT/'MotionRecoveryV15/Casting/M07_Original_Casting_Anatomical_V15.blend'
DONOR = PROJECT/'SourceAssets/HundredEyedSlagMeshy20260930/RampageReferenceIntake/source_motion'
FPS = 30
UP, RIGHT, FWD = Vector((0, 0, 1)), Vector((1, 0, 0)), Vector((0, -1, 0))
sys.path.insert(0, str(Path(__file__).parent))
import author_motion_v04 as motion
from author_sweep_cast_v14 import export, read_donor, sample_donor, palm_frame
from author_cast_v15 import base_pose, pole_from_pose, solve_segments, signed_angle, limit_swing, angle
from repair_attack_arms_v13 import curves


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def clamp(value, low=0., high=1.):
    return min(high, max(low, value))


def ease(value):
    value = clamp(value)
    return value**3*(10.-15.*value+6.*value**2)


def shaped_time(seconds, keys):
    """Monotone cubic warp: continuous speed, rapid strike, slower recovery."""
    slopes = [(b[1]-a[1])/(b[0]-a[0]) for a, b in zip(keys, keys[1:])]
    tangents = [slopes[0]]
    for index in range(1, len(keys)-1):
        a, b = slopes[index-1:index+1]
        tangents.append(0. if a*b <= 0. else 2.*a*b/(a+b))
    tangents.append(slopes[-1])
    if seconds <= keys[0][0]:
        return keys[0][1]
    for index, (a, b) in enumerate(zip(keys, keys[1:])):
        if seconds <= b[0]:
            span = b[0]-a[0]
            t = (seconds-a[0])/span
            value = ((2*t**3-3*t*t+1)*a[1]+(t**3-2*t*t+t)*span*tangents[index]
                     +(-2*t**3+3*t*t)*b[1]+(t**3-t*t)*span*tangents[index+1])
            return clamp(value, a[1], b[1])
    return keys[-1][1]


def sweep_time_map(contact, duration):
    return [(0., 0.), (contact-.25, .16), (contact-.14, .23),
            (contact-.08, .30), (contact, .34), (contact+.07, .39),
            (contact+.22, .52), (duration, 1.)]


def donor_forward_yaw(source, neutral, name):
    delta = source[name][1]@neutral[name][1].inverted()
    forward = delta@FWD
    return math.degrees(math.atan2(forward.x, -forward.y))


def choreography(seconds, contact, duration, side, donor):
    donor_seconds = shaped_time(seconds, sweep_time_map(contact, duration))
    source, neutral = sample_donor(donor, donor_seconds), donor['frames'][0]
    shoulder, elbow, wrist = [source[n][0] for n in ('upperarm_r', 'lowerarm_r', 'hand_r')]
    relative = wrist-shoulder
    upper, lower = (elbow-shoulder).normalized(), (wrist-elbow).normalized()
    # The original donor crosses frontal space at .34s. Keep almost its full
    # horizontal arc; V14 kept only .49 and capped one side at 44 degrees.
    azimuth = math.degrees(math.atan2(relative.x, -relative.y))
    sweep_azimuth = clamp((azimuth+19.3)*.90, -108., 105.)
    mirror = 1. if side == 'r' else -1.
    active = ease(seconds/.19)*(1.-ease((seconds-(duration-.28))/.28))
    shoulder_lead = sample_donor(donor, clamp(donor_seconds+.035, 0., 1.))
    hip_lead = sample_donor(donor, clamp(donor_seconds+.055, 0., 1.))
    # Retain the real donor's load/rotation at a scale appropriate for this
    # long humanoid, rather than replacing it by a sine waving the arm alone.
    yaw = clamp(donor_forward_yaw(shoulder_lead, neutral, 'spine_03')*.46, -49., 49.)*mirror*active
    hip_yaw = clamp(donor_forward_yaw(hip_lead, neutral, 'pelvis')*.26, -18., 18.)*mirror*active
    body_delta = shoulder_lead['spine_03'][1]@neutral['spine_03'][1].inverted()
    forward = body_delta@FWD
    lean = clamp(math.degrees(math.asin(clamp(forward.z, -1., 1.)))*.18, -3.5, 9.)*active
    shift = hip_lead['pelvis'][0]-neutral['pelvis'][0]
    shift = Vector((clamp(shift.x*.33*mirror, -4.4, 4.4),
                    clamp(shift.y*.30, -4.8, 2.9),
                    -2.2*ease(seconds/.18)*(1.-ease((seconds-(duration-.26))/.26))
                    +clamp(shift.z*.22, -.8, 1.2)))
    shift *= active
    bend = clamp(math.degrees(upper.angle(lower)), 29., 78.)
    # Raised anticipation stays forward of the gill roots instead of tracing
    # the donor's behind-head overhead windup through the back membranes.
    elevation = clamp(relative.z*.42, -28., 23.)
    protraction = (3.5+5.5*ease((seconds-(contact-.12))/.12))
    protraction *= active*(1.-ease((seconds-(contact+.12))/.24))
    claw = active*(.58+.34*ease((seconds-(contact-.10))/.09))
    if seconds < contact-.14:
        stage = 'loaded_outward_anticipation'
    elif seconds < contact-.06:
        stage = 'hip_chest_shoulder_uncoil'
    elif seconds <= contact+.06:
        stage = 'accelerated_frontal_crossing'
    elif seconds < contact+.22:
        stage = 'strike_follow_through'
    else:
        stage = 'whole_body_return_to_hanging_idle'
    return {'stage': stage, 'active': active, 'side': side, 'mirror': mirror,
            'donor_seconds': donor_seconds, 'donor_azimuth_deg': azimuth,
            'arm_azimuth_deg': sweep_azimuth*mirror, 'bend_deg': bend,
            'wrist_elevation_cm': elevation, 'body_yaw_deg': yaw,
            'pelvis_yaw_deg': hip_yaw, 'body_lean_deg': lean,
            'pelvis_shift': shift, 'clavicle_protraction_deg': protraction,
            'claw': claw, 'support': active*.72,
            'wrist_flex_deg': (5.+5.*ease((seconds-contact)/.10))*active}


def wrist_goal(side, attacking, shoulder, thorax, torso, baseline, params):
    base_shoulder = baseline['upperarm_'+side].translation
    base_elbow = baseline['lowerarm_'+side].translation
    base_wrist = baseline['hand_'+side].translation
    a, b = (base_elbow-base_shoulder).length, (base_wrist-base_elbow).length
    hanging = shoulder+torso@(base_wrist-base_shoulder)
    sign = 1. if side == 'l' else -1.
    initial_pole = pole_from_pose(base_shoulder, base_elbow, base_wrist,
                                  Vector((sign, -.2, -.3)))
    if side == attacking:
        bend = math.radians(params['bend_deg'])
        reach = math.sqrt(a*a+b*b+2.*a*b*math.cos(bend))
        elevation = params['wrist_elevation_cm']
        horizontal = math.sqrt(max(1., reach*reach-elevation*elevation))
        azimuth = math.radians(params['arm_azimuth_deg'])
        arm_goal = shoulder+Vector((math.sin(azimuth)*horizontal,
                                    -max(34., math.cos(azimuth)*horizontal), elevation))
        # All relevant crossing/follow-through remains in frontal world
        # space. The body may rotate 49deg without carrying this long hand
        # backwards through the simulated gills or through the thorax.
        arm_goal.y = min(arm_goal.y, thorax.y-34.)
        across_chest = 1.-ease(abs(arm_goal.x-thorax.x)/42.)
        arm_goal.y = min(arm_goal.y, thorax.y-34.-20.*across_chest)
        goal = hanging.lerp(arm_goal, params['active'])
        supported = Vector((sign*.72, .10, -.75)).normalized()
        pole = (torso@initial_pole).lerp(supported, params['active']).normalized()
        return goal, pole, a, b
    # The other hand counterbalances ahead of the abdomen, never mirrors the
    # strike or performs a static sideways extension.
    support_goal = thorax+torso@Vector((sign*27., -36., -24.))
    support_goal.x += -params['mirror']*8.*ease((params['donor_seconds']-.23)/.14)*params['active']
    support_goal.y = min(support_goal.y, thorax.y-27.)
    goal = hanging.lerp(support_goal, params['support'])
    pole = torso@initial_pole.lerp(Vector((sign*.85, .05, -.65)).normalized(), params['support']).normalized()
    return goal, pole, a, b


def author_action(rig, rest, baseline, baseline_local, ordered, role, frames, contact, donor):
    action = bpy.data.actions.new('A_M07_'+role+'_PowerSweepV16')
    action.use_fake_user = True
    motion.activate(rig, action)
    for p in ordered:
        p.rotation_mode = 'QUATERNION'
        p.matrix_basis = Matrix.Identity(4)
        for channel in ('location', 'rotation_quaternion', 'scale'):
            p.keyframe_insert(data_path=channel, frame=0)
    duration = (frames-1)/FPS
    attacking = 'l' if role == 'SweepLeft' else 'r'
    previous, samples = {}, []
    for index in range(frames):
        frame, seconds = index+1, index/FPS
        bpy.context.scene.frame_set(frame)
        params = choreography(seconds, contact, duration, attacking, donor)
        target, forearm_goal, arm_q = {}, {}, {}
        row = {'frame': frame, 'seconds': seconds, 'stage': params['stage'],
               'donor_seconds': params['donor_seconds'],
               'donor_azimuth_deg': params['donor_azimuth_deg'],
               'arm_azimuth_deg': params['arm_azimuth_deg'],
               'body_yaw_deg': params['body_yaw_deg'],
               'pelvis_yaw_deg': params['pelvis_yaw_deg'],
               'pelvis_shift_cm': list(params['pelvis_shift']), 'arms': {}}
        for p in ordered:
            name, parent = p.name, p.parent.name if p.parent else None
            target[name] = p.bone.convert_local_to_pose(baseline_local[name], rest[name],
                **({'parent_matrix': target[parent], 'parent_matrix_local': rest[parent]} if parent else {}))
            if name == 'pelvis':
                q = Quaternion(UP, math.radians(params['pelvis_yaw_deg']))@baseline[name].to_quaternion()
                target[name] = Matrix.LocRotScale(baseline[name].translation+params['pelvis_shift'], q, Vector((1, 1, 1)))
            elif name in ('spine_01', 'spine_02', 'spine_03', 'spine_04', 'spine_05'):
                # Hip winds/advances first; chest and shoulder magnify the
                # following turn. The arm is consequently not the only mover.
                extra_yaw = (params['body_yaw_deg']-params['pelvis_yaw_deg'])*.20
                q = (Quaternion(UP, math.radians(extra_yaw))
                     @Quaternion(RIGHT, math.radians(params['body_lean_deg']*.20))@target[name].to_quaternion())
                target[name] = Matrix.LocRotScale(target[name].translation, q, Vector((1, 1, 1)))
            elif name in ('neck_01', 'neck_02'):
                q = (Quaternion(UP, math.radians(-params['body_yaw_deg']*.19))
                     @Quaternion(RIGHT, math.radians(-params['body_lean_deg']*.14))@target[name].to_quaternion())
                target[name] = Matrix.LocRotScale(target[name].translation, q, Vector((1, 1, 1)))
            elif name.startswith('clavicle_'):
                side = name[-1]
                sign = 1. if side == 'l' else -1.
                amount = params['clavicle_protraction_deg'] if side == attacking else -params['active']*2.
                q = Quaternion(UP, math.radians(-sign*amount))@target[name].to_quaternion()
                target[name] = Matrix.LocRotScale(target[name].translation, q, Vector((1, 1, 1)))
            torso = (target['spine_05'].to_quaternion()@baseline['spine_05'].to_quaternion().inverted()
                     if 'spine_05' in target else Quaternion())
            if name.startswith('upperarm_'):
                side = name[-1]
                goal, pole, a, b = wrist_goal(side, attacking, target[name].translation,
                                               target['spine_05'].translation, torso, baseline, params)
                ceiling = .9999-(.9999-.968)*params['active']
                u, l, reached = solve_segments(goal-target[name].translation, a, b, pole, ceiling)
                original = (baseline['lowerarm_'+side].translation-baseline[name].translation).normalized()
                q = (torso@original).rotation_difference(u)@torso@baseline[name].to_quaternion()
                # Minimum swing preserves the transported original humeral
                # roll. No donor axial rotation is allowed to flip the elbow.
                target[name] = Matrix.LocRotScale(target[name].translation, q, Vector((1, 1, 1)))
                forearm_goal[side], arm_q[side] = l, q
                row['arms'][side] = {'requested_wrist_cm': list(goal),
                                     'elbow_bend_deg': math.degrees(u.angle(l)),
                                     'reach_fraction': reached.length/(a+b),
                                     'axial_upper_roll_deg': 0.}
            elif name.startswith('lowerarm_'):
                side = name[-1]
                original = (baseline['hand_'+side].translation-baseline[name].translation).normalized()
                # Parallel-transport from the upper arm, then swing to the
                # anatomical elbow result. This shares its continuous pole.
                upper_delta = arm_q[side]@baseline['upperarm_'+side].to_quaternion().inverted()
                u_reference = upper_delta@original
                q = u_reference.rotation_difference(forearm_goal[side])@upper_delta@baseline[name].to_quaternion()
                target[name] = Matrix.LocRotScale(target[name].translation, q, Vector((1, 1, 1)))
            elif name.startswith('hand_'):
                side = name[-1]
                lower = 'lowerarm_'+side
                lower_delta = target[lower].to_quaternion()@baseline[lower].to_quaternion().inverted()
                q = lower_delta@baseline[name].to_quaternion()
                if side == attacking:
                    # A modest wrist lead/follow accent carries the claw;
                    # force comes from torso and elbow, not a twisted wrist.
                    axis = q@RIGHT
                    q = Quaternion(axis, math.radians(params['wrist_flex_deg']))@q
                target[name] = Matrix.LocRotScale(target[name].translation, q, Vector((1, 1, 1)))
            elif name.startswith(('thumb_', 'index_', 'middle_', 'ring_', 'pinky_')) and '_metacarpal_' not in name:
                side = name[-1]
                digit, segment = name.split('_')[0], int(name.split('_')[1])-1
                hand = 'hand_'+side
                hand_delta = target[hand].to_quaternion()@rest[hand].to_quaternion().inverted()
                along = (rest['middle_01_'+side].translation-rest[hand].translation).normalized()
                across = (rest['index_01_'+side].translation-rest['pinky_01_'+side].translation).normalized()
                normal = hand_delta@along.cross(across).normalized()
                direction = target[name].to_3x3()@Vector((0, 1, 0))
                axis = direction.cross(normal).normalized()
                delay = {'thumb': 0., 'index': .015, 'middle': .025, 'ring': .04, 'pinky': .05}[digit]+segment*.012
                amount = clamp((params['claw']-delay)/(1.-delay)) if side == attacking else params['active']*.20
                flex = (10., 16., 12.)[segment] if digit != 'thumb' else (5., 9., 7.)[segment]
                q = Quaternion(axis, math.radians(flex*amount))@target[name].to_quaternion()
                target[name] = Matrix.LocRotScale(target[name].translation, q, Vector((1, 1, 1)))
            elif name.startswith('thigh_'):
                side = name[-1]
                a, b, c = [baseline[n+'_'+side].translation for n in ('thigh', 'calf', 'foot')]
                pelvis_delta = target['pelvis'].to_quaternion()@baseline['pelvis'].to_quaternion().inverted()
                pole = pelvis_delta@pole_from_pose(a, b, c, FWD)
                u, l, _ = solve_segments(c-target[name].translation, (b-a).length, (c-b).length, pole, .9999)
                original = (b-a).normalized()
                q = (pelvis_delta@original).rotation_difference(u)@pelvis_delta@baseline[name].to_quaternion()
                target[name] = Matrix.LocRotScale(target[name].translation, q, Vector((1, 1, 1)))
                forearm_goal['leg_'+side] = l
            elif name.startswith('calf_'):
                side = name[-1]
                pelvis_delta = target['pelvis'].to_quaternion()@baseline['pelvis'].to_quaternion().inverted()
                original = (baseline['foot_'+side].translation-baseline[name].translation).normalized()
                u = forearm_goal['leg_'+side]
                q = (pelvis_delta@original).rotation_difference(u)@pelvis_delta@baseline[name].to_quaternion()
                target[name] = Matrix.LocRotScale(target[name].translation, q, Vector((1, 1, 1)))
            elif name.startswith('foot_'):
                target[name] = Matrix.LocRotScale(target[name].translation, baseline[name].to_quaternion(), Vector((1, 1, 1)))
            p.matrix_basis = p.bone.convert_local_to_pose(target[name], rest[name],
                **({'parent_matrix': target[parent], 'parent_matrix_local': rest[parent]} if parent else {}), invert=True)
            p.rotation_mode = 'QUATERNION'
            q = p.rotation_quaternion.copy()
            if name in previous and q.dot(previous[name]) < 0:
                q.negate()
            p.rotation_quaternion = q
            previous[name] = q.copy()
            p.scale = Vector((1, 1, 1))
            if name != 'pelvis':
                p.location = Vector()
            for channel in ('location', 'rotation_quaternion', 'scale'):
                p.keyframe_insert(data_path=channel, frame=frame)
        for side in ('l', 'r'):
            row['arms'][side].update({part+'_cm': list(target[part+'_'+side].translation)
                                      for part in ('upperarm', 'lowerarm', 'hand')})
            row.setdefault('support_feet', {})[side] = list(target['foot_'+side].translation)
        samples.append(row)
    for curve in curves(action):
        for key in curve.keyframe_points:
            key.interpolation = 'LINEAR'
    return action, samples


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(MASTER))
    rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    # Preserve the latest two cast actions in this editable animation master.
    casting = json.loads((ROOT/'MotionRecoveryV15/Casting/casting_manifest_v15.json').read_text(encoding='utf-8'))
    wanted = [entry['action'] for entry in casting['clips'].values()]
    with bpy.data.libraries.load(str(CAST_MASTER), link=False) as (available, loaded):
        loaded.actions = [n for n in wanted if n in available.actions and n not in bpy.data.actions]
    rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
    ordered = sorted(rig.pose.bones, key=lambda p: len(p.bone.parent_recursive))
    original = json.loads((ROOT/'RecoveryOriginalV13/motion_manifest_v13.json').read_text(encoding='utf-8'))
    baseline, baseline_local = base_pose(rig, original)
    donor = read_donor('Attack_Biped_Melee_A')
    scene = bpy.context.scene
    scene.render.fps, scene.render.fps_base = FPS, 1.
    scene.unit_settings.system, scene.unit_settings.scale_length = 'METRIC', .01
    rig.data.pose_position = 'POSE'
    entries, samples, actions = {}, {}, {}
    for role, frames, contact in (('SweepLeft', 34, .47), ('SweepRight', 37, .50)):
        action, authored = author_action(rig, rest, baseline, baseline_local, ordered, role, frames, contact, donor)
        file = OUT/('A_M07_'+role+'.fbx')
        export(rig, action, file, frames)
        duration = (frames-1)/FPS
        entries[role] = {'file': str(file), 'action': action.name, 'frames': frames, 'fps': FPS,
                         'duration': duration, 'seconds': duration,
                         'asset': '/Game/Monsters/BlindSupplicantM07/AnimationsArmSweepV16/A_M07_'+role,
                         'contact_seconds': contact, 'impact_seconds': contact,
                         'contact_window_seconds': .12,
                         'contact_window_start_seconds': contact-.06,
                         'contact_window_end_seconds': contact+.06,
                         'reference_only_blender_frame': 0, 'exported_blender_frame_start': 1,
                         'exported_blender_frame_end': frames, 'loop': False, 'root_motion': False,
                         'bone_tracks': list(rest), 'source_time_map': sweep_time_map(contact, duration),
                         'runtime_melee_playback_multiplier': 1.30,
                         'expected_runtime_duration_seconds': duration/1.30,
                         'expected_runtime_contact_seconds': contact/1.30,
                         'expected_runtime_contact_window_seconds': .12/1.30}
        samples[role], actions[role] = authored, action
        print('M07_V16_POWER_SWEEP_EXPORTED '+role+' '+str(file), flush=True)
    motion.activate(rig, actions['SweepRight'])
    scene.frame_start, scene.frame_end = 1, entries['SweepRight']['frames']
    scene.frame_set(0)
    source = OUT/'M07_Original_PowerSweeps_V16.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(source), compress=True)
    write(OUT/'power_sweep_manifest_v16.json', {
        'revision': 'PowerSweepV16', 'fps': FPS, 'source': str(source), 'source_master': str(MASTER),
        'casting_master_appended': str(CAST_MASTER), 'clips': entries,
        'ue_skeleton': original.get('ue_skeleton', '/Game/Monsters/BlindSupplicantM07/SK_M07_ReferenceOriginalV11'),
        'bone_names': list(rest), 'reference_bones': {n: motion.rows(m) for n, m in rest.items()},
        'bone_parents': {b.name: b.parent.name if b.parent else None for b in rig.data.bones},
        'mesh_geometry_uv_weights_and_reference_preserved': True,
        'bone_lengths_preserved': True,
        'retained_motion': 'V15 SlowWalk/Chase/Death, appended V15 MagicGather/MagicRelease, original V13 Idle and unrelated actions; UE references managed separately by importer',
        'sweep_reference': {'monster': 'HundredEyedSlag', 'formal_role': 'AttackSweep_R',
            'formal_asset': '/Game/Monsters/HundredEyedSlag/V1/Animations/A_HundredEyedSlag_AttackSweep_R',
            'author': str(PROJECT/'SourceAssets/HundredEyedSlagMeshy20260930/RampageV8/author_rampage.py'),
            'donor_asset': donor['asset'], 'donor_source': str(DONOR/'Attack_Biped_Melee_A.json'),
            'source_seconds': donor['seconds'], 'source_fps': donor['fps'],
            'donor_crossing_time_seconds': .34, 'donor_fast_crossing_interval_seconds': [.30, .39],
            'actual_reference_method': 'Real joint component positions, elbow bend, pelvis translation and spine/pelvis rotations; monotone cubic source-time shaping. Hip leads by .055 donor seconds, chest/shoulder by .035; quick strike preserves source .30-.39, then real .39-.52 follow-through and complete return.',
            'no_donor_skin_mesh_bone_matrices_copied': True},
        'changes_from_v14': {'old_left_seconds': 1.5, 'old_right_seconds': 1.6666666667,
            'old_left_contact_seconds': .68, 'old_right_contact_seconds': .78,
            'old_wrist_azimuth_factor': .49, 'new_wrist_azimuth_factor': .90,
            'old_torso_yaw_factor': .18, 'new_torso_yaw_factor': .46,
            'old_torso_yaw_cap_deg': 21., 'new_torso_yaw_cap_deg': 49.,
            'old_windup': 'Arm-only compressed front projection, reduced whole-body load',
            'new_identity': 'Visible loaded outward anticipation, hip/chest/shoulder driven acceleration through frontal space, bent anatomical elbow and following claw, other arm balances, planted legs load and whole body recovers'},
        'anatomy': {'minimum_segment_swing': True, 'axial_upper_roll_deg': 0.,
            'no_axial_forearm_donor_copy': True, 'reach_ceiling_fraction': .968,
            'wrist_flex_degrees': [5., 10.], 'continuous_downward_outward_elbow_pole': True,
            'actual_hanging_idle_entrance_and_exit': True,
            'frontal_wrist_thorax_clearance_cm': 34., 'frontal_center_crossing_extra_clearance_cm': 20.,
            'support': 'Original ankle positions and foot frames planted; original forward knee support; pelvis shifts and bends through thigh/calf solve'},
        'child_location_policy': 'Zero on every child, unit bone scales; authored original-pelvis movement only; reference frame0 excluded',
        'authoring_samples': samples, 'source_saved': True, 'animation_fbx_exported': True,
        'ue_imported': False, 'runtime_tested': False, 'rendered': False, 'visual_accepted': False})
    print('M07_V16_POWER_SWEEP_SOURCE_SAVED '+str(source), flush=True)


if __name__ == '__main__':
    main()
