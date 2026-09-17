"""Render the current Enter (left-hand retract) frames for review.

blender -b --python render_retract_review.py -- <Weapon> <Profile> <outdir>
Renders Enter frames [0, 6, 10, 14, 18] with the accepted sprint reference camera.
"""
import bpy
import json
import math
import sys
from pathlib import Path
from mathutils import Vector

O = Path(__file__).resolve().parent
S = O.parent
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
cam_data = bpy.data.cameras.new('RetractReview')
cam = bpy.data.objects.new('RetractReview', cam_data)
scene.collection.objects.link(cam)
cam.location = (-.07, -.06 if weapon == 'AKM' else 0, .07)
cam.rotation_euler = (math.pi / 2, 0, 0)
cam_data.type = 'PERSP'
cam_data.lens_unit = 'FOV'
cam_data.angle = math.radians(112)
cam_data.clip_start = .005
scene.camera = cam
for name, loc, power, size in [('key', (1, -1, 1), 180, 2), ('fill', (-1, 0, .5), 110, 2)]:
    data = bpy.data.lights.new(name, 'AREA')
    data.energy = power
    data.size = size
    light = bpy.data.objects.new(name, data)
    scene.collection.objects.link(light)
    light.location = loc
    light.rotation_euler = (Vector((0, .3, -.1)) - light.location).to_track_quat('-Z', 'Y').to_euler()
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 640
scene.render.resolution_y = 360
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
for frame in (0, 6, 10, 14, 18):
    pose('Enter', frame / 18.)
    scene.render.filepath = str(out / f'{weapon}-{profile}-enter-{frame:02d}.png')
    bpy.ops.render.render(write_still=True)
print('RETRACT_REVIEW_COMPLETE', weapon, profile)
