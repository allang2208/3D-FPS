"""ASH-12 empty charge: enter from camera right, pull, withdraw right.

Replaces the two lateral-offset attempts. Work in the calibrated camera frame,
keep the receiver/left arm untouched, and author a distinct right-hand route.
"""
import json
import math
from pathlib import Path

import bpy
from mathutils import Matrix, Quaternion, Vector

OUT = Path(__file__).resolve().parent
SOURCE = OUT.parent / 'ASH12ReloadRefine20260919/ASH12_Reload_Reference_Editable.blend'
ACTION = 'ASH12_Reference_reload_empty'
START, END = 1.91, 3.16


def smooth(x):
    x = max(0., min(1., x))
    return x * x * x * (x * (x * 6. - 15.) + 10.)


def blend(a, b, weight):
    p, q, s = a.decompose()
    p1, q1, s1 = b.decompose()
    return Matrix.LocRotScale(p.lerp(p1, weight), q.slerp(q1, weight), s.lerp(s1, weight))


def roll_angle(lower, hand, rest_lower, rest_hand, axis):
    neutral = lower.to_quaternion() @ rest_lower.to_quaternion().inverted() @ rest_hand.to_quaternion()
    q = hand.to_quaternion() @ neutral.inverted()
    value = 2. * math.atan2(Vector((q.x, q.y, q.z)).dot(axis), q.w)
    return (value + math.pi) % (2. * math.pi) - math.pi


bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene = bpy.context.scene
rig = bpy.data.objects['SK_M4_Infima']
parents = {b.name: b.parent.name if b.parent else None for b in rig.data.bones}
rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
local_rest = {n: rest[parents[n]].inverted() @ m if parents[n] else m for n, m in rest.items()}


def descendants(name):
    return [name] + [n for child in rig.data.bones[name].children for n in descendants(child.name)]


def read_pose(action_name, time):
    action = bpy.data.actions[action_name]
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    frame = time * 60.
    scene.frame_set(int(frame), subframe=frame % 1.)
    bpy.context.view_layer.update()
    return {b.name: b.matrix.copy() for b in rig.pose.bones}


aim = read_pose('ASH12_aim', 0)
forward = (aim['WPN_FrontSight'].translation - aim['WPN_RearSight'].translation).normalized()
up = (Vector((0., 0., 1.)) - forward * forward.z).normalized()
right = forward.cross(up).normalized()
eye = aim['WPN_RearSight'].translation - forward * .18 - right * .07 + up * .07


def camera_point(x, depth, height):
    return eye + right * x + forward * depth + up * height


contact_pose = read_pose(ACTION, 2.34)
rest_forearm = (rest['hand_r'].translation - rest['lowerarm_r'].translation).normalized()
hand_axis = contact_pose['hand_r'].to_3x3() @ rest['hand_r'].to_3x3().inverted() @ rest_forearm
old_heading = math.atan2(hand_axis.dot(forward), hand_axis.dot(right))
new_heading = math.atan2(.40, -.92)
yaw = (new_heading - old_heading + math.pi) % (2. * math.pi) - math.pi
contact_turn = Quaternion(up, yaw)


def side_grasp(pose):
    # Rotate the palm around the accepted knuckle contact, leaving that
    # contact on the real charging tab. The palm comes from the right side;
    # the gun and its handle retain their original animation.
    pivot = sum((pose[n].translation for n in ('index_01_r', 'middle_01_r', 'ring_01_r')), Vector()) / 3.
    turn = Matrix.Translation(pivot) @ contact_turn.to_matrix().to_4x4() @ Matrix.Translation(-pivot)
    return turn @ pose['hand_r']


start_hand = read_pose(ACTION, START)['hand_r'].copy()
contact_hand = side_grasp(contact_pose)
release_hand = side_grasp(read_pose(ACTION, 2.60))
end_hand = read_pose(ACTION, END)['hand_r'].copy()


def relocated(hand, point):
    result = hand.copy()
    result.translation = point
    return result


right_out = relocated(contact_hand, camera_point(.42, .16, -.11))
near_contact = relocated(contact_hand, contact_hand.translation + right * .075 + up * .018)
release_clear = relocated(release_hand, release_hand.translation + right * .060 + up * .022)
right_exit = relocated(release_hand, camera_point(.42, .16, -.12))
right_low = relocated(blend(release_hand, end_hand, .60), camera_point(.40, .12, -.25))
keys = [(START, start_hand), (2.08, right_out), (2.16, right_out),
        (2.28, near_contact), (2.34, contact_hand), (2.60, release_hand),
        (2.70, release_clear), (2.84, right_exit), (2.96, right_low), (END, end_hand)]


def hand_at(t, original):
    if 2.34 <= t <= 2.60:
        return side_grasp(original)
    for (t0, h0), (t1, h1) in zip(keys, keys[1:]):
        if t <= t1:
            return blend(h0, h1, smooth((t - t0) / (t1 - t0)))
    return end_hand.copy()


hand_bones = descendants('hand_r')
arm_bones = [n for n in descendants('upperarm_r') if n not in set(hand_bones[1:])]
changed_bones = ['clavicle_r'] + arm_bones
shares = {'lowerarm_twist_02_r': .55, 'lowerarm_twist_01_r': .95}
previous_roll = 0.
samples = []
for step in range(397):
    t, frame = step / 120., step / 2.
    if not START < t < END:
        continue
    original = read_pose(ACTION, t)
    original_quats = {n: rig.pose.bones[n].rotation_quaternion.copy() for n in changed_bones}
    pose = {n: m.copy() for n, m in original.items()}
    weight = smooth((t - START) / .27) * smooth((END - t) / .24)
    H = hand_at(t, original)
    upper, lower, old_hand = (original[n] for n in ('upperarm_r', 'lowerarm_r', 'hand_r'))
    old_a, old_b, old_c = upper.translation, lower.translation, old_hand.translation
    # This first-person shoulder sits behind the right screen edge. It is a
    # dedicated action pose, independent of the rolled receiver's local axes.
    a = old_a.lerp(camera_point(.34, -.025, -.14), weight)
    c = H.translation
    l1, l2 = (old_b - old_a).length, (old_c - old_b).length
    distance = (c - a).length
    if distance > l1 + l2 - .012:
        a += (c - a).normalized() * (distance - (l1 + l2 - .012))
        distance = (c - a).length
    axis = (c - a).normalized()
    along = (l1 * l1 - l2 * l2 + distance * distance) / (2. * distance)
    center = a + axis * along
    wanted_elbow = old_b.lerp(camera_point(.34, .16, -.08), weight)
    pole = wanted_elbow - center
    pole -= axis * pole.dot(axis)
    b = center + pole.normalized() * math.sqrt(max(0., l1 * l1 - along * along))
    old_u, old_v = (old_b - old_a).normalized(), (old_c - old_b).normalized()
    new_u, new_v = (b - a).normalized(), (c - b).normalized()
    pose['upperarm_r'] = Matrix.LocRotScale(a, old_u.rotation_difference(new_u) @ upper.to_quaternion(), upper.to_scale())
    pose['lowerarm_r'] = Matrix.LocRotScale(b, old_v.rotation_difference(new_v) @ lower.to_quaternion(), lower.to_scale())
    pose['clavicle_r'] = Matrix.Translation(a - old_a) @ original['clavicle_r']
    hand_delta = H @ old_hand.inverted()
    for name in hand_bones:
        pose[name] = hand_delta @ original[name]
    old_roll = roll_angle(lower, old_hand, rest['lowerarm_r'], rest['hand_r'], old_v)
    new_roll = roll_angle(pose['lowerarm_r'], H, rest['lowerarm_r'], rest['hand_r'], new_v)
    roll_delta = (new_roll - old_roll + math.pi) % (2. * math.pi) - math.pi
    while roll_delta - previous_roll > math.pi:
        roll_delta -= 2. * math.pi
    while roll_delta - previous_roll < -math.pi:
        roll_delta += 2. * math.pi
    previous_roll = roll_delta
    for name in arm_bones:
        if name in ('upperarm_r', 'lowerarm_r', 'hand_r'):
            continue
        parent = parents[name]
        pose[name] = pose[parent] @ original[parent].inverted() @ original[name]
        if name in shares:
            m = pose['lowerarm_r'] @ lower.inverted() @ original[name]
            pose[name] = Matrix.LocRotScale(m.translation,
                Quaternion(new_v, roll_delta * shares[name]) @ m.to_quaternion(), m.to_scale())
    values = {}
    for name in changed_bones:
        local = local_rest[name].inverted() @ pose[parents[name]].inverted() @ pose[name]
        loc, q, scale = local.decompose()
        if q.dot(original_quats[name]) < 0.:
            q.negate()
        values[name] = (loc, q, scale)
    samples.append((frame, values))

action = bpy.data.actions[ACTION].copy()
action.name = 'ASH12_EmptyReload_RightEdgeReachPullReturn'
action.use_fake_user = True
rig.animation_data.action = action
rig.animation_data.action_slot = action.slots[0]
for frame, values in samples:
    for name, (loc, q, scale) in values.items():
        bone = rig.pose.bones[name]
        bone.rotation_mode = 'QUATERNION'
        bone.location, bone.rotation_quaternion, bone.scale = loc, q, scale
        for prop in ('location', 'rotation_quaternion', 'scale'):
            bone.keyframe_insert(prop, frame=frame)
for layer in action.layers:
    for strip in layer.strips:
        for bag in strip.channelbags:
            for curve in bag.fcurves:
                for key in curve.keyframe_points:
                    key.interpolation = 'LINEAR'
scene.render.fps = 60
scene.frame_start, scene.frame_end = 0, 198
scene.frame_set(147)
bpy.context.view_layer.update()
bpy.ops.object.select_all(action='DESELECT')
rig.select_set(True)
bpy.context.view_layer.objects.active = rig
bpy.ops.export_scene.fbx(filepath=str(OUT / 'A_ASH12_reload_empty.fbx'),
    use_selection=True, object_types={'ARMATURE'}, axis_forward='-Y', axis_up='Z',
    add_leaf_bones=False, bake_anim=True, bake_anim_use_all_actions=False,
    bake_anim_use_nla_strips=False, bake_anim_force_startend_keying=True,
    bake_anim_step=.5, bake_anim_simplify_factor=0)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'ASH12_RightEdgeCharge_Editable.blend'))
report = {'source': str(SOURCE), 'action': action.name, 'sample_rate': 120, 'duration': 3.3,
    'camera_frame': {'eye': list(eye), 'right': list(right), 'forward': list(forward), 'up': list(up)},
    'hand_route_seconds': [t for t, _ in keys], 'pull_seconds': [2.34, 2.60],
    'right_edge_hand_camera_meters': [.42, .16, -.11],
    'right_shoulder_camera_meters': [.34, -.025, -.14],
    'contact_palm_yaw_degrees': math.degrees(yaw), 'edited_bones': changed_bones,
    'preserved': ['receiver', 'magazine', 'bolt', 'left_arm', 'finger_local_pose', 'timing'],
    'visual_test': 'Not run; user will assess in game.'}
(OUT / 'authoring.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('ASH12_RIGHT_EDGE_AUTHOR_COMPLETE ' + json.dumps(report))
