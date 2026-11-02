"""Viewmodel-camera review renders of an Inspect Blend (author check only, never saved).

blender -b --factory-startup --python render_review.py -- <blend> <out_dir> <step_frames> [--hand] [--frames=a,b,c]
Camera: rig origin looking +Y, Z up, 75 deg vertical FOV, 16:9 (as the earlier source studies).
--hand renders a 2x closer crop camera aimed at the right hand instead.
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index('--') + 1:]
blend, out_dir, step = Path(argv[0]), Path(argv[1]), int(argv[2])
frames_arg = next((a.split('=', 1)[1] for a in argv if a.startswith('--frames=')), None)
bpy.ops.wm.open_mainfile(filepath=str(blend))
s = bpy.context.scene
rig = bpy.data.objects['SK_RuneSword_Rig']
arms = next(o for o in s.objects if o.type == 'MESH' and o.name.startswith('V7_'))
blade = bpy.data.objects['RuneSword_Blade']
for o in s.objects:
    o.hide_render = o not in (arms, blade)
arms.color = (.64, .39, .27, 1)
blade.color = (.40, .57, .72, 1)
s.render.engine = 'BLENDER_WORKBENCH'
sh = s.display.shading
sh.light, sh.color_type, sh.show_shadows, sh.show_cavity, sh.cavity_type = 'STUDIO', 'OBJECT', True, True, 'BOTH'
sh.background_type = 'WORLD'
s.world.color = (.045, .052, .068)
s.render.resolution_x, s.render.resolution_y, s.render.resolution_percentage = 960, 540, 100
s.render.image_settings.file_format = 'PNG'
cd = bpy.data.cameras.new('ReviewCam')
cam = bpy.data.objects.new('ReviewCam', cd)
s.collection.objects.link(cam)
s.camera = cam
cam.location = (0, 0, 0)
cam.rotation_euler = (math.pi / 2, 0, 0)
cd.sensor_fit, cd.sensor_height = 'VERTICAL', 24
cd.lens = 24 / (2 * math.tan(math.radians(75 / 2)))
cd.clip_start = .005
if '--hand' in argv:
    cd.lens *= 2.2
TANV, ASPECT = math.tan(math.radians(75 / 2)), 16 / 9
out_dir.mkdir(parents=True, exist_ok=True)
wb = rig.data.bones['WPN_root']
pts = [v.co.copy() for v in blade.data.vertices]
lo = min(pts, key=lambda p: p.z)
hi = max(pts, key=lambda p: p.z)


def ndc(p):
    return p.x / (p.y * TANV * ASPECT), p.z / (p.y * TANV)


rows = []
action = rig.animation_data.action
last = int(action.frame_range[1])
frames = [int(f) for f in frames_arg.split(',')] if frames_arg else list(range(0, last + 1, step))
for f in frames:
    s.frame_set(f)
    bpy.context.view_layer.update()
    if '--hand' in argv:
        h = rig.matrix_world @ rig.pose.bones['hand_r'].head
        cam.rotation_euler = h.to_track_quat('-Z', 'Y').to_euler()
    mw = rig.matrix_world @ rig.pose.bones['WPN_root'].matrix @ wb.matrix_local.inverted() @ blade.matrix_world
    a, b = ndc(mw @ lo), ndc(mw @ hi)
    hand = rig.matrix_world @ rig.pose.bones['hand_r'].head
    rows.append({'frame': f, 't': f / 120.0, 'hand_ndc': ndc(hand),
                 'blade_screen_deg': math.degrees(math.atan2(b[1] - a[1], (b[0] - a[0]) * ASPECT))})
    s.render.filepath = str(out_dir / f'f{f:04d}.png')
    bpy.ops.render.render(write_still=True)
(out_dir / 'measure.json').write_text(json.dumps(rows, indent=1))
print('REVIEW_RENDERED', len(rows), out_dir)
