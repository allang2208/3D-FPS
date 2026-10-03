"""The bones that hold the weapon must be bit-identical after Elbow42.

Only the three forearm twist helpers are allowed to move; hand_l and every finger
bone hang off lowerarm_l but must keep their world matrices exactly.
"""
import json
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922')
CASES = [('shipped', ROOT / 'Elbow39' / 'Edit' / 'PKM_idle_Elbow39.blend',
          'PKM_idle_Elbow39'),
         ('elbow42', ROOT / 'Elbow42' / 'Edit' / 'PKM_idle_Elbow42.blend',
          'PKM_idle_Elbow42')]
RAMPED = ('lowerarm_l', 'lowerarm_twist_02_l', 'lowerarm_twist_01_l')

captured = {}
for tag, blend, action_name in CASES:
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    scene = bpy.context.scene
    rig = bpy.data.objects['PKM_Manny_Rig']
    act = bpy.data.actions[action_name]
    rig.animation_data.action = act
    rig.animation_data.action_slot = act.slots[0]
    scene.render.fps = 60
    start, end = map(int, act.frame_range)
    names = [b.name for b in rig.pose.bones]
    frames = []
    for frame in range(start, end + 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        frames.append({n: np.array(rig.pose.bones[n].matrix) for n in names})
    captured[tag] = (names, frames)
    print('%-8s frames %d bones %d' % (tag, len(frames), len(names)))

names, a = captured['shipped']
_, b = captured['elbow42']

worst = {}
for n in names:
    m = 0.0
    for fa, fb in zip(a, b):
        m = max(m, float(np.abs(fa[n] - fb[n]).max()))
    if m > 1e-9:
        worst[n] = m

print('\nbones whose world matrix changed at all (over the whole clip):')
for n, m in sorted(worst.items(), key=lambda kv: -kv[1]):
    print('  %-26s %.3e   %s' % (n, m, 'RAMPED (intended)' if n in RAMPED else '*** UNEXPECTED ***'))

GripBones = [n for n in names if n.startswith(('hand_', 'thumb_', 'index_', 'middle_',
                                               'ring_', 'pinky_'))
             or 'WPN' in n or n in ('root', 'VM_Root', 'PKM_Charge')]
gm = max((worst.get(n, 0.0) for n in GripBones), default=0.0)
print('\ngrip/hand/weapon bones checked: %d' % len(GripBones))
print('max world matrix delta on any of them: %.3e' % gm)
print('unexpected movers: %s' % ([n for n in worst if n not in RAMPED] or 'none'))

print('\nhand chain (world position of hand_l, metres), shipped vs elbow42:')
for i in (0, len(a) // 2, len(a) - 1):
    pa = a[i]['hand_l'][:3, 3]
    pb = b[i]['hand_l'][:3, 3]
    print('  frame %3d  %s  |  %s   delta %.3e'
          % (i, np.round(pa, 6).tolist(), np.round(pb, 6).tolist(),
             float(np.abs(pa - pb).max())))

(ROOT / 'Elbow42' / 'grip_check.json').write_text(json.dumps(
    {'changed_bones': worst, 'grip_max_delta': gm,
     'unexpected': [n for n in worst if n not in RAMPED]}, indent=2), encoding='utf-8')
print('\nGRIP_CHECK_DONE')