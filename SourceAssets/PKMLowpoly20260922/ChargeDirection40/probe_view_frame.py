"""Establish the PKM view frame and measure the current charge-hand approach."""
import json
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector

ROOT = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922')
HERE = ROOT / 'ChargeDirection40'
HERE.mkdir(exist_ok=True)
BLEND = ROOT / 'Charge34' / 'PKM_base_ChargePush_Editable.blend'
ACTION = 'PKM34_base_reload_empty'
FPS = 120

bpy.ops.wm.open_mainfile(filepath=str(BLEND))
scene = bpy.context.scene
rig = bpy.data.objects['PKM_Manny_Rig']
action = bpy.data.actions[ACTION]
rig.animation_data.action = action
rig.animation_data.action_slot = action.slots[0]
scene.render.fps = FPS
scene.render.fps_base = 1.0

names = [b.name for b in rig.data.bones]
interesting = [n for n in names if any(k in n.lower() for k in
                                       ('wpn', 'root', 'cam', 'charge', 'bolt', 'handle'))]
print('RIG_BONES', len(names))
print('INTERESTING', interesting)
print('RIGHT_ARM', [n for n in names if n.endswith('_r') and
                    any(k in n for k in ('clavicle', 'upperarm', 'lowerarm', 'hand'))])
print('LEFT_ARM', [n for n in names if n.endswith('_l') and
                   any(k in n for k in ('clavicle', 'upperarm', 'lowerarm', 'hand'))])

scene.frame_set(0)
bpy.context.view_layer.update()
for n in ['WPN_root'] + interesting[:14]:
    if n in rig.pose.bones:
        m = rig.pose.bones[n].matrix
        print('%-22s head %s' % (n, np.round(np.array(m.translation), 4)))

W = rig.pose.bones['WPN_root'].matrix
winv = W.inverted()
hl = rig.pose.bones['hand_l'].head
hr = rig.pose.bones['hand_r'].head
print('HAND_L in WPN space', np.round(np.array(winv @ hl), 4))
print('HAND_R in WPN space', np.round(np.array(winv @ hr), 4))
print('L->R in WPN space', np.round(np.array(winv @ hr - winv @ hl), 4))

rows = []
for frame in range(0, 793, 1):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    W = rig.pose.bones['WPN_root'].matrix
    winv = W.inverted()
    if 'PKM_Charge' in rig.pose.bones:
        ch = rig.pose.bones['PKM_Charge'].matrix.translation
    else:
        ch = None
    hr = rig.pose.bones['hand_r'].head
    he = rig.pose.bones['lowerarm_r'].head
    sh = rig.pose.bones['upperarm_r'].head
    rows.append({
        'frame': frame, 'sec': round(frame / FPS, 4),
        'hand_r': [round(v, 5) for v in (winv @ hr)],
        'elbow_r': [round(v, 5) for v in (winv @ he)],
        'shoulder_r': [round(v, 5) for v in (winv @ sh)],
        'charge': [round(v, 5) for v in (winv @ ch)] if ch else None,
    })

(HERE / 'charge_path.json').write_text(json.dumps(
    {'blend': str(BLEND), 'action': ACTION, 'fps': FPS,
     'bones': names, 'rows': rows}, indent=2), encoding='utf-8')

print('\nsec    hand_y   hand_z   hand_x | elbow_y elbow_z | charge_y charge_z')
for r in rows:
    if 4.9 <= r['sec'] <= 6.1 and abs(r['sec'] * 12 - round(r['sec'] * 12)) < 0.06:
        h, e, c = r['hand_r'], r['elbow_r'], r['charge']
        print('%5.2f  %7.3f %7.3f %7.3f | %7.3f %7.3f | %8.3f %8.3f' % (
            r['sec'], h[1], h[2], h[0], e[1], e[2],
            c[1] if c else float('nan'), c[2] if c else float('nan')))
print('CHARGE_PATH_DONE')