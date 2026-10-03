"""Elbow-camera frames of the PKM left-arm fix for review GIFs."""
import bpy
import math
from pathlib import Path
from mathutils import Matrix, Quaternion, Vector

ROOT = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922')
OUT = ROOT / 'Elbow38' / 'Review'
OUT.mkdir(parents=True, exist_ok=True)
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


def spread(pose, rest, rest_local):
    def twist_angle(delta, axis):
        quat = delta.to_quaternion()
        if quat.w < 0.0:
            quat.negate()
        return math.degrees(2.0 * math.atan2(Vector((quat.x, quat.y, quat.z)).dot(axis), quat.w))

    cumulative = {}
    running = 0.0
    for name, _station in STATIONS:
        direction = (rest['upperarm_l'].translation - rest['lowerarm_l'].translation).normalized()
        axis = (rest[name].to_3x3().inverted() @ direction).normalized()
        delta = rest_local[name].inverted() @ (pose[PARENT[name]].inverted() @ pose[name])
        running += twist_angle(delta, axis)
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


def maybe_fix(pose, rest, rest_local):
    original = {name: matrix.copy() for name, matrix in pose.items()}
    before = gap(pose, rest)
    spread(pose, rest, rest_local)
    if abs(gap(pose, rest)) > abs(before) + 1.0:
        return original
    return pose


def prepare(scene, rig):
    arms = bpy.data.objects.get('SK_Manny_Arms_Export')
    for ob in scene.objects:
        show = ob is arms
        ob.hide_render = not show
        if show:
            ob.hide_set(False)
            ob.color = (0.72, 0.58, 0.48, 1)
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.display.shading.light = 'STUDIO'
    scene.display.shading.color_type = 'OBJECT'
    scene.display.shading.show_shadows = False
    scene.render.resolution_x = 480
    scene.render.resolution_y = 360
    scene.render.image_settings.file_format = 'PNG'
    data = bpy.data.cameras.new('ElbowCam')
    camera = bpy.data.objects.new('ElbowCam', data)
    scene.collection.objects.link(camera)
    data.lens = 48
    scene.camera = camera
    rig.hide_render = True
    return camera


def aim(camera, rig):
    elbow = rig.pose.bones['lowerarm_l'].matrix.translation
    camera.location = elbow + Vector((0.32, -0.18, 0.06))
    camera.rotation_euler = (elbow - camera.location).to_track_quat('-Z', 'Y').to_euler()


def shoot(scene, folder, index):
    scene.render.filepath = str(folder / ('frame_%03d.png' % index))
    bpy.ops.render.render(write_still=True)


def render_clip(blend, action_name, fps, step, folder, fix):
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    scene = bpy.context.scene
    rig = bpy.data.objects['PKM_Manny_Rig']
    action = bpy.data.actions[action_name]
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
    parent = {b.name: (b.parent.name if b.parent else None) for b in rig.data.bones}
    rest_local = {n: (rest[parent[n]].inverted() @ rest[n]) if parent[n] else rest[n] for n in rest}
    order = []
    pending = set(rest)
    while pending:
        for name in list(pending):
            if parent[name] is None or parent[name] not in pending:
                order.append(name)
                pending.remove(name)
    camera = prepare(scene, rig)
    folder.mkdir(parents=True, exist_ok=True)
    start, end = map(int, action.frame_range)
    index = 0
    frame = start
    while frame <= end:
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        pose = {b.name: b.matrix.copy() for b in rig.pose.bones}
        if fix:
            pose = maybe_fix(pose, rest, rest_local)
        rig.animation_data.action = None
        for name in order:
            rig.pose.bones[name].matrix = pose[name]
        bpy.context.view_layer.update()
        aim(camera, rig)
        shoot(scene, folder, index)
        rig.animation_data.action = action
        rig.animation_data.action_slot = action.slots[0]
        index += 1
        frame += step
    print('ELBOW_GIF_FRAMES', folder.name, index, flush=True)


render_clip(
    ROOT / 'Wrist12' / 'PKM_WristContact_Editable.blend',
    'PKM_Game_idle_Wrist12', 60, 60,
    OUT / 'idle_before', False)
render_clip(
    ROOT / 'Wrist12' / 'PKM_WristContact_Editable.blend',
    'PKM_Game_idle_Wrist12', 60, 60,
    OUT / 'idle_after', True)
render_clip(
    ROOT / 'Reload16' / 'PKM_base_Reload_Editable.blend',
    'PKM16_base_reload', 120, 15,
    OUT / 'reload', True)
render_clip(
    ROOT / 'Charge34' / 'PKM_base_ChargePush_Editable.blend',
    'PKM34_base_reload_empty', 120, 15,
    OUT / 'reload_empty', True)
print('ELBOW_GIF_RENDERED', flush=True)
