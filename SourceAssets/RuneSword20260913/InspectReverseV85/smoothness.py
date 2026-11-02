"""Per-frame angular step (deg per 1/120 s) of the arm, hand, finger and sword bones of an Inspect Blend.

blender -b --factory-startup --python smoothness.py -- <blend> <out.json>
Flags single-frame pops: a step larger than 2.5x the mean of its neighbours and > 4 deg.
"""
import json
import sys
from pathlib import Path

import bpy

argv = sys.argv[sys.argv.index('--') + 1:]
bpy.ops.wm.open_mainfile(filepath=argv[0])
s = bpy.context.scene
rig = bpy.data.objects['SK_RuneSword_Rig']
act = rig.animation_data.action
last = int(act.frame_range[1])
names = [n for n in ('upperarm_r', 'lowerarm_r', 'lowerarm_twist_01_r', 'lowerarm_twist_02_r', 'hand_r', 'WPN_root',
                     'index_01_r', 'middle_01_r', 'ring_01_r', 'pinky_01_r', 'thumb_01_r', 'thumb_02_r',
                     'upperarm_l', 'lowerarm_l', 'hand_l') if n in rig.pose.bones]
prev, steps = {}, {n: [] for n in names}
loc_steps = {n: [] for n in ('hand_r', 'lowerarm_r', 'upperarm_r', 'WPN_root')}
prev_loc = {}
for f in range(last + 1):
    s.frame_set(f)
    for n in names:
        m = rig.pose.bones[n].matrix
        q = m.to_quaternion()
        if n in prev:
            a = prev[n].rotation_difference(q).angle * 57.29578
            steps[n].append(min(a, 360.0 - a))  # q and -q are the same rotation
        prev[n] = q
        if n in loc_steps:
            if n in prev_loc:
                loc_steps[n].append((m.translation - prev_loc[n]).length * 1000.0)
            prev_loc[n] = m.translation.copy()
report = {}
for n, st in steps.items():
    pops = []
    for i in range(1, len(st) - 1):
        around = 0.5 * (st[i - 1] + st[i + 1])
        if st[i] > 4.0 and st[i] > 2.5 * max(around, 0.5):
            pops.append((round((i + 1) / 120.0, 3), round(st[i], 2), round(around, 2)))
    k = max(range(len(st)), key=lambda i: st[i])
    report[n] = {'max_step_deg': round(st[k], 2), 'at_s': round((k + 1) / 120.0, 3), 'pops': pops[:8]}
for n, st in loc_steps.items():
    k = max(range(len(st)), key=lambda i: st[i])
    report[n]['max_move_mm'] = round(st[k], 2)
    report[n]['move_at_s'] = round((k + 1) / 120.0, 3)
Path(argv[1]).write_text(json.dumps(report, indent=1))
print('SMOOTHNESS', json.dumps(report))
