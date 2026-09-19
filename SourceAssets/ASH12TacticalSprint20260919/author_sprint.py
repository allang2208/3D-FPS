"""ASH-12 one-handed sprint from its current fitted idle and existing rifle motion.

Reference: Saved/RifleSprintAudit/RifleSprintAudit-final60-v2/Preview/
M4-grips-transitions.jpg; continuous 0.30 s entry/return and 0.60 s stride.
Exports animation only and an editable source. Does not render or run tests.
"""
import json
import math
from pathlib import Path

import bpy
from mathutils import Matrix, Quaternion, Vector

OUT = Path(__file__).resolve().parent
SOURCE = OUT.parent / 'ASH1220260917/ASH12_Editable.blend'
(OUT / 'Animations').mkdir(parents=True, exist_ok=True)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
rig = bpy.data.objects['SK_M4_Infima']
rig.data.pose_position = 'POSE'
scene = bpy.context.scene
scene.render.fps = 60
rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
parent = {b.name: b.parent.name if b.parent else None for b in rig.data.bones}
names = list(rest)
local_rest = {n: rest[parent[n]].inverted() @ rest[n] if parent[n] else rest[n] for n in names}
idle_action = bpy.data.actions['ASH12_idle']
rig.animation_data.action = idle_action
rig.animation_data.action_slot = idle_action.slots[0]
scene.frame_set(0)
bpy.context.view_layer.update()
idle = {b.name: b.matrix.copy() for b in rig.pose.bones}


def place_arm(pose, old, side, hand):
    """Existing rifle sprint two-bone solver; preserve the fitted twist chain."""
    hn = 'hand_' + side
    delta = hand @ old[hn].inverted()
    for n in names:
        if n == hn or (n.endswith('_' + side) and n.startswith(('thumb', 'index', 'middle', 'ring', 'pinky'))):
            pose[n] = delta @ old[n]
    upper, lower = 'upperarm_' + side, 'lowerarm_' + side
    shoulder = old[upper].translation.copy()
    elbow, wrist, target = old[lower].translation, old[hn].translation, hand.translation
    l1, l2 = (elbow - shoulder).length, (wrist - elbow).length
    v = target - shoulder
    distance, axis = v.length, v.normalized()
    reach = (l1 + l2) * .985
    if distance > reach:
        shoulder += axis * (distance - reach)
        distance = reach
    distance = max(abs(l1 - l2) + .0001, distance)
    pole = elbow - old[upper].translation
    pole -= axis * pole.dot(axis)
    if pole.length < 1e-6:
        pole = Vector((0, 0, -1)) - axis * axis.dot(Vector((0, 0, -1)))
    pole.normalize()
    along = (l1*l1 - l2*l2 + distance*distance) / (2*distance)
    solved_elbow = shoulder + axis*along + pole*math.sqrt(max(0, l1*l1 - along*along))
    pose['clavicle_' + side] = old['clavicle_' + side].copy()
    pose['clavicle_' + side].translation += shoulder - old[upper].translation
    for n, pos, direction, was in [
        (upper, shoulder, solved_elbow - shoulder, elbow - old[upper].translation),
        (lower, solved_elbow, target - solved_elbow, wrist - elbow),
    ]:
        pose[n] = Matrix.LocRotScale(pos, was.rotation_difference(direction) @ old[n].to_quaternion(), old[n].to_scale())
    for n in names:
        if n.endswith('_' + side) and n.startswith(('upperarm_twist', 'lowerarm_twist')):
            bone = upper if n.startswith('upperarm') else lower
            pose[n] = pose[bone] @ old[bone].inverted() @ old[n]
    if 'ik_hand_' + side in pose:
        pose['ik_hand_' + side] = hand.copy()


def smooth(a, b, value):
    x = max(0., min(1., (value - a) / (b - a)))
    return x*x*(3 - 2*x)


# Derive raising axes from this rifle, not from a copied donor root transform.
up = Vector((0, 0, 1))
barrel = (idle['WPN_SOCKET_Muzzle'].translation - idle['WPN_root'].translation).normalized()
forward = Vector((barrel.x, barrel.y, 0)).normalized()
right = forward.cross(up).normalized()
elevation = math.radians(76)
upright = forward*math.cos(elevation) + up*math.sin(elevation)
raise_rotation = Quaternion(up, math.radians(-7)) @ Quaternion(upright, math.radians(-8)) @ barrel.rotation_difference(upright)
q_wrist_idle = idle['lowerarm_l'].to_quaternion().inverted() @ idle['hand_l'].to_quaternion()
q_wrist_rest = rest['lowerarm_l'].to_quaternion().inverted() @ rest['hand_l'].to_quaternion()


def make_pose(progress, phase=None):
    pose = {n: m.copy() for n, m in idle.items()}
    if progress <= 0:
        return pose
    released = smooth(0., .22, progress)
    withdrawn = smooth(.10, .65, progress)
    raised = smooth(.25, 1., progress)
    side = math.sin(phase) if phase is not None else 0.
    step = math.sin(2*phase) if phase is not None else 0.
    # Bullpup clearance: carry the bearing wrist right and forward so the rear
    # receiver stays beside the view. The small loop begins/ends on Enter's pose.
    offset = (right*.120 + forward*.095 - up*.020) * raised
    offset += (right*(.004*side) + forward*(.006*step) - up*(.005*step)) * raised
    stride_rotation = Quaternion(right, math.radians(1.0*side)) @ Quaternion(up, math.radians(.6*step))
    rotation = Quaternion().slerp(stride_rotation @ raise_rotation, raised)
    pivot = idle['hand_r'].translation
    delta = Matrix.Translation(pivot + offset) @ rotation.to_matrix().to_4x4() @ Matrix.Translation(-pivot)
    for n in names:
        if n.startswith('WPN_'):
            pose[n] = delta @ idle[n]
    place_arm(pose, idle, 'r', delta @ idle['hand_r'])

    # Release before lifting. The support arm follows an outward shoulder arc
    # into a near-straight hang below the camera, with a small offscreen stride.
    shoulder = idle['upperarm_l'].translation
    clear = idle['hand_l'].translation + (-right*.045 - forward*.005 - up*.055)*released
    l1 = (idle['lowerarm_l'].translation - shoulder).length
    l2 = (idle['hand_l'].translation - idle['lowerarm_l'].translation).length
    dx, dy = -.055 - .004*side, .015 + .025*side
    distance = .975*(l1 + l2)
    target = shoulder + right*dx + forward*dy - up*math.sqrt(distance*distance - dx*dx - dy*dy)
    v0, v1 = clear - shoulder, target - shoulder
    r0, r1 = v0.length, v1.length
    d0, d1 = v0/r0, v1/r1
    axis = d0.cross(d1)
    angle = d0.angle(d1)
    direction = d0.lerp(d1, withdrawn).normalized() if axis.length < 1e-6 else Quaternion(axis.normalized(), angle*withdrawn) @ d0
    direction = (direction - right*(.30*math.sin(math.pi*withdrawn))).normalized()
    location = shoulder + direction*(r0 + (r1-r0)*(1-(1-withdrawn)**4))
    # Relax at the wrist joint; preserving the gripping hand's world rotation
    # while lowering the arm would invert it in the withdrawal segment.
    local_wrist = q_wrist_idle.slerp(q_wrist_rest, min(1., .55*released + .40*withdrawn))
    place_arm(pose, idle, 'l', Matrix.LocRotScale(location, idle['hand_l'].to_quaternion(), idle['hand_l'].to_scale()))
    wrist = pose['lowerarm_l'].to_quaternion() @ local_wrist
    place_arm(pose, idle, 'l', Matrix.LocRotScale(location, wrist, idle['hand_l'].to_scale()))
    for n in names:
        if n.endswith('_l') and n.startswith(('thumb_', 'index_', 'middle_', 'ring_', 'pinky_')) and '_metacarpal_' not in n:
            local = idle[parent[n]].inverted() @ idle[n]
            loc, q, scale = local.decompose()
            pose[n] = pose[parent[n]] @ Matrix.LocRotScale(loc, q.slerp(local_rest[n].to_quaternion(), .60*released), scale)
    return pose


report = {'source': str(SOURCE), 'source_action': idle_action.name,
          'reference': 'Saved/RifleSprintAudit/RifleSprintAudit-final60-v2/Preview/M4-grips-transitions.jpg',
          'barrel_direction': list(barrel), 'right_direction': list(right),
          'target_elevation_degrees': 76, 'right_wrist_offset_m': [.120, .095, -.020],
          'left_arm_reach': .975, 'sample_rate': 120, 'clips': {}}
for kind, end in [('Enter', 18), ('Loop', 36), ('Exit', 18)]:
    action = bpy.data.actions.new('ASH12_TacticalSprint_' + kind)
    action.use_fake_user = True
    rig.animation_data.action = action
    previous = {}
    for step in range(end*2 + 1):
        t = step/(end*2)
        pose = make_pose(1. if kind == 'Loop' else (1-t if kind == 'Exit' else t), 2*math.pi*t if kind == 'Loop' else None)
        for n in names:
            basis = local_rest[n].inverted() @ (pose[parent[n]].inverted() @ pose[n] if parent[n] else pose[n])
            loc, q, scale = basis.decompose()
            if n in previous and previous[n].dot(q) < 0:
                q.negate()
            previous[n] = q.copy()
            bone = rig.pose.bones[n]
            bone.rotation_mode = 'QUATERNION'
            bone.location, bone.rotation_quaternion, bone.scale = loc, q, scale
            for prop in ('location', 'rotation_quaternion', 'scale'):
                bone.keyframe_insert(prop, frame=step*.5)
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    for key in curve.keyframe_points:
                        key.interpolation = 'LINEAR'
    scene.frame_start, scene.frame_end = 0, end
    scene.frame_set(0)
    bpy.ops.object.select_all(action='DESELECT')
    rig.hide_set(False)
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    fbx = OUT / 'Animations' / ('A_ASH12_TacticalSprint_' + kind + '.fbx')
    bpy.ops.export_scene.fbx(filepath=str(fbx), use_selection=True, object_types={'ARMATURE'},
        axis_forward='-Y', axis_up='Z', add_leaf_bones=False, bake_anim=True,
        bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False,
        bake_anim_force_startend_keying=True, bake_anim_step=.5, bake_anim_simplify_factor=0)
    report['clips'][kind] = {'action': action.name, 'duration': end/60., 'fbx': str(fbx)}

rig.animation_data.action = bpy.data.actions['ASH12_TacticalSprint_Loop']
rig.animation_data.action_slot = rig.animation_data.action.slots[0]
scene.frame_start, scene.frame_end = 0, 36
scene.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'ASH12_TacticalSprint_Editable.blend'))
(OUT / 'authoring.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('ASH12_TACTICAL_SPRINT_AUTHORED', json.dumps(report), flush=True)
