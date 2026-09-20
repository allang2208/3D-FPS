"""Two-sided anatomical elbow support and non-linear overhead pickaxe attack.

Only Swing and HitRecover are replaced. Read current grasp and skin; keep the
model, skeleton, finger shape, accepted idle, equip and locomotion endpoints.
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
REFERENCE = ROOT/'SourceAssets/PickaxeOverhead20260919/Pickaxe_Overhead_Editable.blend'
OUT = HERE/'Export'
OUT.mkdir(parents=True, exist_ok=True)
FPS = CFG['fps']
STATIONS = json.loads((ROOT/'SourceAssets/AxeTwoHandAttack20260919/V5/authoring.json').read_text())['skin_stations']
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
bpy.context.preferences.filepaths.save_version = 0
scene = bpy.context.scene
rig = bpy.data.objects['SK_RusticPickaxe_Rig']
original_idle = bpy.data.actions['A_RusticPickaxe_Idle']
rig.animation_data.action = original_idle
rig.animation_data.action_slot = original_idle.slots[0]
scene.frame_set(0)
rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
local_rest = {b.name: rest[b.parent.name].inverted() @ rest[b.name] if b.parent else rest[b.name] for b in rig.data.bones}
idle = {b.name: b.matrix.copy() for b in rig.pose.bones}
ready = idle['WPN_root']
grips = {s: ready.inverted() @ idle['hand_'+s] for s in ('l', 'r')}
finger_basis = {b.name: b.matrix_basis.copy() for b in rig.pose.bones if b.name.startswith(('thumb', 'index', 'middle', 'ring', 'pinky'))}
PIVOT = Vector(CFG['grip_pivot_local_m'])
READY_CENTER = ready @ PIVOT

# Use the actual handle section for each rigid hand's circumferential regrip.
# This changes the palm's approach side without altering finger joint angles.
tool = bpy.data.objects['Harvest_Pickaxe']
to_local = rest['WPN_root'].inverted() @ rig.matrix_world.inverted() @ tool.matrix_world
points = [to_local @ v.co for v in tool.data.vertices]
grip_axes = {}
for side, along in (('l', .08), ('r', .30)):
    samples = []
    for z in (along+.025, along+.065):
        band = [p for p in points if abs(p.z-z) < .012]
        samples.append(Vector(((min(p.x for p in band)+max(p.x for p in band))*.5,
                               (min(p.y for p in band)+max(p.y for p in band))*.5, z)))
    grip_axes[side] = ((samples[0]+samples[1])*.5, (samples[1]-samples[0]).normalized())


def ease(u):
    u = max(0., min(1., u))
    return u*u*u*(10.-15.*u+6.*u*u)


def centered(center, q):
    return Matrix.LocRotScale(Vector(center)-q @ PIVOT, q, Vector((1, 1, 1)))


def pitch_frame(center, pitch, roll=5.):
    angle = math.radians(pitch)
    shaft = Vector((0, math.sin(angle), math.cos(angle)))
    point = Vector((0, math.cos(angle), -math.sin(angle)))
    q = Quaternion(shaft, math.radians(roll)) @ Matrix((point, shaft.cross(point), shaft)).transposed().to_quaternion()
    return centered(center, q)


def key(label):
    k = CFG[label]
    return pitch_frame(k['center_m'], k['pitch_degrees'], k['roll_degrees'])


RAISED, TOP, IMPACT, FOLLOW, REBOUND = [key(k) for k in ('raised', 'top', 'impact', 'follow', 'rebound')]


def bezier(frames, u):
    centers = [m @ PIVOT for m in frames]
    quats = [m.to_quaternion() for m in frames]
    while len(centers) > 1:
        centers = [a.lerp(b, u) for a, b in zip(centers, centers[1:])]
        quats = [a.slerp(b, u) for a, b in zip(quats, quats[1:])]
    return centered(centers[0], quats[0])


def return_frame(start, u):
    return bezier([start, pitch_frame((-.005, .30, -.29), 48),
        centered(READY_CENTER+Vector((0, -.025, -.035)), ready.to_quaternion()), ready], ease(u))


def swing_frame(t):
    if t <= CFG['raise_end_seconds']:
        return bezier([ready, centered(READY_CENTER+Vector((-.025, -.055, .035)), ready.to_quaternion()),
                       pitch_frame((-.015, .32, .16), -2), RAISED], ease(t/CFG['raise_end_seconds']))
    if t <= CFG['release_seconds']:
        # Load a little farther back, then hold the complete pose for 45 ms.
        return bezier([RAISED, TOP], ease((t-CFG['raise_end_seconds'])/.105))
    if t <= CFG['contact_seconds']:
        u = (t-CFG['release_seconds'])/(CFG['contact_seconds']-CFG['release_seconds'])
        return bezier([TOP, pitch_frame((-.015, .33, .21), -5),
            pitch_frame((-.015, .385, -.08), 43), IMPACT], u**1.65)
    if t <= CFG['follow_end_seconds']:
        u = (t-CFG['contact_seconds'])/(CFG['follow_end_seconds']-CFG['contact_seconds'])
        return bezier([IMPACT, FOLLOW], 1-(1-u)**2.5)
    return return_frame(FOLLOW, (t-CFG['follow_end_seconds'])/(CFG['swing_seconds']-CFG['follow_end_seconds']))


def hit_frame(age):
    if age <= CFG['hit_hold_seconds']:
        return IMPACT.copy()
    if age <= CFG['hit_release_seconds']:
        return bezier([IMPACT, REBOUND], ease((age-CFG['hit_hold_seconds'])/(CFG['hit_release_seconds']-CFG['hit_hold_seconds'])))
    return return_frame(REBOUND, (age-CFG['hit_release_seconds'])/(CFG['swing_seconds']-CFG['contact_seconds']-CFG['hit_release_seconds']))


def arm_phase(t, hit):
    if t <= CFG['release_seconds']:
        u = ease(t/CFG['raise_end_seconds'])
        return u, 0., u
    if t <= CFG['contact_seconds']:
        u = ease((t-CFG['release_seconds'])/(CFG['contact_seconds']-CFG['release_seconds']))
        return 1., u, 1.-u
    start = CFG['contact_seconds']+CFG['hit_release_seconds'] if hit else CFG['follow_end_seconds']
    returning = ease((t-start)/(CFG['swing_seconds']-start))
    return 1.-returning, 1., 0.


def hand_frame(wpn, side, grip_weight, down, support_weight, lift):
    roll = (CFG['top_grip_roll_degrees'][side]*(1-down)+CFG['impact_grip_roll_degrees'][side]*down)*grip_weight
    origin, axis = grip_axes[side]
    def wrapped(degrees):
        wrap = Matrix.Translation(origin) @ Quaternion(axis, math.radians(degrees)).to_matrix().to_4x4() @ Matrix.Translation(-origin)
        return wpn @ wrap @ grips[side]
    # During entry/exit the tool, shoulder and wrap follow different arcs.
    # Fit only the circumferential grasp within a small authored allowance;
    # never move finger joints or let wrist fitting choose an inward elbow.
    U, F, H = [p+'_'+side for p in ('upperarm', 'lowerarm', 'hand')]
    l1, l2 = (rest[F].translation-rest[U].translation).length, (rest[H].translation-rest[F].translation).length
    fore_rest = (rest[H].translation-rest[F].translation).normalized()
    sign = 1 if side == 'r' else -1
    shoulder = idle[U].translation+Vector((sign*CFG['shoulder_outward_m'], CFG['shoulder_forward_m'],
                     .005+(CFG['shoulder_top_lift_m']-.005)*lift))*support_weight
    def cost(degrees):
        hand = wrapped(degrees)
        d = hand.translation-shoulder
        direction, distance = d.normalized(), d.length
        along = (l1*l1-l2*l2+distance*distance)/(2*distance)
        center = shoulder+direction*along
        guide = Vector(CFG['elbow_pole_top']).lerp(Vector(CFG['elbow_pole_impact']), down)
        guide.x *= sign
        desired = (guide-direction*guide.dot(direction)).normalized()
        initial = idle[F].translation-center
        initial = (initial-direction*initial.dot(direction)).normalized()
        angle = math.atan2(direction.dot(initial.cross(desired)), initial.dot(desired))
        elbow = center+(Quaternion(direction, angle*support_weight)@initial)*math.sqrt(max(0., l1*l1-along*along))
        neutral = hand.to_quaternion()@rest[H].to_quaternion().inverted()@fore_rest
        return neutral.angle((hand.translation-elbow).normalized())**2+.025*math.radians(degrees-roll)**2
    allowance = 35.*4.*grip_weight*(1.-grip_weight)
    lo, hi = roll-allowance, roll+allowance
    for _ in range(16):
        a, b = lo+(hi-lo)*.382, lo+(hi-lo)*.618
        if cost(a) < cost(b):
            hi = b
        else:
            lo = a
    return wrapped((lo+hi)*.5)


def unwrap(value, previous):
    return value if previous is None else previous+(value-previous+math.pi)%(2*math.pi)-math.pi


def axial_delta(a, b, axis):
    q = a @ b.inverted()
    return (2*math.atan2(Vector((q.x, q.y, q.z)).dot(axis), q.w)+math.pi)%(2*math.pi)-math.pi


def frame_rotation(axis, normal):
    return Matrix((axis, normal, axis.cross(normal))).transposed().to_quaternion()


def solve_arm(pose, side, hand, weight, down, lift, state):
    upper, fore, wrist = [p+'_'+side for p in ('upperarm', 'lowerarm', 'hand')]
    sign = 1. if side == 'r' else -1.
    l1 = (rest[fore].translation-rest[upper].translation).length
    l2 = (rest[wrist].translation-rest[fore].translation).length
    a = (rest[fore].translation-rest[upper].translation).normalized()
    b = (rest[wrist].translation-rest[fore].translation).normalized()
    rest_normal = a.cross(b).normalized()
    shoulder = idle[upper].translation+Vector((sign*CFG['shoulder_outward_m'],
                  CFG['shoulder_forward_m'], .005+(CFG['shoulder_top_lift_m']-.005)*lift))*weight
    target = hand.translation
    d = target-shoulder
    direction = d.normalized()
    distance = d.length
    along = (l1*l1-l2*l2+distance*distance)/(2*distance)
    radius = math.sqrt(max(0., l1*l1-along*along))
    center = shoulder+direction*along
    guide = Vector(CFG['elbow_pole_top']).lerp(Vector(CFG['elbow_pole_impact']), down)
    guide.x *= sign
    desired = (guide-direction*guide.dot(direction)).normalized()
    # Each elbow has its own outward/backward pole. No wrist-driven search may
    # move the left elbow to the right half of the body, or vice versa.
    initial = idle[fore].translation-center
    initial = (initial-direction*initial.dot(direction)).normalized()
    angle = math.atan2(direction.dot(initial.cross(desired)), initial.dot(desired))
    pole = Quaternion(direction, angle*weight) @ initial
    elbow = center+pole*radius
    up_axis, fore_axis = (elbow-shoulder).normalized(), (target-elbow).normalized()
    normal = up_axis.cross(fore_axis).normalized()
    hinge_upper = frame_rotation(up_axis, normal) @ frame_rotation(a, rest_normal).inverted()
    idle_axis = (idle[fore].translation-idle[upper].translation).normalized()
    source_q = idle_axis.rotation_difference(up_axis) @ idle[upper].to_quaternion()
    upper_q = source_q.slerp(hinge_upper @ rest[upper].to_quaternion(), weight)
    upper_deform = upper_q @ rest[upper].to_quaternion().inverted()
    # Keep the elbow hinge continuous with the humerus. Pronating the hand must
    # not roll the upper arm or collapse the skin right at the elbow seam.
    fore_hinge = (upper_deform @ b).rotation_difference(fore_axis) @ upper_deform
    hand_deform = hand.to_quaternion() @ rest[wrist].to_quaternion().inverted()
    full_fore = (hand_deform @ b).rotation_difference(fore_axis) @ hand_deform
    twist = unwrap(axial_delta(full_fore, fore_hinge, fore_axis), state.get(side+'_twist'))
    state[side+'_twist'] = twist
    pose['clavicle_'+side].translation += shoulder-idle[upper].translation
    pose[upper] = Matrix.LocRotScale(shoulder, upper_q, Vector((1, 1, 1)))
    for index in ('01', '02'):
        name = 'upperarm_twist_'+index+'_'+side
        pose[name] = pose[upper] @ rest[upper].inverted() @ rest[name]
    full_matrix = Matrix.LocRotScale(elbow, full_fore @ rest[fore].to_quaternion(), Vector((1, 1, 1)))
    for name, station in STATIONS[side].items():
        location = (full_matrix @ rest[fore].inverted() @ rest[name]).translation
        rotation = Quaternion(fore_axis, twist*(1.-weight*(1.-station))) @ fore_hinge @ rest[name].to_quaternion()
        pose[name] = Matrix.LocRotScale(location, rotation, Vector((1, 1, 1)))
    pose[wrist] = hand
    for bone in rig.pose.bones:
        if bone.name.endswith('_'+side) and bone.name in finger_basis:
            pose[bone.name] = pose[bone.parent.name] @ local_rest[bone.name] @ finger_basis[bone.name]


def pose_frame(wpn, t, hit, state):
    if t <= 0 or t >= CFG['swing_seconds']-1e-8:
        return {n: m.copy() for n, m in idle.items()}
    weight = ease(t/CFG['entry_blend_seconds'])*(1-ease((t-(CFG['swing_seconds']-CFG['exit_blend_seconds']))/CFG['exit_blend_seconds']))
    grip, down, lift = arm_phase(t, hit)
    pose = {n: m.copy() for n, m in idle.items()}
    for side in ('l', 'r'):
        # The elbow opens with the circumferential regrip, then folds inward
        # with the return. Opening it before the palm turns kinks the wrist.
        hand = hand_frame(wpn, side, grip, down, weight*grip, lift)
        solve_arm(pose, side, hand, weight*grip, down, lift, state)
    pose['WPN_root'] = wpn
    return pose


report = {'revision': CFG['revision'], 'source': str(SOURCE), 'reference': str(REFERENCE),
          'config': CFG, 'fps': FPS, 'runtime_tested': False, 'preview_rendered': False,
          'clips': {}, 'key_poses': {}}
contact_pose = contact_state = None
for clip, duration in (('Swing', CFG['source_swing_seconds']), ('HitRecover', CFG['source_recovery_seconds'])):
    name = 'A_RusticPickaxe_'+clip
    old = bpy.data.actions[name]
    old.name = 'REF_BeforeNaturalArms_'+name
    old.use_fake_user = True
    action = bpy.data.actions.new(name)
    action.use_fake_user = True
    rig.animation_data.action = action
    scene.render.fps, scene.render.fps_base = FPS, 1
    scene.frame_start, scene.frame_end = 0, round(duration*FPS)
    previous = {}
    state = {} if clip == 'Swing' else copy.deepcopy(contact_state)
    for frame in range(scene.frame_end+1):
        scene.frame_set(frame)
        source_time = frame/FPS
        if clip == 'Swing':
            t = source_time*CFG['contact_seconds']/CFG['source_contact_seconds'] if source_time <= CFG['source_contact_seconds'] else CFG['contact_seconds']+(source_time-CFG['source_contact_seconds'])*(CFG['swing_seconds']-CFG['contact_seconds'])/CFG['source_recovery_seconds']
            pose = pose_frame(swing_frame(t), t, False, state)
            if frame == round(CFG['source_contact_seconds']*FPS):
                contact_pose = {n: m.copy() for n, m in pose.items()}
                contact_state = copy.deepcopy(state)
        else:
            age = source_time/CFG['source_recovery_seconds']*(CFG['swing_seconds']-CFG['contact_seconds'])
            t = CFG['contact_seconds']+age
            pose = {n: m.copy() for n, m in contact_pose.items()} if age <= CFG['hit_hold_seconds'] else pose_frame(hit_frame(age), t, True, state)
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
        if clip == 'Swing' and frame in (0, 48, 56, 72, 204):
            report['key_poses'][str(round(t, 4))] = {s: {p: list(pose[b+'_'+s].translation) for p, b in (('shoulder', 'upperarm'), ('elbow', 'lowerarm'), ('wrist', 'hand'))} for s in ('l', 'r')}
    # Dense samples already contain quintic curves, a power-law strike, and a
    # true contact hold. Linear interpolation only joins adjacent baked samples.
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    for k in curve.keyframe_points:
                        k.interpolation = 'LINEAR'
    bpy.ops.object.select_all(action='DESELECT')
    rig.hide_set(False)
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    path = OUT/(name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(path), use_selection=True, object_types={'ARMATURE'},
        axis_forward='-Y', axis_up='Z', add_leaf_bones=False, bake_anim=True,
        bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False, bake_anim_simplify_factor=0)
    report['clips'][clip] = {'fbx': str(path), 'source_seconds': duration}
    print('PICKAXE_NATURAL_ARMS_EXPORTED', clip, flush=True)

rig.animation_data.action = bpy.data.actions['A_RusticPickaxe_Swing']
rig.animation_data.action_slot = rig.animation_data.action.slots[0]
scene.frame_end = round(CFG['source_swing_seconds']*FPS)
scene.frame_set(0)
blend_file = HERE/'Pickaxe_NaturalArms_Editable.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(blend_file))
report['blend'] = str(blend_file)
(HERE/'authoring.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('PICKAXE_NATURAL_ARMS_AUTHORED', flush=True)
