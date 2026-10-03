"""M07 V20: posterior palms, anatomical arm chains and sweep recovery.

Copies the accepted V19 locomotion and V18 whole-body sweep actions. Only
upper-arm, forearm, hand and digit curves are replaced. Original skin, mesh,
UVs, materials, 83-bone reference and every non-arm animation curve remain
unchanged. Palm orientation comes from the actual wrist/finger landmarks,
not a guessed hand-bone axis. This producer exports only; no UE or render.
"""
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Quaternion, Vector

PROJECT = Path('D:/FPS3D/FPSGAME')
ROOT = PROJECT/'SourceAssets/BlindSupplicantM07Meshy20261001'
OUT = ROOT/'PalmArmMotionV20/Motion'
SKIN = ROOT/'LegJointsV17/Skin/M07_Original_LegJoints_V17.blend'
MOVE = ROOT/'VideoLocomotionV19/Move/M07_Original_VideoLocomotion_V19.blend'
ATTACK = ROOT/'BodyMotionV18/Attack/M07_Original_BodySweeps_V18.blend'
IDLE = ROOT/'RecoveryOriginalV13/M07_Original_Recovery_V13.blend'
FPS = 30
UP = Vector((0., 0., 1.))
REAR = Vector((0., 1., 0.))
DOWN = Vector((0., 0., -1.))
ARM_PREFIXES = ('upperarm_', 'lowerarm_', 'hand_', 'thumb_', 'index_',
                'middle_', 'ring_', 'pinky_')
sys.path.insert(0, str(Path(__file__).parent))
import author_motion_v04 as motion
import author_running_v12 as running
import author_locomotion_death_v15 as v15
import author_leg_joint_motion_v17 as v17
import author_power_sweep_v16 as v16
import author_body_sweeps_v18 as v18
from author_sweep_cast_v14 import read_donor
from author_cast_v15 import signed_angle, solve_segments


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def clamp(value, lo, hi):
    return min(hi, max(lo, value))


def matrix(point, quaternion):
    return Matrix.LocRotScale(point, quaternion, Vector((1., 1., 1.)))


def original_rig():
    return next(o for o in bpy.data.objects if o.type == 'ARMATURE'
                and o.data.bones.get('gill_01_00'))


def arm_reference(rest, side):
    shoulder, elbow, wrist = [rest[n+'_'+side].translation
                              for n in ('upperarm', 'lowerarm', 'hand')]
    upper, lower = (elbow-shoulder).normalized(), (wrist-elbow).normalized()
    hinge = upper.cross(lower).normalized()
    along = (rest['middle_01_'+side].translation-wrist).normalized()
    across = (rest['index_01_'+side].translation
              -rest['pinky_01_'+side].translation).normalized()
    # The index/pinky ordering is mirrored, but both biological palm surfaces
    # face the same side of the flat T-pose. The sign must therefore mirror.
    palm = along.cross(across).normalized()*(1. if side == 'l' else -1.)
    return {'upper': upper, 'lower': lower, 'hinge': hinge,
            'reference_frame': motion.anatomical_frame(upper, hinge),
            'rest_bend': math.atan2(hinge.dot(upper.cross(lower)), upper.dot(lower)),
            'palm_normal': palm, 'finger_along': along,
            'upper_length': (elbow-shoulder).length,
            'lower_length': (wrist-elbow).length}


def body_rear(pose, rest):
    delta = pose['spine_05'].to_quaternion()@rest['spine_05'].to_quaternion().inverted()
    direction = delta@REAR
    direction.z = 0.
    return direction.normalized()


def arm_fit(source, rest, side, reference, wanted_palm, previous_roll, active):
    """One elbow hinge followed by bounded physiological forearm pronation.

    A bounded elbow-pole swivel transports the complete upper/lower hinge
    while preserving the wrist corridor. Forearm pronation happens AFTER flexion, about the actual forearm
    direction. Wrist axial residual is limited to six degrees. No independently
    guessed upper/lower shortest-arc rolls, reversed hinge or 180-degree wrist.
    """
    d = reference
    shoulder, elbow, wrist = [source[n+'_'+side].translation
                              for n in ('upperarm', 'lowerarm', 'hand')]
    upper, lower = (elbow-shoulder).normalized(), (wrist-elbow).normalized()
    hinge = upper.cross(lower)
    if hinge.length < .00001:
        hinge = source['upperarm_'+side].to_quaternion()@rest['upperarm_'+side].to_quaternion().inverted()@d['hinge']
    hinge.normalize()
    bend = math.atan2(hinge.dot(upper.cross(lower)), upper.dot(lower))
    wrist_axis = (wrist-shoulder).normalized()
    best = None
    # Swivel around the shoulder/wrist chord, not the humerus alone: the two
    # segment endpoints remain exactly on the original desired wrist corridor.
    # The explicit strike relaxes to its naturally transported palm orientation.
    roll_limit = 46.*(1.-active)
    for step in range(-23, 24):
        roll_deg = step*2.*(1.-active)
        swivel = Quaternion(wrist_axis, math.radians(roll_deg))
        fitted_upper, fitted_hinge = swivel@upper, swivel@hinge
        du = (motion.anatomical_frame(fitted_upper, fitted_hinge)@d['reference_frame'].transposed()).to_quaternion()
        dl = du@Quaternion(d['hinge'], bend-d['rest_bend'])
        actual_lower = dl@d['lower']
        normal = dl@d['palm_normal']
        # During the strike the palm follows the common elbow frame; recovery
        # continuously resumes the corrected posterior hanging orientation.
        wanted = wanted_palm.lerp(normal, active*.97).normalized()
        desired = wanted-actual_lower*wanted.dot(actual_lower)
        if desired.length < .08:
            desired = DOWN-actual_lower*DOWN.dot(actual_lower)
        desired.normalize()
        needed = math.degrees(signed_angle(normal, desired, actual_lower))
        forearm = clamp(needed*.93, -65., 65.)
        wrist_roll = clamp(needed-forearm, -6., 6.)
        remaining = needed-forearm-wrist_roll
        # The continuity term discourages pole excursions between consecutive
        # samples; palm direction and anatomical pronation bounds dominate.
        cost = remaining*remaining*12.+roll_deg*roll_deg*.003+forearm*forearm*.0004
        cost += (roll_deg-previous_roll)**2*.007
        if best is None or cost < best[0]:
            best = (cost, du, dl, fitted_upper, actual_lower, roll_deg, forearm,
                    wrist_roll, remaining, desired)
    _, du, dl, fitted_upper, actual_lower, roll_deg, pronation, wrist_roll, remaining, desired = best
    forearm_delta = Quaternion(actual_lower, math.radians(pronation))@dl
    hand_delta = Quaternion(actual_lower, math.radians(wrist_roll))@forearm_delta
    # A naturally hanging claw also yields at the wrist's transverse hinge.
    # Axial pronation alone cannot face a palm rearward while the forearm is
    # pointing horizontally forward. This is bounded wrist flexion, not twist.
    palm = hand_delta@d['palm_normal']
    fingers = hand_delta@d['finger_along']
    across = palm.cross(fingers).normalized()
    wrist_flex = math.degrees(signed_angle(palm, wanted_palm, across))
    wrist_flex = clamp(wrist_flex, -25.*(1.-active), 25.*(1.-active))
    hand_delta = Quaternion(across, math.radians(wrist_flex))@hand_delta
    result = {
        'upperarm_'+side: matrix(shoulder, du@rest['upperarm_'+side].to_quaternion()),
        'lowerarm_'+side: matrix(shoulder+fitted_upper*d['upper_length'],
                               forearm_delta@rest['lowerarm_'+side].to_quaternion()),
        'hand_'+side: matrix(shoulder+fitted_upper*d['upper_length']+actual_lower*d['lower_length'],
                            hand_delta@rest['hand_'+side].to_quaternion())}
    palm = hand_delta@d['palm_normal']
    return result, {'elbow_pole_swivel_degrees': roll_deg,
                    'forearm_pronation_degrees': pronation,
                    'wrist_axial_residual_degrees': wrist_roll,
                    'wrist_transverse_flex_degrees': wrist_flex,
                    'elbow_flex_degrees': math.degrees(bend),
                    'palm_surface_normal': list(palm),
                    'desired_projected_palm_normal': list(desired),
                    'remaining_palm_roll_degrees': remaining,
                    'elbow_pole_swivel_limit_degrees': roll_limit}, roll_deg


def locomotion_arm_source(source, reference, role):
    """Keep the accepted shoulder swing, relax the over-flexed forearm.

    V19's 36-60 degree jogging elbow combined with shoulder-forward swing
    brings a forearm nearly horizontal. Its palm cannot face posterior using
    pronation alone. Human low-hand locomotion keeps a mild yielding elbow.
    """
    adjusted = {n: m.copy() for n,m in source.items()}
    for side in ('l', 'r'):
        shoulder, elbow, wrist = [source[n+'_'+side].translation
                                  for n in ('upperarm', 'lowerarm', 'hand')]
        upper, lower = (elbow-shoulder).normalized(), (wrist-elbow).normalized()
        old_bend = math.degrees(upper.angle(lower))
        bend = 24.+(old_bend-48.)/3. if role == 'Chase' else 19.+(old_bend-31.)*.35
        bend = math.radians(clamp(bend, 16., 28.))
        flex = lower-upper*lower.dot(upper)
        flex.normalize()
        new_lower = upper*math.cos(bend)+flex*math.sin(bend)
        adjusted['hand_'+side].translation = elbow+new_lower*reference[side]['lower_length']
    return adjusted


def sweep_arm_source(source, baseline, params, attacking):
    """Recreate actual donor wrist corridor with the hanging arm baseline.

    The historical V18 action contains a near-T striking arm at entry/exit.
    Its preserved body choreography is useful, but that arm basis cannot be
    the recovery target. Reference wrist intent is solved again as a chain.
    """
    adjusted = {n: m.copy() for n,m in source.items()}
    torso = source['spine_05'].to_quaternion()@baseline['spine_05'].to_quaternion().inverted()
    for side in ('l', 'r'):
        shoulder = source['upperarm_'+side].translation
        u0 = (baseline['lowerarm_'+side].translation-baseline['upperarm_'+side].translation)
        l0 = (baseline['hand_'+side].translation-baseline['lowerarm_'+side].translation)
        if side == attacking:
            goal, pole, a, b = v16.wrist_goal(side, attacking, shoulder,
                source['spine_05'].translation, torso, baseline, params)
            ceiling = .9999-(.9999-.968)*params['active']
            upper, lower, reached = solve_segments(goal-shoulder, a, b, pole, ceiling)
            elbow, wrist = shoulder+upper*a, shoulder+reached
        else:
            elbow, wrist = shoulder+torso@u0, shoulder+torso@(u0+l0)
        adjusted['upperarm_'+side].translation = shoulder
        adjusted['lowerarm_'+side].translation = elbow
        adjusted['hand_'+side].translation = wrist
    return adjusted


def digit_pose(target, source, rest, ordered, side, reference, role, active):
    """Five separate digits, mirrored biological flexion into the palm side."""
    hand = 'hand_'+side
    delta = target[hand].to_quaternion()@rest[hand].to_quaternion().inverted()
    palm = delta@reference['palm_normal']
    if role == 'Idle':
        curls = (4., 7., 5.)
    elif role == 'SlowWalk':
        curls = (5., 9., 7.)
    elif role == 'Chase':
        curls = (6., 11., 8.)
    else:
        curls = (5.+8.*active, 9.+13.*active, 7.+10.*active)
    for pose in ordered:
        name = pose.name
        if not name.startswith(('thumb_', 'index_', 'middle_', 'ring_', 'pinky_')) or not name.endswith('_'+side):
            continue
        parent = pose.parent.name
        local = rest[parent].inverted()@rest[name]
        point = target[parent]@local.translation
        q = target[parent].to_quaternion()@local.to_quaternion()
        if '_metacarpal_' not in name:
            digit, segment, _ = name.split('_')
            amount = curls[int(segment)-1]
            if digit == 'thumb':
                amount *= .56
            elif digit == 'pinky':
                amount *= .92
            direction = q@Vector((0., 1., 0.))
            axis = direction.cross(palm)
            if axis.length > .00001:
                q = Quaternion(axis.normalized(), math.radians(amount))@q
        target[name] = matrix(point, q)


def insert_arm_frame(rig, target, rest, ordered, frame, previous):
    # All unmodified channels are copied bit-for-bit from their source Action.
    # Re-keying only the owned arm/digit channels avoids changing accepted gait.
    for pose in ordered:
        if not pose.name.startswith(ARM_PREFIXES):
            continue
        name, parent = pose.name, pose.parent.name
        pose.matrix_basis = pose.bone.convert_local_to_pose(target[name], rest[name],
            parent_matrix=target[parent], parent_matrix_local=rest[parent], invert=True)
        pose.rotation_mode = 'QUATERNION'
        pose.location = Vector()
        pose.scale = Vector((1., 1., 1.))
        q = pose.rotation_quaternion.copy()
        if name in previous and previous[name].dot(q) < 0.:
            q.negate()
        pose.rotation_quaternion = q
        previous[name] = q.copy()
        for channel in ('location', 'rotation_quaternion', 'scale'):
            pose.keyframe_insert(data_path=channel, frame=frame, group=name)


def cache_sources():
    definitions = (
        (MOVE, ROOT/'VideoLocomotionV19/Move/video_locomotion_manifest_v19.json', ('SlowWalk', 'Chase')),
        (ATTACK, ROOT/'BodyMotionV18/Attack/body_sweep_manifest_v18.json', ('SweepLeft', 'SweepRight')),
        (IDLE, ROOT/'RecoveryOriginalV13/motion_manifest_v13.json', ('Idle',)))
    cached = {}
    for blend, manifest_path, roles in definitions:
        data = json.loads(manifest_path.read_text(encoding='utf-8'))
        bpy.ops.wm.open_mainfile(filepath=str(blend))
        rig = original_rig()
        rig.data.pose_position = 'POSE'
        ordered = sorted(rig.pose.bones, key=lambda p: len(p.bone.parent_recursive))
        for role in roles:
            entry = data['clips'][role]
            action = bpy.data.actions[entry['action']]
            cached[role] = {'samples': v17.cache_action(rig, action, entry['frames'], ordered),
                            'entry': entry, 'source_blend': str(blend),
                            'source_manifest': str(manifest_path)}
            print('M07_V20_SOURCE_CACHED '+role, flush=True)
    return cached


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    cached = cache_sources()
    donor = read_donor('Attack_Biped_Melee_A')
    bpy.ops.wm.open_mainfile(filepath=str(SKIN))
    rig = original_rig()
    rig.data.pose_position = 'POSE'
    rig.animation_data_clear()
    rig.hide_set(False)
    ordered = sorted(rig.pose.bones, key=lambda p: len(p.bone.parent_recursive))
    rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
    reference = {s: arm_reference(rest, s) for s in ('l', 'r')}
    hidden = {o.name: o.hide_viewport for o in bpy.data.objects if o.type == 'MESH'}
    for name in hidden:
        bpy.data.objects[name].hide_viewport = True
    scene = bpy.context.scene
    scene.render.fps, scene.render.fps_base = FPS, 1.
    scene.unit_settings.system, scene.unit_settings.scale_length = 'METRIC', .01
    manifest = {'revision': 'PalmArmMotionV20', 'fps': FPS,
        'source': str(OUT/'M07_Original_PalmArmMotion_V20.blend'),
        'mesh_skin_master': str(SKIN),
        'reference_skeleton': '/Game/Monsters/BlindSupplicantM07/SK_M07_ReferenceOriginalV11',
        'bone_names': list(rest), 'bone_reference': {n: motion.rows(m) for n,m in rest.items()},
        'rig_object_matrix_world': motion.rows(rig.matrix_world),
        'reference_pose_modified': False, 'geometry_modified': False,
        'weights_modified': False, 'materials_modified': False, 'uv_modified': False,
        'root_motion': False, 'animation_export_pose_position': 'POSE',
        'unchanged_animation_tracks_copied_exactly': True,
        'changed_bone_prefixes': list(ARM_PREFIXES), 'clips': {},
        'candidate': True, 'runtime_tested': False, 'tested': False,
        'rendered': False, 'visual_accepted': False, 'ue_imported': False,
        'palm_definition': 'Wrist to middle MCP and index-to-pinky MCP plane, biological side mirrored explicitly; forearm-projected torso posterior direction during moving and idle',
        'joint_method': 'One geometric elbow hinge transports upper/lower arm; locomotion retains shoulder swing while relaxing elbow to16-28deg; bounded elbow-pole swivel preserves desired wrist corridor, forearm pronation capped65deg, wrist axial residual capped6deg and transverse yielding capped25deg',
        'finger_method': 'Five distinct original digit chains curl toward the actual biological palm normal, including mirrored right hand; no dorsal/right-hand reversed curl',
        'sweep_reference': {'asset': donor['asset'], 'source_clip': 'Attack_Biped_Melee_A',
            'source_cache': str(v16.DONOR/'Attack_Biped_Melee_A.json'),
            'body_and_contact_choreography': 'V18 exact original body channels and original donor time map retained; wrist corridor solved again from genuine hanging idle, replacing historical near-T entry/exit arm',
            'idle_reason': 'Matching corrected resting arm/palm posture prevents attack recovery returning to the old incompatible wrist/forearm roll'},
        'runtime_cost': 'Offline animation keys only; no additional Tick, physics, cloth collision or prediction work'}
    actions = {}
    for role in ('Idle', 'SlowWalk', 'Chase', 'SweepLeft', 'SweepRight'):
        item, source_entry = cached[role], cached[role]['entry']
        source_action_name = source_entry['action']
        # Load the source action itself to preserve every unmodified curve.
        with bpy.data.libraries.load(item['source_blend'], link=False) as (available, loaded):
            loaded.actions = [source_action_name]
        source_action = loaded.actions[0]
        action = source_action.copy()
        action.name = 'A_M07_'+role+'_PalmArmV20'
        action.use_fake_user = True
        motion.activate(rig, action)
        previous, last_roll = {}, {'l': 0., 'r': 0.}
        production = []
        targets = []
        count = source_entry['frames']
        duration = (count-1)/FPS
        contact = source_entry.get('contact_time', source_entry.get('contact_seconds'))
        attacking = ('l' if role == 'SweepLeft' else 'r') if role.startswith('Sweep') else None
        for index, source in enumerate(item['samples']):
            frame, seconds = index+1, index/FPS
            scene.frame_set(frame)
            target = {n: m.copy() for n,m in source.items()}
            rear = body_rear(source, rest)
            params = v18.body_choreography(seconds, contact, duration, attacking, donor) if attacking else None
            active = params['active'] if params else 0.
            if attacking:
                arm_source = sweep_arm_source(source, cached['Idle']['samples'][0], params, attacking)
            elif role in ('SlowWalk', 'Chase'):
                arm_source = locomotion_arm_source(source, reference, role)
            else:
                arm_source = source
            row = {'frame': frame, 'seconds': seconds, 'arms': {},
                   'stage': params['stage'] if params else 'cyclic_posterior_palms'}
            for side in ('l', 'r'):
                striking = active if side == attacking else 0.
                fit, record, last_roll[side] = arm_fit(arm_source, rest, side, reference[side],
                    rear, last_roll[side], striking)
                target.update(fit)
                digit_pose(target, source, rest, ordered, side, reference[side],
                    role if side == attacking or not attacking else 'Idle', striking)
                record.update({'upperarm_cm': list(target['upperarm_'+side].translation),
                    'elbow_cm': list(target['lowerarm_'+side].translation),
                    'wrist_cm': list(target['hand_'+side].translation),
                    'attacking': side == attacking if attacking else False})
                row['arms'][side] = record
            if source_entry.get('loop') and index == count-1:
                for name in target:
                    if name.startswith(ARM_PREFIXES):
                        target[name] = targets[0][name].copy()
                row['arms'] = production[0]['arms']
            targets.append(target)
            production.append(row)
            insert_arm_frame(rig, target, rest, ordered, frame, previous)
        for curve in running.curves(action):
            if any(('"'+prefix) in curve.data_path for prefix in ARM_PREFIXES):
                for key in curve.keyframe_points:
                    key.interpolation = 'LINEAR'
        file = OUT/('A_M07_'+role+'.fbx')
        v15.export(rig, action, file, count)
        entry = {'role': role, 'action': action.name, 'file': str(file),
            'asset': '/Game/Monsters/BlindSupplicantM07/AnimationsPalmArmV20/A_M07_'+role,
            'frames': count, 'fps': FPS, 'duration': duration,
            'duration_seconds': duration, 'seconds': duration,
            'loop': source_entry.get('loop', False), 'root_motion': False,
            'reference_only_blender_frame': 0, 'exported_blender_frame_start': 1,
            'exported_blender_frame_end': count, 'bone_tracks': list(rest),
            'source_action': source_action_name, 'source_blend': item['source_blend'],
            'source_manifest': item['source_manifest'],
            'source_speed_cm_s': source_entry.get('source_speed_cm_s', 0.),
            'speed_cm_s': source_entry.get('source_speed_cm_s', 0.),
            'expected_speed_cm_s': source_entry.get('expected_speed_cm_s', 0.),
            'unmodified_body_leg_head_gill_tracks_copied_exactly': True,
            'contact_time': contact, 'contact_seconds': contact,
            'impact_seconds': contact,
            'runtime_melee_playback_multiplier': source_entry.get('runtime_melee_playback_multiplier'),
            'production_record': str(OUT/('authored_'+role.lower()+'_production_record_v20.json')),
            'runtime_tested': False, 'rendered': False}
        if attacking:
            entry['quiet_arm_side'] = 'r' if attacking == 'l' else 'l'
            entry['quiet_arm_local_pose'] = 'Corrected hanging rest; source torso carrying only, no mirrored strike'
            entry['contact_window_seconds'] = source_entry.get('contact_window_seconds', .12)
        else:
            for field in ('expected_playback_ratio_at_ai_speed', 'expected_cycle_seconds_at_ai_speed',
                          'foot_contact', 'curves', 'stride_cm', 'step_cm', 'stance_fraction'):
                if field in source_entry:
                    entry[field] = source_entry[field]
        write(Path(entry['production_record']), {'scope': 'Authoring records, not a separate test',
              'action': action.name, 'frames': production, 'runtime_tested': False, 'rendered': False})
        manifest['clips'][role], actions[role] = entry, action
        print('M07_V20_CLIP_EXPORTED '+role+' '+json.dumps({'frames': count,
            'duration': duration, 'max_forearm_pronation_deg': max(abs(s['arms'][side]['forearm_pronation_degrees'])
            for s in production for side in ('l', 'r')),
            'max_remaining_palm_roll_deg': max(abs(s['arms'][side]['remaining_palm_roll_degrees'])
            for s in production for side in ('l', 'r'))}), flush=True)
    for name, was_hidden in hidden.items():
        bpy.data.objects[name].hide_viewport = was_hidden
    motion.activate(rig, actions['Chase'])
    scene.frame_start, scene.frame_end = 1, manifest['clips']['Chase']['frames']
    scene.frame_set(0)
    rig['palm_arm_revision'] = 'V20 actual biological palm posterior, transported elbow hinge, bounded humeral/pronation/wrist correction; original skin and exact body action curves retained'
    bpy.ops.wm.save_as_mainfile(filepath=manifest['source'], compress=True)
    manifest['source_saved'], manifest['animation_fbx_exported'] = True, True
    write(OUT/'palm_arm_motion_manifest_v20.json', manifest)
    print('M07_V20_PALM_ARM_COMPLETE '+str(OUT), flush=True)


if __name__ == '__main__':
    main()
