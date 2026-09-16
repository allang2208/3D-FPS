"""Author V46: the Inspect with the forearm pronation spread along the forearm.

Reads the shipped V42 source, rebuilds the right forearm chain frame by frame,
and writes a new Inspect action.  Only the forearm bones' roll changes: every
bone head keeps its position and ``hand_r`` keeps its world orientation, so the
grip, the sword path, the sword's rotation and the 2.90 s timing are identical
to V42.
"""
import bpy, json, math, sys
from pathlib import Path
from mathutils import Matrix, Quaternion, Vector

P = Path(__file__).parent
sys.path.insert(0, str(P))
import inspect_arm_roll as arm

SOURCE = P.parent / 'OffscreenLeftInspectV42/AzureRunesword_OffscreenLeftInspectV42.blend'
OUT = P / 'Export'
OUT.mkdir(exist_ok=True)
FPS = 120.0
CLIP = 'A_RuneSword_Inspect'

bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene = bpy.context.scene
rig = bpy.data.objects['SK_RuneSword_Rig']
rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
parent = {b.name: (b.parent.name if b.parent else None) for b in rig.data.bones}
local_rest = {n: (rest[parent[n]].inverted() @ rest[n]) if parent[n] else rest[n]
              for n in rest}

source = bpy.data.actions[CLIP]
rig.animation_data.action = source
rig.animation_data.action_slot = source.slots[0]
start, end = map(int, source.frame_range)
count = end - start + 1

# Pass 1: read every authored pose BEFORE the action is rewritten.  Reading and
# keying in one pass would evaluate the partly rebuilt action and corrupt the
# source pose from the first keyed frame onwards.
poses = []
for offset in range(count):
    scene.frame_set(start + offset)
    bpy.context.view_layer.update()
    poses.append({b.name: b.matrix.copy() for b in rig.pose.bones})

source.name = 'RETAINED_V42_' + CLIP
source.use_fake_user = True
action = source.copy()
action.name = CLIP
action.use_fake_user = True
rig.animation_data.action = action
rig.animation_data.action_slot = action.slots[0]


def edited_curve(curve):
    return any(curve.data_path.startswith('pose.bones["' + n + '"].')
               for n in arm.EDITED)


for layer in action.layers:
    for strip in layer.strips:
        for bag in strip.channelbags:
            for curve in list(bag.fcurves):
                if edited_curve(curve):
                    bag.fcurves.remove(curve)

# Pass 2: build, key, record.
rows = []
for offset, pose in enumerate(poses):
    frame = start + offset
    seconds = offset / FPS
    weight = arm.envelope(seconds)
    built, info = arm.build(pose, local_rest, rest, weight)

    previous_quat = {}
    for name in arm.EDITED:
        parent_name = arm.PARENT_OF[name]
        parent_matrix = built.get(parent_name, pose[parent_name])
        local = parent_matrix.inverted() @ built[name]
        loc, quat, scale = (local_rest[name].inverted() @ local).decompose()
        if name in previous_quat and quat.dot(previous_quat[name]) < 0:
            quat.negate()
        previous_quat[name] = quat.copy()
        bone = rig.pose.bones[name]
        bone.rotation_mode = 'QUATERNION'
        bone.location = loc
        bone.rotation_quaternion = quat
        bone.scale = scale
        for channel in ('location', 'rotation_quaternion', 'scale'):
            bone.keyframe_insert(channel, frame=frame, group=name)

    if offset % 2 == 0:
        head_error = max((built[n].translation - pose[n].translation).length
                         for n in arm.EDITED)
        hand_angle = max(
            (built[arm.bones(side)['hand']].to_quaternion()
             @ pose[arm.bones(side)['hand']].to_quaternion().inverted()
             ).to_axis_angle()[1] for side in arm.SIDES)
        rows.append({
            'frame': frame, 'seconds': round(seconds, 4), 'weight': round(weight, 4),
            'elbow_twist_before': {s: round(info[s]['elbow_twist_before'], 2)
                                   for s in arm.SIDES},
            'elbow_twist_after': {s: round(info[s]['elbow_twist_after'], 2)
                                  for s in arm.SIDES},
            'profile_after': {s: {n: round(v, 2) for n, v in
                                  info[s]['profile_after'].items()} for s in arm.SIDES},
            'head_error_mm': round(head_error * 1000.0, 6),
            'hand_rotation_error_deg': round(math.degrees(hand_angle), 8)})

for layer in action.layers:
    for strip in layer.strips:
        for bag in strip.channelbags:
            for curve in bag.fcurves:
                if edited_curve(curve):
                    for key in curve.keyframe_points:
                        key.interpolation = 'LINEAR'

scene.render.fps = int(FPS)
scene.render.fps_base = 1.0
scene.frame_start, scene.frame_end = start, end
scene.frame_set(start)

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
    'revision': 'InspectGripArcV46',
    'source': str(SOURCE),
    'clip': CLIP, 'frames': [start, end], 'seconds': (end - start) / FPS, 'fps': FPS,
    'edited_bones': list(arm.EDITED),
    'profile': {side: [{'bone': name, 'station': station}
                       for name, station in arm.PROFILE[side]] for side in arm.SIDES},
    'envelope': {'rise_seconds': [0.0, 0.25], 'fall_seconds': [2.65, 2.90]},
    'preserved': {
        'bone_head_error_mm_max': max(r['head_error_mm'] for r in rows),
        'hand_rotation_error_deg_max': max(r['hand_rotation_error_deg'] for r in rows),
    },
    'elbow_twist': {side: {
        'before_max_abs': max(abs(r['elbow_twist_before'][side]) for r in rows),
        'after_max_abs': max(abs(r['elbow_twist_after'][side]) for r in rows),
        'after_max_abs_in_working_range': max(
            abs(r['elbow_twist_after'][side]) for r in rows if r['weight'] >= 0.999),
    } for side in arm.SIDES},
    'samples': rows,
    'method': ('The forearm pronation of both arms is rebuilt as a cumulative roll '
               'profile over lowerarm_*, lowerarm_twist_02_*, lowerarm_twist_01_* and '
               'hand_* at '
               'their measured dominant-skin stations 0.000 / 0.274 / 0.863 / 1.000, '
               'expressed in rig space (swing-twist split) so there is no +-180 '
               'reference-frame wrap. The elbow cap keeps only swing, the twist '
               'helpers that hold 1636 forearm vertices carry the gradient, and '
               'hand_* keeps its authored world orientation, so the grip, the sword, '
               'the silhouette and the timing are unchanged. The envelope is zero at '
               'both idle seams, so Idle, Slash, Guard and Equip are untouched.'),
    'testing': 'No gameplay, PIE, render or acceptance run performed; user tests.',
}
(P / 'authoring.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(P / 'AzureRunesword_InspectGripArcV46.blend'))

for side in arm.SIDES:
    entry = report['elbow_twist'][side]
    print('V46 %s elbow twist max %.1f -> %.1f deg (working range %.1f)'
          % (side, entry['before_max_abs'], entry['after_max_abs'],
             entry['after_max_abs_in_working_range']))
print('V46 head error max %.6f mm' % report['preserved']['bone_head_error_mm_max'])
print('V46 hand error max %.8f deg' % report['preserved']['hand_rotation_error_deg_max'])
print('INSPECT_GRIP_ARC_V46_AUTHORED')
