"""Author M07's heavy, deliberate walk from the original anatomical bind.

One shared support clock coordinates foot roll, load transfer, yielding knees,
pelvis, five spinal joints, scapulae, elbows, wrists and gill follow-through.
This is original choreography for the user's giant/robot brief, not a retimed
jog or a claim to reproduce motion capture. Only two locomotion clips export.
No runtime tests, screenshots, acceptance renders or interactive UE launch.
"""
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Quaternion, Vector

PROJECT = Path('D:/FPS3D/FPSGAME')
ROOT = PROJECT / 'SourceAssets/BlindSupplicantM07Meshy20261001'
OUT = ROOT / 'HeavyGaitV22/Motion'
SKIN = ROOT / 'LegJointsV17/Skin/M07_Original_LegJoints_V17.blend'
FPS = 30
UP, RIGHT, FORWARD = Vector((0., 0., 1.)), Vector((1., 0., 0.)), Vector((0., -1., 0.))
REAR = -FORWARD
sys.path.insert(0, str(Path(__file__).parent))
import author_motion_v04 as motion
import author_running_v12 as running
import author_locomotion_death_v15 as v15
import author_leg_joint_motion_v17 as v17
import author_palm_arm_motion_v20 as v20
from author_cast_v15 import signed_angle

# The current native gait selector has +/-20 cm/s hysteresis. Keep the two
# source speeds more than 40 apart so the faster gait is reachable naturally.
# Navigation and clip speed are changed together by the companion importer.
CONFIG = {
    'SlowWalk': dict(intervals=96, source_speed_cm_s=42., ai_speed_cm_s=42.,
        stance_fraction=.68, foot_lift_cm=11., sway_cm=8.5, gain=.85,
        pelvis_drop_cm=8.5, chest_lean_deg=7., shoulder_lag_s=.10,
        arm_lag_s=.17, wrist_lag_s=.23),
    'Chase': dict(intervals=72, source_speed_cm_s=86., ai_speed_cm_s=86.,
        stance_fraction=.68, foot_lift_cm=15., sway_cm=9.5, gain=1.,
        pelvis_drop_cm=11., chest_lean_deg=9., shoulder_lag_s=.085,
        arm_lag_s=.14, wrist_lag_s=.20),
}

# Unequally spaced poses put the long holds over the supporting foot and the
# short changes inside double support. Periodic monotone Hermite interpolation
# has a continuous seam and no Catmull-Rom overshoot between pose extrema.
SWAY = [(0., -.28), (.10, .65), (.18, 1.), (.34, .92), (.42, .75),
        (.50, .28), (.60, -.65), (.68, -1.), (.84, -.92), (.92, -.75)]
COMPRESSION = [(0., .28), (.075, 1.), (.18, .72), (.34, 0.), (.44, .15),
               (.50, .28), (.575, 1.), (.68, .72), (.84, 0.), (.94, .15)]
PELVIS_YAW = [(0., -4.5), (.10, -4.), (.25, -.6), (.42, 3.8),
              (.50, 4.5), (.60, 4.), (.75, .6), (.92, -3.8)]
ARM_SWING = [(0., -5.), (.10, -10.), (.25, -7.), (.42, 8.),
             (.50, 13.), (.62, 17.), (.78, 11.), (.92, 0.)]
ELBOW_FLEX = [(0., 27.), (.12, 30.), (.28, 34.), (.44, 39.),
              (.55, 40.), (.70, 35.), (.86, 29.)]


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def clamp(value, low, high):
    return max(low, min(high, value))


def ease(t):
    t = clamp(t, 0., 1.)
    return t*t*t*(10. + t*(-15. + 6.*t))


def ramp(t, start, end):
    return ease((t-start)/(end-start))


def rot(axis, degrees):
    return Quaternion(axis, math.radians(degrees))


def matrix(point, q):
    return Matrix.LocRotScale(point, q, Vector((1., 1., 1.)))


def cyclic(keys, phase):
    p = phase % 1.
    n = len(keys)
    def point(index):
        cycle, index = divmod(index, n)
        x, y = keys[index]
        return x+cycle, y
    def slope(index):
        x0, y0 = point(index-1)
        x1, y1 = point(index)
        x2, y2 = point(index+1)
        a, b = x1-x0, x2-x1
        da, db = (y1-y0)/a, (y2-y1)/b
        if da*db <= 0.:
            return 0.
        wa, wb = 2.*b+a, b+2.*a
        return (wa+wb)/(wa/da+wb/db)
    index = next((i-1 for i in range(1, n) if p < keys[i][0]), n-1)
    x0, y0 = point(index)
    x1, y1 = point(index+1)
    span = x1-x0
    return running.hermite((p-x0)/span, y0, y1, slope(index)*span, slope(index+1)*span)


def shaped(keys, phase):
    for (a, va), (b, vb) in zip(keys, keys[1:]):
        if phase <= b:
            return va+(vb-va)*ramp(phase, a, b)
    return keys[-1][1]


def soft_max(a, b, width=.8):
    # Smooth conservative reach envelope: never sacrifices a planted foot to
    # an unreachable pelvis, and avoids a kink when support changes legs.
    overlap = max(width-abs(a-b), 0.)/width
    return max(a, b)+overlap*overlap*width*.25


def body_pose(rest, local, ordered, phase, config, reach_drop=0.):
    duration = config['intervals']/FPS
    gain = config['gain']
    load = cyclic(COMPRESSION, phase)
    sway = cyclic(SWAY, phase)
    pelvis_yaw = cyclic(PELVIS_YAW, phase)*gain
    # The chest absorbs load after the hip, with the head damping the last
    # part of that response. All delays are seconds, not frame counts.
    chest_phase = phase-config['shoulder_lag_s']/duration
    chest_load = cyclic(COMPRESSION, chest_phase)
    chest_yaw = -cyclic(PELVIS_YAW, chest_phase)*.82*gain
    hip_pitch = (1.8+1.5*load)*gain
    chest_pitch = config['chest_lean_deg']+2.3*chest_load
    hip_roll, chest_roll = 1.7*sway*gain, 1.1*cyclic(SWAY, chest_phase)*gain
    target = {}
    for pose in ordered:
        name = pose.name
        position, q = v15.inherited(target, rest, local, pose)
        if name == 'pelvis':
            position = rest[name].translation.copy()
            position.x += config['sway_cm']*sway
            position.y -= 1.5+1.1*load
            position.z -= config['pelvis_drop_cm']+4.8*load*gain+reach_drop
            q = rot(UP, pelvis_yaw)@rot(RIGHT, hip_pitch)@rot(FORWARD, hip_roll)@rest[name].to_quaternion()
        elif name.startswith('spine_'):
            fraction = (int(name[-2:])/5.)**.9
            pitch = hip_pitch+(chest_pitch-hip_pitch)*fraction
            yaw = pelvis_yaw+(chest_yaw-pelvis_yaw)*fraction
            roll = hip_roll+(chest_roll-hip_roll)*fraction
            q = rot(UP, yaw)@rot(RIGHT, pitch)@rot(FORWARD, roll)@rest[name].to_quaternion()
        elif name.startswith('clavicle_'):
            side = name[-1]
            sign, offset = (1., 0.) if side == 'l' else (-1., .5)
            arm_phase = chest_phase+offset
            scapula = cyclic(ARM_SWING, arm_phase)*.12*gain
            # Clavicle protraction/retraction precedes the long upper arm;
            # small impact depression subsequently passes through the elbow.
            delta = target['spine_05'].to_quaternion()@rest['spine_05'].to_quaternion().inverted()
            q = delta@rot(UP, -sign*scapula)@rot(FORWARD, -sign*.8*chest_load)@rest[name].to_quaternion()
        elif name.startswith('neck_') or name == 'head':
            head_load = cyclic(COMPRESSION, phase-.16/duration)
            blend = .42 if name == 'neck_01' else .74 if name == 'neck_02' else 1.
            pitch = chest_pitch+(3.8+.65*head_load-chest_pitch)*blend
            yaw = chest_yaw*(1.-.90*blend)
            roll = chest_roll*(1.-.86*blend)
            q = rot(UP, yaw)@rot(RIGHT, pitch)@rot(FORWARD, roll)@rest[name].to_quaternion()
        target[name] = matrix(position, q)
    return target, dict(load=load, lateral_transfer=sway, pelvis_yaw_deg=pelvis_yaw,
        chest_yaw_deg=chest_yaw, pelvis_pitch_deg=hip_pitch, chest_pitch_deg=chest_pitch,
        reach_drop_cm=reach_drop)


def foot_goal(rest, side, phase, config):
    duration = config['intervals']/FPS
    stride = config['source_speed_cm_s']*duration
    stance = config['stance_fraction']
    front = stride*stance*.5
    back = -front
    sign = 1. if side == 'l' else -1.
    foot, ball = rest['foot_'+side].translation, rest['ball_'+side].translation
    hip = rest['thigh_'+side].translation
    # Narrow, constant contact lanes. Support points stay fixed in the
    # virtual travelling world; pelvis sway never drags the support sideways.
    shift = Vector((hip.x+sign*3.-foot.x, hip.y-foot.y, 0.))
    heel = Vector((foot.x, foot.y+7., 0.))
    if phase < stance:
        fore, lift = front-stride*phase, 0.
        if phase < .09:
            pitch = -7.*(1.-ramp(phase, 0., .09))
            pivot, ball_pitch, stage = heel, pitch, 'heel_contact_to_flat'
        elif phase < .51:
            pitch = ball_pitch = 0.
            pivot, stage = ball, 'flat_loaded_support'
        else:
            pitch = 19.*ramp(phase, .51, stance)
            pivot, ball_pitch, stage = ball, 0., 'heel_rise_toe_support'
        support = 1.
    else:
        swing = (phase-stance)/(1.-stance)
        # Position and velocity match the constant-speed planted trajectory
        # at both ends; small toe-off/landing overshoot follows from momentum.
        tangent = -stride*(1.-stance)
        fore = back+tangent*swing+(front-back-tangent)*ease(swing)
        lift = config['foot_lift_cm']*shaped(
            [(0., 0.), (.20, .58), (.42, 1.), (.66, .72), (.86, .20), (1., 0.)], swing)
        pitch = shaped([(0., 19.), (.20, 14.), (.46, 2.), (.77, -7.), (1., -7.)], swing)
        # Carry the toe with the forefoot after release. On approach, restore
        # a unified heel-first foot before touching down.
        ball_pitch = pitch*ramp(swing, 0., .20)
        pivot = ball.lerp(heel, ramp(swing, .66, .90))
        shift.x += sign*1.5*math.sin(math.pi*swing)**2
        stage = 'knee_fold_and_clear' if swing < .42 else 'under_body_pass' if swing < .67 else 'lower_and_brake_for_heel'
        support = 0.
    delta = rot(RIGHT, pitch)
    ankle = pivot+delta@(foot-pivot)+shift+FORWARD*fore+UP*lift
    foot_q = delta@rest['foot_'+side].to_quaternion()
    ball_q = rot(RIGHT, ball_pitch)@rest['ball_'+side].to_quaternion()
    return ankle, foot_q, ball_q, dict(phase=phase, support=support, stage=stage,
        foot_fore_cm=fore, clearance_cm=lift, foot_pitch_deg=pitch, toe_pitch_deg=ball_pitch)


def install_legs(target, rest, local, leg_data, goals):
    records = {}
    for side in ('l', 'r'):
        ankle, foot_q, ball_q, record = goals[side]
        source = dict(target)
        source['foot_'+side] = matrix(ankle, foot_q)
        source['ball_'+side] = matrix(ankle, ball_q)
        target.update(v17.solve_chain(rest, local, leg_data, source, side, record['phase'], .68))
        records[side] = record
    return records


def install_arms(target, rest, ordered, references, phase, config, role):
    duration = config['intervals']/FPS
    records = {}
    for side, sign, offset in (('l', 1., 0.), ('r', -1., .5)):
        reference = references[side]
        arm_phase = phase+offset-config['arm_lag_s']/duration
        wrist_phase = phase+offset-config['wrist_lag_s']/duration
        swing = cyclic(ARM_SWING, arm_phase)*config['gain']
        flexion = cyclic(ELBOW_FLEX, wrist_phase)
        shoulder_delta = target['clavicle_'+side].to_quaternion()@rest['clavicle_'+side].to_quaternion().inverted()
        direction = Vector((0., -math.sin(math.radians(swing)), -math.cos(math.radians(swing))))
        abduct = math.radians(8.5)
        upper = (shoulder_delta@(direction*math.cos(abduct)+RIGHT*(sign*math.sin(abduct)))).normalized()
        front = shoulder_delta@FORWARD
        bend_direction = (front-upper*front.dot(upper)).normalized()
        lower = (upper*math.cos(math.radians(flexion))+bend_direction*math.sin(math.radians(flexion))).normalized()
        hinge = upper.cross(lower).normalized()
        du = (motion.anatomical_frame(upper, hinge)@reference['reference_frame'].transposed()).to_quaternion()
        dl = du@Quaternion(reference['hinge'], math.radians(flexion)-reference['rest_bend'])
        desired = shoulder_delta@REAR
        projected = (desired-lower*desired.dot(lower)).normalized()
        normal = dl@reference['palm_normal']
        pronation = clamp(math.degrees(signed_angle(normal, projected, lower)), -65., 65.)
        forearm = rot(lower, pronation)@dl
        # A soft wrist follows shoulder and elbow motion, without forcing the
        # palm direction by straightening the arm or overturning the wrist.
        palm, fingers = forearm@reference['palm_normal'], forearm@reference['finger_along']
        across = palm.cross(fingers).normalized()
        yield_angle = clamp(math.degrees(signed_angle(palm, desired, across)), -10., 10.)
        yield_angle += 1.5*cyclic(COMPRESSION, wrist_phase)
        hand_delta = rot(across, yield_angle)@forearm
        shoulder = target['upperarm_'+side].translation.copy()
        elbow = shoulder+upper*reference['upper_length']
        wrist = elbow+lower*reference['lower_length']
        target['upperarm_'+side] = matrix(shoulder, du@rest['upperarm_'+side].to_quaternion())
        target['lowerarm_'+side] = matrix(elbow, forearm@rest['lowerarm_'+side].to_quaternion())
        target['hand_'+side] = matrix(wrist, hand_delta@rest['hand_'+side].to_quaternion())
        v20.digit_pose(target, rest, rest, ordered, side, reference, role, 0.)
        records[side] = dict(upperarm_swing_deg=swing, elbow_flexion_deg=flexion,
            forearm_pronation_deg=pronation, wrist_yield_deg=yield_angle)
    return records


def gill_follow_through(target, rest, local, ordered, phase, config):
    duration = config['intervals']/FPS
    for pose in ordered:
        name = pose.name
        if not name.startswith('gill_'):
            continue
        _, panel, segment = name.split('_')
        index = int(segment)
        position, q = v15.inherited(target, rest, local, pose)
        if index > 0:
            delay = (.16+index*.045+int(panel)*.007)/duration
            # The fixed attachment roots follow the spine. Free membrane
            # bones settle after body compression; no new simulation work.
            follow = cyclic(COMPRESSION, phase-delay)-cyclic(COMPRESSION, phase-.08/duration)
            side = 1. if int(panel) <= 3 else -1.
            q = rot(RIGHT, follow*(.8+.45*index))@rot(FORWARD, side*.35*follow)@q
        target[name] = matrix(position, q)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(SKIN))
    rig = v20.original_rig()
    rig.data.pose_position = 'POSE'
    rig.animation_data_clear()
    rig.hide_set(False)
    ordered = sorted(rig.pose.bones, key=lambda pose: len(pose.bone.parent_recursive))
    rest = {bone.name: bone.matrix_local.copy() for bone in rig.data.bones}
    local = {bone.name: bone.parent.matrix_local.inverted()@bone.matrix_local if bone.parent else bone.matrix_local.copy()
             for bone in rig.data.bones}
    leg_data = {side: v17.hinge_data(rest, side) for side in ('l', 'r')}
    arm_data = {side: v20.arm_reference(rest, side) for side in ('l', 'r')}
    hidden = {obj.name: obj.hide_viewport for obj in bpy.data.objects if obj.type == 'MESH'}
    for name in hidden:
        bpy.data.objects[name].hide_viewport = True
    scene = bpy.context.scene
    scene.render.fps, scene.render.fps_base = FPS, 1.
    scene.unit_settings.system, scene.unit_settings.scale_length = 'METRIC', .01
    manifest = dict(revision='HeavyGaitV22', fps=FPS,
        source=str(OUT/'M07_Original_HeavyGait_V22.blend'), mesh_skin_master=str(SKIN),
        reference_skeleton='/Game/Monsters/BlindSupplicantM07/SK_M07_ReferenceOriginalV11',
        bone_names=list(rest), bone_reference={name: motion.rows(value) for name, value in rest.items()},
        rig_object_matrix_world=motion.rows(rig.matrix_world),
        geometry_modified=False, weights_modified=False, reference_pose_modified=False,
        root_motion=False, animation_export_pose_position='POSE',
        choreography='Original giant/robot-inspired deliberate heavy walking; no jogging donor and no video reproduction claim',
        support_contract='Left heel at phase 0; right heel at .5; each foot supports 68%; 36% double support; no flight',
        body_contract='Pre-transfer over support, delayed load compression, smooth support recovery, hip/chest counterrotation, scapular lead, elbow/wrist/gill lag, damped head',
        support_root_policy='Container root is fixed; only pelvis and its descendants receive reach compensation',
        performance='Offline baked keys on existing 83 bones; no new Tick, runtime IK, cloth bodies or simulation vertices',
        scope='Two movement clips and existing BP locomotion references/speeds only',
        clips={}, candidate=True, runtime_tested=False, rendered=False, visual_accepted=False,
        tested=False, ue_imported=False, user_review_pending=True)
    actions = {}
    for role, config in CONFIG.items():
        count, duration = config['intervals']+1, config['intervals']/FPS
        action = bpy.data.actions.new('A_M07_'+role+'_HeavyGaitV22')
        action.use_fake_user = True
        motion.activate(rig, action)
        previous, production = {}, []
        first_pose = None
        for index in range(count):
            phase, frame = index/config['intervals'], index+1
            scene.frame_set(frame)
            goals = {side: foot_goal(rest, side, (phase+offset)%1., config) for side, offset in (('l', 0.), ('r', .5))}
            target, params = body_pose(rest, local, ordered, phase, config)
            settling = 0.
            for side in ('l', 'r'):
                ankle = goals[side][0]
                hip = target['thigh_'+side].translation
                data = leg_data[side]
                # Retain a 14-degree bend as the geometric reach limit. The
                # shared anatomical solver has a looser 10-degree hard limit.
                reach = math.sqrt(data['upper_length']**2+data['lower_length']**2+
                    2.*data['upper_length']*data['lower_length']*math.cos(math.radians(14.)))
                horizontal_sq = (ankle.x-hip.x)**2+(ankle.y-hip.y)**2
                lower_by = hip.z-ankle.z-math.sqrt(max(0., reach*reach-horizontal_sq))
                settling = soft_max(settling, lower_by)
            target, params = body_pose(rest, local, ordered, phase, config, settling)
            legs = install_legs(target, rest, local, leg_data, goals)
            arms = install_arms(target, rest, ordered, arm_data, phase, config, role)
            gill_follow_through(target, rest, local, ordered, phase, config)
            if index == 0:
                first_pose = {name: transform.copy() for name, transform in target.items()}
            elif index == count-1:
                target = {name: transform.copy() for name, transform in first_pose.items()}
            running.insert_frame(rig, target, rest, ordered, frame, previous)
            production.append(dict(frame=frame, seconds=index/FPS, phase=phase,
                body=params, pelvis_cm=list(target['pelvis'].translation), legs=legs, arms=arms))
        # Explicit bind outside the export interval; POSE mode remains active.
        scene.frame_set(0)
        for pose in ordered:
            pose.matrix_basis = Matrix.Identity(4)
            for channel in ('location', 'rotation_quaternion', 'scale'):
                pose.keyframe_insert(data_path=channel, frame=0, group=pose.name)
        for curve in running.curves(action):
            for key in curve.keyframe_points:
                key.interpolation = 'LINEAR'
        fbx = OUT/('A_M07_'+role+'.fbx')
        v15.export(rig, action, fbx, count)
        record_path = OUT/('authored_'+role.lower()+'_production_record_v22.json')
        write(record_path, dict(scope='Intrinsic authoring parameters, not tests or pose acceptance',
            action=action.name, frames=production, runtime_tested=False, rendered=False))
        contacts = {side: [record['legs'][side]['support'] for record in production] for side in ('l', 'r')}
        manifest['clips'][role] = dict(role=role, action=action.name, file=str(fbx),
            asset='/Game/Monsters/BlindSupplicantM07/AnimationsHeavyGaitV22/A_M07_'+role,
            fps=FPS, frames=count, duration=duration, duration_seconds=duration,
            loop=True, root_motion=False, source_speed_cm_s=config['source_speed_cm_s'],
            speed_cm_s=config['source_speed_cm_s'], ai_speed_cm_s=config['ai_speed_cm_s'],
            expected_playback_ratio_at_ai_speed=1., expected_cycle_seconds_at_ai_speed=duration,
            step_cm=config['source_speed_cm_s']*duration*.5,
            stride_cm=config['source_speed_cm_s']*duration,
            stance_fraction=config['stance_fraction'], double_support_fraction=.36,
            contact_seconds={'left': 0., 'right': duration*.5}, foot_contact=contacts,
            reference_only_blender_frame=0, exported_blender_frame_start=1,
            exported_blender_frame_end=count, config=config, production_record=str(record_path),
            runtime_tested=False, rendered=False)
        actions[role] = action
        print('M07_V22_CLIP_EXPORTED '+role+' '+str(duration)+'s '+str(fbx), flush=True)
    for name, value in hidden.items():
        bpy.data.objects[name].hide_viewport = value
    motion.activate(rig, actions['SlowWalk'])
    scene.frame_start, scene.frame_end = 1, manifest['clips']['SlowWalk']['frames']
    scene.frame_set(1)
    rig['locomotion_revision'] = 'V22 heavy coordinated gait; original geometry, skin and reference retained'
    bpy.ops.wm.save_as_mainfile(filepath=manifest['source'], compress=True)
    manifest.update(source_saved=True, animation_fbx_exported=True)
    write(OUT/'heavy_gait_manifest_v22.json', manifest)
    print('M07_V22_HEAVY_GAIT_SOURCE_SAVED '+str(OUT), flush=True)


if __name__ == '__main__':
    main()
