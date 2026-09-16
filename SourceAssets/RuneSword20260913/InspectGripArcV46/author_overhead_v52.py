"""Author V52: the overhead chop matched to the reference segment 1:30-1:32.

The user pointed at BV1hCJFzQEyR 1:30-1:32.  Frames pulled from that segment
show the reference's overhead phase keeps the view usable: the weapon is up out
of frame and the hands sit high and *in front*, while the enemy and level stay
visible.  V51 instead carried the whole hold straight up, which parked the
forearms across the middle of the screen.

Two changes from V51, both about that reference read:

* the lift is now up *and forward* (0, +0.10, +0.28) instead of straight up, so
  the raised hands sit further from the lens and stop filling the view;
* the beat at the top is 0.45 s instead of 0.20 s, matching how long the
  reference holds its raised pose before the strike.

Poses and the rest of the clock are unchanged from V51.
"""
import bpy, json, math, sys
from pathlib import Path
from mathutils import Matrix, Quaternion, Vector

P = Path(__file__).parent
sys.path.insert(0, str(P))
sys.path.insert(0, str(P.parent / 'ChargedErgoV43'))
import twirl_model as model
import hold_shift

SOURCE = P.parent / 'ChargedErgoV43/AzureRunesword_ChargedHoldV45.blend'
OUT = P / 'ExportV52'
OUT.mkdir(exist_ok=True)
FPS = 120.0
TARGET_CLIP = 'A_RuneSword_Overhead'
CHARGING = 'A_RuneSword_HeavyCharge'
RELEASE = 'A_RuneSword_HeavyRelease'
RAISE_END = 1.00
SWEEP_ENTRY = 0.033
SWEEP_EXIT = 0.075
# Up, slightly away from the camera and towards the left of the view: the
# reference keeps the enemy and level visible while the weapon is raised, with
# the hands over at the left edge rather than across the middle of the screen.
LIFT = Vector((-0.14, 0.10, 0.26))

SEGMENTS = (
    (0.00, 0.45, CHARGING, 0.00, RAISE_END, 'source'),
    (0.45, 0.63, CHARGING, RAISE_END, RAISE_END, 'lift'),
    (0.63, 1.08, CHARGING, RAISE_END, RAISE_END, 'hold'),
    (1.08, 1.20, RELEASE, SWEEP_ENTRY, SWEEP_ENTRY, 'blend'),
    (1.20, 1.42, RELEASE, SWEEP_ENTRY, SWEEP_EXIT, 'source'),
    (1.42, 1.65, RELEASE, SWEEP_EXIT, 0.150, 'source'),
    (1.65, 2.50, RELEASE, 0.150, 1.000, 'source'),
    (2.50, 2.60, RELEASE, 1.000, 1.000, 'hold'),
)
TOTAL_SECONDS = 2.60


def smoothstep(value):
    value = max(0.0, min(1.0, value))
    return value * value * value * (value * (value * 6.0 - 15.0) + 10.0)


def segment_of(seconds):
    for start, end, clip, source_start, source_end, kind in SEGMENTS:
        if start <= seconds <= end:
            span = end - start
            weight = 0.0 if span <= 1e-9 else (seconds - start) / span
            return clip, source_start + (source_end - source_start) * weight, kind, weight
    last = SEGMENTS[-1]
    return last[2], last[4], last[5], 1.0


bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene = bpy.context.scene
rig = bpy.data.objects['SK_RuneSword_Rig']
mesh = bpy.data.objects['RuneSword_Blade']
source_fps = scene.render.fps / scene.render.fps_base
rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
parent = {b.name: (b.parent.name if b.parent else None) for b in rig.data.bones}
local_rest = {n: (rest[parent[n]].inverted() @ rest[n]) if parent[n] else rest[n]
              for n in rest}
geometry = model.sword_geometry(rest['WPN_root'], mesh)

held = bpy.data.actions[RELEASE]
ANIMATED = set()
for layer in held.layers:
    for strip in layer.strips:
        for bag in strip.channelbags:
            for curve in bag.fcurves:
                if curve.data_path.startswith('pose.bones["'):
                    ANIMATED.add(curve.data_path.split('"')[1])
BONES = tuple(b.name for b in rig.data.bones if b.name in ANIMATED)


def pose_at(clip, seconds):
    action = bpy.data.actions[clip]
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    frame = seconds * source_fps
    scene.frame_set(int(frame), subframe=frame - int(frame))
    bpy.context.view_layer.update()
    return {b.name: b.matrix.copy() for b in rig.pose.bones}


def lifted(pose, amount):
    if amount <= 0.0:
        return pose
    offset = LIFT * amount
    result = dict(pose)
    result['WPN_root'] = Matrix.LocRotScale(
        pose['WPN_root'].translation + offset, pose['WPN_root'].to_quaternion(),
        pose['WPN_root'].decompose()[2])
    for right in (False, True):
        solved, _ = hold_shift.solve_arm(pose, right, offset)
        result.update(solved)
    return result


def blend(first, second, weight):
    result = {}
    for name in BONES:
        al, aq, asc = first[name].decompose()
        bl, bq, bsc = second[name].decompose()
        if aq.dot(bq) < 0:
            bq.negate()
        result[name] = Matrix.LocRotScale(al.lerp(bl, weight),
                                          aq.slerp(bq, weight),
                                          asc.lerp(bsc, weight))
    return result


top_pose = lifted(pose_at(CHARGING, RAISE_END), 1.0)
entry_pose = pose_at(RELEASE, SWEEP_ENTRY)


def pose_for(seconds):
    clip, moment, kind, weight = segment_of(seconds)
    if kind == 'lift':
        return lifted(pose_at(CHARGING, RAISE_END), smoothstep(weight))
    if kind == 'hold':
        return top_pose if clip == CHARGING else pose_at(RELEASE, moment)
    if kind == 'blend':
        return blend(top_pose, entry_pose, smoothstep(weight))
    return pose_at(clip, moment)


frames = list(range(int(TOTAL_SECONDS * FPS) + 1))
seconds_list = [index / FPS for index in frames]
cache = {round(seconds, 6): pose_for(seconds) for seconds in seconds_list}

if TARGET_CLIP in bpy.data.actions:
    bpy.data.actions.remove(bpy.data.actions[TARGET_CLIP])
action = bpy.data.actions.new(TARGET_CLIP)
action.use_fake_user = True
rig.animation_data.action = action
if getattr(action, 'slots', None):
    rig.animation_data.action_slot = action.slots[0]

rows = []
previous = {}
max_step = 0.0
last_hand = None
for frame, seconds in zip(frames, seconds_list):
    pose = cache[round(seconds, 6)]
    for name in BONES:
        parent_name = parent[name]
        local = (pose[parent_name].inverted() @ pose[name]) if parent_name else pose[name]
        loc, quat, scale = (local_rest[name].inverted() @ local).decompose()
        if name in previous and quat.dot(previous[name]) < 0:
            quat.negate()
        previous[name] = quat.copy()
        bone = rig.pose.bones[name]
        bone.rotation_mode = 'QUATERNION'
        bone.location = loc
        bone.rotation_quaternion = quat
        bone.scale = scale
        for channel in ('location','rotation_quaternion','scale'):
            bone.keyframe_insert(channel, frame=frame, group=name)
    hand = pose['hand_r'].translation
    if last_hand is not None:
        max_step = max(max_step, (hand - last_hand).length)
    last_hand = hand.copy()
    if frame % 2 == 0:
        full = pose['WPN_root'] @ rest['WPN_root'].inverted()
        tip = full @ geometry['high']
        rows.append({'frame': frame, 'seconds': round(seconds, 4),
                     'hand_y': round(hand.y, 4), 'hand_z': round(hand.z, 4),
                     'tip_y': round(tip.y, 4), 'tip_z': round(tip.z, 4)})

for layer in action.layers:
    for strip in layer.strips:
        for bag in strip.channelbags:
            for curve in bag.fcurves:
                for key in curve.keyframe_points:
                    key.interpolation = 'LINEAR'

scene.render.fps = int(FPS)
scene.render.fps_base = 1.0
scene.frame_start, scene.frame_end = 0, frames[-1]
scene.frame_set(0)
bpy.ops.object.select_all(action='DESELECT')
rig.hide_set(False)
rig.select_set(True)
bpy.context.view_layer.objects.active = rig
bpy.ops.export_scene.fbx(
    filepath=str(OUT / (TARGET_CLIP + '.fbx')),
    use_selection=True, object_types={'ARMATURE'},
    axis_forward='-Y', axis_up='Z', add_leaf_bones=False,
    bake_anim=True, bake_anim_use_all_actions=False,
    bake_anim_use_nla_strips=False, bake_anim_simplify_factor=0)

hand_top = max(row['hand_z'] for row in rows)
hand_low = min(row['hand_z'] for row in rows)
report = {
    'revision': 'RuneSwordOverheadV52',
    'source': str(SOURCE), 'reference': 'BV1hCJFzQEyR 1:30-1:32',
    'clip': TARGET_CLIP, 'seconds': TOTAL_SECONDS, 'fps': FPS,
    'lift_vector': [round(v, 3) for v in LIFT],
    'segments': [{'my_seconds': [a, b], 'source_clip': clip.split('_')[-1],
                  'source_seconds': [c, d], 'kind': kind}
                 for a, b, clip, c, d, kind in SEGMENTS],
    'hand_z_range': [round(hand_low, 4), round(hand_top, 4)],
    'hand_vertical_travel_m': round(hand_top - hand_low, 4),
    'max_hand_step_per_frame_m': round(max_step, 4),
    'tip_z_range': [round(min(row['tip_z'] for row in rows), 4),
                    round(max(row['tip_z'] for row in rows), 4)],
    'samples': rows,
    'testing': 'No gameplay, PIE or acceptance run; user tests.',
}
(P / 'authoring_v52.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(P / 'AzureRunesword_OverheadV52.blend'))

print('V52 %.2f s, %d frames, hand z %.3f .. %.3f, max step/frame %.4f'
      % (TOTAL_SECONDS, len(frames), hand_low, hand_top, max_step))
print('RUNESWORD_OVERHEAD_V52_AUTHORED')
