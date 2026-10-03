"""M-07 V21 coordinated video-reference locomotion, on the original bind.

The eight observed phases define collected shoulders, forward chest, carried
claws, yielding hip/knee support and a heel-fold/pass/forward-plant recovery.
This is an authored interpretation of the selected video, not its unavailable
native animation tracks. The side character is a different jog variant.
Only two new clips are produced. Original geometry, skin and bind stay intact.
No UE, tests, screenshots or acceptance renders are run by this producer.
"""
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Quaternion, Vector

PROJECT = Path('D:/FPS3D/FPSGAME')
ROOT = PROJECT/'SourceAssets/BlindSupplicantM07Meshy20261001'
OUT = ROOT/'FullReferenceGaitV21/Motion'
SOURCE = ROOT/'PalmArmMotionV20/Motion/M07_Original_PalmArmMotion_V20.blend'
SOURCE_MANIFEST = ROOT/'PalmArmMotionV20/Motion/palm_arm_motion_manifest_v20.json'
SKIN = ROOT/'LegJointsV17/Skin/M07_Original_LegJoints_V17.blend'
REFERENCE = ROOT/'VideoLocomotionV19/Reference'
FPS = 30
UP, RIGHT, FORWARD = Vector((0., 0., 1.)), Vector((1., 0., 0.)), Vector((0., -1., 0.))
REAR, DOWN = -FORWARD, -UP
sys.path.insert(0, str(Path(__file__).parent))
import author_motion_v04 as motion
import author_running_v12 as running
import author_locomotion_death_v15 as v15
import author_leg_joint_motion_v17 as v17
import author_palm_arm_motion_v20 as v20
from author_cast_v15 import signed_angle

# Speeds are anatomical authoring choices, not measurements in video pixels.
# Keeping source/AI speed equal retains the 1.333 s reference jog cadence.
# The historical 360/270 multiplier compressed it to 1.0 s and exaggerated
# the required step. Fidelity to the user's selected jog takes precedence.
CONFIG = {
    'SlowWalk': {'intervals': 50, 'source_speed_cm_s': 120., 'ai_speed_cm_s': 120.,
        'stance_fraction': .52, 'foot_lift_cm': 23., 'pose_gain': .76,
        'chest_mean_lean_deg': 16., 'pelvis_forward_cm': 2.3,
        'pelvis_sway_cm': 2.4, 'arm_abduction_deg': 11.5},
    'Chase': {'intervals': 40, 'source_speed_cm_s': 210., 'ai_speed_cm_s': 210.,
        'stance_fraction': .36, 'foot_lift_cm': 34., 'pose_gain': 1.,
        'chest_mean_lean_deg': 20., 'pelvis_forward_cm': 3.5,
        'pelvis_sway_cm': 2.6, 'arm_abduction_deg': 13.},
}

# Contact, compression, passing, release, opposite contact: one shared clock.
# The specific angles are authored fits for M-07's longer torso/arm proportions.
PHASES = {
    'pelvis_height_cm': [-6., -11., -6., -2., -6., -11., -6., -2.],
    'pelvis_pitch_deg': [5., 7., 5., 3.8, 5., 7., 5., 3.8],
    'chest_lean_offset_deg': [0., 2.8, -.5, -2., 0., 2.8, -.5, -2.],
    'pelvis_yaw_deg': [5.8, 7., 1.2, -4.8, -5.8, -7., -1.2, 4.8],
    'chest_yaw_deg': [-5.5, -8.5, -2.8, 5.5, 5.5, 8.5, 2.8, -5.5],
    'pelvis_roll_deg': [-1.4, -2.8, -1.5, .7, 1.4, 2.8, 1.5, -.7],
    'head_yaw_deg': [-.7, -1.5, -.5, 1., .7, 1.5, .5, -1.],
    # Torso-relative humeral flexion offsets the chest's forward lean. A
    # downward humerus inherits that pitch in the opposite sagittal direction;
    # negative values here would over-retract the elbows behind the body.
    'upperarm_swing_deg': [4., 9., 18., 31., 34., 28., 18., 8.],
    'elbow_flexion_deg': [88., 94., 99., 91., 74., 72., 79., 85.],
    'scapula_lead_deg': [-2., -3.5, -1.7, 1.5, 2., 3.5, 1.7, -1.5],
}


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def clamp(v, low, high):
    return max(low, min(high, v))


def rot(axis, degrees):
    return Quaternion(axis, math.radians(degrees))


def matrix(point, q):
    return Matrix.LocRotScale(point, q, Vector((1., 1., 1.)))


def cyclic(values, u):
    """Periodic C1 interpolation of authored poses; no phase-independent waves."""
    x = (u % 1.)*len(values)
    i, t = int(x), x-int(x)
    n = len(values)
    a, b = values[i % n], values[(i+1) % n]
    da = .5*(b-values[(i-1) % n])
    db = .5*(values[(i+2) % n]-a)
    return running.hermite(t, a, b, da, db)


def shape(keys, u):
    """Monotone smooth interpolation with zero end velocities for heel lift."""
    if u <= keys[0][0]:
        return keys[0][1]
    for (a, va), (b, vb) in zip(keys, keys[1:]):
        if u <= b:
            return va+(vb-va)*motion.smooth((u-a)/(b-a))
    return keys[-1][1]


def frame_parameters(u, config):
    gain = config['pose_gain']
    return {
        'pelvis_height_cm': cyclic(PHASES['pelvis_height_cm'], u)*gain,
        'pelvis_pitch_deg': cyclic(PHASES['pelvis_pitch_deg'], u)*gain,
        'chest_pitch_deg': config['chest_mean_lean_deg']+cyclic(PHASES['chest_lean_offset_deg'], u)*gain,
        'pelvis_yaw_deg': cyclic(PHASES['pelvis_yaw_deg'], u)*gain,
        'chest_yaw_deg': cyclic(PHASES['chest_yaw_deg'], u)*gain,
        'pelvis_roll_deg': cyclic(PHASES['pelvis_roll_deg'], u)*gain,
        'head_yaw_deg': cyclic(PHASES['head_yaw_deg'], u)*gain,
    }


def torso_pose(rest, local, ordered, u, config):
    params = frame_parameters(u, config)
    target = {}
    for pose in ordered:
        name = pose.name
        point, q = v15.inherited(target, rest, local, pose)
        if name == 'pelvis':
            point = rest[name].translation.copy()
            point.x += config['pelvis_sway_cm']*cyclic([0., .65, 1., .5, 0., -.65, -1., -.5], u)
            point.y -= config['pelvis_forward_cm']
            point.z += params['pelvis_height_cm']
            delta = rot(UP, params['pelvis_yaw_deg'])@rot(RIGHT, params['pelvis_pitch_deg'])@rot(FORWARD, params['pelvis_roll_deg'])
            q = delta@rest[name].to_quaternion()
        elif name.startswith('spine_'):
            fraction = int(name[-2:])/5.
            # Collected upper back; distributed bend over all five original
            # spine joints rather than rotating one shoulder/neck in isolation.
            t = fraction**.78
            lean = params['pelvis_pitch_deg']+(params['chest_pitch_deg']-params['pelvis_pitch_deg'])*t
            yaw = params['pelvis_yaw_deg']+(params['chest_yaw_deg']-params['pelvis_yaw_deg'])*t
            roll = params['pelvis_roll_deg']*(1.-.70*t)
            q = rot(UP, yaw)@rot(RIGHT, lean)@rot(FORWARD, roll)@rest[name].to_quaternion()
        elif name.startswith('clavicle_'):
            side = name[-1]
            sign = 1. if side == 'l' else -1.
            arm_u = (u+(0. if side == 'l' else .5)) % 1.
            lead = cyclic(PHASES['scapula_lead_deg'], arm_u)*config['pose_gain']
            chest = target['spine_05'].to_quaternion()@rest['spine_05'].to_quaternion().inverted()
            # Both scapulae protract, with a small alternating shoulder lead.
            # Positive/negative left/right yaw comes from actual anatomy.
            q = chest@rot(UP, -sign*6.+lead)@rot(FORWARD, sign*1.7)@rest[name].to_quaternion()
        elif name.startswith('neck_') or name == 'head':
            gain = .70 if name.startswith('neck_') else 1.
            # The neck extends relative to the flexed upper chest, keeping the
            # head directed toward travel instead of staring at the floor.
            lean = (9.+cyclic(PHASES['chest_lean_offset_deg'], u)*.25)*gain
            q = rot(UP, params['head_yaw_deg']*gain)@rot(RIGHT, lean)@rot(FORWARD, params['pelvis_roll_deg']*.08)@rest[name].to_quaternion()
        target[name] = matrix(point, q)
    return target, params


def foot_goal(rest, side, phase, config):
    duration = config['intervals']/FPS
    stride = config['source_speed_cm_s']*duration
    stance = config['stance_fraction']
    span = stride*stance
    front, back = span*.5, -span*.5
    sign = 1. if side == 'l' else -1.
    toe = rest['ball_'+side].translation.copy()
    hip, ankle = rest['thigh_'+side].translation, rest['foot_'+side].translation
    # Same original toe/ankle offset, support lane below its own hip, no extra
    # hock, global tibial yaw or heel dragged through the arbitrary bone axes.
    toe.y -= ankle.y-hip.y
    toe.x += hip.x+4.*sign-ankle.x
    if phase < stance:
        progress = phase/stance
        fore = front-stride*phase
        lift = 0.
        pitch = shape([(0., -5.), (.16, 0.), (.68, 0.), (1., 24.)], progress)
        ball_pitch = -pitch*.70
        contact = 1.
        stage = 'contact_compression' if progress < .36 else 'support_pass' if progress < .74 else 'heel_release'
    else:
        progress = (phase-stance)/(1.-stance)
        brake = .09
        tangent = -stride*(1.-stance)
        overshoot = -tangent*brake*.5
        if progress < brake:
            q = progress/brake
            fore = back+tangent*brake*(q-q**3+.5*q**4)
        elif progress > 1.-brake:
            q = (progress-(1.-brake))/brake
            fore = front+overshoot+tangent*brake*(q**3-.5*q**4)
        else:
            q = (progress-brake)/(1.-2.*brake)
            # Early heel recovery stays behind the body; the foot passes the
            # pelvis before a controlled forward/down reach to the next plant.
            reach = shape([(0., 0.), (.20, .04), (.41, .34), (.66, .74), (1., 1.)], q)
            fore = back-overshoot+(front-back+2.*overshoot)*reach
        lift = config['foot_lift_cm']*shape([(0., 0.), (.09, .24), (.24, .80), (.42, 1.), (.60, .68), (.78, .27), (.92, .035), (1., 0.)], progress)
        pitch = shape([(0., 24.), (.21, 31.), (.42, 23.), (.66, 8.), (.85, -4.), (1., -5.)], progress)
        ball_pitch = -pitch*.56
        toe.x -= sign*2.2*shape([(0., 0.), (.45, 1.), (1., 0.)], progress)
        contact = 0.
        stage = 'heel_fold_behind' if progress < .28 else 'knee_pass_under_body' if progress < .59 else 'forward_down_reach'
    toe += FORWARD*fore+UP*lift
    foot_q = rot(RIGHT, pitch)@rest['foot_'+side].to_quaternion()
    ankle_to_ball = rest['foot_'+side].to_quaternion().inverted()@(rest['ball_'+side].translation-rest['foot_'+side].translation)
    ankle_goal = toe-foot_q@ankle_to_ball
    ball_q = rot(RIGHT, pitch+ball_pitch)@rest['ball_'+side].to_quaternion()
    return ankle_goal, foot_q, ball_q, {'contact': contact, 'stage': stage,
        'toe_fore_aft_cm': fore, 'toe_lift_cm': lift, 'foot_pitch_deg': pitch}


def install_legs(target, rest, local, leg_data, u, config):
    goals, settling = {}, 0.
    for side, offset in (('l', 0.), ('r', .5)):
        goals[side] = foot_goal(rest, side, (u+offset)%1., config)
        ankle_goal = goals[side][0]
        hip, d = target['thigh_'+side].translation, leg_data[side]
        reach = math.sqrt(d['upper_length']**2+d['lower_length']**2+
            2.*d['upper_length']*d['lower_length']*math.cos(math.radians(10.)))
        horizontal = (ankle_goal.x-hip.x)**2+(ankle_goal.y-hip.y)**2
        settling = max(settling, hip.z-ankle_goal.z-math.sqrt(max(0., reach*reach-horizontal)))
    if settling > 0.:
        for transform in target.values():
            transform.translation.z -= settling
    records = {}
    for side, offset in (('l', 0.), ('r', .5)):
        goal, foot_q, ball_q, record = goals[side]
        source = dict(target)
        source['foot_'+side], source['ball_'+side] = matrix(goal, foot_q), matrix(goal, ball_q)
        target.update(v17.solve_chain(rest, local, leg_data, source, side, (u+offset)%1., config['stance_fraction']))
        hip, knee, ankle = (target[n+'_'+side].translation for n in ('thigh', 'calf', 'foot'))
        record.update({'hip_cm': list(hip), 'knee_cm': list(knee), 'ankle_cm': list(ankle),
            'knee_flexion_deg': math.degrees((knee-hip).angle(ankle-knee))})
        records[side] = record
    return records, settling


def fit_carried_arm(target, rest, side, reference, u, config):
    sign = 1. if side == 'l' else -1.
    phase = (u+(0. if side == 'l' else .5))%1.
    swing = cyclic(PHASES['upperarm_swing_deg'], phase)
    elbow = cyclic(PHASES['elbow_flexion_deg'], phase)
    if config['pose_gain'] < 1.:
        swing = 18.+(swing-18.)*.80
        elbow = 84.+(elbow-84.)*.85
    torso = target['spine_05'].to_quaternion()@rest['spine_05'].to_quaternion().inverted()
    sagittal = Vector((0., -math.sin(math.radians(swing)), -math.cos(math.radians(swing))))
    abduct = math.radians(config['arm_abduction_deg'])
    upper = (torso@(sagittal*math.cos(abduct)+RIGHT*(sign*math.sin(abduct)))).normalized()
    front = torso@FORWARD
    flex = (front-upper*front.dot(upper)).normalized()
    lower = (upper*math.cos(math.radians(elbow))+flex*math.sin(math.radians(elbow))).normalized()
    hinge = upper.cross(lower).normalized()
    du = (motion.anatomical_frame(upper, hinge)@reference['reference_frame'].transposed()).to_quaternion()
    dl = du@Quaternion(reference['hinge'], math.radians(elbow)-reference['rest_bend'])
    # Rotation is around the anatomical forearm only after the elbow hinge.
    # Axial correction keeps the transported elbow intact and never spins the
    # wrist 180 degrees. The carried arm is not straightened to satisfy a palm.
    wanted = torso@REAR
    wanted.z = 0.
    wanted.normalize()
    normal = dl@reference['palm_normal']
    projected = wanted-lower*wanted.dot(lower)
    if projected.length < .05:
        projected = DOWN-lower*DOWN.dot(lower)
    projected.normalize()
    needed = math.degrees(signed_angle(normal, projected, lower))
    pronation = clamp(needed, -75., 75.)
    forearm_delta = rot(lower, pronation)@dl
    wrist_roll = clamp(needed-pronation, -6., 6.)
    hand_delta = rot(lower, wrist_roll)@forearm_delta
    palm, fingers = hand_delta@reference['palm_normal'], hand_delta@reference['finger_along']
    across = palm.cross(fingers).normalized()
    yielding = clamp(math.degrees(signed_angle(palm, wanted, across)), -35., 35.)
    hand_delta = rot(across, yielding)@hand_delta
    shoulder = target['upperarm_'+side].translation.copy()
    elbow_point = shoulder+upper*reference['upper_length']
    wrist = elbow_point+lower*reference['lower_length']
    target['upperarm_'+side] = matrix(shoulder, du@rest['upperarm_'+side].to_quaternion())
    target['lowerarm_'+side] = matrix(elbow_point, forearm_delta@rest['lowerarm_'+side].to_quaternion())
    target['hand_'+side] = matrix(wrist, hand_delta@rest['hand_'+side].to_quaternion())
    palm = hand_delta@reference['palm_normal']
    return {'upperarm_body_swing_deg': swing, 'elbow_flexion_deg': elbow,
        'forearm_pronation_deg': pronation, 'wrist_axial_deg': wrist_roll,
        'wrist_yield_deg': yielding, 'actual_palm_normal': list(palm),
        'torso_rear': list(wanted), 'palm_posterior_component': palm.dot(wanted),
        'shoulder_cm': list(shoulder), 'elbow_cm': list(elbow_point), 'wrist_cm': list(wrist)}


def install_arms_details(target, rest, local, ordered, details, references, u, config, role):
    records = {}
    for side in ('l', 'r'):
        records[side] = fit_carried_arm(target, rest, side, references[side], u, config)
        # Same biological five-digit flexion; curl remains mild and distinct.
        v20.digit_pose(target, details, rest, ordered, side, references[side], role, 0.)
    for pose in ordered:
        name = pose.name
        if not name.startswith('gill_'):
            continue
        parent = pose.parent.name
        point, q = v15.inherited(target, rest, local, pose)
        old_local = details[parent].inverted()@details[name]
        q = target[parent].to_quaternion()@old_local.to_quaternion()
        target[name] = matrix(point, q)
    return records


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    source_manifest = json.loads(SOURCE_MANIFEST.read_text(encoding='utf-8'))
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    rig = v20.original_rig()
    rig.data.pose_position = 'POSE'
    ordered = sorted(rig.pose.bones, key=lambda p: len(p.bone.parent_recursive))
    detail_cache = {role: v17.cache_action(rig, bpy.data.actions[source_manifest['clips'][role]['action']],
        source_manifest['clips'][role]['frames'], ordered) for role in CONFIG}
    bpy.ops.wm.open_mainfile(filepath=str(SKIN))
    rig = v20.original_rig()
    rig.data.pose_position = 'POSE'
    rig.animation_data_clear()
    rig.hide_set(False)
    ordered = sorted(rig.pose.bones, key=lambda p: len(p.bone.parent_recursive))
    rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
    local = {b.name: b.parent.matrix_local.inverted()@b.matrix_local if b.parent else b.matrix_local.copy() for b in rig.data.bones}
    leg_data = {side: v17.hinge_data(rest, side) for side in ('l', 'r')}
    arm_data = {side: v20.arm_reference(rest, side) for side in ('l', 'r')}
    visible = {obj.name: obj.hide_viewport for obj in bpy.data.objects if obj.type == 'MESH'}
    for name in visible:
        bpy.data.objects[name].hide_viewport = True
    scene = bpy.context.scene
    scene.render.fps, scene.render.fps_base = FPS, 1.
    scene.unit_settings.system, scene.unit_settings.scale_length = 'METRIC', .01
    manifest = {'revision': 'FullReferenceGaitV21', 'fps': FPS,
        'source': str(OUT/'M07_Original_FullReferenceGait_V21.blend'),
        'mesh_skin_master': str(SKIN), 'local_detail_source': str(SOURCE),
        'reference_skeleton': '/Game/Monsters/BlindSupplicantM07/SK_M07_ReferenceOriginalV11',
        'bone_names': list(rest), 'bone_reference': {name: motion.rows(value) for name, value in rest.items()},
        'rig_object_matrix_world': motion.rows(rig.matrix_world),
        'geometry_modified': False, 'weights_modified': False, 'uv_modified': False,
        'materials_modified': False, 'reference_pose_modified': False,
        'root_motion': False, 'animation_export_pose_position': 'POSE',
        'video_reference': {'url': 'https://www.youtube.com/watch?v=dJ-Ak3X7tiM',
            'seconds': [120., 125.], 'full_frame_observed': str(REFERENCE/'Frames/frame-008.jpg'),
            'phase_board_observed': str(REFERENCE/'reference_cycle_front_side.jpg'),
            'primary_character': 'Front-centre forward Jog',
            'side_character': 'Different Jog direction/variant; qualitative corroboration only',
            'inferred_full_cycle_seconds': 32./24., 'original_native_tracks_obtained': False},
        'method': 'Eight shared whole-body pose phases, five-spine flexion, scapular protraction/lead, head stability, contralateral bent-arm carriage, anatomical knee/elbow hinges and support-speed-matched foot recovery',
        'observed_corrections': ['Collected flexed elbows carrying claws, not hanging straight arms',
            'Compressed forward chest and shoulders with stable head',
            'Pelvis yield after contact and hip/chest counterrotation',
            'Heel folds behind before knee passes and foot extends forward/down',
            'Reference cadence retained without historical 360/270 acceleration'],
        'eight_phase_parameters': PHASES, 'clips': {},
        'changed_scope': 'Two coordinated full-body locomotion clips only; V20 idle/attacks/casting and current physical gill proxy unchanged',
        'performance': 'Offline animation keys; no additional Tick, physical bodies, cloth collision or simulation vertices',
        'inference_limits': ['Angles and speed are authored anatomical fits, not video motion capture',
            'Single oblique front view cannot supply exact 3D joints or centimetres',
            'Rear-facing palm intent is retained with bounded anatomical forearm/wrist articulation; fully horizontal carried forearms cannot present an exactly posterior palm without excessive wrist flexion'],
        'candidate': True, 'runtime_tested': False, 'rendered': False,
        'visual_accepted': False, 'tested': False, 'ue_imported': False}
    actions = {}
    for role, config in CONFIG.items():
        count, duration = config['intervals']+1, config['intervals']/FPS
        action = bpy.data.actions.new('A_M07_'+role+'_FullReferenceV21')
        action.use_fake_user = True
        motion.activate(rig, action)
        previous, first_pose, production = {}, None, []
        contacts = {'l': [], 'r': []}
        for index in range(count):
            u, frame = index/config['intervals'], index+1
            scene.frame_set(frame)
            target, params = torso_pose(rest, local, ordered, u, config)
            legs, settling = install_legs(target, rest, local, leg_data, u, config)
            details = motion.sample({'samples': detail_cache[role], 'rest': rest}, u)
            arms = install_arms_details(target, rest, local, ordered, details, arm_data, u, config, role)
            record = {'frame': frame, 'seconds': index/FPS, 'phase': u,
                'parameters': params, 'pelvis_cm': list(target['pelvis'].translation),
                'pelvis_reach_settling_cm': settling, 'legs': legs, 'arms': arms}
            if index == count-1:
                target = {name: value.copy() for name, value in first_pose.items()}
                record = dict(production[0], frame=frame, seconds=index/FPS, phase=u)
            elif index == 0:
                first_pose = {name: value.copy() for name, value in target.items()}
            production.append(record)
            for side in contacts:
                contacts[side].append(record['legs'][side]['contact'])
            running.insert_frame(rig, target, rest, ordered, frame, previous)
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
        production_file = OUT/('authored_'+role.lower()+'_production_record_v21.json')
        write(production_file, {'scope': 'Intrinsic authoring records, not a separate test',
            'action': action.name, 'frames': production, 'runtime_tested': False, 'rendered': False})
        entry = {'role': role, 'action': action.name, 'file': str(fbx),
            'asset': '/Game/Monsters/BlindSupplicantM07/AnimationsFullReferenceV21/A_M07_'+role,
            'fps': FPS, 'frames': count, 'duration': duration, 'duration_seconds': duration,
            'seconds': duration, 'loop': True, 'source_speed_cm_s': config['source_speed_cm_s'],
            'speed_cm_s': config['source_speed_cm_s'], 'ai_speed_cm_s': config['ai_speed_cm_s'],
            'expected_speed_cm_s': config['ai_speed_cm_s'], 'root_motion': False,
            'expected_playback_ratio_at_ai_speed': 1., 'expected_cycle_seconds_at_ai_speed': duration,
            'stride_cm': config['source_speed_cm_s']*duration,
            'step_cm': config['source_speed_cm_s']*duration*.5,
            'stance_fraction': config['stance_fraction'], 'foot_contact': contacts,
            'curves': {'FootContact_l': contacts['l'], 'FootContact_r': contacts['r']},
            'reference_only_blender_frame': 0, 'exported_blender_frame_start': 1,
            'exported_blender_frame_end': count, 'bone_tracks': list(rest), 'config': config,
            'production_record': str(production_file),
            'knee_frame': 'V17 signed human-forward hinge on exact original reference',
            'arm_frame': 'Collected torso-relative arm, explicit elbow hinge, forearm pronation<=75deg, wrist axial<=6deg and transverse yielding<=35deg; no arm straightening to satisfy palm',
            'speed_choice': 'Source and AI equal, retaining reference cadence and a physically reachable support span; historical AI 160/360 revised to120/210 for shape fidelity',
            'gill_breathing': 'Existing V20 local gill keys retimed to same shared phase, current runtime proxy preserved',
            'max_reach_settling_cm': max(row['pelvis_reach_settling_cm'] for row in production),
            'runtime_tested': False, 'rendered': False}
        manifest['clips'][role], actions[role] = entry, action
        print('M07_V21_CLIP_EXPORTED '+role+' '+json.dumps({'frames': count, 'seconds': duration,
            'speed_cm_s': config['ai_speed_cm_s'], 'support_span_cm': entry['stride_cm']*config['stance_fraction'],
            'pelvis_settling_cm': entry['max_reach_settling_cm']}), flush=True)
    for name, was_hidden in visible.items():
        bpy.data.objects[name].hide_viewport = was_hidden
    motion.activate(rig, actions['Chase'])
    scene.frame_start, scene.frame_end = 1, manifest['clips']['Chase']['frames']
    scene.frame_set(0)
    rig['locomotion_revision'] = 'V21 full selected-video reference silhouette, collected elbows, forward chest and coordinated shared contact phases; original bind/skin preserved'
    bpy.ops.wm.save_as_mainfile(filepath=manifest['source'], compress=True)
    manifest['source_saved'], manifest['animation_fbx_exported'] = True, True
    write(OUT/'full_reference_gait_manifest_v21.json', manifest)
    print('M07_V21_FULL_REFERENCE_GAIT_COMPLETE '+str(OUT), flush=True)


if __name__ == '__main__':
    main()
