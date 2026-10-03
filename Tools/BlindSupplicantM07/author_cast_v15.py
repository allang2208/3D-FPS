"""Reauthor M07's two-stage cast from its actual hanging-arm idle pose.

Retains the V13 Meshy body, UVs, weights and immutable 83-bone reference.
V14 swept attacks and all unrelated actions remain in the editable master.
Only the two casting actions are exported. No UE, render or game is started.
"""
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Quaternion, Vector

PROJECT = Path('D:/FPS3D/FPSGAME')
ROOT = PROJECT/'SourceAssets/BlindSupplicantM07Meshy20261001'
MASTER = ROOT/'CombatMagicV14/Motion/M07_Original_SweepCasting_V14.blend'
OUT = ROOT/'MotionRecoveryV15/Casting'
FPS = 30
GATHER_SECONDS = 1.10
RELEASE_SECONDS = .80
RELEASE_CONTACT = .30
UP = Vector((0, 0, 1))
RIGHT = Vector((1, 0, 0))
FWD = Vector((0, -1, 0))
sys.path.insert(0, str(Path(__file__).parent))
import author_motion_v04 as motion
from author_sweep_cast_v14 import export, palm_frame, hermite, GATHER_KEYS
from repair_attack_arms_v13 import curves, track


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def clamp(value, low=0., high=1.):
    return min(high, max(low, value))


def ease(value):
    value = clamp(value)
    return value**3*(10.-15.*value+6.*value**2)


def arc(a, b, c, d, amount):
    other = 1.-amount
    return a*other**3+b*(3.*other*other*amount)+c*(3.*other*amount*amount)+d*amount**3


def angle(q):
    return math.degrees(2.*math.acos(clamp(abs(q.normalized().w))))


def limit_swing(q, maximum):
    q = q.normalized()
    if q.w < 0:
        q.negate()
    return Quaternion().slerp(q, min(1., maximum/max(angle(q), 1.e-8)))


def signed_angle(a, b, axis):
    a = a-axis*a.dot(axis)
    b = b-axis*b.dot(axis)
    if a.length < 1.e-6 or b.length < 1.e-6:
        return 0.
    a.normalize()
    b.normalize()
    return math.atan2(axis.dot(a.cross(b)), clamp(a.dot(b), -1., 1.))


def pole_from_pose(a, b, c, fallback):
    axis = (c-a).normalized()
    pole = b-a-axis*(b-a).dot(axis)
    return pole.normalized() if pole.length > .001 else fallback.normalized()


def solve_segments(relative, upper_length, lower_length, pole, ceiling=.94):
    """Fixed lengths, continuous outward/downward anatomical elbow support."""
    reach = clamp(relative.length, abs(upper_length-lower_length)+.25,
                  (upper_length+lower_length)*ceiling)
    axis = relative.normalized()
    plane_pole = pole-axis*pole.dot(axis)
    if plane_pole.length < .001:
        plane_pole = RIGHT-axis*RIGHT.dot(axis)
    plane_pole.normalize()
    along = (upper_length**2+reach**2-lower_length**2)/(2.*reach)
    height = math.sqrt(max(0., upper_length**2-along**2))
    elbow = axis*along+plane_pole*height
    wrist = axis*reach
    return elbow.normalized(), (wrist-elbow).normalized(), wrist


def choreography(role, seconds):
    """Gather endpoint and release entry share the same complete body state."""
    if role == 'MagicGather':
        phase = clamp(seconds/1.0)
        hand = hermite(GATHER_KEYS, phase)
        pelvis = ease((seconds-.02)/.94)
        torso = ease((seconds-.05)/.91)
        return {'stage': 'gather' if seconds < 1.0 else 'charged_hold',
                'gather': hand, 'push': 0., 'recovery': 0.,
                'pelvis': pelvis, 'torso': torso, 'yaw': -5.*torso,
                'lean': 1.5*torso, 'pelvis_yaw': -1.6*pelvis,
                'pelvis_shift': Vector((1.5*pelvis, 1.2*pelvis, -1.7*pelvis)),
                'clavicle_protraction': 3.5*ease((seconds-.13)/.80),
                'palm': ease((seconds-.26)/.69), 'release_palm': 0.,
                'finger': ease((seconds-.19)/.68),
                'right_support': ease((seconds-.12)/.85),
                'elbow_support': ease((seconds-.13)/.84), 'recoil': 0.}
    # Torso/shoulder start first, elbow follows and the wrist turns last.
    # The first .08s draws the supported hand back a little, not forwards.
    push = track(seconds, [(0, 0.), (.08, -.065), (.14, .05),
                           (.22, .64), (.30, 1.), (.40, 1.), (.80, 0.)])
    recovery = ease((seconds-.42)/.38)
    lead = track(seconds, [(0, 0.), (.07, -.12), (.17, .45), (.27, 1.),
                           (.40, 1.), (.80, 0.)])
    if seconds < .08:
        stage = 'coiled_anticipation'
    elif seconds < .30:
        stage = 'shoulder_elbow_palm_push'
    elif seconds < .42:
        stage = 'contact_recoil_and_hold'
    else:
        stage = 'complete_body_recovery'
    recoil = 0.
    if RELEASE_CONTACT < seconds < .42:
        age = seconds-RELEASE_CONTACT
        recoil = math.sin(2.*math.pi*9.*age)*ease(age/.015)*(1.-ease(age/.12))
    return {'stage': stage, 'gather': 1., 'push': push, 'recovery': recovery,
            'pelvis': 1.-recovery, 'torso': 1.-recovery,
            'yaw': track(seconds, [(0, -5.), (.08, -6.), (.27, 5.5), (.40, 5.5), (.80, 0.)]),
            'lean': track(seconds, [(0, 1.5), (.08, .9), (.27, 4.2), (.40, 4.2), (.80, 0.)]),
            'pelvis_yaw': track(seconds, [(0, -1.6), (.10, -2.), (.27, 2.4), (.40, 2.4), (.80, 0.)]),
            'pelvis_shift': Vector((track(seconds, [(0, 1.5), (.10, 1.8), (.30, -.8), (.42, -.8), (.80, 0.)]),
                                   track(seconds, [(0, 1.2), (.10, 1.7), (.30, -3.3), (.42, -3.3), (.80, 0.)]),
                                   track(seconds, [(0, -1.7), (.10, -2.4), (.30, -.7), (.42, -.7), (.80, 0.)]))),
            'clavicle_protraction': (3.5+3.*lead)*(1.-recovery),
            'palm': 1.-recovery,
            'release_palm': ease((seconds-.15)/.15)*(1.-recovery),
            'finger': 1.-ease((seconds-.50)/.30),
            'right_support': (1.-recovery), 'elbow_support': 1.-recovery,
            'recoil': recoil}


def base_pose(rig, manifest):
    action = bpy.data.actions[manifest['clips']['Idle']['action']]
    motion.activate(rig, action)
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()
    return ({p.name: p.matrix.copy() for p in rig.pose.bones},
            {p.name: p.matrix_basis.copy() for p in rig.pose.bones})


def diagnose_v14(rig, old_manifest, baseline):
    """Requested source diagnosis, not an automatic visual/game test."""
    report = {}
    for role in ('MagicGather', 'MagicRelease'):
        entry = old_manifest['clips'][role]
        motion.activate(rig, bpy.data.actions[entry['action']])
        samples = []
        for frame in (1, entry['frames']):
            bpy.context.scene.frame_set(frame)
            bpy.context.view_layer.update()
            shoulder = rig.pose.bones['upperarm_l'].matrix.translation.copy()
            elbow = rig.pose.bones['lowerarm_l'].matrix.translation.copy()
            wrist = rig.pose.bones['hand_l'].matrix.translation.copy()
            samples.append({'frame': frame, 'seconds': (frame-1)/FPS,
                            'shoulder_cm': list(shoulder), 'elbow_cm': list(elbow),
                            'wrist_cm': list(wrist),
                            'wrist_distance_to_actual_idle_cm': (wrist-baseline['hand_l'].translation).length,
                            'shoulder_wrist_reach_cm': (wrist-shoulder).length,
                            'elbow_bend_deg': math.degrees((elbow-shoulder).angle(wrist-elbow))})
        report[role] = samples
    return {'scope': 'User-reported preextended/stiff V14 cast source and anatomy diagnosis',
            'cause': 'V14 resets arm locals to identity, including the clavicle. Reference upperarm/forearm are lateral straight bones, not the actual hanging-arm idle. The IK entrance and recovery point use the reference wrist delta, making start/end reach sideways before/after the staged gesture. Gather also copies the FP reach ratio (.68), unnecessarily stretching the third-person charged posture. Gather end/release start additionally sample different idle body frames.',
            'old_samples': report, 'baseline_idle_wrist_l_cm': list(baseline['hand_l'].translation),
            'baseline_idle_wrist_r_cm': list(baseline['hand_r'].translation),
            'runtime_tested': False, 'rendered': False}


def desired_palm(rest, baseline, side, body_delta, parameters):
    hand = 'hand_'+side
    source_along = (rest['middle_01_'+side].translation-rest[hand].translation).normalized()
    source_across = (rest['index_01_'+side].translation-rest['pinky_01_'+side].translation).normalized()
    source_normal = source_along.cross(source_across).normalized()
    reference = palm_frame(source_along, source_normal)
    hanging = body_delta@baseline[hand].to_quaternion()
    if side == 'r':
        # The right hand softly supports below the casting palm; it never
        # performs a mirrored attack or a second fully extended palm push.
        along = body_delta@Vector((-.12, -.74, -.66)).normalized()
        normal = body_delta@Vector((.35, -.65, .67)).normalized()
        support = palm_frame(along, normal)@reference.inverted()@rest[hand].to_quaternion()
        return hanging.slerp(support, parameters['right_support']*.60), source_across
    gather = (palm_frame(body_delta@Vector((-.08, -.94, .33)), body_delta@UP)
              @reference.inverted()@rest[hand].to_quaternion())
    released = (palm_frame(body_delta@Vector((-.03, -.28, .96)), body_delta@FWD)
                @reference.inverted()@rest[hand].to_quaternion())
    goal = gather.slerp(released, parameters['release_palm'])
    return hanging.slerp(goal, parameters['palm']), source_across


def hand_and_forearm(lower_q, lower_direction, goal, across, rest, side, support):
    lower_name, hand_name = 'lowerarm_'+side, 'hand_'+side
    delta = lower_q@rest[lower_name].to_quaternion().inverted()
    hand_delta = goal@rest[hand_name].to_quaternion().inverted()
    # Full hand orientation is deliberately NOT copied into the forearm:
    # upright-palm wrist extension must not become a nearly 90deg arm twist.
    width = delta@across
    desired_width = hand_delta@across
    roll = clamp(signed_angle(width, desired_width, lower_direction),
                 math.radians(-38.), math.radians(38.))*support
    lower_q = Quaternion(lower_direction, roll)@lower_q
    base = lower_q@rest[lower_name].to_quaternion().inverted()@rest[hand_name].to_quaternion()
    residual = goal@base.inverted()
    if residual.w < 0:
        residual.negate()
    axis = lower_direction.normalized()
    twist_angle = 2.*math.atan2(Vector((residual.x, residual.y, residual.z)).dot(axis), residual.w)
    twist = Quaternion(axis, twist_angle)
    swing = residual@twist.inverted()
    bounded = limit_swing(swing, 32.)@Quaternion(axis, clamp(twist_angle, math.radians(-10.), math.radians(10.)))
    return lower_q.normalized(), (bounded@base).normalized(), math.degrees(roll), angle(bounded)


def wrist_and_pole(side, shoulder, thorax, body_delta, baseline, parameters):
    base_shoulder = baseline['upperarm_'+side].translation
    base_wrist = baseline['hand_'+side].translation
    hanging = shoulder+body_delta@(base_wrist-base_shoulder)
    if side == 'r':
        support = thorax+body_delta@Vector((-20., -30., -25.))
        goal = arc(hanging, hanging+body_delta@Vector((-5., -8., 9.)),
                   support+body_delta@Vector((-6., 4., -6.)), support,
                   parameters['right_support'])
        initial = pole_from_pose(base_shoulder, baseline['lowerarm_r'].translation,
                                 base_wrist, Vector((-1, -.2, -.3)))
        pole = body_delta@initial.lerp(Vector((-.72, -.28, -.84)).normalized(),
                                      parameters['right_support']).normalized()
        return goal, pole
    chest = thorax+body_delta@Vector((24., -32., -11.))
    pushed = thorax+body_delta@Vector((30., -84., -3.))
    if parameters['stage'] in ('gather', 'charged_hold'):
        goal = arc(hanging, hanging+body_delta@Vector((7., -10., 4.)),
                   chest+body_delta@Vector((8., 4., -11.)), chest, parameters['gather'])
    else:
        goal = chest.lerp(pushed, parameters['push'])
        if parameters['recovery'] > 0.:
            # Entire supported limb descends on an arc; it never returns to
            # the sideways reference wrist or retracts through the thorax.
            goal = arc(pushed, pushed+body_delta@Vector((5., 9., -6.)),
                       hanging+body_delta@Vector((4., -10., 9.)), hanging,
                       parameters['recovery'])
        goal += body_delta@Vector((.25, 1.6, .4))*parameters['recoil']
    initial = pole_from_pose(base_shoulder, baseline['lowerarm_l'].translation,
                             base_wrist, Vector((1, -.2, -.3)))
    charged_pole = Vector((.95, .35, -.85)).normalized()
    push_pole = Vector((.36, -.02, -1.)).normalized()
    supported_pole = charged_pole.lerp(push_pole, clamp(parameters['push'])).normalized()
    pole = body_delta@initial.lerp(supported_pole, parameters['elbow_support']).normalized()
    return goal, pole


def author_action(rig, rest, baseline, baseline_local, ordered, role, frame_count, config):
    action = bpy.data.actions.new('A_M07_'+role+'_AnatomicalV15')
    action.use_fake_user = True
    motion.activate(rig, action)
    for p in ordered:
        p.rotation_mode = 'QUATERNION'
        p.matrix_basis = Matrix.Identity(4)
        for channel in ('location', 'rotation_quaternion', 'scale'):
            p.keyframe_insert(data_path=channel, frame=0)
    previous_q, samples, poses = {}, [], []
    for index in range(frame_count):
        frame, seconds = index+1, index/FPS
        bpy.context.scene.frame_set(frame)
        parameters = choreography(role, seconds)
        target, desired_lower, hand_goal = {}, {}, {}
        row = {'frame': frame, 'seconds': seconds, 'stage': parameters['stage'],
               'body_yaw_deg': parameters['yaw'], 'body_lean_deg': parameters['lean'],
               'pelvis_translation_cm': list(parameters['pelvis_shift']), 'arms': {}}
        for p in ordered:
            name, parent = p.name, p.parent.name if p.parent else None
            target[name] = p.bone.convert_local_to_pose(baseline_local[name], rest[name],
                **({'parent_matrix': target[parent], 'parent_matrix_local': rest[parent]} if parent else {}))
            if name == 'pelvis':
                q = Quaternion(UP, math.radians(parameters['pelvis_yaw']))@baseline[name].to_quaternion()
                target[name] = Matrix.LocRotScale(baseline[name].translation+parameters['pelvis_shift'],
                                                q, Vector((1, 1, 1)))
            elif name in ('spine_01', 'spine_02', 'spine_03', 'spine_04', 'spine_05'):
                # Countertwist/lean are distributed over the complete trunk;
                # the neck countertracks slightly rather than fixing the head.
                q = (Quaternion(UP, math.radians(parameters['yaw']*.20))
                     @Quaternion(RIGHT, math.radians(parameters['lean']*.20))@target[name].to_quaternion())
                target[name] = Matrix.LocRotScale(target[name].translation, q, Vector((1, 1, 1)))
            elif name in ('neck_01', 'neck_02'):
                q = (Quaternion(UP, math.radians(-parameters['yaw']*.11))
                     @Quaternion(RIGHT, math.radians(-parameters['lean']*.08))@target[name].to_quaternion())
                target[name] = Matrix.LocRotScale(target[name].translation, q, Vector((1, 1, 1)))
            elif name.startswith('clavicle_'):
                # Third-person support comes from rotating the real clavicle,
                # never translating/scaling the FP shoulder through the torso.
                sign = 1 if name.endswith('_l') else -1
                factor = 1. if sign > 0 else -.35
                q = Quaternion(UP, math.radians(-sign*parameters['clavicle_protraction']*factor))@target[name].to_quaternion()
                target[name] = Matrix.LocRotScale(target[name].translation, q, Vector((1, 1, 1)))
            torso = (target['spine_05'].to_quaternion()@baseline['spine_05'].to_quaternion().inverted()
                     if 'spine_05' in target else Quaternion())
            if name.startswith('upperarm_'):
                side = name[-1]
                a, b, c = [baseline[n+'_'+side].translation for n in ('upperarm', 'lowerarm', 'hand')]
                upper_length, lower_length = (b-a).length, (c-b).length
                goal, pole = wrist_and_pole(side, target[name].translation,
                                             target['spine_05'].translation, torso, baseline, parameters)
                support = parameters['elbow_support'] if side == 'l' else parameters['right_support']
                ceiling = .9999-(.9999-.94)*support
                # The source idle reaches slightly beyond .94. Fade the cast
                # reach ceiling in/out, so the actual entering/returning idle
                # remains exact rather than stopping ~2cm before its wrist.
                u, l, reached = solve_segments(goal-target[name].translation,
                                               upper_length, lower_length, pole, ceiling)
                transport = torso@(b-a).normalized()
                q = transport.rotation_difference(u)@torso@baseline[name].to_quaternion()
                # Palm width carries at most a small supported humeral roll.
                palm, across = desired_palm(rest, baseline, side, torso, parameters)
                delta = q@rest[name].to_quaternion().inverted()
                palm_delta = palm@rest['hand_'+side].to_quaternion().inverted()
                share = clamp(signed_angle(delta@across, palm_delta@across, u)*.12,
                              math.radians(-8.), math.radians(8.))*parameters['palm']
                q = Quaternion(u, share)@q
                target[name] = Matrix.LocRotScale(target[name].translation, q, Vector((1, 1, 1)))
                desired_lower[side] = l
                hand_goal[side] = (palm, across)
                row['arms'][side] = {'requested_wrist_cm': list(goal), 'upper_roll_deg': math.degrees(share),
                                    'elbow_bend_deg': math.degrees(u.angle(l)),
                                    'reach_fraction': reached.length/(upper_length+lower_length)}
            elif name.startswith('lowerarm_'):
                side = name[-1]
                base_direction = (baseline['hand_'+side].translation-baseline[name].translation).normalized()
                direction = desired_lower[side]
                q = (torso@base_direction).rotation_difference(direction)@torso@baseline[name].to_quaternion()
                palm, across = hand_goal[side]
                q, palm, roll, residual = hand_and_forearm(q, direction, palm, across, rest, side,
                                                          parameters['palm'] if side == 'l' else parameters['right_support']*.6)
                target[name] = Matrix.LocRotScale(target[name].translation, q, Vector((1, 1, 1)))
                hand_goal[side] = palm
                row['arms'][side].update(forearm_roll_deg=roll, wrist_residual_deg=residual)
            elif name.startswith('hand_'):
                side = name[-1]
                target[name] = Matrix.LocRotScale(target[name].translation, hand_goal[side], Vector((1, 1, 1)))
            elif name.startswith(('thumb_', 'index_', 'middle_', 'ring_', 'pinky_')) and '_metacarpal_' not in name:
                side = name[-1]
                digit, segment = name.split('_')[0], int(name.split('_')[1])-1
                if side == 'l':
                    data = config['digits'][digit]
                    amount = parameters['finger']
                    release = parameters['release_palm']
                    flex = (data['gather_flex'][segment]*(1.-release)+data['release_flex'][segment]*release)
                    # Bone-local baseline is the actual curled idle. Blend it
                    # out while opening in staggered digit/segment order.
                    delay = {'thumb': 0., 'index': .015, 'middle': .025, 'ring': .05, 'pinky': .075}[digit]+segment*.015
                    weight = clamp((amount-delay)/(1.-delay))
                    hand_delta = target['hand_l'].to_quaternion()@rest['hand_l'].to_quaternion().inverted()
                    along = (rest['middle_01_l'].translation-rest['hand_l'].translation).normalized()
                    across = (rest['index_01_l'].translation-rest['pinky_01_l'].translation).normalized()
                    normal = hand_delta@along.cross(across).normalized()
                    direction = target[name].to_3x3()@Vector((0, 1, 0))
                    axis = direction.cross(normal).normalized()
                    # Original digit baseline is interpolated locally, keeping
                    # MCP/PIP/DIP continuity instead of snapping all segments.
                    authored_local = Matrix.Identity(4)
                    base = p.bone.convert_local_to_pose(authored_local, rest[name],
                                parent_matrix=target[parent], parent_matrix_local=rest[parent])
                    q = Quaternion(axis, math.radians(flex))@base.to_quaternion()
                    q = target[name].to_quaternion().slerp(q, weight)
                    target[name] = Matrix.LocRotScale(target[name].translation, q, Vector((1, 1, 1)))
            elif name.startswith('thigh_'):
                side = name[-1]
                a, b, c = [baseline[n+'_'+side].translation for n in ('thigh', 'calf', 'foot')]
                pelvis_delta = target['pelvis'].to_quaternion()@baseline['pelvis'].to_quaternion().inverted()
                pole = pelvis_delta@pole_from_pose(a, b, c, FWD)
                u, l, _ = solve_segments(c-target[name].translation, (b-a).length, (c-b).length, pole, .9999)
                q = (pelvis_delta@(b-a).normalized()).rotation_difference(u)@pelvis_delta@baseline[name].to_quaternion()
                target[name] = Matrix.LocRotScale(target[name].translation, q, Vector((1, 1, 1)))
                desired_lower['leg_'+side] = l
            elif name.startswith('calf_'):
                side = name[-1]
                pelvis_delta = target['pelvis'].to_quaternion()@baseline['pelvis'].to_quaternion().inverted()
                original = (baseline['foot_'+side].translation-baseline[name].translation).normalized()
                direction = desired_lower['leg_'+side]
                q = (pelvis_delta@original).rotation_difference(direction)@pelvis_delta@baseline[name].to_quaternion()
                target[name] = Matrix.LocRotScale(target[name].translation, q, Vector((1, 1, 1)))
            elif name.startswith('foot_'):
                target[name] = Matrix.LocRotScale(target[name].translation, baseline[name].to_quaternion(), Vector((1, 1, 1)))
            p.matrix_basis = p.bone.convert_local_to_pose(target[name], rest[name],
                **({'parent_matrix': target[parent], 'parent_matrix_local': rest[parent]} if parent else {}), invert=True)
            p.rotation_mode = 'QUATERNION'
            q = p.rotation_quaternion.copy()
            if name in previous_q and q.dot(previous_q[name]) < 0:
                q.negate()
            p.rotation_quaternion = q
            previous_q[name] = q.copy()
            p.scale = Vector((1, 1, 1))
            if name != 'pelvis':
                p.location = Vector()
            for channel in ('location', 'rotation_quaternion', 'scale'):
                p.keyframe_insert(data_path=channel, frame=frame)
        for side in ('l', 'r'):
            row['arms'][side].update({part+'_cm': list(target[part+'_'+side].translation)
                                      for part in ('upperarm', 'lowerarm', 'hand')})
            row.setdefault('grounding', {})[side] = {
                'foot_cm': list(target['foot_'+side].translation),
                'ball_cm': list(target['ball_'+side].translation),
                'foot_departure_cm': (target['foot_'+side].translation-baseline['foot_'+side].translation).length}
        samples.append(row)
        poses.append({n: m.copy() for n, m in target.items()})
    for curve in curves(action):
        for key in curve.keyframe_points:
            key.interpolation = 'LINEAR'
    return action, samples, poses


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(MASTER))
    rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
    ordered = sorted(rig.pose.bones, key=lambda p: len(p.bone.parent_recursive))
    old = json.loads((ROOT/'CombatMagicV14/Motion/motion_manifest_v14.json').read_text(encoding='utf-8'))
    original = json.loads((ROOT/'RecoveryOriginalV13/motion_manifest_v13.json').read_text(encoding='utf-8'))
    baseline, baseline_local = base_pose(rig, original)
    diagnosis = diagnose_v14(rig, old, baseline)
    config = json.loads((PROJECT/'Content/ColdSteelData/Skills/fireball_hand_pose.json').read_text(encoding='utf-8'))
    scene = bpy.context.scene
    scene.render.fps, scene.render.fps_base = FPS, 1.
    scene.unit_settings.system, scene.unit_settings.scale_length = 'METRIC', .01
    rig.data.pose_position = 'POSE'
    saved, all_samples, all_poses, actions = {}, {}, {}, {}
    for role, frames, contact in (('MagicGather', 34, None), ('MagicRelease', 25, RELEASE_CONTACT)):
        action, samples, poses = author_action(rig, rest, baseline, baseline_local, ordered, role, frames, config)
        actions[role] = action
        file = OUT/('A_M07_'+role+'.fbx')
        export(rig, action, file, frames)
        saved[role] = {'file': str(file), 'action': action.name, 'frames': frames, 'fps': FPS,
                       'duration': (frames-1)/FPS, 'seconds': (frames-1)/FPS,
                       'asset': '/Game/Monsters/BlindSupplicantM07/AnimationsMotionRecoveryV15/A_M07_'+role,
                       'contact_seconds': contact, 'impact_seconds': contact,
                       'loop': False, 'root_motion': False, 'hold_last_pose': role == 'MagicGather',
                       'reference_only_blender_frame': 0, 'exported_blender_frame_start': 1,
                       'exported_blender_frame_end': frames, 'bone_tracks': list(rest)}
        all_samples[role], all_poses[role] = samples, poses
        print('M07_V15_CAST_EXPORTED '+role+' '+str(file), flush=True)
    motion.activate(rig, actions['MagicGather'])
    scene.frame_start, scene.frame_end = 1, 34
    scene.frame_set(0)
    source = OUT/'M07_Original_Casting_Anatomical_V15.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(source), compress=True)
    # These numbers describe the authored coordinates, not a rendered or PIE
    # acceptance claim. They make the handoff/grounding contract editable.
    seam = {n: {'translation_cm': (all_poses['MagicGather'][-1][n].translation-all_poses['MagicRelease'][0][n].translation).length,
                 'rotation_deg': angle(all_poses['MagicGather'][-1][n].to_quaternion().inverted()@all_poses['MagicRelease'][0][n].to_quaternion())}
            for n in rest}
    manifest = {'revision': 'CastingAnatomicalV15', 'fps': FPS, 'source': str(source),
                'source_master': str(MASTER), 'clips': saved,
                'ue_skeleton': original.get('ue_skeleton', '/Game/Monsters/BlindSupplicantM07/SK_M07_ReferenceOriginalV11'),
                'bone_names': list(rest), 'reference_bones': {n: motion.rows(m) for n, m in rest.items()},
                'mesh_geometry_uv_skin_and_reference_preserved': True,
                'bone_lengths_preserved': True, 'child_location_policy': 'zero on all children; original reference/unit scales; pelvis root movement only',
                'timing': {'gather_seconds': GATHER_SECONDS, 'release_seconds': RELEASE_SECONDS,
                           'release_contact_seconds': RELEASE_CONTACT, 'total_cast_contact_seconds': GATHER_SECONDS+RELEASE_CONTACT,
                           'release_anticipation': [0., .08], 'release_push': [.08, .30],
                           'release_contact_hold': [.30, .42], 'release_full_body_recovery': [.42, .80]},
                'casting_identity': 'Actual idle hanging-arm entrance; left hand coils near the chest palm up, right hand softly supports below; only release pushes the left palm toward the target; complete torso/pelvis/shoulder/elbow/wrist/finger return to the actual idle',
                'player_reference': ['Source/FPSGAME/Skills/FireballCastMotion.h', 'Source/FPSGAME/Skills/FPSCastingMeshComponent.cpp',
                                     'Content/ColdSteelData/Skills/fireball_hand_pose.json'],
                'method': 'Fixed-length two-segment solve from actual V13 idle, actual clavicle rotations, continuous original elbow support plane, body-relative minimal segment swing; forearm roll derived only from palm width, not full hand orientation. Pelvis shifts/countertwist drive the spine and shoulders; thigh/calf solve keeps original planted ankle and foot frames.',
                'arm_limits': {'upper_roll_deg': 8., 'forearm_roll_deg': 38., 'wrist_swing_deg': 32., 'wrist_twist_deg': 10., 'maximum_reach_fraction': .94},
                'grounding_contract': {'left_ankle': list(baseline['foot_l'].translation),
                                       'right_ankle': list(baseline['foot_r'].translation),
                                       'feet': 'Both ankles and original foot/ball frames remain planted during the light crouch/weight shift; no root motion'},
                'gather_release_seam': seam, 'authoring_samples': all_samples,
                'source_diagnosis': diagnosis, 'source_saved': True, 'animation_fbx_exported': True,
                'ue_imported': False, 'runtime_tested': False, 'rendered': False, 'visual_accepted': False}
    write(OUT/'casting_manifest_v15.json', manifest)
    print('M07_V15_CAST_MASTER_SAVED '+str(source), flush=True)


if __name__ == '__main__':
    main()
