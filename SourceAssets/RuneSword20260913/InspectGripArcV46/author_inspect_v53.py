"""Author V53: a readable two-hand face turn for the long rune sword.

Earlier inspects copied a short weapon's baton spin. On this 1.09 m blade the
tip leaves the frame, a picture-plane spin shows the hilt, and a tumble toward
the camera crosses the near plane. V53 keeps both accepted grips locked to the
hilt, pitches the blade forward into the view, then rolls 180 degrees about
the blade axis so the other face is readable, and returns on the same path.
Arms are re-solved, shoulder roll clears the elbow seam, and forearm twist is
spread along the twist bones.
"""
import bpy
import json
import math
import sys
from pathlib import Path
from mathutils import Matrix, Quaternion, Vector

P = Path(__file__).parent
sys.path.insert(0, str(P))
import inspect_arm_roll as arm_roll

SOURCE = P / 'AzureRunesword_InspectTwirlV47.blend'
OUT = P / 'ExportV53'
OUT.mkdir(exist_ok=True)
FPS = 120.0
DURATION = 3.05
CLIP = 'A_RuneSword_Inspect'
WPN = 'WPN_root'
PITCH = -58.0
TURN = 180.0

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

source = bpy.data.actions[CLIP]
rig.animation_data.action = source
rig.animation_data.action_slot = source.slots[0]
scene.render.fps = int(FPS)
scene.frame_set(0)
bpy.context.view_layer.update()
idle = {b.name: b.matrix.copy() for b in rig.pose.bones}

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
flat = (transform.to_3x3() @ basis[spans[2][1]]).normalized()
pivot = (idle['hand_r'].translation + idle['hand_l'].translation) * 0.5
grip = {side: idle[WPN].inverted() @ idle['hand_' + side] for side in ('r', 'l')}
idle_scale = {n: idle[n].to_scale() for n in names}


def smoothstep(value):
    value = max(0.0, min(1.0, value))
    return value * value * value * (value * (value * 6.0 - 15.0) + 10.0)


def ramp(seconds, start, end):
    return smoothstep((seconds - start) / (end - start))


def schedule(seconds):
    """Pitch into view, roll to the other face, then undo both."""
    if seconds < 0.45:
        pitch = PITCH * ramp(seconds, 0.04, 0.45)
        roll = 0.0
    elif seconds < 0.65:
        pitch, roll = PITCH, 0.0
    elif seconds < 1.50:
        pitch = PITCH
        roll = TURN * ramp(seconds, 0.65, 1.50)
    elif seconds < 1.85:
        pitch, roll = PITCH, TURN
    elif seconds < 2.70:
        pitch = PITCH
        roll = TURN * (1.0 - ramp(seconds, 1.85, 2.70))
    else:
        pitch = PITCH * (1.0 - ramp(seconds, 2.70, 3.00))
        roll = 0.0
    return pitch, roll


def weapon_world(pitch_deg, roll_deg):
    pitched = Quaternion(Vector((1.0, 0.0, 0.0)), math.radians(pitch_deg))
    axis = pitched @ blade_axis
    rolled = Quaternion(axis, math.radians(roll_deg)) @ pitched
    rotation = rolled @ idle[WPN].to_quaternion()
    translation = pivot + rolled @ (idle[WPN].translation - pivot)
    return Matrix.LocRotScale(translation, rotation, idle_scale[WPN])


def solve_arm(hand_world, side):
    up = 'upperarm_' + side
    lo = 'lowerarm_' + side
    hand = 'hand_' + side
    shoulder = idle[up].translation
    elbow = idle[lo].translation
    wrist = idle[hand].translation
    upper_len = (elbow - shoulder).length
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
    pole = (elbow - shoulder) - direction * (elbow - shoulder).dot(direction)
    if pole.length < 1e-5:
        pole = Vector((0.0, -1.0, 0.0))
        pole = pole - direction * pole.dot(direction)
    pole.normalize()
    cos_alpha = (upper_len * upper_len + reach * reach - fore_len * fore_len) / (2.0 * upper_len * reach)
    cos_alpha = max(-1.0, min(1.0, cos_alpha))
    alpha = math.acos(cos_alpha)
    elbow_pos = shoulder + (direction * math.cos(alpha) + pole * math.sin(alpha)) * upper_len
    upper_rot = (elbow - shoulder).normalized().rotation_difference(
        (elbow_pos - shoulder).normalized()) @ idle[up].to_quaternion()
    fore_rot = (wrist - elbow).normalized().rotation_difference(
        (target - elbow_pos).normalized()) @ idle[lo].to_quaternion()
    return {
        up: Matrix.LocRotScale(shoulder, upper_rot, idle_scale[up]),
        lo: Matrix.LocRotScale(elbow_pos, fore_rot, idle_scale[lo]),
        hand: Matrix.LocRotScale(target, hand_world.to_quaternion(), idle_scale[hand]),
    }, clamped


def elbow_gap(pose, rest_map, side):
    up, lo, hand = 'upperarm_' + side, 'lowerarm_' + side, 'hand_' + side
    axis = (pose[hand].translation - pose[lo].translation).normalized()
    rest_fore = (rest_map[hand].translation - rest_map[lo].translation).normalized()
    up_delta = pose[up].to_quaternion() @ rest_map[up].to_quaternion().inverted()
    fore_delta = pose[lo].to_quaternion() @ rest_map[lo].to_quaternion().inverted()
    no_roll = (up_delta @ rest_fore).rotation_difference(axis) @ up_delta
    relative = fore_delta @ no_roll.inverted()
    vector = Vector((relative.x, relative.y, relative.z))
    angle = 2.0 * math.atan2(vector.dot(axis), relative.w)
    return math.degrees((angle + math.pi) % (2.0 * math.pi) - math.pi)


def roll_shoulder(pose, side, previous):
    up = 'upperarm_' + side
    lo = 'lowerarm_' + side
    axis = (pose[lo].translation - pose[up].translation).normalized()

    def metric(degrees):
        trial = dict(pose)
        trial[up] = Matrix.LocRotScale(
            pose[up].translation,
            Quaternion(axis, math.radians(degrees)) @ pose[up].to_quaternion(),
            idle_scale[up])
        return abs(elbow_gap(trial, rest, side))

    samples = [(metric(deg), deg) for deg in range(-95, 96, 5)]
    best = min(value for value, _deg in samples)
    candidates = [deg for value, deg in samples if value <= best + 1.0]
    if previous is None:
        chosen = min(candidates, key=lambda deg: abs(deg))
    else:
        chosen = min(candidates, key=lambda deg: abs(deg - previous))
    pose[up] = Matrix.LocRotScale(
        pose[up].translation,
        Quaternion(axis, math.radians(chosen)) @ pose[up].to_quaternion(),
        idle_scale[up])
    return chosen


def channels(world, parent_world, name):
    local = parent_world.inverted() @ world
    loc, quat, scale_value = (local_rest[name].inverted() @ local).decompose()
    return loc, quat, scale_value


def idle_local(name, cache):
    if name not in cache:
        parent_name = parent[name]
        parent_world = idle[parent_name] if parent_name else Matrix.Identity(4)
        cache[name] = channels(idle[name], parent_world, name)
    return cache[name]


source.name = 'RETAINED_V47_' + CLIP
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

previous_quat = {}
shoulder_prev = {'r': None, 'l': None}
rows = []
local_cache = {}
end_frame = int(DURATION * FPS)
order = []
pending = set(names)
while pending:
    for name in list(pending):
        parent_name = parent[name]
        if parent_name is None or parent_name not in pending:
            order.append(name)
            pending.remove(name)

for frame in range(end_frame + 1):
    seconds = frame / FPS
    pitch, roll = schedule(seconds)
    exact = abs(pitch) < 0.05 and abs(roll) < 0.05
    pose = {n: idle[n].copy() for n in names}
    clamped = 0.0
    if not exact:
        weapon = weapon_world(pitch, roll)
        pose[WPN] = weapon
        for side in ('r', 'l'):
            hand_world = weapon @ grip[side]
            solved, error = solve_arm(hand_world, side)
            clamped = max(clamped, error)
            pose.update(solved)
            shoulder_prev[side] = roll_shoulder(pose, side, shoulder_prev[side])
        spread, _report = arm_roll.build(pose, local_rest, rest, 1.0)
        pose.update(spread)
    else:
        shoulder_prev = {'r': None, 'l': None}

    parent_world = {}
    for name in order:
        bone = rig.pose.bones[name]
        bone.rotation_mode = 'QUATERNION'
        if exact or name not in pose or (
            name not in ('WPN_root', 'upperarm_r', 'upperarm_l', 'lowerarm_r', 'lowerarm_l',
                         'lowerarm_twist_01_r', 'lowerarm_twist_02_r',
                         'lowerarm_twist_01_l', 'lowerarm_twist_02_l',
                         'hand_r', 'hand_l')
            and name != WPN
        ):
            driven = name in (
                WPN, 'upperarm_r', 'upperarm_l', 'lowerarm_r', 'lowerarm_l',
                'lowerarm_twist_01_r', 'lowerarm_twist_02_r',
                'lowerarm_twist_01_l', 'lowerarm_twist_02_l', 'hand_r', 'hand_l')
            if exact or not driven:
                loc, quat, scale_value = idle_local(name, local_cache)
            else:
                parent_name = parent[name]
                parent_matrix = parent_world.get(parent_name, Matrix.Identity(4))
                loc, quat, scale_value = channels(pose[name], parent_matrix, name)
        else:
            parent_name = parent[name]
            parent_matrix = parent_world.get(parent_name, Matrix.Identity(4))
            loc, quat, scale_value = channels(pose[name], parent_matrix, name)
        if name in previous_quat and quat.dot(previous_quat[name]) < 0.0:
            quat.negate()
        previous_quat[name] = quat.copy()
        bone.location = loc
        bone.rotation_quaternion = quat
        bone.scale = scale_value
        parent_world[name] = (
            (parent_world[parent[name]] if parent[name] else Matrix.Identity(4))
            @ local_rest[name] @ Matrix.LocRotScale(loc, quat, scale_value))
        if frame % 2 == 0 and name in (
            WPN, 'upperarm_r', 'upperarm_l', 'lowerarm_r', 'lowerarm_l', 'hand_r', 'hand_l',
            'lowerarm_twist_01_r', 'lowerarm_twist_01_l'):
            for channel in ('location', 'rotation_quaternion', 'scale'):
                bone.keyframe_insert(channel, frame=frame, group=name)
        elif frame in (0, end_frame):
            for channel in ('location', 'rotation_quaternion', 'scale'):
                bone.keyframe_insert(channel, frame=frame, group=name)

    if frame % 8 == 0:
        moved = parent_world[WPN] @ rest[WPN].inverted()
        depths = [(moved @ (transform.inverted() @ p)).y for p in points[::8]]
        rows.append({
            'seconds': round(seconds, 3),
            'pitch_deg': round(pitch, 2),
            'roll_deg': round(roll, 2),
            'min_depth_m': round(min(depths), 4),
            'reach_clamp_m': round(clamped, 4),
            'hand_r': [round(v, 4) for v in parent_world['hand_r'].translation],
            'hand_l': [round(v, 4) for v in parent_world['hand_l'].translation],
        })

for layer in action.layers:
    for strip in layer.strips:
        for bag in strip.channelbags:
            for curve in bag.fcurves:
                for key in curve.keyframe_points:
                    key.interpolation = 'LINEAR'

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

report = {
    'revision': 'InspectFaceTurnV53',
    'seconds': DURATION,
    'pitch_deg': PITCH,
    'turn_deg': TURN,
    'blade_axis': [round(v, 4) for v in blade_axis],
    'flat_normal': [round(v, 4) for v in flat],
    'pivot': [round(v, 4) for v in pivot],
    'min_depth_m': min(row['min_depth_m'] for row in rows),
    'max_reach_clamp_m': max(row['reach_clamp_m'] for row in rows),
    'samples': rows,
    'method': (
        'Both hands stay locked to the accepted grip. The sword pitches forward '
        'about the grip so the blade enters the view, rolls 180 degrees about its '
        'own axis so the other face can be read, then returns on the same path. '
        'This is not a picture-plane baton spin and does not tumble the tip at the camera.'
    ),
    'testing': 'No gameplay, PIE or acceptance run; user tests.',
}
(P / 'authoring_v53.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(P / 'AzureRunesword_InspectFaceTurnV53.blend'))
print('V53 min depth %.4f m  reach clamp %.4f m' % (
    report['min_depth_m'], report['max_reach_clamp_m']))
print('INSPECT_FACE_TURN_V53_AUTHORED')
