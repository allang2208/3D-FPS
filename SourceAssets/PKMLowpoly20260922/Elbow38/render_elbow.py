"""Before/after still of the PKM left elbow, twist spread only."""
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

bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'Wrist12' / 'PKM_WristContact_Editable.blend'))
scene = bpy.context.scene
rig = bpy.data.objects['PKM_Manny_Rig']
action = bpy.data.actions['PKM_Game_idle_Wrist12']
rig.animation_data.action = action
rig.animation_data.action_slot = action.slots[0]
scene.frame_set(0)
bpy.context.view_layer.update()
rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
parent = {b.name: (b.parent.name if b.parent else None) for b in rig.data.bones}
rest_local = {n: (rest[parent[n]].inverted() @ rest[n]) if parent[n] else rest[n] for n in rest}
pose = {b.name: b.matrix.copy() for b in rig.pose.bones}


def local_delta(name, world, parent_world):
    return rest_local[name].inverted() @ (parent_world.inverted() @ world)


def twist_angle(delta, axis):
    quat = delta.to_quaternion()
    if quat.w < 0.0:
        quat.negate()
    return math.degrees(2.0 * math.atan2(Vector((quat.x, quat.y, quat.z)).dot(axis), quat.w))


def limb_axis(name):
    direction = (rest['upperarm_l'].translation - rest['lowerarm_l'].translation).normalized()
    return (rest[name].to_3x3().inverted() @ direction).normalized()


cumulative = {}
running = 0.0
for name, _station in STATIONS:
    angle = twist_angle(local_delta(name, pose[name], pose[PARENT[name]]), limb_axis(name))
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

meshes = [ob for ob in scene.objects if ob.type == 'MESH']
for ob in scene.objects:
    ob.hide_render = ob not in meshes and ob is not rig
for ob in meshes:
    ob.hide_render = False
    ob.hide_set(False)
    ob.color = (0.72, 0.58, 0.48, 1)
scene.render.engine = 'BLENDER_WORKBENCH'
scene.display.shading.light = 'STUDIO'
scene.display.shading.color_type = 'OBJECT'
scene.display.shading.show_shadows = False
scene.render.resolution_x = 480
scene.render.resolution_y = 480
scene.render.image_settings.file_format = 'PNG'
elbow = rig.pose.bones['lowerarm_l'].matrix.translation
data = bpy.data.cameras.new('ElbowCam')
camera = bpy.data.objects.new('ElbowCam', data)
scene.collection.objects.link(camera)
camera.location = elbow + Vector((0.28, -0.22, 0.08))
camera.rotation_euler = (elbow - camera.location).to_track_quat('-Z', 'Y').to_euler()
data.lens = 50
scene.camera = camera
rig.hide_render = True
scene.render.filepath = str(OUT / 'idle_before.png')
bpy.ops.render.render(write_still=True)

rig.animation_data.action = None
for name in ('lowerarm_l', 'lowerarm_twist_01_l', 'lowerarm_twist_02_l'):
    bone = rig.pose.bones[name]
    bone.matrix = pose[name]
bpy.context.view_layer.update()
scene.render.filepath = str(OUT / 'idle_after.png')
bpy.ops.render.render(write_still=True)
print('ELBOW_STILLS', flush=True)
