"""Right-hand approach to the PKM charging handle, in first-person view space.

Rig space is the viewmodel space: VM_Root sits at the origin, the barrel points
+Y, the ejection port and the right hand sit at -X, up is +Z.  Screen-right is
therefore -X, screen-up +Z, screen-depth +Y.
"""
import json
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922')
HERE = ROOT / 'ChargeDirection40'
BLEND = ROOT / 'Charge34' / 'PKM_base_ChargePush_Editable.blend'
ACTION = 'PKM34_base_reload_empty'
FPS = 120


def view(p):
    """(right, up, forward) with positive right = the player's right."""
    return np.array([-p[0], p[2], p[1]])


bpy.ops.wm.open_mainfile(filepath=str(BLEND))
scene = bpy.context.scene
rig = bpy.data.objects['PKM_Manny_Rig']
action = bpy.data.actions[ACTION]
rig.animation_data.action = action
rig.animation_data.action_slot = action.slots[0]
scene.render.fps = FPS
scene.render.fps_base = 1.0

rows = []
for frame in range(0, 793):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    pb = rig.pose.bones
    hr = view(pb['hand_r'].head)
    he = view(pb['lowerarm_r'].head)
    hs = view(pb['upperarm_r'].head)
    ch = view(pb['PKM_Charge'].head) if 'PKM_Charge' in pb else None
    hl = view(pb['hand_l'].head)
    rows.append({'frame': frame, 'sec': round(frame / FPS, 4),
                 'hand_r': [round(float(v), 5) for v in hr],
                 'elbow_r': [round(float(v), 5) for v in he],
                 'shoulder_r': [round(float(v), 5) for v in hs],
                 'hand_l': [round(float(v), 5) for v in hl],
                 'charge': [round(float(v), 5) for v in ch] if ch is not None else None})

(HERE / 'charge_view_path.json').write_text(json.dumps(
    {'blend': str(BLEND), 'action': ACTION, 'fps': FPS,
     'convention': 'right=-X, up=+Z, forward=+Y (rig space)', 'rows': rows},
    indent=2), encoding='utf-8')

print('  sec |   hand R    U    F  |  elbow R    U    F  | charge R    U    F')
for r in rows:
    if abs(r['sec'] * 20 - round(r['sec'] * 20)) < 0.02 and 4.40 <= r['sec'] <= 6.40:
        h, e, c = r['hand_r'], r['elbow_r'], r['charge']
        print('%5.2f | %6.3f %6.3f %6.3f | %6.3f %6.3f %6.3f | %6.3f %6.3f %6.3f' % (
            r['sec'], h[0], h[1], h[2], e[0], e[1], e[2], c[0], c[1], c[2]))

print('\n--- where the right hand sits, by phase ---')
phases = [('idle/rest', 0.0, 4.0), ('approach', 4.40, 5.10),
          ('contact', 5.10, 5.20), ('pull back', 5.20, 5.36),
          ('hold rear', 5.36, 5.48), ('push fwd', 5.48, 5.82),
          ('release', 5.82, 5.95), ('retreat', 5.95, 6.35)]
for label, a, b in phases:
    sel = [r for r in rows if a <= r['sec'] < b]
    if not sel:
        continue
    h = np.array([r['hand_r'] for r in sel])
    e = np.array([r['elbow_r'] for r in sel])
    print('%-11s hand R %6.3f..%6.3f  U %6.3f..%6.3f  F %6.3f..%6.3f | elbow R %6.3f..%6.3f U %6.3f..%6.3f'
          % (label, h[:, 0].min(), h[:, 0].max(), h[:, 1].min(), h[:, 1].max(),
             h[:, 2].min(), h[:, 2].max(), e[:, 0].min(), e[:, 0].max(),
             e[:, 1].min(), e[:, 1].max()))

print('\n--- approach detail, 1/20 s steps ---')
sel = [r for r in rows if 4.50 <= r['sec'] <= 5.20]
for r in sel[::6]:
    h = r['hand_r']
    print('%5.2f  hand R %6.3f  U %6.3f  F %6.3f' % (r['sec'], h[0], h[1], h[2]))
print('CHARGE_VIEW_DONE')