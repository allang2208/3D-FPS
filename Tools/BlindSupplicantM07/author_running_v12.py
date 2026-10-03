"""Author M07 V12 large-stride coordinated walk/run on the unchanged V11 rig.

The installed Epic unarmed Jog supplies the running torso, shoulder and arm
timing; Witch Foundation's installed Epic Walk supplies the walk timing. The
feet are authored as physically matched support/recovery trajectories rather
than accelerating the old small-step clip. Geometry, UVs, weights, 83-bone
reference and the ten non-locomotion V11 actions remain unchanged. This script
only authors and exports source files; it does not render, test or launch UE.
"""
from pathlib import Path
import copy
import json
import math
import sys

import bpy
from mathutils import Euler, Matrix, Quaternion, Vector

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/BlindSupplicantM07Meshy20261001')
OUT = ROOT/'RunningV12'
RIG_OUT = OUT/'rig_motion'
SOURCE = ROOT/'RecoveryHandsV11/M07_Original_HandArm_Master_V11.blend'
V11_MANIFEST = ROOT/'RecoveryHandsV11/rig_motion/motion_manifest_v11.json'
FPS = 30
sys.path.insert(0, str(Path(__file__).parent))
import author_motion_v04 as motion

UP = Vector((0., 0., 1.))
FORWARD = Vector((0., -1., 0.))
OUTWARD = Vector((1., 0., 0.))
ROLES = {
    'SlowWalk': {
        'donor': 'Walk', 'intervals': 40, 'speed_cm_s': 160.,
        'stance_fraction': .61, 'foot_lift_cm': 23.,
        'crouch_cm': 8., 'pelvis_bounce_cm': 2.2, 'body_lean_deg': 4.,
        'upperarm_swing_deg': (-26., 38.), 'elbow_range_deg': (34., 66.),
        'arm_abduction_deg': 13., 'pelvis_yaw_deg': 3.8, 'shoulder_yaw_deg': 5.2,
        'push_off_pitch_deg': 23., 'recovery_pitch_deg': -13.,
    },
    'Chase': {
        'donor': 'Jog', 'intervals': 28, 'speed_cm_s': 360.,
        'stance_fraction': .38, 'foot_lift_cm': 58.,
        'crouch_cm': 13., 'pelvis_bounce_cm': 4.8, 'body_lean_deg': 11.,
        'upperarm_swing_deg': (-34., 50.), 'elbow_range_deg': (78., 100.),
        'arm_abduction_deg': 14., 'pelvis_yaw_deg': 5., 'shoulder_yaw_deg': 7.,
        'push_off_pitch_deg': 28., 'recovery_pitch_deg': -19.,
    },
}


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def curves(action):
    if not action.is_action_layered:
        return list(action.fcurves)
    return [curve for layer in action.layers for strip in layer.strips
            for bag in strip.channelbags for curve in bag.fcurves]


def rotation_x(degrees):
    return Quaternion((1., 0., 0.), math.radians(degrees))


def rotation_y(degrees):
    return Quaternion((0., 1., 0.), math.radians(degrees))


def rotation_z(degrees):
    return Quaternion((0., 0., 1.), math.radians(degrees))


def hermite(t, start, end, velocity_start, velocity_end):
    return ((2*t**3-3*t*t+1)*start + (t**3-2*t*t+t)*velocity_start
            + (-2*t**3+3*t*t)*end + (t**3-t*t)*velocity_end)


def source_cycle(source):
    """Select one complete left-leg cycle from the installed source span.

    The jogging asset contains more than one stride. Relative ball/pelvis
    motion removes any navigation/root travel before selecting successive
    forward extrema; this prevents retiming several running cycles into one.
    """
    samples = source['samples']
    relative_forward = [-(frame['ball_l'].translation.y-frame['pelvis'].translation.y)
                        for frame in samples]
    peaks = []
    for i in range(1, len(relative_forward)-1):
        if relative_forward[i] >= relative_forward[i-1] and relative_forward[i] > relative_forward[i+1]:
            if not peaks or i-peaks[-1] >= 7:
                peaks.append(i)
            elif relative_forward[i] > relative_forward[peaks[-1]]:
                peaks[-1] = i
    spans = [(a, b) for a, b in zip(peaks, peaks[1:]) if b-a >= 9]
    if spans:
        start, end = max(spans, key=lambda ab: (min(relative_forward[ab[0]], relative_forward[ab[1]]), ab[1]-ab[0]))
    else:
        # A single-cycle source may place the repeated extremum at its bounds.
        start, end = 0, len(samples)-1
    selected = samples[start:end+1]
    travel = selected[-1]['pelvis'].translation-selected[0]['pelvis'].translation
    mean = sum((frame['pelvis'].translation-travel*(i/(len(selected)-1))
                for i, frame in enumerate(selected)), Vector())/len(selected)
    source.update({'samples':selected, 'travel':travel, 'mean_pelvis':mean,
                   'cycle_sample_start':start, 'cycle_sample_end':end,
                   'cycle_duration_seconds':(end-start)/FPS,
                   'cycle_selection':'Successive left forefoot forward extrema after common pelvis travel removal'})
    return source


def read_donors():
    jog = json.loads((OUT/'donor/source_motion.json').read_text(encoding='utf-8'))['Jog']
    walk = json.loads((ROOT.parent/'WitchFoundation20260920/source_motion.json').read_text(encoding='utf-8'))['Walk']
    result = {}
    for role, record in (('Walk', walk), ('Jog', jog)):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.fbx(filepath=record['file'], use_anim=True)
        rig = next(obj for obj in bpy.data.objects if obj.type == 'ARMATURE')
        action = rig.animation_data.action
        motion.activate(rig, action)
        rate = bpy.context.scene.render.fps/bpy.context.scene.render.fps_base
        count = int(record['frames'])+1
        samples = []
        for i in range(count):
            frame = 1+i/FPS*rate
            bpy.context.scene.frame_set(math.floor(frame), subframe=frame % 1.)
            samples.append({p.name:rig.matrix_world@p.matrix for p in rig.pose.bones})
        source = {'samples':samples,
                  'rest':{b.name:rig.matrix_world@b.matrix_local for b in rig.data.bones},
                  'source':record['file'], 'asset':record['asset'], 'source_frames':record['frames'],
                  'source_duration_seconds':record['duration'], 'source_fps':rate,
                  'license':'Installed Epic UE mannequin template; local UE project adaptation only'}
        source_cycle(source)
        result[role] = source
        print('M07_V12_DONOR_CYCLE '+role+' '+str(source['cycle_sample_start'])+'..'+str(source['cycle_sample_end']), flush=True)
    return result


def arm_profile(source, side):
    values = []
    for raw in source['samples'][:-1]:
        torso = raw['spine_03'].to_quaternion()@source['rest']['spine_03'].to_quaternion().inverted()
        upper = torso.inverted()@(raw['lowerarm_'+side].translation-raw['upperarm_'+side].translation)
        values.append(math.atan2(-upper.y, -upper.z))
    lo, hi = min(values), max(values)
    return {'center':(lo+hi)*.5, 'amplitude':max(.03, (hi-lo)*.5)}


def foot_trajectory(phase, config, stride_cm, anchor, side):
    """Support speed equals capsule speed; recovery includes genuine lift.

    Stance is linear in navigation space. Recovery is a Hermite return with
    the same start/end horizontal velocity as support, while heel recovery
    raises the four-bone original foot without introducing an extra hock.
    """
    stance = config['stance_fraction']
    support_distance = stride_cm*stance
    front = support_distance*.52
    back = front-support_distance
    toe = anchor.copy()
    if phase < stance:
        progress = phase/stance
        forward = front-stride_cm*phase
        lift = 0.
        pitch = -3.*(1.-motion.smooth(progress/.18))
        pitch += config['push_off_pitch_deg']*motion.smooth((progress-.58)/.42)
        toe_pitch = -min(17., pitch*.70)
        contact = 1.
    else:
        progress = (phase-stance)/(1.-stance)
        tangent = -stride_cm*(1.-stance)
        forward = hermite(progress, back, front, tangent, tangent)
        lift = config['foot_lift_cm']*math.sin(math.pi*progress)**1.65
        pitch = config['push_off_pitch_deg']*(1.-motion.smooth(progress/.23))
        pitch += config['recovery_pitch_deg']*math.sin(math.pi*progress)**1.2
        pitch -= 3.*motion.smooth((progress-.78)/.22)
        toe_pitch = -8.*math.sin(math.pi*progress)
        contact = 0.
    toe += FORWARD*forward+UP*lift
    toe.x += (1. if side == 'l' else -1.)*2.0*math.sin(math.pi*phase)**2
    return toe, pitch, toe_pitch, contact


def geometric_rotation(original_upper, original_lower, upper, lower):
    reference_hinge = original_upper.cross(original_lower)
    if reference_hinge.length < 1.e-8:
        reference_hinge = Vector((1., 0., 0.))
    reference_hinge.normalize()
    hinge = upper.cross(lower).normalized()
    return (motion.anatomical_frame(upper, hinge)@motion.anatomical_frame(original_upper, reference_hinge).transposed(),
            motion.anatomical_frame(lower, hinge)@motion.anatomical_frame(original_lower, reference_hinge).transposed())


def rebuild_descendants(target, rest, local, ordered, changed, skip=()):
    """Fixed child offsets are always evaluated with explicitly known parents."""
    descendants = set(changed)
    for pose in ordered:
        n = pose.name
        parent = pose.parent.name if pose.parent else None
        if n in skip or n in changed or parent not in descendants:
            continue
        q = target[parent].to_quaternion()@rest[parent].to_quaternion().inverted()@rest[n].to_quaternion()
        target[n] = Matrix.LocRotScale(target[parent]@local[n].translation, q, Vector((1., 1., 1.)))
        descendants.add(n)


def pose_body(rest, local, ordered, source, raw, u, config, leg_ratio):
    common = source['travel']*u
    sway = raw['pelvis'].translation-common-source['mean_pelvis']
    theta = 2.*math.pi*u
    pelvis_position = rest['pelvis'].translation.copy()
    pelvis_position.x += max(-3.5, min(3.5, sway.x*leg_ratio))
    pelvis_position.y += max(-1.5, min(1.5, sway.y*leg_ratio*.2))
    pelvis_position.z -= config['crouch_cm']
    pelvis_position.z += config['pelvis_bounce_cm']*(-math.cos(2.*theta))
    pelvis_position.z += max(-2., min(2., sway.z*leg_ratio*.30))
    target = {}
    lean = rotation_x(config['body_lean_deg'])
    # Targeted pelvis and shoulder opposition is layered on the mature cycle.
    pelvis_delta = (rotation_x(config['body_lean_deg']*.30)
                    @rotation_z(-config['pelvis_yaw_deg']*math.cos(theta))
                    @rotation_y(1.4*math.sin(theta)))
    for pose in ordered:
        n = pose.name
        parent = pose.parent.name if pose.parent else None
        position = target[parent]@local[n].translation if parent else rest[n].translation.copy()
        if n == 'pelvis':
            position = pelvis_position
            q = pelvis_delta@rest[n].to_quaternion()
        elif n in raw and n.startswith(('spine_', 'clavicle_', 'neck_', 'head')):
            donor_delta = raw[n].to_quaternion()@source['rest'][n].to_quaternion().inverted()
            # Preserve the donor's rich torso timing without forcing its exact
            # human shoulder offsets onto M07's much wider source anatomy.
            donor_expression = Quaternion().slerp(donor_delta, .55)
            if n.startswith(('neck_', 'head')):
                yaw = config['shoulder_yaw_deg']*.38
            else:
                yaw = config['shoulder_yaw_deg']
            q = lean@rotation_z(yaw*math.cos(theta))@donor_expression@rest[n].to_quaternion()
        elif parent:
            q = target[parent].to_quaternion()@rest[parent].to_quaternion().inverted()@rest[n].to_quaternion()
        else:
            q = rest[n].to_quaternion()
        target[n] = Matrix.LocRotScale(position, q, Vector((1., 1., 1.)))
    return target


def pose_legs(target, rest, local, ordered, u, config, stride_cm):
    foot_targets = {}
    additional_settling = 0.
    pelvis_delta = target['pelvis'].to_quaternion()@rest['pelvis'].to_quaternion().inverted()
    for side, offset in (('l', 0.), ('r', .5)):
        phase = (u+offset) % 1.
        toe, pitch, toe_pitch, contact = foot_trajectory(phase, config, stride_cm, rest['ball_'+side].translation, side)
        foot_q = rotation_x(pitch)@rest['foot_'+side].to_quaternion()
        ankle_to_ball = rest['foot_'+side].to_quaternion().inverted()@(rest['ball_'+side].translation-rest['foot_'+side].translation)
        goal = toe-foot_q@ankle_to_ball
        hip = target['thigh_'+side].translation
        l1 = (rest['calf_'+side].translation-rest['thigh_'+side].translation).length
        l2 = (rest['foot_'+side].translation-rest['calf_'+side].translation).length
        reach = (l1+l2)*.993
        horizontal = (goal.x-hip.x)**2+(goal.y-hip.y)**2
        available = math.sqrt(max(0., reach*reach-horizontal))
        additional_settling = max(additional_settling, hip.z-goal.z-available)
        foot_targets[side] = (toe, goal, foot_q, toe_pitch, contact)
    if additional_settling > 0.:
        for matrix in target.values():
            matrix.translation.z -= additional_settling
    contacts = {}
    for side, (toe, goal, foot_q, toe_pitch, contact) in foot_targets.items():
        thigh, calf, foot, ball = [name+'_'+side for name in ('thigh', 'calf', 'foot', 'ball')]
        hip = target[thigh].translation.copy()
        original_upper = rest[calf].translation-rest[thigh].translation
        original_lower = rest[foot].translation-rest[calf].translation
        l1, l2 = original_upper.length, original_lower.length
        vector = goal-hip
        axis = vector.normalized()
        minimum = math.sqrt(l1*l1+l2*l2+2.*l1*l2*math.cos(math.radians(148.)))
        distance = max(minimum, min(vector.length, (l1+l2)*.995))
        # Human knees bend in the forward sagittal plane. M07's original
        # reference joints are retained; its old backward hock is not reused.
        bend = pelvis_delta@FORWARD
        bend -= axis*bend.dot(axis)
        bend.normalize()
        along = (l1*l1-l2*l2+distance*distance)/(2.*distance)
        knee = hip+axis*along+bend*math.sqrt(max(0., l1*l1-along*along))
        ankle = hip+axis*distance
        upper, lower = (knee-hip).normalized(), (ankle-knee).normalized()
        upper_rot, lower_rot = geometric_rotation(original_upper, original_lower, upper, lower)
        target[thigh] = Matrix.LocRotScale(hip, upper_rot.to_quaternion()@rest[thigh].to_quaternion(), Vector((1.,1.,1.)))
        target[calf] = Matrix.LocRotScale(knee, lower_rot.to_quaternion()@rest[calf].to_quaternion(), Vector((1.,1.,1.)))
        target[foot] = Matrix.LocRotScale(ankle, foot_q, Vector((1.,1.,1.)))
        foot_delta = foot_q@rest[foot].to_quaternion().inverted()
        toe_q = rotation_x(toe_pitch)@foot_delta@rest[ball].to_quaternion()
        target[ball] = Matrix.LocRotScale(toe, toe_q, Vector((1.,1.,1.)))
        contacts[side] = contact
    return contacts


def pose_arms(target, rest, local, ordered, source, raw, u, config, profiles, curls):
    torso = target['spine_03'].to_quaternion()@rest['spine_03'].to_quaternion().inverted()
    forward, up, outward = torso@FORWARD, torso@UP, torso@OUTWARD
    raw_torso = raw['spine_03'].to_quaternion()@source['rest']['spine_03'].to_quaternion().inverted()
    for side, sign, offset in (('l',1.,0.), ('r',-1.,.5)):
        upper_name, lower_name, hand_name = [n+'_'+side for n in ('upperarm','lowerarm','hand')]
        phase = (u+offset) % 1.
        raw_upper = raw_torso.inverted()@(raw[lower_name].translation-raw[upper_name].translation)
        donor_angle = math.atan2(-raw_upper.y, -raw_upper.z)
        profile = profiles[side]
        donor_wave = max(-1., min(1., (donor_angle-profile['center'])/profile['amplitude']))
        # Left hand retracts as left foot advances; right side is opposite.
        wave = -.88*math.cos(2.*math.pi*phase)+.12*donor_wave
        lo, hi = config['upperarm_swing_deg']
        theta = math.radians((lo+hi)*.5+(hi-lo)*.5*wave)
        elbow_lo, elbow_hi = config['elbow_range_deg']
        elbow_angle = math.radians(elbow_lo+(elbow_hi-elbow_lo)*(.5+.5*wave))
        abduction = math.radians(config['arm_abduction_deg'])
        sagittal = forward*math.sin(theta)-up*math.cos(theta)
        upper = (sagittal*math.cos(abduction)+outward*(sign*math.sin(abduction))).normalized()
        # A single analytic flexion plane stays continuous through the large
        # swing. There is no stateless pole projection or elbow sign switch.
        flex = forward-upper*forward.dot(upper)
        flex.normalize()
        lower = (upper*math.cos(elbow_angle)+flex*math.sin(elbow_angle)).normalized()
        original_upper = rest[lower_name].translation-rest[upper_name].translation
        original_lower = rest[hand_name].translation-rest[lower_name].translation
        shoulder = target[upper_name].translation.copy()
        elbow = shoulder+upper*original_upper.length
        wrist = elbow+lower*original_lower.length
        upper_rot, lower_rot = geometric_rotation(original_upper, original_lower, upper, lower)
        target[upper_name] = Matrix.LocRotScale(shoulder, upper_rot.to_quaternion()@rest[upper_name].to_quaternion(), Vector((1.,1.,1.)))
        lower_q = lower_rot.to_quaternion()@rest[lower_name].to_quaternion()
        target[lower_name] = Matrix.LocRotScale(elbow, lower_q, Vector((1.,1.,1.)))
        neutral = lower_q@rest[lower_name].to_quaternion().inverted()@rest[hand_name].to_quaternion()
        wrist_q = neutral@rotation_x(3.2*math.sin(2.*math.pi*phase-.18))
        target[hand_name] = Matrix.LocRotScale(wrist, wrist_q, Vector((1.,1.,1.)))
        for pose in ordered:
            n = pose.name
            if not n.endswith('_'+side) or not n.startswith(('thumb_', 'index_', 'middle_', 'ring_', 'pinky_')):
                continue
            parent = pose.parent.name
            position = target[parent]@local[n].translation
            local_q = local[n].to_quaternion()
            if '_metacarpal_' not in n:
                finger, segment, _ = n.split('_')
                degrees = curls[finger][int(segment)-1]*.85
                degrees += 1.3*math.sin(2.*math.pi*phase+.2+int(segment)*.15)
                local_q = local_q@rotation_x(degrees)
                if finger == 'thumb' and segment == '01':
                    local_q = local_q@rotation_y(3.)
            target[n] = Matrix.LocRotScale(position, target[parent].to_quaternion()@local_q, Vector((1.,1.,1.)))


def pose_gills(target, rest, local, ordered, u):
    for pose in ordered:
        n = pose.name
        if not n.startswith('gill_'):
            continue
        _, panel, segment = n.split('_')
        phase = -(int(panel)-1)*.38
        wave = math.sin(2.*math.pi*u+phase)-math.sin(phase)
        q = rotation_x((1.+int(segment)*.65)*wave)@rotation_y(.4*wave)
        parent = pose.parent.name
        target[n] = Matrix.LocRotScale(target[parent]@local[n].translation,
                target[parent].to_quaternion()@local[n].to_quaternion()@q, Vector((1.,1.,1.)))


def insert_frame(rig, target, rest, ordered, frame, previous):
    for pose in ordered:
        n = pose.name
        parent = pose.parent.name if pose.parent else None
        kwargs = {'parent_matrix':target[parent], 'parent_matrix_local':rest[parent]} if parent else {}
        pose.matrix_basis = pose.bone.convert_local_to_pose(target[n], rest[n], invert=True, **kwargs)
        pose.rotation_mode = 'QUATERNION'
        pose.scale = Vector((1.,1.,1.))
        if n != 'pelvis':
            pose.location = Vector()
        q = pose.rotation_quaternion.copy()
        if n in previous and q.dot(previous[n]) < 0.:
            q.negate()
        pose.rotation_quaternion = q
        previous[n] = q.copy()
        for prop in ('location','rotation_quaternion','scale'):
            pose.keyframe_insert(data_path=prop, frame=frame, group=n)


def author():
    OUT.mkdir(parents=True, exist_ok=True)
    RIG_OUT.mkdir(parents=True, exist_ok=True)
    donors = read_donors()
    v11 = json.loads(V11_MANIFEST.read_text(encoding='utf-8'))
    curls = json.loads((ROOT/'RecoveryOriginalV07/hands/hand_action_guides_v07.json').read_text(encoding='utf-8'))['recommended_curl_degrees']['Locomotion']
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    rig = next(obj for obj in bpy.data.objects if obj.type == 'ARMATURE' and obj.data.bones.get('gill_01_00'))
    original_visibility = {o.name:o.hide_viewport for o in bpy.data.objects if o.type == 'MESH'}
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            obj.hide_viewport = True
    rig.animation_data_clear()
    rig.data.pose_position = 'POSE'
    rig.hide_set(False)
    rest = {b.name:b.matrix_local.copy() for b in rig.data.bones}
    local = {b.name:b.parent.matrix_local.inverted()@b.matrix_local if b.parent else b.matrix_local.copy() for b in rig.data.bones}
    ordered = sorted(rig.pose.bones, key=lambda p:len(p.bone.parent_recursive))
    scene = bpy.context.scene
    scene.render.fps, scene.render.fps_base = FPS, 1
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = .01
    manifest = {
        'revision':'RunningV12', 'fps':FPS, 'source':str(OUT/'M07_Original_Running_V12.blend'),
        'source_master':str(SOURCE), 'reference_skeleton':v11['ue_skeleton'],
        'reference_bones':copy.deepcopy(v11['reference_bones']), 'reference_pose_modified':False,
        'geometry_modified':False, 'weights_modified':False, 'materials_modified':False,
        'reference_units':v11['reference_units'], 'clips':{},
        'retained_clips':{role:copy.deepcopy(entry) for role,entry in v11['clips'].items() if role not in ROLES},
        'method':'Installed Epic Walk/Jog timing with larger contralateral upper-arm swing and torso opposition; authored linear planted-foot support matched to navigation speed, Hermite recovery, forward human knees, ankle push-off, relaxed fingers, preserved original V11 joint offsets',
        'donors':{}, 'source_saved':False, 'animation_fbx_exported':False,
        'tested':False, 'rendered':False, 'runtime_tested':False, 'visual_accepted':False,
    }
    actions = {}
    for role, config in ROLES.items():
        donor = donors[config['donor']]
        count = config['intervals']+1
        duration = config['intervals']/FPS
        stride = config['speed_cm_s']*duration
        action = bpy.data.actions.new('A_M07_'+role+'_RunningV12')
        action.use_fake_user = True
        motion.activate(rig, action)
        actions[role] = action
        profiles = {side:arm_profile(donor, side) for side in ('l','r')}
        source_leg_length = sum((donor['rest']['calf_'+s].translation-donor['rest']['thigh_'+s].translation).length+
                                (donor['rest']['foot_'+s].translation-donor['rest']['calf_'+s].translation).length for s in ('l','r'))
        target_leg_length = sum((rest['calf_'+s].translation-rest['thigh_'+s].translation).length+
                                (rest['foot_'+s].translation-rest['calf_'+s].translation).length for s in ('l','r'))
        leg_ratio = target_leg_length/source_leg_length
        previous = {}
        contacts = {'l':[], 'r':[]}
        opening = None
        for i in range(count):
            scene.frame_set(i+1)
            u = i/config['intervals']
            raw = motion.sample(donor, u)
            target = pose_body(rest, local, ordered, donor, raw, u, config, leg_ratio)
            foot_contact = pose_legs(target, rest, local, ordered, u, config, stride)
            pose_arms(target, rest, local, ordered, donor, raw, u, config, profiles, curls)
            pose_gills(target, rest, local, ordered, u)
            if opening is None:
                opening = {n:m.copy() for n,m in target.items()}
            if i == config['intervals']:
                target = {n:m.copy() for n,m in opening.items()}
            insert_frame(rig, target, rest, ordered, i+1, previous)
            for side in contacts:
                contacts[side].append(foot_contact[side])
        scene.frame_set(0)
        for pose in ordered:
            pose.matrix_basis = Matrix.Identity(4)
            for prop in ('location','rotation_quaternion','scale'):
                pose.keyframe_insert(data_path=prop, frame=0, group=pose.name)
        for curve in curves(action):
            for point in curve.keyframe_points:
                point.interpolation = 'LINEAR'
        manifest['clips'][role] = {
            'action':action.name, 'file':str(RIG_OUT/('A_M07_'+role+'.fbx')),
            'asset':'/Game/Monsters/BlindSupplicantM07/AnimationsRunningV12/A_M07_'+role,
            'frames':count, 'fps':FPS, 'duration_seconds':duration, 'duration':duration,
            'seconds':duration, 'loop':True, 'root_motion':False,
            'speed_cm_s':config['speed_cm_s'], 'expected_speed_cm_s':config['speed_cm_s'],
            'stride_cm':stride, 'step_cm':stride*.5, 'steps_per_cycle':2,
            'play_rate':1., 'playback_rate':1.,
            'stance_fraction':config['stance_fraction'], 'flight_phase':role == 'Chase',
            'arm_upper_sagittal_range_degrees':list(config['upperarm_swing_deg']),
            'elbow_bend_range_degrees':list(config['elbow_range_deg']),
            'arm_abduction_degrees':config['arm_abduction_deg'],
            'forefoot_recovery_lift_cm':config['foot_lift_cm'],
            'body_lean_degrees':config['body_lean_deg'], 'arm_leg_phase':'Contralateral; ipsilateral arm retracts when foot advances',
            'foot_contact':contacts, 'curves':{'FootContact_l':contacts['l'],'FootContact_r':contacts['r']},
            'reference_only_frame':0, 'export_frame_start':1, 'export_frame_end':count,
            'exported_blender_frame_start':1, 'exported_blender_frame_end':count,
            'bone_tracks':[p.name for p in ordered], 'source_donor':config['donor'],
        }
        print('M07_V12_AUTHORED '+role+' '+str(duration)+'s stride='+str(stride)+'cm speed='+str(config['speed_cm_s']), flush=True)
    for role, source in donors.items():
        manifest['donors'][role] = {k:copy.deepcopy(source[k]) for k in ('source','asset','source_frames','source_duration_seconds','source_fps','license','cycle_sample_start','cycle_sample_end','cycle_duration_seconds','cycle_selection')}
    bpy.ops.object.select_all(action='DESELECT')
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    for role, entry in manifest['clips'].items():
        motion.activate(rig, actions[role])
        scene.frame_start, scene.frame_end = 1, entry['frames']
        scene.frame_set(0)
        bpy.ops.export_scene.fbx(filepath=entry['file'], use_selection=True,
            object_types={'ARMATURE'}, add_leaf_bones=False, use_armature_deform_only=False,
            armature_nodetype='NULL', bake_anim=True, bake_anim_use_all_bones=True,
            bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False,
            bake_anim_force_startend_keying=True, bake_anim_step=1,
            bake_anim_simplify_factor=0., axis_forward='-Y', axis_up='Z',
            apply_unit_scale=True, apply_scale_options='FBX_SCALE_UNITS')
        print('M07_V12_EXPORTED '+role, flush=True)
    for name, hidden in original_visibility.items():
        bpy.data.objects[name].hide_viewport = hidden
    motion.activate(rig, actions['Chase'])
    scene.frame_start, scene.frame_end = 1, manifest['clips']['Chase']['frames']
    scene.frame_set(0)
    rig['locomotion_revision'] = 'RunningV12: original V11 rig; 160 cm/s walk and 360 cm/s coordinated large-stride human run'
    destination = OUT/'M07_Original_Running_V12.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(destination), compress=True)
    manifest.update({'source_saved':True, 'animation_fbx_exported':True,
                     'other_ten_actions_retained':True, 'ue_imported':False})
    write_json(OUT/'motion_manifest_v12.json', manifest)
    print('M07_V12_RUNNING_SOURCE_AND_TWO_FBX_SAVED '+str(destination), flush=True)


if __name__ == '__main__':
    author()
