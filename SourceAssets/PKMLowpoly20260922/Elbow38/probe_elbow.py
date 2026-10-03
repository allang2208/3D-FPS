"""Measure the live PKM left-elbow twist on idle and reload."""
import bpy
import json
import math
from pathlib import Path
from mathutils import Matrix, Quaternion, Vector

ROOT = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922')
OUT = ROOT / 'Elbow38'
OUT.mkdir(exist_ok=True)


def gap(pose, rest):
    up, lo, hand = 'upperarm_l', 'lowerarm_l', 'hand_l'
    axis = (pose[hand].translation - pose[lo].translation).normalized()
    rest_fore = (rest[hand].translation - rest[lo].translation).normalized()
    up_delta = pose[up].to_quaternion() @ rest[up].to_quaternion().inverted()
    fore_delta = pose[lo].to_quaternion() @ rest[lo].to_quaternion().inverted()
    no_roll = (up_delta @ rest_fore).rotation_difference(axis) @ up_delta
    relative = fore_delta @ no_roll.inverted()
    vector = Vector((relative.x, relative.y, relative.z))
    angle = 2.0 * math.atan2(vector.dot(axis), relative.w)
    return math.degrees((angle + math.pi) % (2.0 * math.pi) - math.pi)


def twist_on(pose, rest, name, axis_world):
    delta = pose[name].to_quaternion() @ rest[name].to_quaternion().inverted()
    local_axis = (rest[name].to_3x3().inverted() @ axis_world).normalized()
    q = delta
    if q.w < 0.0:
        q = q.inverted()
        q.negate() if False else None
    vector = Vector((q.x, q.y, q.z))
    return math.degrees(2.0 * math.atan2(vector.dot(local_axis), q.w))


def sample(path, action_name, times, fps):
    bpy.ops.wm.open_mainfile(filepath=str(path))
    scene = bpy.context.scene
    rig = bpy.data.objects['PKM_Manny_Rig']
    action = bpy.data.actions[action_name]
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
    rows = []
    for seconds in times:
        frame = seconds * fps
        scene.frame_set(int(frame), subframe=frame - int(frame))
        bpy.context.view_layer.update()
        pose = {b.name: b.matrix.copy() for b in rig.pose.bones}
        axis = (pose['hand_l'].translation - pose['lowerarm_l'].translation).normalized()
        rows.append({
            'seconds': seconds,
            'elbow_gap_deg': round(gap(pose, rest), 2),
            'lowerarm_twist_deg': round(twist_on(pose, rest, 'lowerarm_l', axis), 2),
            'twist01_deg': round(twist_on(pose, rest, 'lowerarm_twist_01_l', axis), 2),
            'twist02_deg': round(twist_on(pose, rest, 'lowerarm_twist_02_l', axis), 2),
        })
    return rows


report = {
    'idle': sample(
        ROOT / 'Wrist12' / 'PKM_WristContact_Editable.blend',
        'PKM_Game_idle_Wrist12', [0.0], 60.0),
}
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'Reload16' / 'PKM_base_Reload_Editable.blend'))
report['reload_action_names'] = [a.name for a in bpy.data.actions if 'PKM16_base' in a.name]
report['reload'] = sample(
    ROOT / 'Reload16' / 'PKM_base_Reload_Editable.blend',
    'PKM16_base_reload', [0.0, 1.2, 2.0, 3.5, 6.4], 120.0)
report['reload_empty'] = sample(
    ROOT / 'Reload16' / 'PKM_base_Reload_Editable.blend',
    'PKM16_base_reload_empty', [0.0, 1.25, 2.2, 4.0, 6.5], 120.0)
(OUT / 'probe_elbow.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('ELBOW_PROBE_DONE')
