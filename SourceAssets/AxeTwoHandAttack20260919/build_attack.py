"""Author a two-hand axe load-right-high / cut-left attack from the H3 hold.

Reads the sword's existing HeavyCharge/HeavyRelease as reference, preserves the
axe's own contacts, and exports Swing/HitRecover only. No renders or tests.
The canonical 0.68/0.24-second source clock is retained for ProductionToolMotion;
production_tools.json supplies the new 1.10/0.48-second gameplay clock.
"""
import json
import math
from pathlib import Path

import bpy
from mathutils import Matrix, Quaternion, Vector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CFG = json.loads((HERE / 'motion.json').read_text(encoding='utf-8'))
EXPORT = HERE / 'Export'
EXPORT.mkdir(parents=True, exist_ok=True)
bpy.context.preferences.filepaths.save_version = 0

# Read the actual editable reference at its documented phase times. This is
# source material for authoring, not a test of the sword or the new axe motion.
sword_source = ROOT / 'SourceAssets/RuneSword20260913/ChargedErgoV43/AzureRunesword_ChargedHoldV45.blend'
bpy.ops.wm.open_mainfile(filepath=str(sword_source))
scene = bpy.context.scene
sword = bpy.data.objects['SK_RuneSword_Rig']
reference = {'source': str(sword_source), 'clips': {}}
for clip, times in [('HeavyCharge', [0.0, 0.65, 1.6, 2.0]),
                    ('HeavyRelease', [0.0, 0.075, 0.2375, 0.6, 1.0])]:
    action = bpy.data.actions['A_RuneSword_' + clip]
    sword.animation_data.action = action
    sword.animation_data.action_slot = action.slots[0]
    fps = scene.render.fps / scene.render.fps_base
    rows = []
    for t in times:
        f = t * fps
        scene.frame_set(int(f), subframe=f - int(f))
        bpy.context.view_layer.update()
        rows.append({'seconds': t, 'pose': {n: [list(row) for row in sword.pose.bones[n].matrix]
                     for n in ('WPN_root', 'hand_r', 'hand_l', 'lowerarm_r', 'lowerarm_l')}})
    reference['clips'][clip] = {'fps': fps, 'frame_range': list(action.frame_range), 'samples': rows}
(HERE / 'sword_reference.json').write_text(json.dumps(reference, indent=2), encoding='utf-8')

idle_dir = ROOT / 'SourceAssets/KimodoAxeIdle20260919'
idle_receipt = json.loads((idle_dir / 'BuildH3/authoring.json').read_text(encoding='utf-8'))
IDLE = idle_receipt['config']
source = Path(idle_receipt['blend'])
bpy.ops.wm.open_mainfile(filepath=str(source))
scene = bpy.context.scene
rig = bpy.data.objects['SK_Harvest_Axe_Rig']
rig.data.pose_position = 'POSE'
rig.animation_data.action = bpy.data.actions[IDLE['name']]
rig.animation_data.action_slot = rig.animation_data.action.slots[0]
scene.frame_set(0)
bpy.context.view_layer.update()
rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
local_rest = {b.name: rest[b.parent.name].inverted() @ rest[b.name] if b.parent else rest[b.name]
              for b in rig.data.bones}
idle_pose = {b.name: b.matrix.copy() for b in rig.pose.bones}
ready = idle_pose['WPN_root']
grips = {side: ready.inverted() @ idle_pose['hand_' + side] for side in ('r', 'l')}
fingers = {side: {b.name: idle_pose['hand_' + side].inverted() @ idle_pose[b.name]
                 for b in rig.data.bones if b.name.endswith('_' + side)
                 and b.name.startswith(('index', 'middle', 'ring', 'pinky', 'thumb'))}
           for side in ('r', 'l')}
pivot = Vector(CFG['grip_pivot_local_m'])
diagonal = Vector(CFG['cut_diagonal']).normalized()
forward = Vector((0, 1, 0))


def smooth(u):
    u = min(1.0, max(0.0, u))
    return u * u * u * (10.0 - 15.0 * u + 6.0 * u * u)


def mix(a, b, u):
    return Matrix.LocRotScale(a.translation.lerp(b.translation, u),
                             a.to_quaternion().slerp(b.to_quaternion(), u), Vector((1, 1, 1)))


def arc(theta_degrees, center):
    # The blade (+X) is tangent to the sweep; the shaft (+Z) lies in its plane.
    # At contact it faces left/down while the head moves through the forward arc.
    theta = math.radians(theta_degrees)
    shaft = diagonal * math.cos(theta) + forward * math.sin(theta)
    edge = -diagonal * math.sin(theta) + forward * math.cos(theta)
    normal = shaft.cross(edge).normalized()
    rotation = Matrix((edge, normal, shaft)).transposed().to_quaternion()
    return Matrix.LocRotScale(Vector(center) - rotation @ pivot, rotation, Vector((1, 1, 1)))


poses = {key: arc(CFG[key]['theta_deg'], CFG[key]['center_m'])
         for key in ('raised', 'loaded', 'contact', 'follow', 'return_corner', 'rebound', 'hit_return_corner')}


def hermite(a, b, va, vb, duration, u):
    return ((2 * u**3 - 3 * u**2 + 1) * a + (u**3 - 2 * u**2 + u) * duration * va
            + (-2 * u**3 + 3 * u**2) * b + (u**3 - u**2) * duration * vb)


def cut_segment(t, start_time, end_time, start, end, start_velocity, end_velocity,
                start_angular_velocity, end_angular_velocity):
    duration = end_time - start_time
    u = (t - start_time) / duration
    center = hermite(Vector(CFG[start]['center_m']), Vector(CFG[end]['center_m']),
                     Vector(start_velocity), Vector(end_velocity), duration, u)
    theta = hermite(CFG[start]['theta_deg'], CFG[end]['theta_deg'],
                    start_angular_velocity, end_angular_velocity, duration, u)
    return arc(theta, center)


def swing(t):
    if t < CFG['raise_corner_s']:
        return mix(ready, poses['raised'], smooth(t / CFG['raise_corner_s']))
    if t < CFG['load_end_s']:
        return mix(poses['raised'], poses['loaded'], smooth((t - CFG['raise_corner_s']) /
                   (CFG['load_end_s'] - CFG['raise_corner_s'])))
    if t <= CFG['release_start_s']:
        return poses['loaded'].copy()
    if t <= CFG['runtime_contact_s']:
        return cut_segment(t, CFG['release_start_s'], CFG['runtime_contact_s'], 'loaded', 'contact',
                           (0, 0, 0), CFG['contact_center_velocity_m_s'],
                           0.0, CFG['contact_angular_velocity_deg_s'])
    if t < CFG['follow_end_s']:
        return cut_segment(t, CFG['runtime_contact_s'], CFG['follow_end_s'], 'contact', 'follow',
                           CFG['contact_center_velocity_m_s'], (0, 0, 0),
                           CFG['contact_angular_velocity_deg_s'], 0.0)
    if t < CFG['return_corner_s']:
        return mix(poses['follow'], poses['return_corner'], smooth((t - CFG['follow_end_s']) /
                   (CFG['return_corner_s'] - CFG['follow_end_s'])))
    return mix(poses['return_corner'], ready, smooth((t - CFG['return_corner_s']) /
               (CFG['runtime_duration_s'] - CFG['return_corner_s'])))


def hit_recover(t):
    hold_end = CFG['runtime_contact_s'] + CFG['hit_hold_s']
    if t <= hold_end:
        return poses['contact'].copy()
    if t < CFG['hit_rebound_end_s']:
        return mix(poses['contact'], poses['rebound'], smooth((t - hold_end) /
                   (CFG['hit_rebound_end_s'] - hold_end)))
    if t < CFG['hit_return_corner_s']:
        return mix(poses['rebound'], poses['hit_return_corner'], smooth((t - CFG['hit_rebound_end_s']) /
                   (CFG['hit_return_corner_s'] - CFG['hit_rebound_end_s'])))
    return mix(poses['hit_return_corner'], ready, smooth((t - CFG['hit_return_corner_s']) /
               (CFG['runtime_duration_s'] - CFG['hit_return_corner_s'])))


def support(side, hand):
    upper, fore, wrist = [p + '_' + side for p in ('upperarm', 'lowerarm', 'hand')]
    shoulder = rest[upper].translation + Vector((0, IDLE['shoulder_forward_m'], -IDLE['shoulder_down_m']))
    target = hand.translation
    l1 = (rest[fore].translation - rest[upper].translation).length
    l2 = (rest[wrist].translation - rest[fore].translation).length
    reach = target - shoulder
    direction = reach.normalized()
    shoulder += direction * max(0.0, reach.length - IDLE['reach_fraction'] * (l1 + l2))
    distance = (target - shoulder).length
    down_out = Vector((IDLE['elbow_outward'] * (1 if side == 'r' else -1), IDLE['elbow_backward'], -1))
    pole = (down_out - direction * down_out.dot(direction)).normalized()
    along = (l1 * l1 - l2 * l2 + distance * distance) / (2 * distance)
    elbow = shoulder + direction * along + pole * math.sqrt(max(0.0, l1 * l1 - along * along))
    return shoulder, elbow, target


def arm_frames(side, hand):
    upper, fore, wrist = [p + '_' + side for p in ('upperarm', 'lowerarm', 'hand')]
    shoulder, elbow, target = support(side, hand)
    upper_rest = (rest[fore].translation - rest[upper].translation).normalized()
    fore_rest = (rest[wrist].translation - rest[fore].translation).normalized()
    upper_direction = (elbow - shoulder).normalized()
    hand_deform = hand.to_quaternion() @ rest[wrist].to_quaternion().inverted()
    fore_deform = (hand_deform @ fore_rest).rotation_difference((target - elbow).normalized()) @ hand_deform
    # Transport the forearm frame back through the elbow into the humerus. This
    # gives the raised shoulder an intentional roll instead of a rest-to-axis
    # shortest rotation with arbitrary axial orientation.
    upper_deform = (fore_deform @ upper_rest).rotation_difference(upper_direction) @ fore_deform
    return shoulder, elbow, target, upper_direction, upper_deform, fore_deform


idle_roll = {}
for side in ('r', 'l'):
    _, _, _, direction, transported, _ = arm_frames(side, idle_pose['hand_' + side])
    base_q = transported @ rest['upperarm_' + side].to_quaternion()
    delta = idle_pose['upperarm_' + side].to_quaternion() @ base_q.inverted()
    if delta.w < 0:
        delta.negate()
    idle_roll[side] = 2 * math.atan2(Vector((delta.x, delta.y, delta.z)).dot(direction), delta.w)


def apply_frame(wpn, t):
    pose = {n: m.copy() for n, m in rest.items()}
    weight = smooth(t / 0.14) * (1 - smooth((t - 0.88) / (CFG['runtime_duration_s'] - 0.88)))
    for side in ('r', 'l'):
        upper, fore, wrist = [p + '_' + side for p in ('upperarm', 'lowerarm', 'hand')]
        hand = wpn @ grips[side]
        shoulder, elbow, target, direction, upper_deform, fore_deform = arm_frames(side, hand)
        residual = idle_roll[side] * (1 - weight * (1 - CFG['active_upperarm_idle_roll_fraction']))
        upper_q = Quaternion(direction, residual) @ upper_deform @ rest[upper].to_quaternion()
        pose['clavicle_' + side].translation += shoulder - rest[upper].translation
        pose[upper] = Matrix.LocRotScale(shoulder, upper_q, Vector((1, 1, 1)))
        pose[fore] = Matrix.LocRotScale(elbow, fore_deform @ rest[fore].to_quaternion(), Vector((1, 1, 1)))
        for segment in (upper, fore):
            for index in ('01', '02'):
                helper = segment.replace('_' + side, '_twist_' + index + '_' + side)
                if helper in rest:
                    pose[helper] = pose[segment] @ rest[segment].inverted() @ rest[helper]
        pose[wrist] = hand
        for bone in rig.pose.bones:
            if bone.name in fingers[side]:
                position = pose[bone.parent.name] @ local_rest[bone.name].translation
                rotation = hand.to_quaternion() @ fingers[side][bone.name].to_quaternion()
                pose[bone.name] = Matrix.LocRotScale(position, rotation, Vector((1, 1, 1)))
    pose['WPN_root'] = wpn
    for bone in rig.pose.bones:
        parent_inv = pose[bone.parent.name].inverted() if bone.parent else Matrix.Identity(4)
        bone.matrix_basis = local_rest[bone.name].inverted() @ parent_inv @ pose[bone.name]
    bpy.context.view_layer.update()


report = {'runtime_tested': False, 'rendered': False, 'source': str(source), 'config': CFG,
          'reference': str(sword_source), 'clips': {}, 'grips': {s: [list(r) for r in m] for s, m in grips.items()}}
for clip, source_duration in [('Swing', CFG['source_swing_s']), ('HitRecover', CFG['source_hit_recover_s'])]:
    old = bpy.data.actions.get('A_Harvest_Axe_' + clip)
    if old:
        old.name = 'REF_SingleHand_' + old.name
        old.use_fake_user = True
    action = bpy.data.actions.new('A_Harvest_Axe_' + clip)
    action.use_fake_user = True
    rig.animation_data.action = action
    scene.render.fps = CFG['fps']
    scene.render.fps_base = 1
    scene.frame_start = 0
    scene.frame_end = round(source_duration * CFG['fps'])
    previous_quats = {}
    for frame in range(scene.frame_end + 1):
        scene.frame_set(frame)
        s = frame / CFG['fps']
        if clip == 'HitRecover':
            t = CFG['runtime_contact_s'] + s / CFG['source_hit_recover_s'] * (CFG['runtime_duration_s'] - CFG['runtime_contact_s'])
            wpn = hit_recover(t)
        else:
            if s <= CFG['source_contact_s']:
                t = s / CFG['source_contact_s'] * CFG['runtime_contact_s']
            else:
                t = CFG['runtime_contact_s'] + (s - CFG['source_contact_s']) / CFG['source_hit_recover_s'] * (CFG['runtime_duration_s'] - CFG['runtime_contact_s'])
            wpn = swing(t)
        apply_frame(wpn, t)
        for bone in rig.pose.bones:
            bone.rotation_mode = 'QUATERNION'
            q = bone.rotation_quaternion.copy()
            if bone.name in previous_quats and q.dot(previous_quats[bone.name]) < 0:
                q.negate()
            bone.rotation_quaternion = q
            previous_quats[bone.name] = q.copy()
            for channel in ('location', 'rotation_quaternion', 'scale'):
                bone.keyframe_insert(channel, frame=frame, group=bone.name)
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    for key in curve.keyframe_points:
                        key.interpolation = 'LINEAR'
    bpy.ops.object.select_all(action='DESELECT')
    rig.hide_set(False)
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    path = EXPORT / (action.name + '.fbx')
    bpy.ops.export_scene.fbx(filepath=str(path), use_selection=True, object_types={'ARMATURE'},
                            axis_forward='-Y', axis_up='Z', add_leaf_bones=False,
                            bake_anim=True, bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False,
                            bake_anim_simplify_factor=0)
    report['clips'][clip] = {'source_seconds': source_duration, 'fbx': str(path)}
    print('AXE_TWO_HAND_EXPORTED ' + clip, flush=True)

rig.animation_data.action = bpy.data.actions['A_Harvest_Axe_Swing']
rig.animation_data.action_slot = rig.animation_data.action.slots[0]
scene.frame_start, scene.frame_end = 0, round(CFG['source_swing_s'] * CFG['fps'])
scene.frame_set(0)
bpy.ops.file.pack_all()
blend = HERE / 'Axe_TwoHand_Attack_Editable.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(blend))
report['blend'] = str(blend)
(HERE / 'authoring.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('AXE_TWO_HAND_ATTACK_AUTHORED', flush=True)
