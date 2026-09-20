"""Two-hand overhead mining strike from the current rustic-pickaxe grasp.

The existing sword overhead supplies the raise/hold/chop/recover reference.
The pickaxe has its own path and fixed grips. No preview or runtime tests.
"""
import copy
import json
import math
from pathlib import Path

import bpy
from mathutils import Matrix, Quaternion, Vector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CFG = json.loads((HERE/'motion.json').read_text(encoding='utf-8'))
SOURCE = ROOT/'SourceAssets/RusticPickaxe20260919/RusticPickaxe_TwoHand_Editable.blend'
REFERENCE = ROOT/'SourceAssets/RuneSword20260913/InspectGripArcV46/AzureRunesword_OverheadV52.blend'
OUT = HERE/'Export'
OUT.mkdir(parents=True, exist_ok=True)
FPS = CFG['fps']
STATIONS = json.loads((ROOT/'SourceAssets/AxeTwoHandAttack20260919/V5/authoring.json').read_text(encoding='utf-8'))['skin_stations']

# Read actual source keys, in addition to the existing rendered reference sheet.
bpy.ops.wm.open_mainfile(filepath=str(REFERENCE))
ref_rig = bpy.data.objects['SK_RuneSword_Rig']
ref_action = bpy.data.actions['A_RuneSword_Overhead']
ref_rig.animation_data.action = ref_action
ref_rig.animation_data.action_slot = ref_action.slots[0]
ref_scene = bpy.context.scene
ref_fps = ref_scene.render.fps/ref_scene.render.fps_base
reference_poses = []
for seconds in (0., .63, 1.08, 1.30, 1.42, 2.60):
    frame = seconds*ref_fps
    ref_scene.frame_set(math.floor(frame), subframe=frame-math.floor(frame))
    reference_poses.append({'seconds': seconds,
        'hands': {side: list(ref_rig.pose.bones['hand_'+side].matrix.translation) for side in ('l', 'r')}})

bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
bpy.context.preferences.filepaths.save_version = 0
scene = bpy.context.scene
rig = bpy.data.objects['SK_RusticPickaxe_Rig']
original_idle = bpy.data.actions['A_RusticPickaxe_Idle']
rig.animation_data.action = original_idle
rig.animation_data.action_slot = original_idle.slots[0]
scene.frame_set(0)
rest = {bone.name: bone.matrix_local.copy() for bone in rig.data.bones}
local_rest = {bone.name: rest[bone.parent.name].inverted() @ rest[bone.name] if bone.parent else rest[bone.name]
              for bone in rig.data.bones}
idle = {bone.name: bone.matrix.copy() for bone in rig.pose.bones}
ready = idle['WPN_root']
grips = {side: ready.inverted() @ idle['hand_'+side] for side in ('l', 'r')}
finger_basis = {bone.name: bone.matrix_basis.copy() for bone in rig.pose.bones
                if bone.name.startswith(('thumb', 'index', 'middle', 'ring', 'pinky'))}
PIVOT = Vector(CFG['grip_pivot_local_m'])
READY_CENTER = ready @ PIVOT


def ease(u):
    u = max(0., min(1., u))
    return u*u*u*(10.-15.*u+6.*u*u)


def blend(a, b, u):
    return Matrix.LocRotScale(a.translation.lerp(b.translation, u),
        a.to_quaternion().slerp(b.to_quaternion(), u), Vector((1, 1, 1)))


def centered(center, quaternion):
    return Matrix.LocRotScale(Vector(center)-quaternion @ PIVOT, quaternion, Vector((1, 1, 1)))


def pitch_frame(center, degrees):
    angle = math.radians(degrees)
    shaft = Vector((0, math.sin(angle), math.cos(angle)))
    point = Vector((0, math.cos(angle), -math.sin(angle)))
    return centered(center, Matrix((point, shaft.cross(point), shaft)).transposed().to_quaternion())


def key(label):
    return pitch_frame(CFG[label]['center_m'], CFG[label]['pitch_degrees'])


TOP, IMPACT, FOLLOW, REBOUND = [key(label) for label in ('top', 'impact', 'follow', 'rebound')]


def bezier(frames, u):
    # Interpolate the grip midpoint, not the distant root; the head and both
    # fixed hand contacts travel along the same continuous rigid-tool curve.
    centers = [frame @ PIVOT for frame in frames]
    quats = [frame.to_quaternion() for frame in frames]
    while len(centers) > 1:
        centers = [a.lerp(b, u) for a, b in zip(centers, centers[1:])]
        quats = [a.slerp(b, u) for a, b in zip(quats, quats[1:])]
    return centered(centers[0], quats[0])


def return_frame(start, u):
    center = start @ PIVOT
    return bezier([start, pitch_frame(center+Vector((0, -.035, -.025)), 62),
        centered(READY_CENTER+Vector((.035, -.035, -.035)), ready.to_quaternion()), ready], ease(u))


def swing_frame(seconds):
    if seconds <= CFG['raise_end_seconds']:
        u = ease(seconds/CFG['raise_end_seconds'])
        return bezier([ready, pitch_frame((.065, .365, -.055), 32),
            pitch_frame((.025, .32, .23), -10), TOP], u)
    if seconds <= CFG['release_seconds']:
        return TOP.copy()
    if seconds <= CFG['contact_seconds']:
        u = (seconds-CFG['release_seconds'])/(CFG['contact_seconds']-CFG['release_seconds'])
        return bezier([TOP, pitch_frame((.015, .335, .29), -20),
            pitch_frame((.015, .455, .085), 58), IMPACT], u**1.8)
    if seconds <= CFG['follow_end_seconds']:
        u = (seconds-CFG['contact_seconds'])/(CFG['follow_end_seconds']-CFG['contact_seconds'])
        return blend(IMPACT, FOLLOW, 1.-(1.-u)**2.6)
    return return_frame(FOLLOW, (seconds-CFG['follow_end_seconds'])/(CFG['swing_seconds']-CFG['follow_end_seconds']))


def hit_frame(age):
    if age <= CFG['hit_hold_seconds']:
        return IMPACT.copy()
    if age <= CFG['hit_release_seconds']:
        return blend(IMPACT, REBOUND, ease((age-CFG['hit_hold_seconds'])/
                     (CFG['hit_release_seconds']-CFG['hit_hold_seconds'])))
    return return_frame(REBOUND, (age-CFG['hit_release_seconds'])/
        (CFG['swing_seconds']-CFG['contact_seconds']-CFG['hit_release_seconds']))


def unwrap(angle, previous):
    return angle if previous is None else previous+(angle-previous+math.pi)%(2*math.pi)-math.pi


def axial_delta(a, b, axis):
    q = a @ b.inverted()
    return (2*math.atan2(Vector((q.x, q.y, q.z)).dot(axis), q.w)+math.pi)%(2*math.pi)-math.pi


def frame_rotation(axis, normal):
    return Matrix((axis, normal, axis.cross(normal))).transposed().to_quaternion()


def solve_arm(pose, side, hand, weight, state):
    upper, fore, wrist = [part+'_'+side for part in ('upperarm', 'lowerarm', 'hand')]
    sign = 1. if side == 'r' else -1.
    l1 = (rest[fore].translation-rest[upper].translation).length
    l2 = (rest[wrist].translation-rest[fore].translation).length
    up_rest = (rest[fore].translation-rest[upper].translation).normalized()
    fore_rest = (rest[wrist].translation-rest[fore].translation).normalized()
    normal_rest = up_rest.cross(fore_rest).normalized()
    up_frame = frame_rotation(up_rest, normal_rest)
    fore_frame = frame_rotation(fore_rest, normal_rest)
    target = hand.translation
    elevation = ease((target.z-idle[wrist].translation.z)/.52)
    shoulder = idle[upper].translation+Vector((.005*sign, CFG['shoulder_forward_m'],
                        CFG['shoulder_lift_m']*elevation))*weight
    hand_deform = hand.to_quaternion() @ rest[wrist].to_quaternion().inverted()
    neutral = hand_deform @ fore_rest
    neutral_elbow = target-neutral*l2
    support = neutral_elbow-shoulder
    limit = CFG['neutral_shoulder_assist_m']
    shoulder += support.normalized()*limit*math.tanh(max(0., support.length-l1)/limit)*weight
    reach = target-shoulder
    direction = reach.normalized()
    shoulder += direction*max(0., reach.length-CFG['reach_fraction']*(l1+l2))
    distance = (target-shoulder).length
    along = (l1*l1-l2*l2+distance*distance)/(2*distance)
    radius = math.sqrt(max(0., l1*l1-along*along))
    center = shoulder+direction*along
    natural = Vector((.55*sign, -.12, -1.))
    natural = (natural-direction*natural.dot(direction)).normalized()
    previous_pole = state.get(side+'_pole', 0.)
    previous_roll = state.get(side+'_roll')

    def geometry(angle):
        elbow = center+(Quaternion(direction, angle) @ natural)*radius
        up_axis = (elbow-shoulder).normalized()
        fore_axis = (target-elbow).normalized()
        normal = up_axis.cross(fore_axis).normalized()
        upper_deform = frame_rotation(up_axis, normal) @ up_frame.inverted()
        hinge = frame_rotation(fore_axis, normal) @ fore_frame.inverted()
        full_fore = neutral.rotation_difference(fore_axis) @ hand_deform
        roll = unwrap(axial_delta(full_fore, hinge, fore_axis), previous_roll)
        wrist_bend = neutral.angle(fore_axis)
        inward = max(0., .025-sign*elbow.x)
        raised = max(0., elbow.z-target.z+.045)
        excess_roll = max(0., abs(roll)-math.radians(80))
        wrist_excess = max(0., wrist_bend-math.radians(35))
        # Keep each elbow on its own side instead of solving a straighter wrist
        # by folding the left upper arm across the body beneath the right arm.
        cost = 3.*wrist_bend*wrist_bend+3.*wrist_excess*wrist_excess+.18*roll*roll+.6*excess_roll*excess_roll \
            +(inward*28.)**2+(raised*12.)**2+.035*angle*angle+.10*(angle-previous_pole)**2
        return cost, elbow, up_axis, fore_axis, upper_deform, full_fore, roll

    cap = math.radians(CFG['elbow_pole_limit_degrees'])
    angle = min((-cap+2*cap*i/68 for i in range(69)), key=lambda a: geometry(a)[0])
    lo, hi = max(-cap, angle-cap/34), min(cap, angle+cap/34)
    for _ in range(12):
        a, b = lo+(hi-lo)*.382, lo+(hi-lo)*.618
        if geometry(a)[0] < geometry(b)[0]:
            hi = b
        else:
            lo = a
    angle = (lo+hi)*.5
    state[side+'_pole'] = angle
    # Fade from the idle bend plane along the IK circle, not by shortening bones.
    idle_pole = idle[fore].translation-center
    idle_pole = (idle_pole-direction*idle_pole.dot(direction)).normalized()
    desired_pole = Quaternion(direction, angle) @ natural
    pole_delta = math.atan2(direction.dot(idle_pole.cross(desired_pole)), idle_pole.dot(desired_pole))
    elbow = center+(Quaternion(direction, pole_delta*weight) @ idle_pole)*radius
    up_axis = (elbow-shoulder).normalized()
    fore_axis = (target-elbow).normalized()
    normal = up_axis.cross(fore_axis).normalized()
    upper_deform = frame_rotation(up_axis, normal) @ up_frame.inverted()
    hinge = frame_rotation(fore_axis, normal) @ fore_frame.inverted()
    full_fore = neutral.rotation_difference(fore_axis) @ hand_deform
    roll = unwrap(axial_delta(full_fore, hinge, fore_axis), previous_roll)
    state[side+'_roll'] = roll
    share_cap = math.radians(CFG['upper_arm_roll_limit_degrees'])
    share = max(-share_cap, min(share_cap, roll*CFG['upper_arm_roll_share']))
    desired_upper = Quaternion(up_axis, share) @ upper_deform @ rest[upper].to_quaternion()
    idle_axis = (idle[fore].translation-idle[upper].translation).normalized()
    transported_idle = idle_axis.rotation_difference(up_axis) @ idle[upper].to_quaternion()
    up_q = transported_idle.slerp(desired_upper, weight)
    up_deform = up_q @ rest[upper].to_quaternion().inverted()
    no_roll = (up_deform @ fore_rest).rotation_difference(fore_axis) @ up_deform
    residual = unwrap(axial_delta(full_fore, no_roll, fore_axis), state.get(side+'_residual'))
    state[side+'_residual'] = residual
    pose['clavicle_'+side].translation += shoulder-idle[upper].translation
    pose[upper] = Matrix.LocRotScale(shoulder, up_q, Vector((1, 1, 1)))
    for index in ('01', '02'):
        helper = 'upperarm_twist_'+index+'_'+side
        pose[helper] = pose[upper] @ rest[upper].inverted() @ rest[helper]
    fore_matrix = Matrix.LocRotScale(elbow, full_fore @ rest[fore].to_quaternion(), Vector((1, 1, 1)))
    for name, station in STATIONS[side].items():
        position = (fore_matrix @ rest[fore].inverted() @ rest[name]).translation
        # Parent starts at the hinge frame. Helpers carry cumulative pronation;
        # this is not partial twist stacked on an already fully rotated parent.
        remaining = residual*(1.-weight*(1.-station))
        q = Quaternion(fore_axis, remaining) @ no_roll @ rest[name].to_quaternion()
        pose[name] = Matrix.LocRotScale(position, q, Vector((1, 1, 1)))
    pose[wrist] = hand
    for bone in rig.pose.bones:
        if bone.name.endswith('_'+side) and bone.name in finger_basis:
            pose[bone.name] = pose[bone.parent.name] @ local_rest[bone.name] @ finger_basis[bone.name]


def pose_frame(wpn, seconds, state):
    if seconds <= 0 or seconds >= CFG['swing_seconds']-1e-8:
        return {name: matrix.copy() for name, matrix in idle.items()}
    weight = ease(seconds/.12)*(1.-ease((seconds-(CFG['swing_seconds']-.16))/.16))
    pose = {name: matrix.copy() for name, matrix in idle.items()}
    for side in ('l', 'r'):
        solve_arm(pose, side, wpn @ grips[side], weight, state)
    pose['WPN_root'] = wpn
    return pose


report = {'revision': CFG['revision'], 'source': str(SOURCE), 'reference': str(REFERENCE),
          'reference_fps': ref_fps, 'reference_poses': reference_poses,
          'config': CFG, 'fps': FPS, 'runtime_tested': False, 'preview_rendered': False,
          'clips': {}, 'key_poses': {}}
contact_pose, contact_state = None, None
for clip, duration in (('Swing', CFG['source_swing_seconds']), ('HitRecover', CFG['source_recovery_seconds'])):
    name = 'A_RusticPickaxe_'+clip
    old = bpy.data.actions[name]
    old.name = 'REF_BeforeOverhead_'+name
    old.use_fake_user = True
    action = bpy.data.actions.new(name)
    action.use_fake_user = True
    rig.animation_data.action = action
    scene.render.fps = FPS
    scene.render.fps_base = 1
    scene.frame_start, scene.frame_end = 0, round(duration*FPS)
    previous = {}
    state = {} if clip == 'Swing' else copy.deepcopy(contact_state)
    raised_pose = None
    for frame in range(scene.frame_end+1):
        scene.frame_set(frame)
        source_time = frame/FPS
        if clip == 'Swing':
            seconds = source_time*CFG['contact_seconds']/CFG['source_contact_seconds'] if source_time <= CFG['source_contact_seconds'] else \
                CFG['contact_seconds']+(source_time-CFG['source_contact_seconds'])*(CFG['swing_seconds']-CFG['contact_seconds'])/CFG['source_recovery_seconds']
            wpn = swing_frame(seconds)
            if CFG['raise_end_seconds'] <= seconds <= CFG['release_seconds']:
                if raised_pose is None:
                    raised_pose = pose_frame(TOP, CFG['raise_end_seconds'], state)
                pose = {n: m.copy() for n, m in raised_pose.items()}
            else:
                pose = pose_frame(wpn, seconds, state)
            if frame == round(CFG['source_contact_seconds']*FPS):
                contact_pose = {n: m.copy() for n, m in pose.items()}
                contact_state = copy.deepcopy(state)
        else:
            age = source_time/CFG['source_recovery_seconds']*(CFG['swing_seconds']-CFG['contact_seconds'])
            seconds = CFG['contact_seconds']+age
            pose = {n: m.copy() for n, m in contact_pose.items()} if age <= CFG['hit_hold_seconds'] else pose_frame(hit_frame(age), seconds, state)
        for bone in rig.pose.bones:
            parent_inverse = pose[bone.parent.name].inverted() if bone.parent else Matrix.Identity(4)
            bone.matrix_basis = local_rest[bone.name].inverted() @ parent_inverse @ pose[bone.name]
        for bone in rig.pose.bones:
            bone.rotation_mode = 'QUATERNION'
            q = bone.rotation_quaternion.copy()
            if bone.name in previous and q.dot(previous[bone.name]) < 0:
                q.negate()
            bone.rotation_quaternion = q
            previous[bone.name] = q.copy()
            for channel in ('location', 'rotation_quaternion', 'scale'):
                bone.keyframe_insert(channel, frame=frame, group=bone.name)
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    for keyframe in curve.keyframe_points:
                        keyframe.interpolation = 'LINEAR'
    bpy.ops.object.select_all(action='DESELECT')
    rig.hide_set(False)
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    path = OUT/(name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(path), use_selection=True, object_types={'ARMATURE'},
        axis_forward='-Y', axis_up='Z', add_leaf_bones=False, bake_anim=True,
        bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False, bake_anim_simplify_factor=0)
    report['clips'][clip] = {'fbx': str(path), 'source_seconds': duration}
    if raised_pose:
        for label, key_pose in (('idle', idle), ('overhead', raised_pose), ('impact', contact_pose)):
            report['key_poses'][label] = {side: {'hand': list(key_pose['hand_'+side].translation),
                'elbow': list(key_pose['lowerarm_'+side].translation),
                'shoulder': list(key_pose['upperarm_'+side].translation)} for side in ('l', 'r')}
    print('PICKAXE_OVERHEAD_EXPORTED', clip, flush=True)

rig.animation_data.action = bpy.data.actions['A_RusticPickaxe_Swing']
rig.animation_data.action_slot = rig.animation_data.action.slots[0]
scene.frame_end = round(CFG['source_swing_seconds']*FPS)
scene.frame_set(0)
blend_file = HERE/'Pickaxe_Overhead_Editable.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(blend_file))
report['blend'] = str(blend_file)
(HERE/'authoring.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('PICKAXE_OVERHEAD_AUTHORED', flush=True)
