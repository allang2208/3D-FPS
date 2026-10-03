"""Left-arm path through the PKM reloads, in first-person screen space.

Camera basis follows Framing11/read_handle.py, corrected for the framing the
game actually uses while a reload plays:
    HipFraming = Lerp(hip(9,9,-11), M4ActionViewmodelLocation(10,0,-5), alpha)
so a reload is framed at (10, 0, -5) cm.  Camera space is X forward, Y right,
Z up; screen coords are fractions of the half-width / half-height at 75 deg
vertical FOV, 16:9.
"""
import json
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922')
HERE = ROOT / 'ChargeDirection40'
ANCHOR = np.array([10.0, 0.0, -5.0])
HALF_V = np.tan(np.radians(75.0) / 2.0)
HALF_H = HALF_V * 16.0 / 9.0

CLIPS = (
    ('reload_empty', ROOT / 'Charge34' / 'PKM_base_ChargePush_Editable.blend',
     'PKM34_base_reload_empty', 120),
    ('reload', ROOT / 'Reload16' / 'PKM_base_Reload_Editable.blend',
     'PKM16_base_reload', 120),
)


def cam(p):
    return np.array([p[1] * 100 + ANCHOR[0], p[0] * 100 + ANCHOR[1],
                     p[2] * 100 + ANCHOR[2]])


def screen(p):
    if p[0] <= 1.0:
        return (float('nan'), float('nan'))
    return (p[1] / (p[0] * HALF_H), p[2] / (p[0] * HALF_V))


out = {}
for key, blend, action_name, fps in CLIPS:
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    scene = bpy.context.scene
    rig = bpy.data.objects['PKM_Manny_Rig']
    action = bpy.data.actions[action_name]
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    scene.render.fps = fps
    scene.render.fps_base = 1.0
    start, end = map(int, action.frame_range)

    rows = []
    for frame in range(start, end + 1, 6):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        pb = rig.pose.bones
        rec = {'frame': frame, 'sec': round(frame / fps, 3)}
        for side in ('l', 'r'):
            for bone, tag in (('hand_%s' % side, 'hand'),
                              ('lowerarm_%s' % side, 'elbow'),
                              ('upperarm_%s' % side, 'shoulder')):
                c = cam(np.array(pb[bone].head))
                s = screen(c)
                rec['%s_%s' % (tag, side)] = [round(float(v), 3) for v in c]
                rec['%s_%s_scr' % (tag, side)] = [round(float(v), 3) for v in s]
        rows.append(rec)
    out[key] = {'blend': str(blend), 'action': action_name, 'fps': fps,
                'frames': [start, end], 'rows': rows}

    print('\n=== %s  (%s, %d..%d @ %d Hz) ===' % (key, action_name, start, end, fps))
    print('  sec |  L hand  scr x     y  |  L elbow scr x     y  |  R hand  scr x     y')
    for r in rows:
        hl, el, hr = r['hand_l_scr'], r['elbow_l_scr'], r['hand_r_scr']
        print('%5.2f | %8.2f %6.2f | %8.2f %6.2f | %8.2f %6.2f' % (
            r['sec'], hl[0], hl[1], el[0], el[1], hr[0], hr[1]))

    # where does the left hand sit lowest / most central -> the "from below" read
    low = [r for r in rows if abs(r['hand_l_scr'][0]) < 0.35 and r['hand_l_scr'][1] < -0.5]
    print('  left hand low+central frames: %d of %d' % (len(low), len(rows)))
    if low:
        print('    span %.2f..%.2f s' % (low[0]['sec'], low[-1]['sec']))

(HERE / 'left_arm_view_path.json').write_text(json.dumps(out, indent=2),
                                              encoding='utf-8')
print('\nLEFT_ARM_PATH_DONE')