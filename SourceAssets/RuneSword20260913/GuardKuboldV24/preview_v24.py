"""Render V24 guard clips from the game camera (author check only):
blender -b --factory-startup --python preview_v24.py -- <blend> <out_dir> <action> <frame,frame,...>
Camera: viewmodel origin looking +Y, Z up, 75 deg vertical FOV, 16:9 at 960x540 (same as InspectReverseV85/render_review.py).
"""
import math
import sys
from pathlib import Path

import bpy

argv = sys.argv[sys.argv.index('--') + 1:]
blend, out_dir, action_name, frames = Path(argv[0]), Path(argv[1]), argv[2], [int(v) for v in argv[3].split(',')]
bpy.ops.wm.open_mainfile(filepath=str(blend))
s = bpy.context.scene
rig = bpy.data.objects['SK_RuneSword_Rig']
rig.animation_data.action = bpy.data.actions[action_name]
rig.animation_data.action_slot = rig.animation_data.action.slots[0]
arms = next(o for o in s.objects if o.type == 'MESH' and o.name.startswith('V7_'))
blade = bpy.data.objects['RuneSword_Blade']
for o in s.objects:
    o.hide_render = o not in (arms, blade)
arms.color = (.64, .39, .27, 1)
blade.color = (.78, .80, .84, 1)
s.render.engine = 'BLENDER_WORKBENCH'
sh = s.display.shading
sh.light, sh.color_type, sh.show_shadows, sh.show_cavity, sh.cavity_type = 'STUDIO', 'OBJECT', True, True, 'BOTH'
sh.background_type = 'WORLD'
s.world.color = (.10, .09, .08)
s.render.resolution_x, s.render.resolution_y, s.render.resolution_percentage = 960, 540, 100
s.render.image_settings.file_format = 'PNG'
s.render.film_transparent = False
cd = bpy.data.cameras.new('ReviewCam')
cam = bpy.data.objects.new('ReviewCam', cd)
s.collection.objects.link(cam)
s.camera = cam
cam.location = (0, 0, 0)
cam.rotation_euler = (math.pi / 2, 0, 0)
cd.sensor_fit, cd.sensor_height = 'VERTICAL', 24
cd.lens = 24 / (2 * math.tan(math.radians(75 / 2)))
cd.clip_start = .005
out_dir.mkdir(parents=True, exist_ok=True)
for f in frames:
    s.frame_set(f)
    bpy.context.view_layer.update()
    s.render.filepath = str(out_dir / ('%s_f%04d.png' % (action_name, f)))
    bpy.ops.render.render(write_still=True)
print('PREVIEW_V24_RENDERED', action_name, len(frames), out_dir)
