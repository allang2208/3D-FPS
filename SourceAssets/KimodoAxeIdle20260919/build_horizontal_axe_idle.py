"""Author a HORIZONTAL two-hand axe idle for the harvest-tool viewmodel.

Blender --background --python <this> -- <blend> <sway.json> <out_dir> <name> <blade_yaw_deg> [--render]

Layout requested 2026-09-19: the axe is held ACROSS the body (near-horizontal), the head pointing
outward to the player's right, the right hand up the handle next to the metal head, the left hand
lower down the handle. Grip heights and the lean are parameters below; both hands keep the
accepted single-hand wrap (anatomically mirrored for the left), supplied by the shipped idle pose.

The generator (Kimodo) still only supplies the ambient sway; the hold itself is solved here, as
the skill note on that tool requires.
"""
import bpy
import json
import math
import sys
from pathlib import Path
from mathutils import Matrix, Quaternion, Vector

args = sys.argv[sys.argv.index('--') + 1:]
blend = Path(args[0])
sway_path = Path(args[1])
out_dir = Path(args[2])
name = args[3]
blade_yaw = math.radians(float(args[4])) if len(args) > 4 and not args[4].startswith('--') else 0.0
do_render = '--render' in args
# Optional rig-space hold offset override (args 5..7), for framing the hold in the game camera.
if len(args) > 7:
    shift_x, shift_y, shift_z = (float(v) for v in args[5:8])
else:
    shift_x, shift_y, shift_z = None, None, None
out_dir.mkdir(parents=True, exist_ok=True)

FPS = 150
SOURCE_FPS = 30
DURATION = 90 / SOURCE_FPS                       # 3.0 s
POSITION_SCALE = 0.60
ROTATION_SCALE = 0.45
GRIP_UP_M = 0.26                                 # right hand this far up the handle from the old grip
LEFT_DOWN_M = 0.12                               # left hand this far BELOW the right, down the handle
LEAN_DEG = 14.0                                  # face-on lean of the shaft, head side raised
HEAD_OUT_SIGN = 1.0                              # +1 puts the head toward the player's right
REACH_MARGIN_M = 0.045
GRIP_SHIFT_GOAL = Vector((-0.28, 0.08, 0.02))   # rig-space hold offset; overridable from the command line
FINGER_PAIRS = [('pinky_metacarpal_r', 'pinky_metacarpal_l'), ('pinky_01_r', 'pinky_01_l'),
                ('pinky_02_r', 'pinky_02_l'), ('pinky_03_r', 'pinky_03_l'),
                ('ring_metacarpal_r', 'ring_metacarpal_l'), ('ring_01_r', 'ring_01_l'),
                ('ring_02_r', 'ring_02_l'), ('ring_03_r', 'ring_03_l'),
                ('middle_metacarpal_r', 'middle_metacarpal_l'), ('middle_01_r', 'middle_01_l'),
                ('middle_02_r', 'middle_02_l'), ('middle_03_r', 'middle_03_l'),
                ('index_metacarpal_r', 'index_metacarpal_l'), ('index_01_r', 'index_01_l'),
                ('index_02_r', 'index_02_l'), ('index_03_r', 'index_03_l'),
                ('thumb_01_r', 'thumb_01_l'), ('thumb_02_r', 'thumb_02_l'), ('thumb_03_r', 'thumb_03_l')]

report = {'runtime_tested': False, 'duration_s': DURATION, 'fps': FPS, 'layout': 'horizontal',
          'blade_yaw_deg': math.degrees(blade_yaw), 'lean_deg': LEAN_DEG,
          'grip_up_m': GRIP_UP_M, 'left_down_m': LEFT_DOWN_M,
          'position_scale': POSITION_SCALE, 'rotation_scale': ROTATION_SCALE,
          'source': str(sway_path)}

bpy.ops.wm.open_mainfile(filepath=str(blend))
scene = bpy.context.scene
rig = bpy.data.objects['SK_Harvest_Axe_Rig']
arms = bpy.data.objects['SK_Manny_Arms_Export']
tool = next(o for o in scene.objects if o.type == 'MESH' and o.name.startswith('Harvest_Axe'))

rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
local_rest = {b.name: (rest[b.parent.name].inverted() @ rest[b.name]) if b.parent else rest[b.name]
              for b in rig.data.bones}

# --- accepted single-hand pose: frame 0 of the shipped idle ---------------
rig.animation_data_create()
rig.animation_data.action = bpy.data.actions['A_Harvest_Axe_Idle']
scene.frame_set(0)
bpy.context.view_layer.update()
pose0 = {b.name: b.matrix.copy() for b in rig.pose.bones}
wpn0 = pose0['WPN_root']
grasp_r_at_grip = wpn0.inverted() @ pose0['hand_r']     # right hand relative to its grip point
right_relative = {n_r: pose0['hand_r'].inverted() @ pose0[n_r] for n_r, _ in FINGER_PAIRS}

# --- orient the tool for a horizontal carry --------------------------------
# WPN_root's local Z runs up the handle (toward the head). Reorient that axis so it lies across
# the body instead: first turn it to the player's side, then add the requested lean and blade yaw.
origin = wpn0.to_translation()
handle_up = (wpn0.to_3x3() @ Vector((0.0, 0.0, 1.0))).normalized()
target = Vector((HEAD_OUT_SIGN * math.cos(math.radians(LEAN_DEG)) * (1 if True else 0),
                 math.sin(math.radians(LEAN_DEG)) * 0.0,
                 math.sin(math.radians(LEAN_DEG))))
# Target handle direction: across the body (+X to the player's right) with a small upward lean,
# and tipped slightly forward so the head clears the arm silhouette.
target = Vector((HEAD_OUT_SIGN * math.cos(math.radians(LEAN_DEG)),
                 -0.10,
                 math.sin(math.radians(LEAN_DEG)))).normalized()
align = handle_up.rotation_difference(target).to_matrix().to_4x4()
# Keep the blade the requested way round about the new handle axis.
blade_spin = Matrix.Rotation(blade_yaw, 4, target)
ready_rotation = blade_spin @ align
ready = Matrix.Translation(origin) @ ready_rotation @ Matrix.Translation(-origin) @ wpn0

# --- where do the hands go on the handle? ---------------------------------
axis = (ready.to_3x3() @ Vector((0.0, 0.0, 1.0))).normalized()
grip_base = ready.to_translation()
# Both hands keep their accepted wrap relation, moved along the handle to the new heights.
def hand_at(along, side_source, mirrored):
    pose = pose0[side_source]
    if mirrored:
        normal = (wpn0.to_3x3() @ Vector((1.0, 0.0, 0.0))).normalized()
        linear = Matrix.Identity(3)
        for row in range(3):
            for column in range(3):
                linear[row][column] -= 2.0 * normal[row] * normal[column]
        plane_shift = 2.0 * normal * normal.dot(wpn0.to_translation())
        position = linear @ pose.to_translation() + plane_shift
        rotation = (linear @ pose.to_3x3() @ linear).to_quaternion()
        pose = Matrix.LocRotScale(position, rotation, Vector((1, 1, 1)))
    return Matrix.Translation(axis * along) @ pose


RIGHT_ALONG = GRIP_UP_M
LEFT_ALONG = GRIP_UP_M - LEFT_DOWN_M
hand_r_world = hand_at(RIGHT_ALONG, 'hand_r', False)
hand_l_world = hand_at(LEFT_ALONG, 'hand_r', True)
grasp_r = ready.inverted() @ hand_r_world
grasp_l = ready.inverted() @ hand_l_world

# Fingers: the right hand keeps the accepted curl. The left hand is the anatomical mirror of the
# right, so each left finger pose is the mirrored right finger pose expressed in the left hand's
# frame — one wrap, both hands.
mirror_normal = (wpn0.to_3x3() @ Vector((1.0, 0.0, 0.0))).normalized()
mirror_linear = Matrix.Identity(3)
for row in range(3):
    for column in range(3):
        mirror_linear[row][column] -= 2.0 * mirror_normal[row] * mirror_normal[column]
mirror_shift = 2.0 * mirror_normal * mirror_normal.dot(wpn0.to_translation())
left_relative = {}
for n_r, n_l in FINGER_PAIRS:
    source = pose0[n_r]
    position = mirror_linear @ source.to_translation() + mirror_shift
    rotation = (mirror_linear @ source.to_3x3() @ mirror_linear).to_quaternion()
    finger = Matrix.Translation(axis * LEFT_ALONG) @ Matrix.LocRotScale(position, rotation, Vector((1, 1, 1)))
    left_relative[n_l] = hand_l_world.inverted() @ finger

# --- reach math ------------------------------------------------------------
def slack(side, hand_position):
    anchor = rest['upperarm_' + side].translation
    span = ((rest['lowerarm_' + side].translation - anchor).length +
            (rest['hand_' + side].translation - rest['lowerarm_' + side].translation).length)
    return span - (hand_position - anchor).length, span


if shift_x is not None:
    GRIP_SHIFT_GOAL = Vector((shift_x, shift_y, shift_z))
report['grip_shift_goal'] = [round(v, 4) for v in GRIP_SHIFT_GOAL]

shift_table = []
chosen_t = None
for step in range(41):
    t = step / 40.0
    shift = GRIP_SHIFT_GOAL * t
    offset = ready.to_3x3() @ shift
    slack_r, span_r = slack('r', hand_r_world.to_translation() + offset)
    slack_l, span_l = slack('l', hand_l_world.to_translation() + offset)
    shift_table.append({'t': round(t, 2), 'right_slack_m': round(slack_r, 4), 'left_slack_m': round(slack_l, 4)})
    if chosen_t is None and slack_l >= REACH_MARGIN_M and slack_r >= REACH_MARGIN_M:
        chosen_t = t
if chosen_t is None:
    chosen_t = 1.0
grip_shift = GRIP_SHIFT_GOAL * chosen_t
ready = Matrix.Translation(grip_shift) @ ready
hand_r_world = Matrix.Translation(grip_shift) @ hand_r_world
hand_l_world = Matrix.Translation(grip_shift) @ hand_l_world
grip_base = ready.to_translation()
axis = (ready.to_3x3() @ Vector((0.0, 0.0, 1.0))).normalized()
grasp_r = ready.inverted() @ hand_r_world
grasp_l = ready.inverted() @ hand_l_world

report['chosen'] = {'t': round(chosen_t, 2), 'shift_m': [round(v, 4) for v in grip_shift],
                    'right_slack_m': round(slack('r', hand_r_world.to_translation())[0], 4),
                    'left_slack_m': round(slack('l', hand_l_world.to_translation())[0], 4),
                    'hand_separation_m': round((hand_l_world.to_translation() -
                                                hand_r_world.to_translation()).length, 4)}
report['shift_search'] = shift_table[::4]

# Sanity: both hands on the handle at the intended heights, opposite sides, thumbs up the handle.
for label, pose, side, along in [('right', hand_r_world, 'r', RIGHT_ALONG), ('left', hand_l_world, 'l', LEFT_ALONG)]:
    delta = pose.to_translation() - grip_base
    a = delta.dot(axis)
    perp = (delta - axis * a).length
    report.setdefault('checks', {})[label] = {'along_m': round(a, 4), 'perp_m': round(perp, 4), 'side_dot': None}
local_r = ready.inverted() @ hand_r_world
local_l = ready.inverted() @ hand_l_world
report['checks']['mirror'] = {
    'right_local_x': round(local_r.to_translation().x, 4),
    'left_local_x': round(local_l.to_translation().x, 4),
    'same_perp': round(abs(local_r.to_translation().y - local_l.to_translation().y), 4)}
compass = {'head_axis_world': [round(v, 4) for v in axis],
           'head_direction': 'player right (+X)' if axis.x > 0 else 'player left (-X)'}
report['orientation'] = compass

# --- ambient sway ----------------------------------------------------------
sway = json.loads(sway_path.read_text(encoding='utf-8'))
samples = sway['samples']
chest0_pos = Vector(samples[0]['Chest']['pos'])
chest0_quat = Quaternion(samples[0]['Chest']['quat'])
conversion = Matrix.Diagonal((-1.0, -1.0, 1.0, 1.0))
pivot = ready.to_translation()


def ambient(t):
    u = min(max(t / DURATION, 0.0), 1.0)
    x = u * (len(samples) - 1)
    i = min(int(x), len(samples) - 2)
    f = x - i
    position = Vector(samples[i]['Chest']['pos']).lerp(Vector(samples[i + 1]['Chest']['pos']), f) - chest0_pos
    delta = chest0_quat.inverted() @ Quaternion(samples[i]['Chest']['quat']).slerp(
        Quaternion(samples[i + 1]['Chest']['quat']), f)
    envelope = math.sin(math.pi * u) ** 2
    offset_position = conversion.to_3x3() @ position * (POSITION_SCALE * envelope)
    mapped = conversion.to_3x3() @ delta.to_matrix() @ conversion.to_3x3()
    offset_rotation = Quaternion().slerp(mapped.to_quaternion(), ROTATION_SCALE * envelope)
    return (Matrix.Translation(offset_position) @ Matrix.Translation(pivot)
            @ offset_rotation.to_matrix().to_4x4() @ Matrix.Translation(-pivot) @ ready)


# --- arm solver (same procedure as the accepted clips) ---------------------
def support(side, hand):
    upper, fore, wrist = [prefix + '_' + side for prefix in ['upperarm', 'lowerarm', 'hand']]
    anchor = rest[upper].translation
    tgt = hand.translation
    l1 = (rest[fore].translation - anchor).length
    l2 = (rest[wrist].translation - rest[fore].translation).length
    neutral = (hand.to_quaternion() @ rest[wrist].to_quaternion().inverted()) @ (rest[wrist].translation - rest[fore].translation).normalized()
    ideal = tgt - neutral * l2
    preferred = anchor + Vector((0, .07, -.02))
    shoulder = ideal + (preferred - ideal).normalized() * l1
    offset = shoulder - anchor
    offset.x = max(-.10, min(.10, offset.x))
    offset.y = max(-.04, min(.20, offset.y))
    offset.z = max(-.10, min(.08, offset.z))
    shoulder = anchor + offset
    direction = (tgt - shoulder).normalized()
    distance = (tgt - shoulder).length
    overstretch = 0.0
    if distance > l1 + l2 - .015:
        overstretch = distance - (l1 + l2 - .015)
        shoulder += direction * overstretch
        distance = (tgt - shoulder).length
    pole = ideal - shoulder
    pole -= direction * pole.dot(direction)
    down = Vector((.55 if side == 'r' else -.55, -.15, -1))
    down -= direction * down.dot(direction)
    pole = (pole.normalized() * .94 + down.normalized() * .06).normalized()
    along = (l1 * l1 - l2 * l2 + distance * distance) / (2 * distance)
    elbow = shoulder + direction * along + pole * math.sqrt(max(0., l1 * l1 - along * along))
    bend = (tgt - elbow).normalized().angle(neutral)
    return bend * bend * .045 + (shoulder - preferred).length_squared * 1.8, shoulder, elbow, tgt, overstretch


def solve_arm(p, side, hand, relatives):
    upper, fore, wrist = [prefix + '_' + side for prefix in ['upperarm', 'lowerarm', 'hand']]
    _, shoulder, elbow, tgt, overstretch = support(side, hand)
    overstretch_report[side] = max(overstretch_report.get(side, 0.0), overstretch)
    p['clavicle_' + side].translation += shoulder - rest[upper].translation
    for bone_name, start, end, old_end in [(upper, shoulder, elbow, rest[fore].translation),
                                           (fore, elbow, tgt, rest[wrist].translation)]:
        q = (old_end - rest[bone_name].translation).normalized().rotation_difference((end - start).normalized()) @ rest[bone_name].to_quaternion()
        p[bone_name] = Matrix.LocRotScale(start, q, Vector((1, 1, 1)))
    neutral = p[fore].to_quaternion() @ rest[fore].to_quaternion().inverted() @ rest[wrist].to_quaternion()
    delta = hand.to_quaternion() @ neutral.inverted()
    twist_axis = (tgt - elbow).normalized()
    twist = (2 * math.atan2(Vector((delta.x, delta.y, delta.z)).dot(twist_axis), delta.w) + math.pi) % (2 * math.pi) - math.pi
    previous = twist_history.get(side, twist)
    while twist - previous > math.pi:
        twist -= 2 * math.pi
    while twist - previous < -math.pi:
        twist += 2 * math.pi
    twist_history[side] = twist
    neutral_forearm = p[fore].copy()
    p[fore] = Matrix.LocRotScale(elbow, Quaternion(twist_axis, twist) @ neutral_forearm.to_quaternion(), Vector((1, 1, 1)))
    for prefix, parent in [('upperarm', upper), ('lowerarm', fore)]:
        for index in ['01', '02']:
            twist_name = f'{prefix}_twist_{index}_{side}'
            if twist_name not in rest:
                continue
            base = neutral_forearm if prefix == 'lowerarm' else p[parent]
            m = base @ rest[parent].inverted() @ rest[twist_name]
            if prefix == 'lowerarm':
                weight = (rest[twist_name].translation - rest[fore].translation).length / (rest[wrist].translation - rest[fore].translation).length
                m = Matrix.LocRotScale(m.translation, Quaternion(twist_axis, twist * weight) @ m.to_quaternion(), Vector((1, 1, 1)))
            p[twist_name] = m
    p[wrist] = hand
    for bone in rig.pose.bones:
        bone_name = bone.name
        if bone_name in relatives and bone_name.endswith('_' + side):
            location = p[bone.parent.name] @ local_rest[bone_name].translation
            p[bone_name] = Matrix.LocRotScale(location, hand.to_quaternion() @ relatives[bone_name].to_quaternion(), Vector((1, 1, 1)))


def apply_frame(tool_frame):
    p = {n: m.copy() for n, m in rest.items()}
    solve_arm(p, 'r', tool_frame @ grasp_r, right_relative)
    solve_arm(p, 'l', tool_frame @ grasp_l, left_relative)
    p['WPN_root'] = tool_frame
    for bone in rig.pose.bones:
        bone.matrix_basis = local_rest[bone.name].inverted() @ (p[bone.parent.name].inverted() @ p[bone.name] if bone.parent else p[bone.name])
    bpy.context.view_layer.update()


# --- bake ------------------------------------------------------------------
twist_history = {}
overstretch_report = {}
rig.data.pose_position = 'POSE'
action = bpy.data.actions.new(name)
action.use_fake_user = True
rig.animation_data.action = action
scene.render.fps = FPS
scene.render.fps_base = 1
scene.frame_start = 0
scene.frame_end = round(DURATION * FPS)
previous_quats = {}
tool_positions = []
for frame in range(scene.frame_end + 1):
    scene.frame_set(frame)
    tool_frame = ambient(frame / FPS)
    apply_frame(tool_frame)
    tool_positions.append(tool_frame.to_translation())
    for bone in rig.pose.bones:
        bone.rotation_mode = 'QUATERNION'
        q = bone.rotation_quaternion.copy()
        if bone.name in previous_quats and q.dot(previous_quats[bone.name]) < 0:
            q.negate()
        bone.rotation_quaternion = q
        previous_quats[bone.name] = q.copy()
        for property_name in ['location', 'rotation_quaternion', 'scale']:
            bone.keyframe_insert(property_name, frame=frame, group=bone.name)

report['tool_travel_m'] = [round(max(p[i] for p in tool_positions) - min(p[i] for p in tool_positions), 5) for i in range(3)]
report['max_overstretch_m'] = {k: round(v, 5) for k, v in overstretch_report.items()}
report['frames'] = scene.frame_end + 1

# --- previews --------------------------------------------------------------
if do_render:
    preview = out_dir / 'Preview'
    preview.mkdir(parents=True, exist_ok=True)
    keep = {arms.name, rig.name, tool.name}
    for obj in scene.objects:
        if obj.type in ('MESH', 'ARMATURE'):
            obj.hide_render = obj.name not in keep
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.display.shading.light = 'STUDIO'
    scene.display.shading.color_type = 'TEXTURE'
    scene.render.resolution_x = 960
    scene.render.resolution_y = 540
    camera_data = bpy.data.cameras.new('GameCam')
    camera_data.lens = 13.2
    camera_data.sensor_width = 36.0
    camera = bpy.data.objects.new('GameCam', camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.location = (-0.07, 0.0, 0.07)
    camera.rotation_euler = (math.radians(90.0), 0.0, 0.0)
    for frame in [0, 112, 225, 337, 449]:
        scene.frame_set(frame)
        scene.render.filepath = str(preview / f'game_f{frame:03d}.png')
        bpy.ops.render.render(write_still=True)
    camera_data.type = 'ORTHO'
    camera_data.ortho_scale = 1.45
    camera.location = pivot + Vector((0.35, -1.25, 0.10))
    camera.rotation_euler = (pivot - camera.location).to_track_quat('-Z', 'Y').to_euler()
    for frame in [0, 225]:
        scene.frame_set(frame)
        scene.render.filepath = str(preview / f'front_f{frame:03d}.png')
        bpy.ops.render.render(write_still=True)
    camera.location = pivot + Vector((1.25, -0.30, 0.10))
    camera.rotation_euler = (pivot - camera.location).to_track_quat('-Z', 'Y').to_euler()
    for frame in [0, 225]:
        scene.frame_set(frame)
        scene.render.filepath = str(preview / f'side_f{frame:03d}.png')
        bpy.ops.render.render(write_still=True)
    for obj in scene.objects:
        if obj.type in ('MESH', 'ARMATURE'):
            obj.hide_render = False

# --- save + export ---------------------------------------------------------
rig.animation_data.action = action
scene.frame_set(0)
blend_out = out_dir / f'{name}_Editable.blend'
for material in list(bpy.data.materials):
    if material.users == 0:
        bpy.data.materials.remove(material)
for image in list(bpy.data.images):
    if image.users == 0 or '.fbm' in (image.filepath or ''):
        bpy.data.images.remove(image)
try:
    bpy.ops.file.pack_all()
except RuntimeError as error:
    print('PACK_SKIPPED', error, flush=True)
bpy.ops.wm.save_as_mainfile(filepath=str(blend_out))

export_dir = out_dir / 'Export'
export_dir.mkdir(parents=True, exist_ok=True)
bpy.ops.object.select_all(action='DESELECT')
rig.hide_set(False)
rig.select_set(True)
bpy.context.view_layer.objects.active = rig
bpy.ops.export_scene.fbx(filepath=str(export_dir / f'{name}.fbx'), use_selection=True,
    object_types={'ARMATURE'}, axis_forward='-Y', axis_up='Z', add_leaf_bones=False,
    bake_anim=True, bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False,
    bake_anim_simplify_factor=0)
report['export'] = str(export_dir / f'{name}.fbx')
report['blend'] = str(blend_out)
(out_dir / f'{name}-build.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
print('HORIZONTAL_TWO_HAND_IDLE_BUILT')