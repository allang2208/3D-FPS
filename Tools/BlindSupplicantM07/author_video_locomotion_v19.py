"""M-07 V19: video-guided jog on a mature CC0 whole-body motion donor.

Only two new animation actions are produced. The selected 120--125 s
Yummy Games video is a visual reference; its paid animation tracks have
not been obtained. This is an authored imitation candidate, not a rip or
a claim of exact mocap recovery. No UE, rendering or runtime test runs.
"""
from pathlib import Path
import json
import math
import sys

import bpy
from mathutils import Matrix, Quaternion, Vector

PROJECT = Path('D:/FPS3D/FPSGAME')
ROOT = PROJECT/'SourceAssets/BlindSupplicantM07Meshy20261001'
BASE = ROOT/'VideoLocomotionV19'
OUT = BASE/'Move'
DONOR = BASE/'Donor'
SKIN = ROOT/'LegJointsV17/Skin/M07_Original_LegJoints_V17.blend'
OLD = ROOT/'BodyMotionV18/Move/M07_Original_BodyGait_V18.blend'
OLD_MANIFEST = ROOT/'BodyMotionV18/Move/body_gait_manifest_v18.json'
FPS = 30
UP, RIGHT, FORWARD = Vector((0., 0., 1.)), Vector((1., 0., 0.)), Vector((0., -1., 0.))
sys.path.insert(0, str(Path(__file__).parent))
import author_motion_v04 as motion
import author_running_v12 as running
import author_locomotion_death_v15 as v15
import author_leg_joint_motion_v17 as v17

CONFIG = {
    'SlowWalk': {'donor': 'Walk', 'intervals': 50, 'source_speed_cm_s': 135.,
        'ai_speed_cm_s': 160., 'stance_fraction': .56, 'foot_lift_cm': 11.,
        'crouch_cm': 7., 'pelvis_height_half_range_cm': 1.9,
        'pelvis_sway_half_range_cm': 2.6, 'pelvis_lean_deg': 2.,
        'chest_lean_deg': 6.5, 'hip_yaw_half_range_deg': 4.,
        'chest_yaw_half_range_deg': 5., 'body_roll_half_range_deg': 1.8,
        'arm_swing_center_deg': 5., 'arm_swing_half_range_deg': 17.,
        'elbow_center_deg': 31., 'elbow_half_range_deg': 8.,
        'arm_abduction_deg': 15., 'arm_abduction_half_range_deg': 2.},
    'Chase': {'donor': 'Jog', 'intervals': 40, 'source_speed_cm_s': 270.,
        'ai_speed_cm_s': 360., 'stance_fraction': .28, 'foot_lift_cm': 27.,
        'crouch_cm': 9., 'pelvis_height_half_range_cm': 2.8,
        'pelvis_sway_half_range_cm': 2., 'pelvis_lean_deg': 3.,
        'chest_lean_deg': 9., 'hip_yaw_half_range_deg': 5.,
        'chest_yaw_half_range_deg': 7., 'body_roll_half_range_deg': 2.2,
        'arm_swing_center_deg': 10., 'arm_swing_half_range_deg': 22.,
        'elbow_center_deg': 48., 'elbow_half_range_deg': 12.,
        'arm_abduction_deg': 16., 'arm_abduction_half_range_deg': 3.}
}


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def rot(axis, degrees):
    return Quaternion(axis, math.radians(degrees))


def matrix(pos, q):
    return Matrix.LocRotScale(pos, q, Vector((1., 1., 1.)))


def scalar(values, phase):
    x = (phase % 1.)*(len(values)-1)
    i = int(x)
    return values[i]+(values[min(i+1, len(values)-1)]-values[i])*(x-i)


def centered(value, values, half_range):
    low, high = min(values), max(values)
    return 0. if high-low < 1e-7 else (value-(low+high)*.5)*2.*half_range/(high-low)


def mean(values):
    return sum(values[:-1])/max(1, len(values)-1)


def body_euler(delta):
    # The donor and M-07 share world +Z up / -Y forward. These world-space
    # channels are anatomical sagittal lean, yaw and lateral roll, rather
    # than the differently rolled individual bone.local axes.
    e = delta.to_euler('XYZ')
    return [math.degrees(e.x), math.degrees(e.z), -math.degrees(e.y)]


def load_donor(role):
    config = CONFIG[role]
    raw = json.loads((DONOR/(config['donor']+'_world_30fps.json')).read_text(encoding='utf-8'))
    ref = json.loads((DONOR/'donor_reference.json').read_text(encoding='utf-8'))
    rest = {n: Matrix(m) for n, m in ref['bone_world_rest_matrices'].items()}
    frames = [{n: Matrix(m) for n, m in s['world_matrices'].items()} for s in raw['samples']]
    result = {'rest': rest, 'samples': frames, 'raw': raw, 'channels': {},
              'donor': config['donor']}
    for name in ('pelvis', 'spine_01', 'spine_02', 'spine_03', 'neck_01', 'head'):
        channels = [body_euler(f[name].to_quaternion()@rest[name].to_quaternion().inverted()) for f in frames]
        result['channels'][name] = [[r[k] for r in channels] for k in range(3)]
    result['channels']['pelvis_position'] = [[f['pelvis'].translation[k] for f in frames] for k in range(3)]
    for side in ('l', 'r'):
        swings, bends, abduct, toe_height, pitch = [], [], [], [], []
        for f in frames:
            torso = f['spine_03'].to_quaternion()@rest['spine_03'].to_quaternion().inverted()
            upper_world = (f['lowerarm_'+side].translation-f['upperarm_'+side].translation).normalized()
            lower_world = (f['hand_'+side].translation-f['lowerarm_'+side].translation).normalized()
            upper = torso.inverted()@upper_world
            swings.append(math.degrees(math.atan2(-upper.y, -upper.z)))
            bends.append(math.degrees(upper_world.angle(lower_world)))
            abduct.append(math.degrees(math.atan2((1. if side == 'l' else -1.)*upper.x,
                math.sqrt(upper.y**2+upper.z**2))))
            foot = f['ball_'+side].translation-f['foot_'+side].translation
            pitch.append(math.degrees(math.atan2(foot.z, math.sqrt(foot.x**2+foot.y**2))))
            toe_height.append(f['ball_'+side].translation.z)
        result['channels']['arm_'+side] = [swings, bends, abduct]
        result['channels']['foot_'+side] = [toe_height, pitch,
            [FORWARD.dot(f['ball_'+side].translation) for f in frames]]
    # A left support onset defines a common phase for body, arms and both
    # feet. Clip-local hints are widened only by the authored support span;
    # no independent half-cycle oscillator is layered over the donor torso.
    hints = raw['foot_support_trajectories']['l']['coarse_stance_intervals_seconds']
    duration = raw['source_duration_seconds']
    result['phase_origin'] = hints[0][0]/duration if hints else 0.
    result['source_stance'] = {}
    for side in ('l', 'r'):
        spans = raw['foot_support_trajectories'][side]['coarse_stance_intervals_seconds']
        # Right walk support crosses the loop seam. Its late interval is
        # connected to the early interval before constructing a swing.
        if len(spans) == 2 and spans[0][0] <= .001 and spans[-1][1] >= duration-.001:
            start, end = spans[-1][0]/duration, 1.+spans[0][1]/duration
        elif spans:
            start, end = spans[0][0]/duration, spans[0][1]/duration
        else:
            start, end = (result['phase_origin']+(0. if side == 'l' else .5))%1., 0.
            end = start+config['stance_fraction']
        result['source_stance'][side] = (start, end)
    return result


def donor_phase(src, u):
    return (u+src['phase_origin'])%1.


def torso_pose(rest, local, ordered, src, phase, config):
    target = {}
    sampled = motion.sample(src, phase)
    donor_anchors = ('pelvis', 'spine_01', 'spine_02', 'spine_03')
    def donor_delta(name, fraction):
        channels = src['channels'][name]
        pitch = config['pelvis_lean_deg']+(config['chest_lean_deg']-config['pelvis_lean_deg'])*fraction
        pitch += centered(scalar(channels[0], phase), channels[0], .5+.55*fraction)
        yaw_range = config['hip_yaw_half_range_deg']+(config['chest_yaw_half_range_deg']-config['hip_yaw_half_range_deg'])*fraction
        yaw = centered(scalar(channels[1], phase), channels[1], yaw_range)
        roll = centered(scalar(channels[2], phase), channels[2], config['body_roll_half_range_deg']*(1.-.4*fraction))
        return rot(RIGHT, pitch)@rot(UP, yaw)@rot(FORWARD, roll)
    for pose in ordered:
        name = pose.name
        point, q = v15.inherited(target, rest, local, pose)
        if name == 'pelvis':
            values = src['channels']['pelvis_position']
            point = rest[name].translation.copy()
            point.x += centered(scalar(values[0], phase), values[0], config['pelvis_sway_half_range_cm'])
            point.y -= 1.2 if src['donor'] == 'Jog' else .6
            point.z += -config['crouch_cm']+centered(scalar(values[2], phase), values[2], config['pelvis_height_half_range_cm'])
            q = donor_delta('pelvis', 0.)@rest[name].to_quaternion()
        elif name.startswith('spine_'):
            fraction = int(name[-2:])/5.
            progress = fraction*3.
            lo, hi = int(progress), min(3, int(progress)+1)
            qa = donor_delta(donor_anchors[lo], lo/3.)
            qb = donor_delta(donor_anchors[hi], hi/3.)
            q = qa.slerp(qb, progress-lo)@rest[name].to_quaternion()
        elif name.startswith('clavicle_'):
            # Preserve small source shoulder lead/rise in the target parent
            # frame; the donor's joint basis is never copied into this rig.
            parent_src = 'spine_03'
            source_parent = sampled[parent_src].to_quaternion()@src['rest'][parent_src].to_quaternion().inverted()
            source_global = sampled[name].to_quaternion()@src['rest'][name].to_quaternion().inverted()
            residual = source_parent.inverted()@source_global
            magnitude = residual.angle
            gain = min(.28, math.radians(5.)/max(.0001, magnitude))
            parent_target = target['spine_05'].to_quaternion()@rest['spine_05'].to_quaternion().inverted()
            q = parent_target@Quaternion().slerp(residual, gain)@rest[name].to_quaternion()
        elif name.startswith(('neck_', 'head')):
            channels = src['channels']['head']
            factor = .55 if name.startswith('neck_') else 1.
            # The head is comparatively stable, as in the selected frames.
            delta = rot(RIGHT, config['chest_lean_deg']*.2+centered(scalar(channels[0], phase), channels[0], .65)*factor)
            delta = delta@rot(UP, centered(scalar(channels[1], phase), channels[1], 2.)*factor)
            delta = delta@rot(FORWARD, centered(scalar(channels[2], phase), channels[2], .8)*factor)
            q = delta@rest[name].to_quaternion()
        target[name] = matrix(point, q)
    return target


def original_swing_phase(src, side, progress):
    start, end = src['source_stance'][side]
    if end <= start:
        end += 1.
    return end+(1.-(end-start))*progress


def learned_recovery(src, side, progress):
    """Retain mature toe recovery timing, with bounded endpoint braking."""
    height, pitch, forward = src['channels']['foot_'+side]
    start, end = src['source_stance'][side]
    t = original_swing_phase(src, side, progress)
    a, b = scalar(forward, end), scalar(forward, start)
    normalized = max(0., min(1., (scalar(forward, t)-a)/max(.000001, b-a)))
    quintic = progress**3*(10.+progress*(-15.+6.*progress))
    mix = motion.smooth(progress/.18)*motion.smooth((1.-progress)/.18)
    # Source fore/aft plateau and knee-recovery timing remain in the middle;
    # the endpoint envelope supplies exact support-compatible tangents.
    shape = quintic+(normalized-quintic)*.65*mix
    za, zb = scalar(height, end), scalar(height, start)
    lift = max(0., scalar(height, t)-(za+(zb-za)*progress))
    lift_values = [max(0., scalar(height, original_swing_phase(src, side, j/100.))-
        (za+(zb-za)*j/100.)) for j in range(101)]
    lift /= max(.000001, max(lift_values))
    lift *= motion.smooth(progress/.10)*motion.smooth((1.-progress)/.10)
    return shape, lift, scalar(pitch, t)


def foot_goal(rest, side, phase, src, config):
    stance = config['stance_fraction']
    duration = config['intervals']/FPS
    stride = config['source_speed_cm_s']*duration
    span = stride*stance
    front, back = span*.5, -span*.5
    height_values, pitch_values, _ = src['channels']['foot_'+side]
    start, end = src['source_stance'][side]
    # The original ankle lies behind the hip. Recenter around the actual
    # ankle support line while keeping the original ankle/ball offsets.
    toe = rest['ball_'+side].translation.copy()
    hip, ankle = rest['thigh_'+side].translation, rest['foot_'+side].translation
    toe.y -= ankle.y-hip.y
    toe.x += hip.x-ankle.x
    contact_pitch = scalar(pitch_values, start+(end-start)*.25)
    if phase < stance:
        progress = phase/stance
        fore = front-stride*phase
        lift = 0.
        source_pitch = scalar(pitch_values, start+(end-start)*progress)
        pitch = max(-4., min(19., contact_pitch-source_pitch))
        # Late toe-off retains a legible heel release even if the donor's
        # coarse low-toe interval excludes its original heel-rise frames.
        pitch += (17.-pitch)*motion.smooth((progress-.72)/.28)
        ball_pitch = -pitch*.72
        contact = 1.
    else:
        progress = (phase-stance)/(1.-stance)
        brake = .075
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
            shape, _, _ = learned_recovery(src, side, q)
            fore = back-overshoot+(front-back+2.*overshoot)*shape
        _, learned_lift, source_pitch = learned_recovery(src, side, progress)
        lift = config['foot_lift_cm']*learned_lift
        raw_pitch = max(-13., min(22., contact_pitch-source_pitch))
        blend_in = motion.smooth(progress/.14)
        blend_out = motion.smooth((1.-progress)/.14)
        pitch = (17.*(1.-blend_in)+raw_pitch*blend_in)*blend_out-2.*(1.-blend_out)
        ball_pitch = -pitch*.6
        toe.x += (1. if side == 'l' else -1.)*.55*learned_lift
        contact = 0.
    toe += FORWARD*fore+UP*lift
    foot_q = rot(RIGHT, pitch)@rest['foot_'+side].to_quaternion()
    ankle_to_ball = rest['foot_'+side].to_quaternion().inverted()@(rest['ball_'+side].translation-rest['foot_'+side].translation)
    goal = toe-foot_q@ankle_to_ball
    ball_q = rot(RIGHT, ball_pitch)@rot(RIGHT, pitch)@rest['ball_'+side].to_quaternion()
    return goal, foot_q, ball_q, contact


def install_legs(target, rest, local, data, src, u, config):
    goals, settling = {}, 0.
    for side, offset in (('l', 0.), ('r', .5)):
        goals[side] = foot_goal(rest, side, (u+offset)%1., src, config)
        goal = goals[side][0]
        hip, d = target['thigh_'+side].translation, data[side]
        reach = math.sqrt(d['upper_length']**2+d['lower_length']**2+
            2.*d['upper_length']*d['lower_length']*math.cos(math.radians(10.)))
        horizontal = (goal.x-hip.x)**2+(goal.y-hip.y)**2
        settling = max(settling, hip.z-goal.z-math.sqrt(max(0., reach*reach-horizontal)))
    if settling > 0.:
        for m in target.values():
            m.translation.z -= settling
    for side, offset in (('l', 0.), ('r', .5)):
        goal, foot_q, ball_q, _ = goals[side]
        source = dict(target)
        source['foot_'+side] = matrix(goal, foot_q)
        source['ball_'+side] = matrix(goal, ball_q)
        target.update(v17.solve_chain(rest, local, data, source, side, (u+offset)%1., config['stance_fraction']))
    return {s: goals[s][3] for s in goals}, settling


def install_arms_and_details(target, rest, local, ordered, old, src, phase, config):
    torso = target['spine_05'].to_quaternion()@rest['spine_05'].to_quaternion().inverted()
    body_forward = torso@FORWARD
    yaw = math.degrees(math.atan2(body_forward.x, -body_forward.y))
    arm_frame = rot(UP, yaw)
    deltas, arm_values = {}, {}
    for side, sign in (('l', 1.), ('r', -1.)):
        swings, bends, abduct = src['channels']['arm_'+side]
        swing = config['arm_swing_center_deg']+centered(scalar(swings, phase), swings, config['arm_swing_half_range_deg'])
        bend = config['elbow_center_deg']+centered(scalar(bends, phase), bends, config['elbow_half_range_deg'])
        outward = config['arm_abduction_deg']+centered(scalar(abduct, phase), abduct, config['arm_abduction_half_range_deg'])
        # Low relaxed hands and modest rear reach follow the chosen jog.
        # Torso pitch is not added again to the rear humerus excursion.
        sagittal = Vector((0., -math.sin(math.radians(swing)), -math.cos(math.radians(swing))))
        upper = arm_frame@(sagittal*math.cos(math.radians(outward))+RIGHT*(sign*math.sin(math.radians(outward))))
        upper.normalize()
        flex = arm_frame@FORWARD
        flex -= upper*flex.dot(upper)
        flex.normalize()
        lower = (upper*math.cos(math.radians(bend))+flex*math.sin(math.radians(bend))).normalized()
        original_u = (rest['lowerarm_'+side].translation-rest['upperarm_'+side].translation).normalized()
        original_l = (rest['hand_'+side].translation-rest['lowerarm_'+side].translation).normalized()
        reference_hinge = original_u.cross(original_l).normalized()
        hinge = upper.cross(lower).normalized()
        du = (motion.anatomical_frame(upper, hinge)@motion.anatomical_frame(original_u, reference_hinge).transposed()).to_quaternion()
        rest_bend = math.atan2(reference_hinge.dot(original_u.cross(original_l)), original_u.dot(original_l))
        # An explicit hinge transports both segments together. Independent
        # shortest-arc upper/forearm rotations can introduce an elbow roll.
        dl = du@Quaternion(reference_hinge, math.radians(bend)-rest_bend)
        deltas[side] = du, dl
        arm_values[side] = {'swing_deg': swing, 'elbow_deg': bend, 'abduction_deg': outward}
    for pose in ordered:
        name = pose.name
        if not name.startswith(('upperarm_', 'lowerarm_', 'hand_', 'thumb_', 'index_', 'middle_', 'ring_', 'pinky_', 'gill_')):
            continue
        parent = pose.parent.name
        point, q = v15.inherited(target, rest, local, pose)
        if name.startswith('upperarm_'):
            q = deltas[name[-1]][0]@rest[name].to_quaternion()
        elif name.startswith(('lowerarm_', 'hand_')):
            q = deltas[name[-1]][1]@rest[name].to_quaternion()
        else:
            # The accepted local finger shapes and existing gill breathing
            # are retained exactly from the original-rig V18 actions.
            detail_local = old[parent].inverted()@old[name]
            q = target[parent].to_quaternion()@detail_local.to_quaternion()
        target[name] = matrix(point, q)
    return arm_values


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    old_manifest = json.loads(OLD_MANIFEST.read_text(encoding='utf-8'))
    donors = {role: load_donor(role) for role in CONFIG}
    bpy.ops.wm.open_mainfile(filepath=str(OLD))
    rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and o.data.bones.get('gill_01_00'))
    rig.data.pose_position = 'POSE'
    ordered = sorted(rig.pose.bones, key=lambda p: len(p.bone.parent_recursive))
    detail_cache = {role: v17.cache_action(rig, bpy.data.actions[old_manifest['clips'][role]['action']],
        old_manifest['clips'][role]['frames'], ordered) for role in CONFIG}
    bpy.ops.wm.open_mainfile(filepath=str(SKIN))
    rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and o.data.bones.get('gill_01_00'))
    # The skin master is deliberately saved in REST. Baking in REST made
    # earlier exports static T poses, so POSE is mandatory before keying.
    rig.data.pose_position = 'POSE'
    rig.animation_data_clear()
    rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
    local = {b.name: b.parent.matrix_local.inverted()@b.matrix_local if b.parent else b.matrix_local.copy() for b in rig.data.bones}
    ordered = sorted(rig.pose.bones, key=lambda p: len(p.bone.parent_recursive))
    visibility = {o.name: o.hide_viewport for o in bpy.data.objects if o.type == 'MESH'}
    for name in visibility:
        bpy.data.objects[name].hide_viewport = True
    scene = bpy.context.scene
    scene.render.fps, scene.render.fps_base = FPS, 1.
    scene.unit_settings.system, scene.unit_settings.scale_length = 'METRIC', .01
    data = {s: v17.hinge_data(rest, s) for s in ('l', 'r')}
    donor_manifest = json.loads((DONOR/'donor_cache_manifest.json').read_text(encoding='utf-8'))
    manifest = {'revision': 'VideoLocomotionV19', 'source': str(OUT/'M07_Original_VideoLocomotion_V19.blend'),
        'mesh_skin_master': str(SKIN), 'detail_motion_master': str(OLD), 'fps': FPS,
        'reference_skeleton': old_manifest['reference_skeleton'], 'bone_names': list(rest),
        'bone_reference': {n: motion.rows(m) for n, m in rest.items()},
        'rig_object_matrix_world': motion.rows(rig.matrix_world),
        'reference_pose_modified': False, 'geometry_modified': False, 'weights_modified': False,
        'materials_modified': False, 'root_motion': False, 'animation_export_pose_position': 'POSE',
        'clips': {}, 'candidate': True, 'video_reference_imitation': True,
        'original_paid_animation_tracks_obtained': False,
        'video_reference': {'url': 'https://www.youtube.com/watch?v=dJ-Ak3X7tiM', 'seconds': [120., 125.],
            'observation': str(BASE/'Reference/observations.md'), 'cycle_seconds_inferred': 32./24.,
            'source_video_pixel_stride_is_not_cm': True,
            'target_style': 'Modest forward lean, ordinary forward human knees, compliant pelvis, counterturning chest, bent relaxed low hands, modest abduction; not maximum athletic arm swing'},
        'donor_provenance': donor_manifest, 'runtime_tested': False, 'rendered': False,
        'tested': False, 'visual_accepted': False, 'ue_imported': False,
        'scope': 'Two locomotion actions; immutable original 83-bone V11 reference, V17 skin and V16 arms, full original mesh/UV, existing local hand/gill details retained'}
    actions = {}
    for role, config in CONFIG.items():
        src = donors[role]
        duration, count = config['intervals']/FPS, config['intervals']+1
        action = bpy.data.actions.new('A_M07_'+role+'_VideoMotionV19')
        action.use_fake_user = True
        motion.activate(rig, action)
        previous, targets, settling = {}, [], []
        contacts, arms = {'l': [], 'r': []}, {'l': [], 'r': []}
        for i in range(count):
            frame, u = i+1, i/config['intervals']
            phase = donor_phase(src, u)
            scene.frame_set(frame)
            target = torso_pose(rest, local, ordered, src, phase, config)
            contact, settled = install_legs(target, rest, local, data, src, u, config)
            old = motion.sample({'samples': detail_cache[role], 'rest': rest}, u)
            arm = install_arms_and_details(target, rest, local, ordered, old, src, phase, config)
            if i == count-1:
                target = {n: m.copy() for n, m in targets[0].items()}
                contact = {s: contacts[s][0] for s in contacts}
                arm = {s: arms[s][0] for s in arms}
                settled = settling[0]
            targets.append(target)
            settling.append(settled)
            for side in contacts:
                contacts[side].append(contact[side])
                arms[side].append(arm[side])
            running.insert_frame(rig, target, rest, ordered, frame, previous)
        scene.frame_set(0)
        for pose in ordered:
            pose.matrix_basis = Matrix.Identity(4)
            for channel in ('location', 'rotation_quaternion', 'scale'):
                pose.keyframe_insert(data_path=channel, frame=0, group=pose.name)
        for curve in running.curves(action):
            for key in curve.keyframe_points:
                key.interpolation = 'LINEAR'
        file = OUT/('A_M07_'+role+'.fbx')
        v15.export(rig, action, file, count)
        speed_ratio = config['ai_speed_cm_s']/config['source_speed_cm_s']
        entry = {'role': role, 'action': action.name, 'file': str(file),
            'asset': '/Game/Monsters/BlindSupplicantM07/AnimationsVideoMotionV19/A_M07_'+role,
            'frames': count, 'fps': FPS, 'duration': duration, 'duration_seconds': duration,
            'seconds': duration, 'loop': True, 'root_motion': False,
            'speed_cm_s': config['source_speed_cm_s'], 'source_speed_cm_s': config['source_speed_cm_s'],
            'expected_speed_cm_s': config['ai_speed_cm_s'], 'ai_speed_cm_s': config['ai_speed_cm_s'],
            'expected_playback_ratio_at_ai_speed': speed_ratio,
            'expected_cycle_seconds_at_ai_speed': duration/speed_ratio,
            'stride_cm': config['source_speed_cm_s']*duration,
            'step_cm': config['source_speed_cm_s']*duration*.5,
            'source': {'kind': 'CC0 mature whole-body donor, video-guided authored imitation',
                'file': donor_manifest['source'], 'clip': src['donor'],
                'cache': str(DONOR/(src['donor']+'_world_30fps.json')),
                'source_duration_seconds': src['raw']['source_duration_seconds'],
                'source_phase_origin': src['phase_origin'], 'license': 'CC0-1.0'},
            'timing_note': 'Authored chase cadence matches inferred 1.333s reference. Existing AI speed is retained; native speed/source-speed playback advances this same coordinated whole-body motion faster. Video cm/s is unavailable, and source speeds are explicitly authored anatomical fit values.',
            'stance_fraction': config['stance_fraction'], 'foot_contact': contacts,
            'curves': {'FootContact_l': contacts['l'], 'FootContact_r': contacts['r']},
            'reference_only_blender_frame': 0, 'exported_blender_frame_start': 1,
            'exported_blender_frame_end': count, 'all_child_locations_zero_except_pelvis': True,
            'bone_tracks': list(rest), 'config': config,
            'max_reach_settling_cm': max(settling),
            'support_velocity_cm_s': config['source_speed_cm_s'],
            'recovery': 'Mature donor toe fore/aft and lift timing with bounded support-matched C1 braking; source ankle line recentered under actual original hips',
            'knee_frame': 'V17 common signed anatomical hinge; no arbitrary bone-local knee axes or independently rolled lower leg',
            'arm_frame': 'Complete donor phase/channels, low relaxed video pose, one explicit upper/forearm anatomical elbow hinge, bounded -12deg rear humerus excursion',
            'gill_avoidance': 'Existing bounded runtime contact node retained; no new runtime physics or collision workload',
            'details': 'Exact original-rig V18 local finger/gill articulation resampled to the new shared loop phase',
            'runtime_tested': False, 'rendered': False}
        write(OUT/('authored_'+role.lower()+'_production_record_v19.json'), {
            'scope': 'Direct production authoring records, not a separate export or visual test',
            'action': action.name, 'arms': arms, 'pelvis_reach_settling_cm': settling,
            'pelvis_xyz_cm': [list(t['pelvis'].translation) for t in targets],
            'foot_xyz_cm': {s: [list(t['foot_'+s].translation) for t in targets] for s in ('l', 'r')},
            'runtime_tested': False, 'rendered': False})
        manifest['clips'][role], actions[role] = entry, action
        print('M07_V19_CLIP_EXPORTED '+role+' '+json.dumps({'frames': count, 'duration': duration,
            'source_speed_cm_s': entry['source_speed_cm_s'], 'expected_playback_ratio': speed_ratio,
            'expected_runtime_cycle_seconds': entry['expected_cycle_seconds_at_ai_speed'],
            'max_reach_settling_cm': max(settling)}), flush=True)
    for name, hidden in visibility.items():
        bpy.data.objects[name].hide_viewport = hidden
    motion.activate(rig, actions['Chase'])
    scene.frame_start, scene.frame_end = 1, manifest['clips']['Chase']['frames']
    scene.frame_set(0)
    rig['locomotion_revision'] = 'V19 mature CC0 donor phase relationships, selected video jog imitation, natural signed anatomical knee/elbow frames; original model and bind retained'
    bpy.ops.wm.save_as_mainfile(filepath=manifest['source'], compress=True)
    manifest['source_saved'], manifest['animation_fbx_exported'] = True, True
    write(OUT/'video_locomotion_manifest_v19.json', manifest)
    print('M07_V19_VIDEO_LOCOMOTION_COMPLETE '+str(OUT), flush=True)


if __name__ == '__main__':
    main()
