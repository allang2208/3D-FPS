"""Author M07 gathering/release with linked body weight and delayed joints.

Keep the original skin/bind and current V20 idle endpoint. V23 locomotion is
not an input/output of this revision. Exports only two casting animations;
no render, runtime test, diagnostic pass or interactive editor launch.
"""
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Quaternion, Vector

PROJECT = Path('D:/FPS3D/FPSGAME')
ROOT = PROJECT/'SourceAssets/BlindSupplicantM07Meshy20261001'
OUT = ROOT/'FlowCastV24/Motion'
MASTER = ROOT/'PalmArmMotionV20/Motion/M07_Original_PalmArmMotion_V20.blend'
sys.path.insert(0, str(Path(__file__).parent))
import author_motion_v04 as motion
import author_running_v12 as running
import author_locomotion_death_v15 as export_tools
import author_palm_arm_motion_v20 as v20
from author_inward_arm_swing_v23 import arm_reference
from author_heavy_gait_v22 import ramp, rot, matrix, clamp, write
from author_cast_v15 import arc, solve_segments, pole_from_pose, signed_angle, limit_swing
from author_sweep_cast_v14 import palm_frame

FPS = 30
DURATIONS = {'MagicGather': 1.10, 'MagicRelease': 1.10}
CONTACT = .30
UP, RIGHT, FORWARD = Vector((0., 0., 1.)), Vector((1., 0., 0.)), Vector((0., -1., 0.))


def channels(role, t):
    if role == 'MagicGather':
        weight = ramp(t, .0, .64)
        chest = ramp(t, .08, .81)
        return dict(activity=ramp(t, .0, .36), hand=ramp(t, .16, 1.04),
            support=ramp(t, .10, .94), palm=ramp(t, .30, 1.07),
            fingers=ramp(t, .38, 1.08), push=0., opening=0., recovery=0.,
            pelvis_yaw=-2.6*weight, yaw=-8.*chest, lean=-2.*chest,
            shift=Vector((3.*weight, 2.8*weight, -3.*weight)),
            shoulder=5.*ramp(t, .13, .91), settle=0., role=role)
    # Contact remains at 0.30 s. Hips and chest lead the hand; the release
    # continues past contact and then descends along an outward recovery arc.
    brace = ramp(t, .0, .095)*(1.-ramp(t, .095, .20))
    hip = ramp(t, .055, .245)
    chest = ramp(t, .08, .29)
    push = ramp(t, .105, .34)-.075*brace
    recovery = ramp(t, .43, 1.10)
    retained = 1.-recovery
    settle = ramp(t, .32, .44)*(1.-ramp(t, .44, .67))
    return dict(activity=1.-ramp(t, .67, 1.10), hand=retained,
        support=1.-ramp(t, .46, 1.06), palm=1.-ramp(t, .52, 1.10),
        fingers=1.-ramp(t, .55, 1.10), push=push,
        opening=ramp(t, .175, .31), recovery=recovery,
        pelvis_yaw=(-2.6+5.2*hip)*retained,
        yaw=(-8.-1.5*brace+17.*chest)*retained,
        lean=(-2.-.6*brace+8.*chest-1.2*settle)*retained,
        shift=Vector(((3.-5.*hip)*retained, (2.8-7.*hip)*retained,
                      (-3.-.6*brace+1.6*hip-.8*settle)*retained)),
        shoulder=(5.-1.5*brace+7.*ramp(t, .09, .275))*retained,
        settle=settle, role=role)


def wrist_goal(side, shoulder, chest, delta, baseline, p):
    original = baseline['hand_'+side].translation-baseline['upperarm_'+side].translation
    hanging = shoulder+delta@original
    if side == 'r':
        support = chest+delta@Vector((-27., -36., -28.))
        support += delta@Vector((-5., 10., -5.))*(max(0., p['push'])*(1.-p['recovery']))
        goal = arc(hanging, hanging+delta@Vector((-7., -10., 12.)),
                   support+delta@Vector((-5., 9., -9.)), support, p['support'])
        active = p['support']
        cast_pole = Vector((-.70, -.08, -.90)).normalized()
    else:
        held = chest+delta@Vector((27., -43., -12.))
        extension = held+delta@Vector((5., -43., 11.))
        if p['role'] == 'MagicGather':
            goal = arc(hanging, hanging+delta@Vector((9., -9., 12.)),
                       held+delta@Vector((9., 11., -13.)), held, p['hand'])
        else:
            # The same moving outgoing endpoint feeds recovery, eliminating
            # the old separate linear-push / fixed-endpoint recovery switch.
            pushed = held.lerp(extension, p['push'])
            pushed += delta@Vector((1.2, 1.4, -1.8))*p['settle']
            goal = arc(pushed, pushed+delta@Vector((8., 9., -8.)),
                       hanging+delta@Vector((7., -17., 14.)), hanging, p['recovery'])
        active = p['hand']
        cast_pole = Vector((.9, .22, -.85)).normalized().lerp(
            Vector((.48, .02, -1.)).normalized(), max(0., p['push'])).normalized()
    old_pole = pole_from_pose(baseline['upperarm_'+side].translation,
        baseline['lowerarm_'+side].translation, baseline['hand_'+side].translation,
        Vector((1. if side == 'l' else -1., -.1, -.8)))
    return goal, delta@old_pole.lerp(cast_pole, active).normalized(), active


def hand_rotation(lower_q, lower_direction, rest, baseline, delta, reference, side, p):
    lower_delta = lower_q@rest['lowerarm_'+side].to_quaternion().inverted()
    if side == 'l':
        charged_frame = palm_frame(FORWARD, UP)
        release_frame = palm_frame(UP, FORWARD)
        cast_frame = charged_frame.slerp(release_frame, p['opening'])
        amount = p['palm']
    else:
        cast_frame = palm_frame(Vector((.1, -1., -.25)), Vector((.8, 0., .6)))
        amount = p['support']*.85
    reference_frame = palm_frame(reference['finger_along'], reference['palm_normal'])
    authored = delta@cast_frame@reference_frame.inverted()@rest['hand_'+side].to_quaternion()
    original = delta@baseline['hand_'+side].to_quaternion()
    goal = original.slerp(authored, amount)
    goal_delta = goal@rest['hand_'+side].to_quaternion().inverted()
    roll = signed_angle(lower_delta@reference['palm_normal'],
                        goal_delta@reference['palm_normal'], lower_direction)
    roll = clamp(roll, math.radians(-85.), math.radians(85.))*p['activity']
    lower_q = Quaternion(lower_direction, roll)@lower_q
    lower_delta = lower_q@rest['lowerarm_'+side].to_quaternion().inverted()
    base = lower_delta@rest['hand_'+side].to_quaternion()
    residual = (goal@base.inverted()).normalized()
    if residual.w < 0.:
        residual.negate()
    twist = 2.*math.atan2(Vector((residual.x, residual.y, residual.z)).dot(lower_direction), residual.w)
    swing = residual@Quaternion(lower_direction, twist).inverted()
    bounded = limit_swing(swing, 42.)@Quaternion(lower_direction, clamp(twist, math.radians(-10.), math.radians(10.)))
    return lower_q, (bounded@base).normalized()


def author_pose(rest, baseline, baseline_local, ordered, references, p):
    target, solved, hand_goals = {}, {}, {}
    for pose in ordered:
        name = pose.name
        parent = pose.parent.name if pose.parent else None
        target[name] = pose.bone.convert_local_to_pose(baseline_local[name], rest[name],
            **({'parent_matrix': target[parent], 'parent_matrix_local': rest[parent]} if parent else {}))
        position, q = target[name].translation.copy(), target[name].to_quaternion()
        if name == 'pelvis':
            position = baseline[name].translation+p['shift']
            q = rot(UP, p['pelvis_yaw'])@baseline[name].to_quaternion()
        elif name.startswith('spine_'):
            q = rot(UP, p['yaw']*.2)@rot(RIGHT, p['lean']*.2)@q
        elif name.startswith('neck_'):
            q = rot(UP, -p['yaw']*.12)@rot(RIGHT, -p['lean']*.14)@q
        elif name.startswith('clavicle_'):
            # One shoulder drives the cast; the support shoulder answers the
            # ribcage rotation without both arms sliding forward as a block.
            amount = p['shoulder']*(1. if name.endswith('_l') else -.45)
            q = rot(UP, -amount)@rot(FORWARD, amount*.12)@q
        target[name] = matrix(position, q)
        delta = (target['spine_05'].to_quaternion()@baseline['spine_05'].to_quaternion().inverted()
                 if 'spine_05' in target else Quaternion())
        if name.startswith('upperarm_'):
            side = name[-1]
            reference = references[side]
            goal, pole, active = wrist_goal(side, position, target['spine_05'].translation, delta, baseline, p)
            upper, lower, _ = solve_segments(goal-position, reference['upper_length'],
                reference['lower_length'], pole, .9999-.06*active)
            hinge = upper.cross(lower).normalized()
            du = (motion.anatomical_frame(upper, hinge)@reference['reference_frame'].transposed()).to_quaternion()
            bend = math.atan2(hinge.dot(upper.cross(lower)), upper.dot(lower))
            dl = du@Quaternion(reference['hinge'], bend-reference['rest_bend'])
            q = q.slerp(du@rest[name].to_quaternion(), p['activity'])
            solved[side] = dl@rest['lowerarm_'+side].to_quaternion()
        elif name.startswith('lowerarm_'):
            side = name[-1]
            q = q.slerp(solved[side], p['activity'])
            lower_direction = (q@rest[name].to_quaternion().inverted())@references[side]['lower']
            q, hand_goals[side] = hand_rotation(q, lower_direction, rest, baseline, delta, references[side], side, p)
        elif name.startswith('hand_'):
            q = q.slerp(hand_goals[name[-1]], p['activity'])
        elif name.startswith(('index_', 'middle_', 'ring_', 'pinky_', 'thumb_')) and '_metacarpal_' not in name:
            digit, segment, side = name.split('_')
            segment = int(segment)-1
            delay = {'thumb': 0., 'index': .012, 'middle': .024, 'ring': .045, 'pinky': .065}[digit]+segment*.012
            amount = clamp((p['fingers']-delay)/(1.-delay), 0., 1.) if side == 'l' else p['support']*.65
            gather = (12., 20., 16.)[segment]*(.75 if digit == 'thumb' else 1.)
            opening = clamp((p['opening']-delay)/(1.-delay), 0., 1.) if side == 'l' else .0
            flex = gather*(1.-opening)+(1., 5., 4.)[segment]*opening
            base = pose.bone.convert_local_to_pose(Matrix.Identity(4), rest[name],
                parent_matrix=target[parent], parent_matrix_local=rest[parent])
            direction = base.to_quaternion()@Vector((0., 1., 0.))
            palm = (target['hand_'+side].to_quaternion()@rest['hand_'+side].to_quaternion().inverted())@references[side]['palm_normal']
            q = q.slerp(rot(direction.cross(palm).normalized(), flex)@base.to_quaternion(), amount)
        elif name.startswith('thigh_'):
            side = name[-1]
            a, b, c = [baseline[part+'_'+side].translation for part in ('thigh', 'calf', 'foot')]
            pelvis = target['pelvis'].to_quaternion()@baseline['pelvis'].to_quaternion().inverted()
            pole = pelvis@pole_from_pose(a, b, c, FORWARD)
            upper, lower, _ = solve_segments(c-position, (b-a).length, (c-b).length, pole, .99999)
            q = (pelvis@(b-a).normalized()).rotation_difference(upper)@pelvis@baseline[name].to_quaternion()
            solved['leg_'+side] = (pelvis@(c-b).normalized()).rotation_difference(lower)@pelvis@baseline['calf_'+side].to_quaternion()
        elif name.startswith('calf_'):
            q = solved['leg_'+name[-1]]
        elif name.startswith('foot_'):
            q = baseline[name].to_quaternion()
        elif name.startswith('gill_'):
            segment = int(name.split('_')[-1])
            # Mild follow-through on the original appendage bones only.
            lag = p['settle']*(1.+segment*.45)
            q = rot(RIGHT, -1.8*lag)@q
        target[name] = matrix(position, q)
    return target


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(MASTER))
    rig = v20.original_rig()
    rig.data.pose_position = 'POSE'
    ordered = sorted(rig.pose.bones, key=lambda p: len(p.bone.parent_recursive))
    rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
    motion.activate(rig, bpy.data.actions['A_M07_Idle_PalmArmV20'])
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()
    baseline = {p.name: p.matrix.copy() for p in ordered}
    baseline_local = {p.name: p.bone.convert_local_to_pose(baseline[p.name], rest[p.name],
        **({'parent_matrix': baseline[p.parent.name], 'parent_matrix_local': rest[p.parent.name]} if p.parent else {}),
        invert=True) for p in ordered}
    references = {side: arm_reference(rest, side) for side in ('l', 'r')}
    hidden = {o.name: o.hide_viewport for o in bpy.data.objects if o.type == 'MESH'}
    for name in hidden:
        bpy.data.objects[name].hide_viewport = True
    scene = bpy.context.scene
    scene.render.fps, scene.render.fps_base = FPS, 1.
    scene.unit_settings.system, scene.unit_settings.scale_length = 'METRIC', .01
    manifest = dict(revision='FlowCastV24', fps=FPS, source=str(OUT/'M07_Original_FlowCast_V24.blend'),
        source_master=str(MASTER), baseline_action='A_M07_Idle_PalmArmV20',
        reference_skeleton='/Game/Monsters/BlindSupplicantM07/SK_M07_ReferenceOriginalV11',
        bone_names=list(rest), release_contact_seconds=CONTACT, charge_forward_offset_cm=65.,
        scope='MagicGather/MagicRelease only; V23 movement untouched; original skin and bind retained',
        choreography='Weight/hips lead ribcage and scapula, bent elbows send hands on arcs; wrist/fingers release later; counterbalancing right arm and yielding recovery',
        source_saved=False, animation_fbx_exported=False, ue_imported=False, ue_saved=False,
        tested=False, runtime_tested=False, rendered=False, visual_accepted=False, user_review_pending=True, clips={})
    actions = {}
    charged = author_pose(rest, baseline, baseline_local, ordered, references, channels('MagicGather', DURATIONS['MagicGather']))
    for role, duration in DURATIONS.items():
        action = bpy.data.actions.new('A_M07_'+role+'_FlowCastV24')
        action.use_fake_user = True
        motion.activate(rig, action)
        previous = {}
        count = round(duration*FPS)+1
        for index in range(count):
            if (role == 'MagicGather' and index == 0) or (role == 'MagicRelease' and index == count-1):
                target = baseline
            elif (role == 'MagicGather' and index == count-1) or (role == 'MagicRelease' and index == 0):
                target = charged
            else:
                target = author_pose(rest, baseline, baseline_local, ordered, references, channels(role, index/FPS))
            running.insert_frame(rig, target, rest, ordered, index+1, previous)
        scene.frame_set(0)
        for pose in ordered:
            pose.matrix_basis = Matrix.Identity(4)
            for channel in ('location', 'rotation_quaternion', 'scale'):
                pose.keyframe_insert(data_path=channel, frame=0, group=pose.name)
        for curve in running.curves(action):
            for key in curve.keyframe_points:
                key.interpolation = 'LINEAR'
        fbx = OUT/('A_M07_'+role+'.fbx')
        export_tools.export(rig, action, fbx, count)
        actions[role] = action
        manifest['clips'][role] = dict(role=role, action=action.name, file=str(fbx),
            asset='/Game/Monsters/BlindSupplicantM07/AnimationsFlowCastV24/A_M07_'+role,
            fps=FPS, frames=count, duration_seconds=duration, loop=False, root_motion=False,
            reference_only_blender_frame=0, exported_blender_frame_start=1, exported_blender_frame_end=count)
        print('M07_V24_CAST_EXPORTED '+role+' '+str(fbx), flush=True)
    for name, value in hidden.items():
        bpy.data.objects[name].hide_viewport = value
    motion.activate(rig, actions['MagicGather'])
    scene.frame_start, scene.frame_end = 1, manifest['clips']['MagicGather']['frames']
    scene.frame_set(1)
    rig['casting_revision'] = 'V24 linked gather and release with exact current-idle / shared-gather endpoints'
    bpy.ops.wm.save_as_mainfile(filepath=manifest['source'], compress=True)
    manifest.update(source_saved=True, animation_fbx_exported=True)
    write(OUT/'flow_cast_manifest_v24.json', manifest)
    print('M07_V24_CAST_SOURCE_SAVED '+str(OUT), flush=True)


if __name__ == '__main__':
    main()
