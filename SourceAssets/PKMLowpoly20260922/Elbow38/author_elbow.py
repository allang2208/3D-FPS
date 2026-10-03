"""Move PKM left-elbow twist off the elbow cap. Hands stay put."""
import bpy
import json
import math
from pathlib import Path
from mathutils import Matrix, Quaternion, Vector

ROOT = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922')
OUT = ROOT / 'Elbow38'
EXPORT = OUT / 'Exports'
EXPORT.mkdir(parents=True, exist_ok=True)
STATIONS = (
    ('lowerarm_l', 0.0),
    ('lowerarm_twist_02_l', 0.2739),
    ('lowerarm_twist_01_l', 0.8634),
    ('hand_l', 1.0),
)
PARENT = {
    'lowerarm_l': 'upperarm_l',
    'lowerarm_twist_02_l': 'lowerarm_l',
    'lowerarm_twist_01_l': 'lowerarm_l',
    'hand_l': 'lowerarm_l',
}
EDITED = (
    'upperarm_l', 'upperarm_twist_01_l', 'upperarm_twist_02_l',
    'lowerarm_l', 'lowerarm_twist_01_l', 'lowerarm_twist_02_l',
)


def gap(pose, rest):
    axis = (pose['hand_l'].translation - pose['lowerarm_l'].translation).normalized()
    rest_fore = (rest['hand_l'].translation - rest['lowerarm_l'].translation).normalized()
    up_delta = pose['upperarm_l'].to_quaternion() @ rest['upperarm_l'].to_quaternion().inverted()
    fore_delta = pose['lowerarm_l'].to_quaternion() @ rest['lowerarm_l'].to_quaternion().inverted()
    no_roll = (up_delta @ rest_fore).rotation_difference(axis) @ up_delta
    relative = fore_delta @ no_roll.inverted()
    vector = Vector((relative.x, relative.y, relative.z))
    angle = 2.0 * math.atan2(vector.dot(axis), relative.w)
    return math.degrees((angle + math.pi) % (2.0 * math.pi) - math.pi)


def roll_shoulder(pose, rest):
    axis = (pose['lowerarm_l'].translation - pose['upperarm_l'].translation).normalized()

    def metric(degrees):
        trial = dict(pose)
        trial['upperarm_l'] = Matrix.LocRotScale(
            pose['upperarm_l'].translation,
            Quaternion(axis, math.radians(degrees)) @ pose['upperarm_l'].to_quaternion(),
            pose['upperarm_l'].to_scale())
        return abs(gap(trial, rest))

    samples = [(metric(deg), deg) for deg in range(-95, 96, 5)]
    best = min(value for value, _deg in samples)
    chosen = min((deg for value, deg in samples if value <= best + 1.0), key=abs)
    turn = Quaternion(axis, math.radians(chosen))
    pose['upperarm_l'] = Matrix.LocRotScale(
        pose['upperarm_l'].translation, turn @ pose['upperarm_l'].to_quaternion(),
        pose['upperarm_l'].to_scale())
    for name in ('upperarm_twist_01_l', 'upperarm_twist_02_l'):
        pose[name] = Matrix.LocRotScale(
            pose[name].translation, turn @ pose[name].to_quaternion(), pose[name].to_scale())
    return chosen


def local_delta(rest_local, world, parent_world):
    return rest_local.inverted() @ (parent_world.inverted() @ world)


def twist_angle(delta, axis):
    quat = delta.to_quaternion()
    if quat.w < 0.0:
        quat.negate()
    return math.degrees(2.0 * math.atan2(Vector((quat.x, quat.y, quat.z)).dot(axis), quat.w))


def limb_axis(rest, name):
    direction = (rest['upperarm_l'].translation - rest['lowerarm_l'].translation).normalized()
    return (rest[name].to_3x3().inverted() @ direction).normalized()


def spread_forearm(pose, rest, rest_local):
    cumulative = {}
    running = 0.0
    local = {}
    for name, _station in STATIONS:
        axis = limb_axis(rest, name)
        angle = twist_angle(local_delta(rest_local[name], pose[name], pose[PARENT[name]]), axis)
        local[name] = angle
        running += angle
        cumulative[name] = running
    total = cumulative['hand_l']
    axis = (pose['hand_l'].translation - pose['lowerarm_l'].translation).normalized()
    for name, station in STATIONS:
        if name == 'hand_l':
            continue
        delta = station * total - cumulative[name]
        pose[name] = Matrix.LocRotScale(
            pose[name].translation,
            Quaternion(axis, math.radians(delta)) @ pose[name].to_quaternion(),
            pose[name].to_scale())
    return local['lowerarm_l'], total


def channels(world, parent_world, rest_local):
    loc, quat, scale_value = (rest_local.inverted() @ (parent_world.inverted() @ world)).decompose()
    return loc, quat, scale_value


def repair_clip(blend, action_name, fps, dest):
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    scene = bpy.context.scene
    rig = bpy.data.objects['PKM_Manny_Rig']
    source = bpy.data.actions[action_name]
    rig.animation_data.action = source
    rig.animation_data.action_slot = source.slots[0]
    scene.render.fps = int(fps)
    scene.render.fps_base = 1.0
    rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
    parent = {b.name: (b.parent.name if b.parent else None) for b in rig.data.bones}
    rest_local = {
        name: (rest[parent[name]].inverted() @ rest[name]) if parent[name] else rest[name]
        for name in rest
    }
    start, end = map(int, source.frame_range)
    sampled = []
    for frame in range(start, end + 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        sampled.append({b.name: b.matrix.copy() for b in rig.pose.bones})
    before = []
    after = []
    hand_drift = 0.0
    action = source.copy()
    action.name = action_name + '_Elbow38'
    action.use_fake_user = True
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in list(bag.fcurves):
                    if any('"%s"' % name in curve.data_path for name in EDITED):
                        bag.fcurves.remove(curve)
    previous = {}
    for frame, pose in enumerate(sampled, start):
        original = {n: m.copy() for n, m in pose.items()}
        hand_before = pose['hand_l'].copy()
        gap_before = gap(pose, rest)
        elbow_before, _total = spread_forearm(pose, rest, rest_local)
        gap_after = gap(pose, rest)
        if abs(gap_after) > abs(gap_before) + 1.0:
            pose = original
            gap_after = gap_before
        drift = (pose['hand_l'].translation - hand_before.translation).length
        orient = pose['hand_l'].to_quaternion().rotation_difference(hand_before.to_quaternion()).angle
        hand_drift = max(hand_drift, drift, orient)
        if frame % max(1, int(fps)) == 0:
            before.append(round(gap_before, 2))
            after.append(round(gap_after, 2))
        parent_world = {}
        for name in EDITED:
            parent_name = parent[name]
            parent_matrix = pose[parent_name]
            if parent_name in parent_world:
                parent_matrix = parent_world[parent_name]
            loc, quat, scale_value = channels(pose[name], parent_matrix, rest_local[name])
            if name in previous and quat.dot(previous[name]) < 0.0:
                quat.negate()
            previous[name] = quat.copy()
            bone = rig.pose.bones[name]
            bone.rotation_mode = 'QUATERNION'
            bone.location = loc
            bone.rotation_quaternion = quat
            bone.scale = scale_value
            parent_world[name] = parent_matrix @ rest_local[name] @ Matrix.LocRotScale(loc, quat, scale_value)
            for channel in ('location', 'rotation_quaternion', 'scale'):
                bone.keyframe_insert(channel, frame=frame, group=name)
        if frame % 120 == 0:
            print('ELBOW38', action_name, frame, 'gap', round(gap_before, 1), '->', round(gap_after, 1),
                  'elbow_twist', round(elbow_before, 1), flush=True)
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    if any('"%s"' % name in curve.data_path for name in EDITED):
                        for key in curve.keyframe_points:
                            key.interpolation = 'LINEAR'
    scene.frame_start, scene.frame_end = start, end
    scene.frame_set(start)
    bpy.ops.object.select_all(action='DESELECT')
    rig.hide_set(False)
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.export_scene.fbx(
        filepath=str(dest), use_selection=True, object_types={'ARMATURE'},
        axis_forward='-Y', axis_up='Z', add_leaf_bones=False,
        bake_anim=True, bake_anim_use_all_actions=False,
        bake_anim_use_nla_strips=False, bake_anim_simplify_factor=0)
    return {
        'action': action_name, 'frames': end - start + 1,
        'gap_before_deg': before, 'gap_after_deg': after,
        'max_hand_drift': hand_drift,
    }


report = {
    'idle': repair_clip(
        ROOT / 'Wrist12' / 'PKM_WristContact_Editable.blend',
        'PKM_Game_idle_Wrist12', 60, EXPORT / 'A_PKM_idle.fbx'),
    'reload': repair_clip(
        ROOT / 'Reload16' / 'PKM_base_Reload_Editable.blend',
        'PKM16_base_reload', 120, EXPORT / 'A_PKM_reload.fbx'),
    'reload_empty': repair_clip(
        ROOT / 'Charge34' / 'PKM_base_ChargePush_Editable.blend',
        'PKM34_base_reload_empty', 120, EXPORT / 'A_PKM_reload_empty.fbx'),
}
(OUT / 'authoring.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('ELBOW38_AUTHORED', flush=True)
