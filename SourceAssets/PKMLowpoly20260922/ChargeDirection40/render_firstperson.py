"""Render the true first-person view of the PKM empty reload.

Camera mapping comes from Framing11/read_handle.py:
    camera_cm = (rig_y*100 + 9, rig_x*100 + 9, rig_z*100 - 11)
with the current PKM anchor (9, 9, -11).  So the camera sits at rig
(-0.09, -0.09, 0.11), looks along rig +Y, right is rig +X, up is rig +Z.
Vertical FOV 75 degrees, 16:9, matching the running character.
"""
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector

ROOT = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922')
HERE = ROOT / 'ChargeDirection40'
ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
TAG = ARGS[0] if ARGS else 'base'

BLENDS = {
    'base': (ROOT / 'Charge34' / 'PKM_base_ChargePush_Editable.blend',
             'PKM34_base_reload_empty'),
    'before': (ROOT / 'Charge34' / 'BeforeImport' / 'PKM_base_ChargePush_Editable.blend',
               'PKM34_base_reload_empty'),
}
BLEND, ACTION = BLENDS[TAG]
OUT = HERE / 'Review' / TAG
# During a reload the viewmodel is framed by M4ActionViewmodelLocation, not the
# hip anchor: HipFraming = Lerp(hip, action, M4ActionFramingAlpha) -> (10, 0, -5).
ANCHOR = (10.0, 0.0, -5.0)
SENSOR = np.radians(75.0)

bpy.ops.wm.open_mainfile(filepath=str(BLEND))
scene = bpy.context.scene
rig = bpy.data.objects['PKM_Manny_Rig']
action = bpy.data.actions[ACTION]
rig.animation_data.action = action
rig.animation_data.action_slot = action.slots[0]
scene.render.fps = 120
scene.render.fps_base = 1.0

cam_data = bpy.data.cameras.new('FPS')
cam_data.sensor_fit = 'VERTICAL'
cam_data.angle = SENSOR
cam = bpy.data.objects.new('FPS', cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
cam_pos = Vector((-ANCHOR[1] / 100.0, -ANCHOR[0] / 100.0, -ANCHOR[2] / 100.0))
rot = Matrix(((1.0, 0.0, 0.0, 0.0),
              (0.0, 0.0, -1.0, 0.0),
              (0.0, 1.0, 0.0, 0.0),
              (0.0, 0.0, 0.0, 1.0)))
cam.matrix_world = Matrix.Translation(cam_pos) @ rot
print('CAMERA at rig', tuple(round(v, 4) for v in cam_pos))

# arm + weapon only
KEEP = ('SK_Manny_Arms_Export',)
for ob in bpy.data.objects:
    if ob.type != 'MESH':
        continue
    keep = ob.name in KEEP or ('mechanical_bone' in ob and not ob.name.startswith('New_')) \
        or ob.name.startswith('New_')
    ob.hide_render = not keep

scene.render.engine = 'BLENDER_WORKBENCH'
scene.display.shading.light = 'STUDIO'
scene.display.shading.color_type = 'SINGLE'
scene.display.shading.single_color = (0.62, 0.62, 0.62)
scene.display.shading.show_shadows = True
scene.display.shading.show_cavity = True
scene.display.shading.cavity_type = 'BOTH'
scene.render.image_settings.file_format = 'PNG'
scene.render.resolution_x, scene.render.resolution_y = 960, 540

OUT.mkdir(parents=True, exist_ok=True)
FRAMES = [0, 24, 48, 60, 72, 84, 96, 108, 120, 144, 168, 192, 240, 288]
rows = []
for f in FRAMES:
    scene.frame_set(f)
    bpy.context.view_layer.update()
    pb = rig.pose.bones

    def cam_cm(v):
        return np.array([v[1] * 100 + ANCHOR[0], v[0] * 100 + ANCHOR[1],
                         v[2] * 100 + ANCHOR[2]])

    hr = cam_cm(pb['hand_r'].head)
    he = cam_cm(pb['lowerarm_r'].head)
    ch = cam_cm(pb['PKM_Charge'].head)
    # screen projection, vertical FOV 75 deg, 16:9
    def screen(p):
        d = p[0]
        if d <= 0.01:
            return (float('nan'), float('nan'))
        h = d * np.tan(SENSOR / 2.0)
        w = h * (16.0 / 9.0)
        return ((p[1] / w), (p[2] / h))
    sh, se, sc = screen(hr), screen(he), screen(ch)
    rows.append({'frame': f, 'sec': round(f / 120.0, 3),
                 'hand_cam': [round(v, 2) for v in hr],
                 'elbow_cam': [round(v, 2) for v in he],
                 'charge_cam': [round(v, 2) for v in ch],
                 'hand_screen': [round(v, 3) for v in sh],
                 'elbow_screen': [round(v, 3) for v in se],
                 'charge_screen': [round(v, 3) for v in sc]})
    scene.render.filepath = str(OUT / ('fp_%04d.png' % f))
    bpy.ops.render.render(write_still=True)

import json
(HERE / ('fps_view_%s.json' % TAG)).write_text(json.dumps(
    {'blend': str(BLEND), 'action': ACTION, 'anchor': ANCHOR,
     'note': 'camera cm: X forward, Y right, Z up; screen coords are '
             'fractions of half-width / half-height',
     'rows': rows}, indent=2), encoding='utf-8')

print('\n  sec | hand fwd  right    up   | screen x    y   | elbow screen x    y'
      ' | charge screen x    y')
for r in rows:
    h, e, c = r['hand_cam'], r['elbow_cam'], r['charge_cam']
    hs, es, cs = r['hand_screen'], r['elbow_screen'], r['charge_screen']
    print('%5.2f | %6.1f %6.1f %6.1f | %7.2f %7.2f | %7.2f %7.2f | %7.2f %7.2f' % (
        r['sec'], h[0], h[1], h[2], hs[0], hs[1], es[0], es[1], cs[0], cs[1]))
print('FPS_VIEW_DONE', TAG)