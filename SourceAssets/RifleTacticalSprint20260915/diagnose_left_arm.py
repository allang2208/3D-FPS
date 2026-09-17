"""Measure left-arm joint health across the tactical-sprint left-hand retract.

Runs the exact author_sprint.py maths (hand_at full-arm solver + make_pose)
for one weapon/profile and reports, per sampled progress:

- wrist_bend_deg   : angle(forearm_dir, hand_aligned_dir)  [grip-arm-refinement metric]
- lowerarm_twist_deg / upperarm_twist_deg : swing-twist roll of the solved bone
  relative to the idle bone about its own long axis
- shoulder_move_cm : how far the shoulder (upperarm translation) was transported
- reach_ratio      : shoulder->target distance / (l1+l2)
- elbow_flip       : solved elbow switched side of the idle bend plane
- wrist_rot_deg    : total world rotation imposed on the hand vs idle

Usage:
  blender -b --python diagnose_left_arm.py -- <Weapon> <Profile>
Writes JSON to stdout only.
"""
import ast
import json
import math
import sys
from pathlib import Path
import bpy
from mathutils import Matrix, Vector, Euler, Quaternion

O = Path(__file__).resolve().parent
S = O.parent
weapon, profile = sys.argv[sys.argv.index('--') + 1:sys.argv.index('--') + 3]
settings = json.loads((O / 'sources.json').read_text(encoding='utf-8'))[weapon]
record = json.loads((O / 'source-poses.json').read_text(encoding='utf-8'))[weapon + ':' + profile]
source, source_action = record['source'], record['action']
bpy.ops.wm.open_mainfile(filepath=str(S / source))
rig = bpy.data.objects['SK_M4_Infima']
rig.data.pose_position = 'POSE'
scene = bpy.context.scene
scene.render.fps = 60
rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
parent = {b.name: b.parent.name if b.parent else None for b in rig.data.bones}
names = list(rest)
lr = {n: rest[parent[n]].inverted() @ rest[n] if parent[n] else rest[n] for n in names}
action = bpy.data.actions[source_action]
rig.animation_data.action = action
rig.animation_data.action_slot = action.slots[0]
scene.frame_set(0)
bpy.context.view_layer.update()
idle = {b.name: b.matrix.copy() for b in rig.pose.bones}

tree = ast.parse((S / 'DanWesson71520260913/author_weapon.py').read_text(encoding='utf-8'))
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef)
                             and n.name == 'hand_at'], type_ignores=[]), '<full arm solver>', 'exec'))


def smooth(a, b, value):
    x = max(0., min(1., (value - a) / (b - a)))
    return x * x * (3. - 2. * x)


def turn(x, y, z):
    return Euler(tuple(math.radians(a) for a in (x, y, z)), 'XYZ').to_quaternion()


barrel = idle['WPN_SOCKET_Muzzle'].translation - idle['WPN_root'].translation
raise_pitch = 76. - math.degrees(math.atan2(barrel.z, math.hypot(barrel.x, barrel.y)))


def make_pose(progress, phase=None):
    pose = {n: m.copy() for n, m in idle.items()}
    released = smooth(0., .22, progress)
    raised = smooth(.25, 1., progress)
    withdrawn = smooth(.16, .82, progress)
    loop = phase is not None
    side = math.sin(phase) if loop else 0.
    step = math.cos(2 * phase) if loop else 0.
    offset = Vector(settings['right_wrist_offset_m']) * raised
    offset += Vector((.007 * side, .009 * step, -.009 * step))
    rotation = Quaternion().slerp(turn(raise_pitch + 1.2 * side, -8 + 1.5 * side, -7 + .9 * step), raised)
    pivot = idle['hand_r'].translation
    delta = Matrix.Translation(pivot + offset) @ rotation.to_matrix().to_4x4() @ Matrix.Translation(-pivot)
    for n in names:
        if n.startswith('WPN_'):
            pose[n] = delta @ idle[n]
    hand_at(pose, idle, 'r', delta @ idle['hand_r'])

    origin = idle['hand_l'].translation
    clear = origin + Vector((-.045, -.005, -.055)) * released
    hang = settings.get('left_wrist_hang')
    if hang:
        sh = idle['upperarm_l'].translation
        l1 = (idle['lowerarm_l'].translation - sh).length
        l2 = (idle['hand_l'].translation - idle['lowerarm_l'].translation).length
        dx, dy = hang['side_offset']
        if loop:
            sx, sy = hang['swing']
            dx += sx * side
            dy += sy * side
        d = hang['reach'] * (l1 + l2)
        dz = -math.sqrt(max(1e-4, d * d - dx * dx - dy * dy))
        target = sh + Vector((dx, dy, dz))
        withdrawn = smooth(.10, .60, progress)
        t = withdrawn
        v0 = clear - sh
        v1 = target - sh
        r0, r1 = v0.length, v1.length
        d0, d1 = v0 / r0, v1 / r1
        ang = d0.angle(d1)
        axis = d0.cross(d1)
        if axis.length < 1e-6 or ang < 1e-6:
            dm = d0.lerp(d1, t).normalized()
        else:
            dm = Quaternion(axis.normalized(), ang * t) @ d0
        dm = (dm + Vector((-1., 0., 0.)) * .3 * math.sin(math.pi * t)).normalized()
        location = sh + dm * (r0 + (r1 - r0) * (1. - (1. - t) ** 4))
    else:
        target = Vector((-.26 - .008 * side, -.10 - .025 * side, -.36 + .010 * side))
        location = clear.lerp(target, withdrawn)
    q_rest_wrist = rest['lowerarm_l'].to_quaternion().inverted() @ rest['hand_l'].to_quaternion()
    q_idle_wrist = idle['lowerarm_l'].to_quaternion().inverted() @ idle['hand_l'].to_quaternion()
    if settings.get('left_wrist_relax'):
        relax = settings['left_wrist_relax']
        amount = min(1., relax['released_share'] * released + relax['withdrawn_share'] * withdrawn)
        q_local = q_idle_wrist.slerp(q_rest_wrist, amount)
        hand_at(pose, idle, 'l', Matrix.LocRotScale(location, idle['hand_l'].to_quaternion(), idle['hand_l'].to_scale()))
        wrist = turn(5 * side, 0, 0) @ (pose['lowerarm_l'].to_quaternion() @ q_local)
    else:
        wrist = idle['hand_l'].to_quaternion()
        wrist = wrist.slerp(turn(-20 + 5 * side, 8, -16) @ wrist, withdrawn)
    hand_at(pose, idle, 'l', Matrix.LocRotScale(location, wrist, idle['hand_l'].to_scale()))
    finger_relax = settings.get('finger_relax', .52)
    for n in names:
        if n.endswith('_l') and n.startswith(('thumb_', 'index_', 'middle_', 'ring_', 'pinky_')) and '_metacarpal_' not in n:
            local = idle[parent[n]].inverted() @ idle[n]
            loc, q, scale = local.decompose()
            relaxed = q.slerp(lr[n].to_quaternion(), finger_relax * released)
            pose[n] = pose[parent[n]] @ Matrix.LocRotScale(loc, relaxed, scale)
    return pose


def swing_twist(q, axis):
    """Decompose quaternion q into swing * twist about axis; return signed twist degrees."""
    axis = axis.normalized()
    d = Vector((q.x, q.y, q.z)).dot(axis)
    proj = axis * d
    twist = Quaternion((q.w, proj.x, proj.y, proj.z))
    if twist.magnitude < 1e-9:
        return 0.0
    twist.normalize()
    deg = math.degrees(twist.angle)
    # sign: negative when the projected vector points against the quaternion vector
    return deg if d >= 0 else -deg


def measure(pose):
    un, fn, hn = 'upperarm_l', 'lowerarm_l', 'hand_l'
    shoulder_p = pose[un].translation
    elbow_p = pose[fn].translation
    wrist_p = pose[hn].translation
    forearm_dir = (wrist_p - elbow_p).normalized()
    rest_dir = (rest[hn].translation - rest[fn].translation).normalized()

    # joint-local deviation from rest for the wrist and elbow: what reads as twisted
    q_wrist_rest_local = rest[fn].to_quaternion().inverted() @ rest[hn].to_quaternion()
    q_elbow_rest_local = rest[un].to_quaternion().inverted() @ rest[fn].to_quaternion()
    q_wrist_pose_local = pose[fn].to_quaternion().inverted() @ pose[hn].to_quaternion()
    q_elbow_pose_local = pose[un].to_quaternion().inverted() @ pose[fn].to_quaternion()
    q_wrist_delta = q_wrist_pose_local @ q_wrist_rest_local.inverted()
    q_elbow_delta = q_elbow_pose_local @ q_elbow_rest_local.inverted()

    out = {
        'wrist_dev_deg': math.degrees(q_wrist_delta.angle),
        'elbow_dev_deg': math.degrees(q_elbow_delta.angle),
    }
    # split the wrist deviation into twist about the hand long axis vs swing
    proj = rest_dir * Vector((q_wrist_delta.x, q_wrist_delta.y, q_wrist_delta.z)).dot(rest_dir)
    q_twist = Quaternion((q_wrist_delta.w, proj.x, proj.y, proj.z))
    if q_twist.magnitude > 1e-9:
        q_twist.normalize()
        out['wrist_twist_deg'] = math.degrees(q_twist.angle)
        q_swing = q_wrist_delta @ q_twist.inverted()
        out['wrist_swing_deg'] = math.degrees(q_swing.angle)
    else:
        out['wrist_twist_deg'] = 0.0
        out['wrist_swing_deg'] = out['wrist_dev_deg']

    shoulder_i = idle[un].translation
    elbow_i = idle[fn].translation
    out['shoulder_move_cm'] = (shoulder_p - shoulder_i).length * 100.
    out['wrist_world_move_cm'] = (wrist_p - idle[hn].translation).length * 100.

    # reach + elbow side flip
    l1 = (elbow_i - shoulder_i).length
    l2 = (idle[hn].translation - elbow_i).length
    v = wrist_p - shoulder_p
    out['reach_ratio'] = v.length / ((l1 + l2) * .985)
    axis = v.normalized()
    pole_i = elbow_i - shoulder_i
    pole_i -= axis * pole_i.dot(axis)
    pole_p = elbow_p - shoulder_p
    pole_p -= axis * pole_p.dot(axis)
    out['elbow_flip'] = bool(pole_i.length > 1e-6 and pole_p.length > 1e-6 and pole_i.normalized().dot(pole_p.normalized()) < 0.)
    out['pole_dot'] = round(pole_i.normalized().dot(pole_p.normalized()), 3) if pole_i.length > 1e-6 and pole_p.length > 1e-6 else None
    # elbow bend (180 = straight) and first-person bone-point visibility
    cos_elbow = max(-1., min(1., (l1 * l1 + l2 * l2 - (wrist_p - shoulder_p).length ** 2) / (2 * l1 * l2)))
    out['elbow_bend_deg'] = 180. - math.degrees(math.acos(cos_elbow))
    cam_loc = Vector((-.07, -.06, .07))
    cam_axis = Vector((0, 1, 0))
    half_h = math.radians(56.)
    half_v = math.atan(math.tan(half_h) * 9. / 16.)
    in_view = 0
    for p in (wrist_p, elbow_p, pose['lowerarm_l'].translation):
        rel = p - cam_loc
        fwd = rel.dot(cam_axis)
        if fwd <= 0.01:
            continue
        off_h = math.degrees(abs(math.atan(rel.x / fwd)))
        off_v = math.degrees(abs(math.atan(rel.z / fwd)))
        in_view += int(off_h < math.degrees(half_h) and off_v < math.degrees(half_v))
    out['fp_bone_points_in_view'] = in_view
    return out


report = {'weapon': weapon, 'profile': profile, 'source': source, 'action': source_action,
          'raise_pitch': raise_pitch, 'idle_left_wrist': [round(c, 4) for c in idle['hand_l'].translation],
          'samples': []}
kinds = [('Enter', [i / 20. for i in range(21)])]
for kind, values in kinds:
    for t in values:
        pose = make_pose(t)
        row = measure(pose)
        row.update(kind=kind, progress=round(t, 3))
        report['samples'].append(row)
for t in [i / 12. for i in range(13)]:
    pose = make_pose(1., phase=2 * math.pi * t)
    row = measure(pose)
    row.update(kind='Loop', progress=round(t, 3))
    report['samples'].append(row)

print('LEFT_ARM_DIAGNOSTIC' + json.dumps(report))
