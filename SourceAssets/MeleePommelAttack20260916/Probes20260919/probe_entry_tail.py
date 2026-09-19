"""Measure the clip ENTRY (first 0.25 s) per-frame deltas from the authored blend.

Companion to the UE-side 480 Hz tail probe: the recover tail pulse traced to the
elbow-plane zero-correction ramp in `arm_solver.separate_arms` (12 frames). This
script checks whether the same 12-frame ramp produces a matching pulse at the
start of the clip, so the fix covers every endpoint that ramps the correction.

Read-only: opens the blend, steps frames, prints. No export, no save.
"""
import bpy
import json
import math
from pathlib import Path

P = Path(__file__).parent
OUT = P / 'entry_tail_probe.json'
BLEND = P / 'AzureRunesword_PommelStrikeV46.blend'

bpy.ops.wm.open_mainfile(filepath=str(BLEND))
rig = bpy.data.objects['SK_RuneSword_Rig']
scene = bpy.context.scene
FPS = scene.render.fps

BONES = ['hand_r', 'hand_l', 'lowerarm_r', 'lowerarm_l', 'upperarm_r', 'upperarm_l']
WINDOWS = {'entry': (0, 120), 'end': (648, 768)}

res = {'fps': FPS, 'windows': {}}
for tag, (f0, f1) in WINDOWS.items():
    rows = []
    prev = {}
    for f in range(f0, f1 + 1):
        scene.frame_set(f)
        row = {'f': f, 't': round(f / FPS, 4)}
        for name in BONES:
            pb = rig.pose.bones.get(name)
            m = pb.matrix.copy()
            q = m.to_quaternion()
            if name in prev:
                row[name] = round(math.degrees(prev[name].rotation_difference(q).angle), 4)
            else:
                row[name] = 0.0
            prev[name] = q
        rows.append(row)
    res['windows'][tag] = rows

for tag, rows in res['windows'].items():
    print('==', tag)
    for name in BONES:
        sel = [r for r in rows if r['f'] > rows[0]['f']]
        mx = max(sel, key=lambda r: r[name])
        print(f'  {name:12s} max={mx[name]:.3f}deg/frame @f{mx["f"]} (t={mx["t"]})')

OUT.write_text(json.dumps(res, ensure_ascii=False), encoding='utf-8')
print('WROTE', OUT)