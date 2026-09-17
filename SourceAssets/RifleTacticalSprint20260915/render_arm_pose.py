"""Render a third-person view of the fully retracted left arm for comparison.

blender -b --python render_arm_pose.py -- <Weapon> <Profile> <outdir>
One frame at Enter progress 1.0 == Loop start, camera looking at the left arm.
"""
import bpy
import json
import math
import sys
from mathutils import Vector
from pathlib import Path

O = Path(__file__).resolve().parent
weapon, profile, outdir = sys.argv[sys.argv.index('--') + 1:sys.argv.index('--') + 4]
out = O / outdir
out.mkdir(parents=True, exist_ok=True)
folder = O / weapon / profile
info = json.loads((folder / 'authoring.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(folder / f'{weapon}_TacticalSprint_{profile}_Editable.blend'))
rig = bpy.data.objects['SK_M4_Infima']
scene = bpy.context.scene


def pose(kind, t):
    a = bpy.data.actions[info['clips'][kind]['action']]
    rig.animation_data.action = a
    rig.animation_data.action_slot = a.slots[0]
    f = t * info['clips'][kind]['duration'] * 60
    scene.frame_set(int(f), subframe=f - int(f))
    bpy.context.view_layer.update()


for ob in scene.objects:
    if ob.type in ('CAMERA', 'LIGHT'):
        ob.hide_render = True
    elif ob.type == 'MESH':
        keeps = [m for m in ob.modifiers if m.type == 'ARMATURE' and m.object and m.object.name == rig.name]
        if not keeps:
            ob.hide_render = True
world = scene.world
if world and world.use_nodes:
    for node in world.node_tree.nodes:
        if node.type == 'BACKGROUND':
            node.inputs[0].default_value = (.05, .05, .05, 1.)
            node.inputs[1].default_value = 1.
cam_data = bpy.data.cameras.new('ArmReview')
cam = bpy.data.objects.new('ArmReview', cam_data)
scene.collection.objects.link(cam)
cam.location = (.42, -.42, -.08)
look = Vector((-.18, .02, -.42))
cam.rotation_euler = (look - cam.location).to_track_quat('-Z', 'Y').to_euler()
cam_data.type = 'PERSP'
cam_data.lens = 50.
cam_data.clip_start = .005
scene.camera = cam
for name, loc, power, size in [('key', (1, -1, 1), 300, 2), ('fill', (-1, 0, .5), 160, 2)]:
    data = bpy.data.lights.new(name, 'AREA')
    data.energy = power
    data.size = size
    light = bpy.data.objects.new(name, data)
    scene.collection.objects.link(light)
    light.location = loc
    light.rotation_euler = (look - light.location).to_track_quat('-Z', 'Y').to_euler()
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 640
scene.render.resolution_y = 480
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
pose('Enter', 1.)
scene.render.filepath = str(out / f'{weapon}-{profile}-retracted-arm.png')
bpy.ops.render.render(write_still=True)
print('ARM_REVIEW_COMPLETE', weapon, profile)
