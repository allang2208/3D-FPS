"""Author V79: V78 poses, spin window 25% faster.

Prepare and the start throw stay. Spin 0.40-1.06 compresses to 0.40-0.928.
Recover length stays 0.22 s after the new spin end.
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Quaternion, Vector

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / 'InspectGripArcV46'))
sys.path.insert(0, str(HERE.parents[1] / 'RuneSwordWristLocked20260920'))
import inspect_arm_roll as arm_roll
import spin_design as design
import wrist_locked_solver as wrist

SOURCE = Path(r'D:\FPS3D\FPSGAME\SourceAssets\RuneSwordWristLocked20260920\Standard\Sword_Idle_WristLockedV4.blend')
OUT = HERE / 'ExportV79'
OUT.mkdir(exist_ok=True)
BLEND = HERE / 'AzureRunesword_InspectForwardSpinV79.blend'
PREPARE_RIGHT_M = 0.16
OLD_SPIN_END = 1.06
OLD_RECOVER_END = 1.28
OLD_END = 1.40
SPIN_SPEED = 1.25
design.SPIN_START = 0.40
design.SPIN_END = 0.40 + (OLD_SPIN_END - 0.40) / SPIN_SPEED
RECOVER_END = design.SPIN_END + (OLD_RECOVER_END - OLD_SPIN_END)
design.END = RECOVER_END + (OLD_END - OLD_RECOVER_END)
ELBOW_GIVE = 0.055
ELBOW_GIVE_R = 0.11
WRIST_BEND_CAP_R = 18.0
WRIST_TWIST_LIM_R = 18.0
WRIST_BEND_LIM_R = 22.0
CLIP = 'A_RuneSword_Inspect'
WPN = 'WPN_root'
FPS = design.FPS
END = design.END
MIN_TIP_DEPTH = 0.10
SPIN_AXIS_RAW = Vector((0.90, 1.00, 0.06))
VIEW = Vector((0.0, 1.0, 0.0))
UP = Vector((0.0, 0.0, 1.0))
STATIONS = {
    'r': {'lowerarm_twist_02_r': 0.2738741548309727, 'lowerarm_twist_01_r': 0.863392507873546},
    'l': {'lowerarm_twist_02_l': 0.2738694206012943, 'lowerarm_twist_01_l': 0.8633863706969649},
}

FINGER_MAP = {
    'thumb_01_r': 'thumb', 'thumb_02_r': 'thumb', 'thumb_03_r': 'thumb',
    'index_metacarpal_r': 'index', 'index_01_r': 'index', 'index_02_r': 'index', 'index_03_r': 'index',
    'middle_metacarpal_r': 'middle', 'middle_01_r': 'middle', 'middle_02_r': 'middle', 'middle_03_r': 'middle',
    'ring_metacarpal_r': 'ring', 'ring_01_r': 'ring', 'ring_02_r': 'ring', 'ring_03_r': 'ring',
    'pinky_metacarpal_r': 'pinky', 'pinky_01_r': 'pinky', 'pinky_02_r': 'pinky', 'pinky_03_r': 'pinky',
    'thumb_01_l': 'thumb', 'thumb_02_l': 'thumb', 'thumb_03_l': 'thumb',
    'index_metacarpal_l': 'index', 'index_01_l': 'index', 'index_02_l': 'index', 'index_03_l': 'index',
    'middle_metacarpal_l': 'middle', 'middle_01_l': 'middle', 'middle_02_l': 'middle', 'middle_03_l': 'middle',
    'ring_metacarpal_l': 'ring', 'ring_01_l': 'ring', 'ring_02_l': 'ring', 'ring_03_l': 'ring',
    'pinky_metacarpal_l': 'pinky', 'pinky_01_l': 'pinky', 'pinky_02_l': 'pinky', 'pinky_03_l': 'pinky',
}
METACARPALS = {n for n in FINGER_MAP if 'metacarpal' in n}

bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene = bpy.context.scene
rig = bpy.data.objects['SK_RuneSword_Rig']
sword = bpy.data.objects['RuneSword_Blade']
rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
parent = {b.name: (b.parent.name if b.parent else None) for b in rig.data.bones}
local_rest = {
    n: (rest[parent[n]].inverted() @ rest[n]) if parent[n] else rest[n]
    for n in rest
}
names = list(rest)
source = rig.animation_data.action
rig.animation_data.action_slot = source.slots[0]
scene.frame_set(int(source.frame_range[0]))
bpy.context.view_layer.update()
idle = {b.name: b.matrix.copy() for b in rig.pose.bones}
idle_scale = {n: idle[n].to_scale() for n in names}

def remap_t(t):
    if not isinstance(t, (int, float)):
        return t
    if t <= 0.40:
        return t
    if t <= OLD_SPIN_END:
        return 0.40 + (t - 0.40) / SPIN_SPEED
    return design.SPIN_END + (t - OLD_SPIN_END)


def remap_keys(keys):
    return [(remap_t(x), y) for x, y in keys]


# V78 pose keys; wall-clock after 0.40 compressed 1.25x.
design.PHI = remap_keys([
    (0.00, 0.0), (0.18, 0.0), (0.32, -8.0), (0.38, -16.0), (0.40, -18.0),
    (0.450, 25.0), (0.510, 95.0), (0.580, 175.0),
    (0.670, 250.0), (0.780, 310.0), (0.900, 348.0),
    (1.000, 357.0), (1.06, 360.0),
    (OLD_END, 360.0),
])
design.PHI_CURVE = design.Curve(design.PHI)
design.OPEN_PHALANX = 0.95
design.OPEN_METACARPAL = 0.62
# Same six beats, larger pose change at each station.
design.PSI = remap_keys([
    (0.00, 0.0), (0.28, 0.0),
    (0.36, 8.0), (('phi', 20), 16.0), (('phi', 90), 38.0),
    (('phi', 150), 78.0), (('phi', 200), 88.0),
    (('phi', 255), 82.0), (('phi', 300), 58.0),
    (('phi', 335), 22.0), (('phi', 355), 5.0),
    (OLD_SPIN_END, 0.0), (OLD_END, 0.0),
])
design.THETA = remap_keys([
    (0.00, 0.0), (0.20, 0.0), (0.40, -6.0),
    (('phi', 45), 14.0), (('phi', 110), 6.0),
    (('phi', 165), -4.0), (('phi', 215), -22.0),
    (('phi', 260), -10.0), (('phi', 310), -4.0),
    (('phi', 345), 2.0),
    (OLD_SPIN_END, 0.0), (OLD_END, 0.0),
])
design.RHO = remap_keys([
    (0.00, 0.0), (0.10, 0.0), (0.36, 1.0),
    (OLD_SPIN_END, 1.0), (OLD_RECOVER_END, 0.0), (OLD_END, 0.0),
])
design.GRIP = remap_keys([
    (0.00, 1.0), (0.18, 1.0), (0.30, 0.92),
    (0.36, 0.58), (0.40, 0.38),
    (('phi', 60), 0.16), (('phi', 95), 0.04),
    (('phi', 145), 0.0), (('phi', 270), 0.0),
    (('phi', 300), 0.22), (('phi', 325), 0.58),
    (('phi', 348), 0.92), (1.04, 1.0), (OLD_END, 1.0),
])
design.FINGERS = {
    name: remap_keys(keys) for name, keys in {
    'pinky': [
        (0.00, 0.0), (0.26, 0.0), (0.34, 0.70), (0.40, 1.0),
        (('phi', 90), 1.0), (('phi', 280), 1.0),
        (('phi', 335), 0.40), (('phi', 355), 0.0), (OLD_END, 0.0),
    ],
    'ring': [
        (0.00, 0.0), (0.28, 0.0), (0.34, 0.62), (0.40, 0.95),
        (('phi', 90), 1.0), (('phi', 275), 1.0),
        (('phi', 332), 0.32), (('phi', 352), 0.0), (OLD_END, 0.0),
    ],
    'middle': [
        (0.00, 0.0), (0.30, 0.0), (0.36, 0.48), (0.42, 0.82),
        (('phi', 90), 1.0), (('phi', 155), 1.0), (('phi', 270), 1.0),
        (('phi', 328), 0.24), (('phi', 350), 0.0), (OLD_END, 0.0),
    ],
    'index': [
        (0.00, 0.0), (0.32, 0.0), (0.40, 0.32),
        (('phi', 40), 0.45), (('phi', 110), 0.78),
        (('phi', 165), 1.0), (('phi', 255), 0.95),
        (('phi', 305), 0.28), (('phi', 335), 0.06), (('phi', 352), 0.0),
        (OLD_END, 0.0),
    ],
    'thumb': [
        (0.00, 0.0), (0.38, 0.0), (0.42, 0.10),
        (('phi', 60), 0.22), (('phi', 150), 0.62),
        (('phi', 250), 0.58), (('phi', 305), 0.12),
        (('phi', 332), 0.0), (OLD_END, 0.0),
    ],
    }.items()
}
curves = design.build()

# Recover clock owns SPIN_END+. Dummy post keys are unused after that.
curves['out'] = design.Curve(remap_keys([
    (0.00, 0.0), (0.06, 0.0), (0.16, 0.05), (0.26, 0.145),
    (0.34, PREPARE_RIGHT_M), (OLD_SPIN_END, PREPARE_RIGHT_M),
    (OLD_RECOVER_END, 0.0), (OLD_END, 0.0),
]))
curves['left_path'] = design.Curve(remap_keys([
    (0.00, 0.0), (0.14, 0.0), (0.26, 0.75), (0.36, 1.0),
    (OLD_SPIN_END, 1.0), (OLD_RECOVER_END, 0.0), (OLD_END, 0.0),
]))
curves['left_open'] = design.Curve(remap_keys([
    (0.00, 0.0), (0.14, 0.0), (0.24, 0.85), (0.32, 1.0),
    (OLD_SPIN_END, 1.0), (OLD_RECOVER_END, 0.0), (OLD_END, 0.0),
]))
# Short dip then throw. Peak down at the flick, not a held crouch.
curves['lift'] = design.Curve(remap_keys([
    (0.00, 0.0), (0.20, 0.0), (0.28, 0.006),
    (0.36, -0.038), (0.40, -0.048), (0.48, -0.016),
    (0.60, 0.010), (0.86, 0.018), (OLD_SPIN_END, 0.008),
    (OLD_END, 0.0),
]))
curves['forward'] = design.Curve(remap_keys([
    (0.00, 0.0), (0.20, 0.0), (0.32, 0.010),
    (0.40, 0.038), (0.52, 0.020), (0.80, 0.008),
    (OLD_SPIN_END, 0.0), (OLD_END, 0.0),
]))
transform = idle[WPN] @ rest[WPN].inverted()
depsgraph = bpy.context.evaluated_depsgraph_get()
posed = sword.evaluated_get(depsgraph).to_mesh()
points = [sword.matrix_world @ v.co for v in posed.vertices]
sword.evaluated_get(depsgraph).to_mesh_clear()
centre = sum(points, Vector()) / len(points)
local_pts = [transform.inverted() @ p for p in points]
spans = []
for axis in range(3):
    coords = [p[axis] for p in local_pts]
    spans.append((max(coords) - min(coords), axis))
spans.sort(reverse=True)
basis = [Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))]
blade_axis = (transform.to_3x3() @ basis[spans[0][1]]).normalized()
tip = max(points, key=lambda p: (p - centre).dot(blade_axis))
pommel = min(points, key=lambda p: (p - centre).dot(blade_axis))
if (tip - pommel).dot(blade_axis) < 0.0:
    blade_axis = -blade_axis
    tip, pommel = pommel, tip
tip_bind = transform.inverted() @ tip
pommel_bind = transform.inverted() @ pommel

arms = bpy.data.objects['SK_Manny_Arms_Export']
right_groups = {g.index for g in arms.vertex_groups if g.name.endswith('_r')}
hand_vertices = [
    v.index for v in arms.data.vertices
    if any(g.group in right_groups and g.weight > 0.5 for g in v.groups)
]
posed_arms = arms.evaluated_get(depsgraph).to_mesh()
posed_sword = sword.evaluated_get(depsgraph).to_mesh()
arm_points = [arms.matrix_world @ posed_arms.vertices[i].co for i in hand_vertices]
sword_points = [sword.matrix_world @ v.co for v in posed_sword.vertices]
arms.evaluated_get(depsgraph).to_mesh_clear()
sword.evaluated_get(depsgraph).to_mesh_clear()
contact = None
for arm_pt in arm_points[::6]:
    for sword_pt in sword_points[::3]:
        d = (arm_pt - sword_pt).length
        if contact is None or d < contact[0]:
            contact = (d, arm_pt, sword_pt)
contact_distance, _contact_arm, contact_sword = contact
contact_hand_local = idle['hand_r'].inverted() @ contact_sword
contact_mesh_local = transform.inverted() @ contact_sword
contact_bone_local = rest[WPN].inverted() @ contact_mesh_local
grip_r = idle[WPN].inverted() @ idle['hand_r']
grip_l = idle[WPN].inverted() @ idle['hand_l']

forearm = (idle['hand_r'].translation - idle['lowerarm_r'].translation).normalized()
spin_axis = SPIN_AXIS_RAW.normalized()
probe = Quaternion(spin_axis, math.radians(8.0)) @ (tip - contact_sword)
if probe.y < (tip - contact_sword).y:
    spin_axis = -spin_axis
blade_flat = blade_axis - spin_axis * blade_axis.dot(spin_axis)
if blade_flat.length < 1e-5:
    blade_flat = UP - spin_axis * UP.dot(spin_axis)
blade_flat.normalize()
flatten_q = blade_axis.rotation_difference(blade_flat)
fwd_dir = (VIEW - spin_axis * VIEW.dot(spin_axis))
if fwd_dir.length < 1e-5:
    fwd_dir = Vector((1.0, 0.0, 0.0))
fwd_dir.normalize()
right_dir = UP.cross(VIEW).normalized()
if right_dir.dot(Vector((1.0, 0.0, 0.0))) < 0.0:
    right_dir = -right_dir


def recover_weight(seconds):
    # One ease-in-out return. No catch hold, no ease-out crawl.
    t = (seconds - design.SPIN_END) / (RECOVER_END - design.SPIN_END)
    t = max(0.0, min(1.0, t))
    if t <= 0.0:
        return 0.0
    if t >= 1.0:
        return 1.0
    if t < 0.5:
        return 4.0 * t * t * t
    u = 1.0 - t
    return 1.0 - 4.0 * u * u * u


def flatten_weight(seconds, recover):
    # Flatten after the hold group has already moved right of the lens.
    # Decay with recover so the blade does not stay flat then snap to idle.
    return design.smoothstep((seconds - 0.30) / 0.10) * (1.0 - recover)


def mix_mat(a, b, t):
    la, qa, sa = a.decompose()
    lb, qb, sb = b.decompose()
    if qa.dot(qb) < 0.0:
        qb.negate()
    return Matrix.LocRotScale(la.lerp(lb, t), qa.slerp(qb, t), sa.lerp(sb, t))


def weapon_from_rotation(rotation, contact_world):
    return Matrix.LocRotScale(
        contact_world - rotation @ contact_bone_local,
        rotation,
        idle_scale[WPN])


def lift_tip_rotation(sword_rot, contact_world):
    mesh = weapon_from_rotation(sword_rot, contact_world) @ rest[WPN].inverted()
    tip = mesh @ tip_bind
    if tip.y >= MIN_TIP_DEPTH - 1e-5:
        return sword_rot
    blade = tip - contact_world
    axis = blade.cross(VIEW)
    if axis.length < 1e-6:
        return sword_rot
    axis.normalize()
    lo_a, hi_a = 0.0, math.radians(40.0)
    best = sword_rot
    for _ in range(18):
        mid = 0.5 * (lo_a + hi_a)
        trial = Quaternion(axis, mid) @ sword_rot
        mesh = weapon_from_rotation(trial, contact_world) @ rest[WPN].inverted()
        if (mesh @ tip_bind).y >= MIN_TIP_DEPTH:
            best = trial
            hi_a = mid
        else:
            lo_a = mid
    return best


def share_wrist_twist(pose, side, keep_deg):
    twist = wrist_twist_deg(pose, side)
    extra = twist - max(-keep_deg, min(keep_deg, twist))
    if abs(extra) < 0.25:
        return
    lo, hand = 'lowerarm_' + side, 'hand_' + side
    axis = (pose[hand].translation - pose[lo].translation).normalized()
    pose[lo] = Matrix.LocRotScale(
        pose[lo].translation,
        Quaternion(axis, math.radians(extra)) @ pose[lo].to_quaternion(),
        idle_scale[lo])


def limit_wrist(pose, side, twist_cap, bend_cap):
    hand = 'hand_' + side
    lo = 'lowerarm_' + side
    if (abs(wrist_twist_deg(pose, side)) <= twist_cap
            and wrist_axis_bend_deg(pose, side) <= bend_cap):
        return
    keep = pose[hand].translation.copy()
    current = pose[hand].to_quaternion()
    locked = (pose[lo] @ idle[lo].inverted() @ idle[hand]).to_quaternion()
    if current.dot(locked) < 0.0:
        locked.negate()
    lo_t, hi_t = 0.0, 1.0
    best = locked
    for _ in range(16):
        mid = 0.5 * (lo_t + hi_t)
        trial = current.slerp(locked, mid)
        pose[hand] = Matrix.LocRotScale(keep, trial, idle_scale[hand])
        if (abs(wrist_twist_deg(pose, side)) <= twist_cap
                and wrist_axis_bend_deg(pose, side) <= bend_cap):
            best = trial
            hi_t = mid
        else:
            lo_t = mid
    pose[hand] = Matrix.LocRotScale(keep, best, idle_scale[hand])


def frame_quat(direction, normal):
    y = direction.normalized()
    x = normal - y * normal.dot(y)
    if x.length < 1e-6:
        return None
    x.normalize()
    return Matrix((x, y, x.cross(y))).transposed().to_quaternion()


def attach_helpers(pose, parent_name):
    side = parent_name[-1]
    prefix = parent_name[:-2]
    for idx in ('01', '02'):
        name = '%s_twist_%s_%s' % (prefix, idx, side)
        if name in rest:
            pose[name] = pose[parent_name] @ idle[parent_name].inverted() @ idle[name]


def lock_wrist_idle(pose, side):
    lo, hand = 'lowerarm_' + side, 'hand_' + side
    pose[hand] = pose[lo] @ idle[lo].inverted() @ idle[hand]


def solve_arm(hand_world, side, shoulder=None):
    up, lo, hand = 'upperarm_' + side, 'lowerarm_' + side, 'hand_' + side
    shoulder = idle[up].translation.copy() if shoulder is None else shoulder.copy()
    elbow = idle[lo].translation
    wrist = idle[hand].translation
    upper_len = (elbow - idle[up].translation).length
    fore_len = (wrist - elbow).length
    target = hand_world.translation.copy()
    delta = target - shoulder
    reach = delta.length
    limit = upper_len + fore_len - 1e-4
    clamped = 0.0
    if reach > limit:
        clamped = reach - limit
        target = shoulder + delta.normalized() * limit
        delta = target - shoulder
        reach = limit
    direction = delta.normalized()
    pole = (elbow - idle[up].translation) - direction * (elbow - idle[up].translation).dot(direction)
    if pole.length < 1e-5:
        pole = Vector((0.0, -1.0, 0.0))
        pole = pole - direction * pole.dot(direction)
    pole.normalize()
    cos_alpha = (upper_len * upper_len + reach * reach - fore_len * fore_len) / (2.0 * upper_len * reach)
    cos_alpha = max(-1.0, min(1.0, cos_alpha))
    alpha = math.acos(cos_alpha)
    elbow_pos = shoulder + (direction * math.cos(alpha) + pole * math.sin(alpha)) * upper_len
    upper_rot = (elbow - idle[up].translation).normalized().rotation_difference(
        (elbow_pos - shoulder).normalized()) @ idle[up].to_quaternion()
    fore_rot = (wrist - elbow).normalized().rotation_difference(
        (target - elbow_pos).normalized()) @ idle[lo].to_quaternion()
    return {
        up: Matrix.LocRotScale(shoulder, upper_rot, idle_scale[up]),
        lo: Matrix.LocRotScale(elbow_pos, fore_rot, idle_scale[lo]),
        hand: Matrix.LocRotScale(target, hand_world.to_quaternion(), idle_scale[hand]),
    }, clamped


def fit_elbow(shoulder_pos, target, upper_len, fore_len, hint):
    axis = (target - shoulder_pos)
    reach = axis.length
    limit = upper_len + fore_len - 1e-4
    if reach < 1e-6:
        return hint.copy(), 0.0
    if reach > limit:
        clamped = reach - limit
        target = shoulder_pos + axis.normalized() * limit
        axis = target - shoulder_pos
        reach = limit
    else:
        clamped = 0.0
    direction = axis.normalized()
    pole = hint - shoulder_pos
    pole = pole - direction * pole.dot(direction)
    if pole.length < 1e-5:
        pole = Vector((0.0, -1.0, 0.0))
        pole = pole - direction * pole.dot(direction)
    pole.normalize()
    cos_alpha = (upper_len * upper_len + reach * reach - fore_len * fore_len) / (2.0 * upper_len * reach)
    cos_alpha = max(-1.0, min(1.0, cos_alpha))
    alpha = math.acos(cos_alpha)
    elbow = shoulder_pos + (direction * math.cos(alpha) + pole * math.sin(alpha)) * upper_len
    return elbow, clamped


def project_across(vector, axis):
    out = vector - axis * vector.dot(axis)
    if out.length < 1e-6:
        return None
    return out.normalized()


def palm_across(hand_quat, fore):
    best = None
    score = -1.0
    for axis in (Vector((1.0, 0.0, 0.0)), Vector((0.0, 1.0, 0.0)), Vector((0.0, 0.0, 1.0))):
        candidate = hand_quat @ axis
        keep = 1.0 - abs(candidate.dot(fore))
        if keep > score:
            score = keep
            best = candidate
    return project_across(best, fore)


def solve_arm_palm(hand_world, side, shoulder=None, roll_weight=1.0, elbow_give=None, bend_cap_deg=None):
    up, lo, hand = 'upperarm_' + side, 'lowerarm_' + side, 'hand_' + side
    idle_shoulder = idle[up].translation
    idle_elbow = idle[lo].translation
    idle_wrist = idle[hand].translation
    upper_len = (idle_elbow - idle_shoulder).length
    fore_len = (idle_wrist - idle_elbow).length
    target = hand_world.translation.copy()
    shoulder_pos = idle_shoulder.copy() if shoulder is None else shoulder.copy()
    old_fore = (idle_wrist - idle_elbow).normalized()
    planted, clamped = fit_elbow(shoulder_pos, target, upper_len, fore_len, idle_elbow)
    palm_hint = target - old_fore * fore_len
    hand_delta = hand_world.to_quaternion() @ idle[hand].to_quaternion().inverted()
    aimed = hand_delta @ old_fore
    if aimed.length > 1e-6:
        palm_hint = target - aimed.normalized() * fore_len
    ideal_hint = palm_hint.copy()
    give = ELBOW_GIVE if elbow_give is None else elbow_give
    toward = palm_hint - planted
    if toward.length > give:
        palm_hint = planted + toward.normalized() * give
    elbow_pos, extra = fit_elbow(shoulder_pos, target, upper_len, fore_len, palm_hint)
    clamped = max(clamped, extra)

    def assemble(elbow, shoulder):
        axis = (target - elbow).normalized()
        old_upper = (idle_elbow - idle_shoulder).normalized()
        upper_axis = (elbow - shoulder).normalized()
        idle_across = palm_across(idle[hand].to_quaternion(), old_fore)
        now_across = palm_across(hand_world.to_quaternion(), axis)
        transported = project_across(old_fore.rotation_difference(axis) @ idle_across, axis) if idle_across is not None else None
        roll = 0.0
        if transported is not None and now_across is not None:
            rel = transported.rotation_difference(now_across)
            if rel.w < 0.0:
                rel.negate()
            roll = 2.0 * math.atan2(Vector((rel.x, rel.y, rel.z)).dot(axis), rel.w)
        roll *= max(0.0, min(1.0, roll_weight))
        share = max(-math.radians(12.0), min(math.radians(12.0), roll * 0.25))
        fore_rot = Quaternion(axis, roll - share) @ (
            old_fore.rotation_difference(axis) @ idle[lo].to_quaternion())
        upper_rot = Quaternion(upper_axis, share) @ (
            old_upper.rotation_difference(upper_axis) @ idle[up].to_quaternion())
        return {
            up: Matrix.LocRotScale(shoulder, upper_rot, idle_scale[up]),
            lo: Matrix.LocRotScale(elbow, fore_rot, idle_scale[lo]),
            hand: Matrix.LocRotScale(target, hand_world.to_quaternion(), idle_scale[hand]),
        }

    to_elbow = elbow_pos - shoulder_pos
    if to_elbow.length > 1e-5:
        shoulder_pos = elbow_pos - to_elbow.normalized() * upper_len
    solved = assemble(elbow_pos, shoulder_pos)
    if bend_cap_deg is not None and wrist_axis_bend_deg(solved, side) > bend_cap_deg:
        extra_span = ideal_hint - planted
        if extra_span.length > give:
            ideal = planted + extra_span.normalized() * give
        else:
            ideal = ideal_hint
        lo_t, hi_t = 0.0, 1.0
        chosen = solved
        for _ in range(14):
            mid = 0.5 * (lo_t + hi_t)
            hint = elbow_pos.lerp(ideal, mid)
            trial_elbow, trial_extra = fit_elbow(shoulder_pos, target, upper_len, fore_len, hint)
            trial_shoulder = shoulder_pos
            to_e = trial_elbow - trial_shoulder
            if to_e.length > 1e-5:
                trial_shoulder = trial_elbow - to_e.normalized() * upper_len
            trial = assemble(trial_elbow, trial_shoulder)
            if wrist_axis_bend_deg(trial, side) <= bend_cap_deg:
                chosen = trial
                clamped = max(clamped, trial_extra)
                hi_t = mid
            else:
                lo_t = mid
                chosen = trial
                clamped = max(clamped, trial_extra)
        solved = chosen
    return solved, clamped


def solve_arm_supported(hand_world, side, shoulder_pref=None, pole_tilt=None):
    up, lo, hand = 'upperarm_' + side, 'lowerarm_' + side, 'hand_' + side
    idle_elbow = idle[lo].translation
    idle_wrist = idle[hand].translation
    idle_shoulder = idle[up].translation
    upper_len = (idle_elbow - idle_shoulder).length
    fore_len = (idle_wrist - idle_elbow).length
    target = hand_world.translation.copy()
    idle_fore = (idle_wrist - idle_elbow).normalized()
    desired_fore = (
        hand_world.to_quaternion() @ idle[hand].to_quaternion().inverted() @ idle_fore
    ).normalized()
    if pole_tilt is not None and pole_tilt.length > 1e-6:
        desired_fore = (desired_fore + 0.22 * pole_tilt).normalized()
    elbow_pos = target - desired_fore * fore_len
    preferred = idle_shoulder.copy() if shoulder_pref is None else shoulder_pref.copy()
    to_elbow = elbow_pos - preferred
    if to_elbow.length < 1e-5:
        to_elbow = idle_elbow - idle_shoulder
    shoulder = elbow_pos - to_elbow.normalized() * upper_len
    reach = (target - shoulder).length
    limit = upper_len + fore_len - 1e-4
    clamped = 0.0
    if reach > limit:
        clamped = reach - limit
        target = shoulder + (target - shoulder).normalized() * limit
        elbow_pos = target - desired_fore * fore_len
        to_elbow = elbow_pos - preferred
        if to_elbow.length < 1e-5:
            to_elbow = idle_elbow - idle_shoulder
        shoulder = elbow_pos - to_elbow.normalized() * upper_len
    upper_rot = (idle_elbow - idle_shoulder).normalized().rotation_difference(
        (elbow_pos - shoulder).normalized()) @ idle[up].to_quaternion()
    fore_rot = idle_fore.rotation_difference(desired_fore) @ idle[lo].to_quaternion()
    return {
        up: Matrix.LocRotScale(shoulder, upper_rot, idle_scale[up]),
        lo: Matrix.LocRotScale(elbow_pos, fore_rot, idle_scale[lo]),
        hand: Matrix.LocRotScale(target, hand_world.to_quaternion(), idle_scale[hand]),
    }, clamped


def elbow_gap(pose, side):
    up, lo, hand = 'upperarm_' + side, 'lowerarm_' + side, 'hand_' + side
    axis = (pose[hand].translation - pose[lo].translation).normalized()
    rest_fore = (rest[hand].translation - rest[lo].translation).normalized()
    up_delta = pose[up].to_quaternion() @ rest[up].to_quaternion().inverted()
    fore_delta = pose[lo].to_quaternion() @ rest[lo].to_quaternion().inverted()
    no_roll = (up_delta @ rest_fore).rotation_difference(axis) @ up_delta
    relative = fore_delta @ no_roll.inverted()
    vector = Vector((relative.x, relative.y, relative.z))
    angle = 2.0 * math.atan2(vector.dot(axis), relative.w)
    return math.degrees((angle + math.pi) % (2.0 * math.pi) - math.pi)


def roll_shoulder(pose, side, previous):
    up, lo = 'upperarm_' + side, 'lowerarm_' + side
    axis = (pose[lo].translation - pose[up].translation).normalized()

    def metric(degrees):
        trial = dict(pose)
        trial[up] = Matrix.LocRotScale(
            pose[up].translation,
            Quaternion(axis, math.radians(degrees)) @ pose[up].to_quaternion(),
            idle_scale[up])
        return abs(elbow_gap(trial, side))

    samples = [(metric(deg), deg) for deg in range(-95, 96, 5)]
    best = min(value for value, _deg in samples)
    candidates = [deg for value, deg in samples if value <= best + 1.0]
    chosen = min(candidates, key=lambda deg: abs(deg) if previous is None else abs(deg - previous))
    pose[up] = Matrix.LocRotScale(
        pose[up].translation,
        Quaternion(axis, math.radians(chosen)) @ pose[up].to_quaternion(),
        idle_scale[up])
    return chosen


def wrist_twist_deg(pose, side):
    lo, hand = 'lowerarm_' + side, 'hand_' + side
    axis = (pose[hand].translation - pose[lo].translation).normalized()
    idle_rel = idle[lo].to_quaternion().inverted() @ idle[hand].to_quaternion()
    now_rel = pose[lo].to_quaternion().inverted() @ pose[hand].to_quaternion()
    delta = now_rel @ idle_rel.inverted()
    if delta.w < 0.0:
        delta.negate()
    return math.degrees(2.0 * math.atan2(Vector((delta.x, delta.y, delta.z)).dot(axis), delta.w))


def wrist_axis_bend_deg(pose, side):
    lo, hand = 'lowerarm_' + side, 'hand_' + side
    forearm_dir = (pose[hand].translation - pose[lo].translation).normalized()
    rest_dir = (rest[hand].translation - rest[lo].translation).normalized()
    hand_aligned = pose[hand].to_quaternion() @ rest[hand].to_quaternion().inverted() @ rest_dir
    if hand_aligned.length < 1e-6:
        return 0.0
    return math.degrees(forearm_dir.angle(hand_aligned.normalized()))


def elbow_interior_deg(pose, side):
    up, lo, hand = 'upperarm_' + side, 'lowerarm_' + side, 'hand_' + side
    a = pose[up].translation - pose[lo].translation
    b = pose[hand].translation - pose[lo].translation
    if a.length < 1e-6 or b.length < 1e-6:
        return 0.0
    return math.degrees(a.angle(b))


def channels(world, parent_world, name):
    local = parent_world.inverted() @ world
    return (local_rest[name].inverted() @ local).decompose()


idle_local_scale = {}
for _name in names:
    _parent = parent[_name]
    _pw = idle[_parent] if _parent else Matrix.Identity(4)
    idle_local_scale[_name] = channels(idle[_name], _pw, _name)[2]


def rebuild_finger_world(pose, side):
    order = [n for n in FINGER_MAP if n.endswith('_' + side)]
    for name in order:
        rest_local = local_rest[name]
        idle_parent = idle[parent[name]]
        idle_local = idle_parent.inverted() @ idle[name]
        loc_i, quat_i, scale_i = (rest_local.inverted() @ idle_local).decompose()
        amount = amount_for_current[FINGER_MAP[name]]
        weight = amount * (design.OPEN_METACARPAL if name in METACARPALS else design.OPEN_PHALANX)
        loc_r, quat_r, scale_r = Vector((0, 0, 0)), Quaternion(), Vector((1, 1, 1))
        if quat_i.dot(quat_r) < 0.0:
            quat_r.negate()
        local = rest_local @ Matrix.LocRotScale(
            loc_i.lerp(loc_r, weight), quat_i.slerp(quat_r, weight),
            scale_i.lerp(scale_r, weight))
        pose[name] = pose[parent[name]] @ local


source.name = 'RETAINED_V4_Idle'
source.use_fake_user = True
action = source.copy()
action.name = CLIP
action.use_fake_user = True
rig.animation_data.action = action
rig.animation_data.action_slot = action.slots[0]
for layer in action.layers:
    for strip in layer.strips:
        for bag in strip.channelbags:
            for curve in list(bag.fcurves):
                bag.fcurves.remove(curve)

order = []
pending = set(names)
while pending:
    for name in list(pending):
        if parent[name] is None or parent[name] not in pending:
            order.append(name)
            pending.remove(name)

end_frame = int(round(END * FPS))
previous_quat = {}
shoulder_prev = {'r': None, 'l': None}
wrist_state = {}
rows = []
amount_for_current = {'thumb': 0.0, 'index': 0.0, 'middle': 0.0, 'ring': 0.0, 'pinky': 0.0}

for frame in range(end_frame + 1):
    seconds = frame / FPS
    phi = curves['phi'](seconds)
    psi = curves['psi'](seconds)
    theta = curves['theta'](seconds)
    rho = curves['rho'](seconds)
    lift = curves['lift'](seconds)
    forward = curves['forward'](seconds)
    throw = design.smoothstep((seconds - 0.30) / 0.08) * (
        1.0 - design.smoothstep((seconds - remap_t(0.44)) / (remap_t(0.58) - remap_t(0.44))))
    theta -= 8.0 * throw
    recover = recover_weight(seconds)
    out = curves['out'](seconds)
    grip = curves['grip'](seconds)
    left_path = curves['left_path'](seconds)
    left_open = curves['left_open'](seconds)
    if seconds + 1e-6 >= design.SPIN_END:
        out = PREPARE_RIGHT_M * (1.0 - recover)
        left_path = 1.0 - recover
        left_open = 1.0 - recover
        lift *= (1.0 - recover)
        forward *= (1.0 - recover)
    fw = flatten_weight(seconds, recover)
    for finger in amount_for_current:
        amount_for_current[finger] = curves['finger_' + finger](seconds)

    offset = UP * lift + fwd_dir * forward + right_dir * out
    flatten_now = Quaternion().slerp(flatten_q, fw)
    spin_q = Quaternion(spin_axis, math.radians(phi))
    roll_q = Quaternion(spin_q @ flatten_now @ blade_axis, math.radians(rho))
    sword_rot = roll_q @ spin_q @ flatten_now @ idle[WPN].to_quaternion()

    psi_q = Quaternion(forearm, math.radians(psi))
    theta_q = Quaternion(spin_axis, math.radians(theta))
    hand_rot = theta_q @ psi_q @ flatten_now @ idle['hand_r'].to_quaternion()
    hand_open = Matrix.LocRotScale(
        idle['hand_r'].translation + offset, hand_rot, idle_scale['hand_r'])

    contact_idle = contact_sword + offset
    sword_locked = weapon_from_rotation(sword_rot, contact_idle)
    hand_locked = sword_locked @ grip_r
    hand_r = mix_mat(hand_open, hand_locked, grip)
    contact_world = hand_r @ contact_hand_local
    sword_rot = lift_tip_rotation(sword_rot, contact_world)
    sword_world = weapon_from_rotation(sword_rot, contact_world)

    park = Vector(design.LEFT_PARK)
    bulge = Vector(design.LEFT_BULGE)
    left_offset = park * left_path + bulge * (4.0 * left_path * (1.0 - left_path)) + right_dir * out
    hand_l = Matrix.LocRotScale(
        idle['hand_l'].translation + left_offset,
        idle['hand_l'].to_quaternion(),
        idle_scale['hand_l'])
    shoulder_l = idle['upperarm_l'].translation + Vector(design.LEFT_SHOULDER) * left_path

    if recover > 0.0:
        # Rotate toward idle in place; translation already follows out/left_path.
        hand_keep = hand_r.translation.copy()
        sword_keep = sword_world.translation.copy()
        hand_r = mix_mat(hand_r, idle['hand_r'], recover)
        sword_world = mix_mat(sword_world, idle[WPN], recover)
        hand_r = Matrix.LocRotScale(hand_keep, hand_r.to_quaternion(), idle_scale['hand_r'])
        contact_world = hand_r @ contact_hand_local
        sword_rot = sword_world.to_quaternion()
        sword_world = weapon_from_rotation(sword_rot, contact_world)
        for finger in amount_for_current:
            amount_for_current[finger] *= (1.0 - recover)

    pose = {n: idle[n].copy() for n in names}
    pose[WPN] = sword_world
    roll_w = fw
    clamp_r = 0.0
    clamp_l = 0.0
    idle_hold = recover >= 1.0 - 1e-4 or (
        fw < 1e-5 and left_path < 1e-5 and recover < 1e-5
        and abs(out) < 1e-5 and abs(lift) < 1e-5 and abs(forward) < 1e-5)
    if idle_hold:
        pose[WPN] = idle[WPN].copy()
    else:
        solved_r, clamp_r = solve_arm_palm(
            hand_r, 'r', roll_weight=roll_w, elbow_give=ELBOW_GIVE_R, bend_cap_deg=WRIST_BEND_CAP_R)
        solved_l, clamp_l = solve_arm_palm(hand_l, 'l', shoulder_l, roll_weight=0.0)
        lock_wrist_idle(solved_l, 'l')
        pose.update(solved_r)
        pose.update(solved_l)
        for side in ('r', 'l'):
            attach_helpers(pose, 'upperarm_' + side)
            attach_helpers(pose, 'lowerarm_' + side)
        if roll_w > 1e-4:
            shoulder_prev['r'] = roll_shoulder(pose, 'r', shoulder_prev['r'])
        else:
            shoulder_prev['r'] = None
        if left_path > 1e-4:
            shoulder_prev['l'] = roll_shoulder(pose, 'l', shoulder_prev['l'])
        else:
            shoulder_prev['l'] = None
        for side in ('r', 'l'):
            attach_helpers(pose, 'upperarm_' + side)
            attach_helpers(pose, 'lowerarm_' + side)
        share_wrist_twist(pose, 'r', WRIST_TWIST_LIM_R)
        limit_wrist(pose, 'r', WRIST_TWIST_LIM_R, WRIST_BEND_LIM_R)
        pose[WPN] = weapon_from_rotation(sword_rot, pose['hand_r'] @ contact_hand_local)
        attach_helpers(pose, 'lowerarm_r')
    support_w = 0.0
    spread, twist_report = arm_roll.build(pose, local_rest, rest, support_w)
    rebuild_finger_world(pose, 'r')
    saved = dict(amount_for_current)
    for finger in amount_for_current:
        amount_for_current[finger] = left_open
    rebuild_finger_world(pose, 'l')
    amount_for_current.update(saved)

    parent_world = {}
    for name in order:
        bone = rig.pose.bones[name]
        bone.rotation_mode = 'QUATERNION'
        parent_name = parent[name]
        parent_matrix = parent_world.get(parent_name, Matrix.Identity(4))
        loc, quat, scale_value = channels(pose[name], parent_matrix, name)
        if name in previous_quat and quat.dot(previous_quat[name]) < 0.0:
            quat.negate()
        previous_quat[name] = quat.copy()
        bone.location = loc
        bone.rotation_quaternion = quat
        bone.scale = idle_local_scale[name]
        parent_world[name] = (
            parent_matrix @ local_rest[name] @ Matrix.LocRotScale(loc, quat, scale_value))
        if (frame % 2 == 0 or frame >= int(round(design.SPIN_START * FPS))
                or frame in (0, end_frame)):
            for channel in ('location', 'rotation_quaternion', 'scale'):
                bone.keyframe_insert(channel, frame=frame, group=name)

    if frame % 8 == 0 or frame in (0, end_frame):
        mesh_now = parent_world[WPN] @ rest[WPN].inverted()
        tip_w = mesh_now @ tip_bind
        pommel_w = mesh_now @ pommel_bind
        contact_now = parent_world['hand_r'].inverted() @ (mesh_now @ contact_mesh_local)
        rows.append({
            'seconds': round(seconds, 3),
            'phi_deg': round(phi, 2),
            'psi_deg': round(psi, 2),
            'theta_deg': round(theta, 2),
            'grip': round(grip, 3),
            'finger_thumb': round(amount_for_current['thumb'], 3),
            'finger_index': round(amount_for_current['index'], 3),
            'finger_middle': round(amount_for_current['middle'], 3),
            'finger_ring': round(amount_for_current['ring'], 3),
            'finger_pinky': round(amount_for_current['pinky'], 3),
            'flatten': round(fw, 3),
            'recover': round(recover, 3),
            'out_m': round(out, 4),
            'lift_m': round(lift, 4),
            'forward_m': round(forward, 4),
            'left_path': round(left_path, 3),
            'tip_depth_m': round(tip_w.y, 4),
            'pommel_depth_m': round(pommel_w.y, 4),
            'contact_drift_m': round((contact_now - contact_hand_local).length, 6),
            'reach_clamp_r_m': round(clamp_r, 4),
            'reach_clamp_l_m': round(clamp_l, 4),
            'wrist_twist_r_deg': round(wrist_twist_deg(pose, 'r'), 2),
            'wrist_twist_l_deg': round(wrist_twist_deg(pose, 'l'), 2),
            'wrist_axis_bend_r_deg': round(wrist_axis_bend_deg(pose, 'r'), 2),
            'wrist_axis_bend_l_deg': round(wrist_axis_bend_deg(pose, 'l'), 2),
            'elbow_interior_r_deg': round(elbow_interior_deg(pose, 'r'), 2),
            'elbow_interior_l_deg': round(elbow_interior_deg(pose, 'l'), 2),
            'hand_r': [round(v, 4) for v in parent_world['hand_r'].translation],
            'hand_l': [round(v, 4) for v in parent_world['hand_l'].translation],
            'shoulder_r_delta_m': [
                round(v, 4) for v in (
                    parent_world['upperarm_r'].translation - idle['upperarm_r'].translation)
            ],
            'elbow_r_delta_m': [
                round(v, 4) for v in (
                    parent_world['lowerarm_r'].translation - idle['lowerarm_r'].translation)
            ],
            'elbow_twist_r': round(twist_report['r']['elbow_twist_after'], 2),
            'elbow_twist_l': round(twist_report['l']['elbow_twist_after'], 2),
        })

for layer in action.layers:
    for strip in layer.strips:
        for bag in strip.channelbags:
            for curve in bag.fcurves:
                for key in curve.keyframe_points:
                    key.interpolation = 'LINEAR'

scene.render.fps = int(FPS)
scene.render.fps_base = 1.0
scene.frame_start, scene.frame_end = 0, end_frame
scene.frame_set(0)
bpy.ops.object.select_all(action='DESELECT')
rig.hide_set(False)
rig.select_set(True)
bpy.context.view_layer.objects.active = rig
bpy.ops.export_scene.fbx(
    filepath=str(OUT / (CLIP + '.fbx')),
    use_selection=True, object_types={'ARMATURE'},
    axis_forward='-Y', axis_up='Z', add_leaf_bones=False,
    bake_anim=True, bake_anim_use_all_actions=False,
    bake_anim_use_nla_strips=False, bake_anim_simplify_factor=0)

end_err = max(
    (parent_world[n].translation - idle[n].translation).length
    for n in ('hand_r', 'hand_l', WPN))
report = {
    'revision': 'InspectForwardSpinV79',
    'reference': 'V78 poses; spin 25% faster, prepare/throw/recover length kept',
    'spin_speed': SPIN_SPEED,
    'idle_source': str(SOURCE),
    'seconds': END,
    'spin_window_s': [design.SPIN_START, design.SPIN_END],
    'fps': FPS,
    'contact_distance_m': round(contact_distance, 6),
    'contact_hand_local': [round(v, 5) for v in contact_hand_local],
    'blade_axis_idle': [round(v, 4) for v in blade_axis],
    'spin_axis': [round(v, 4) for v in spin_axis],
    'flatten_deg': round(math.degrees(flatten_q.angle), 3),
    'min_tip_depth_m': min(row['tip_depth_m'] for row in rows),
    'max_contact_drift_m': max(row['contact_drift_m'] for row in rows),
    'max_reach_clamp_m': max(max(row['reach_clamp_r_m'], row['reach_clamp_l_m']) for row in rows),
    'max_wrist_twist_r_deg': max(abs(row['wrist_twist_r_deg']) for row in rows),
    'max_wrist_twist_l_deg': max(abs(row['wrist_twist_l_deg']) for row in rows),
    'max_wrist_axis_bend_r_deg': max(row['wrist_axis_bend_r_deg'] for row in rows),
    'max_wrist_axis_bend_l_deg': max(row['wrist_axis_bend_l_deg'] for row in rows),
    'max_hand_r_travel_m': max(
        (Vector(row['hand_r']) - idle['hand_r'].translation).length for row in rows),
    'max_hand_l_travel_m': max(
        (Vector(row['hand_l']) - idle['hand_l'].translation).length for row in rows),
    'max_shoulder_r_travel_m': max(
        Vector(row['shoulder_r_delta_m']).length for row in rows),
    'max_elbow_r_travel_m': max(
        Vector(row['elbow_r_delta_m']).length for row in rows),
    'end_translation_error_m': round(end_err, 6),
    'samples': rows,
    'prepare_right_m': PREPARE_RIGHT_M,
    'method': (
        'No mesh edit. Uniform 1.25x retiming of the spin window only. '
        'Wrist caps and outward axis stay.'
    ),
    'testing': 'No gameplay, PIE or acceptance run; user tests.',
}
(HERE / 'authoring_v79.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
print('V79 min tip %.4f m  contact %.6f m  end %.6f m  wrist_r %.2f deg  bend_r %.2f deg  hand %.3f m  el %.3f m' % (
    report['min_tip_depth_m'], report['max_contact_drift_m'],
    report['end_translation_error_m'], report['max_wrist_twist_r_deg'],
    report['max_wrist_axis_bend_r_deg'],
    report['max_hand_r_travel_m'], report['max_elbow_r_travel_m']))
print('INSPECT_FORWARD_SPIN_V79_AUTHORED')
