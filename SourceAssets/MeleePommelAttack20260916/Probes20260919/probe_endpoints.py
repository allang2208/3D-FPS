"""Per-frame armature-space deltas at both clip ends, sign-flip safe.

Reports the recover tail and the clip entry of the authored blend so the elbow
plane release window can be tuned against measured numbers:

* `angle` from `rotation_difference` can come back as 2*pi - theta when a
  quaternion sign flip lands between two samples; fold anything > pi.
* Per-frame delta in degrees at 480 Hz equals deg/frame * 480 = deg/s.

Read-only: open, step, print. No export, no save.
"""
import bpy
import json
import math
from pathlib import Path

P = Path(__file__).parent
OUT = P / 'endpoint_profile.json'
BLEND = P / 'AzureRunesword_PommelStrikeV46.blend'

bpy.ops.wm.open_mainfile(filepath=str(BLEND))
rig = bpy.data.objects['SK_RuneSword_Rig']
scene = bpy.context.scene
FPS = scene.render.fps
LAST = int(rig.animation_data.action.frame_range[1])

BONES = ['hand_r', 'hand_l', 'lowerarm_r', 'lowerarm_l', 'upperarm_r', 'upperarm_l']
WINDOWS = {'entry': (0, 200), 'tail': (LAST - 200, LAST)}


def delta_deg(q_prev, q_now):
    a = math.degrees(q_prev.rotation_difference(q_now).angle)
    if a > 180.0:
        a = 360.0 - a
    return a


res = {'fps': FPS, 'last_frame': LAST, 'windows': {}}
for tag, (f0, f1) in WINDOWS.items():
    rows = []
    prev = {}
    for f in range(f0, f1 + 1):
        scene.frame_set(f)
        row = {'f': f, 't': round(f / FPS, 4)}
        for name in BONES:
            q = rig.pose.bones[name].matrix.to_quaternion()
            row[name] = round(delta_deg(prev[name], q), 4) if name in prev else 0.0
            prev[name] = q.copy()
        rows.append(row)
    res['windows'][tag] = rows

for tag, rows in res['windows'].items():
    print('==', tag)
    for name in BONES:
        sel = rows[1:]
        mx = max(sel, key=lambda r: r[name])
        med = sorted(r[name] for r in sel)[len(sel) // 2]
        print(f'  {name:12s} max={mx[name]:7.3f}deg/frame @f{mx["f"]:4d} (t={mx["t"]:.3f})  median={med:.3f}')

OUT.write_text(json.dumps(res, ensure_ascii=False), encoding='utf-8')
print('WROTE', OUT)