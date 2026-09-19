"""Verify the V47 recover fix against the V46 baseline.

Same measurement on both blends so the numbers are directly comparable:
per-frame armature-space rotation deltas of the six arm bones at 480 Hz, focused
on the recover tail and the clip entry, plus the idle endpoint continuity.

Read-only.
"""
import bpy
import json
import math
from pathlib import Path

P = Path(__file__).parent
OUT = P / 'recover_fix_verify.json'
BASELINE = P / 'Before/AzureRunesword_PommelStrikeV46_pre-recover-fix-20260919.blend'
FIXED = P / 'AzureRunesword_PommelStrikeV47.blend'

BONES = ['hand_r', 'hand_l', 'lowerarm_r', 'lowerarm_l', 'upperarm_r', 'upperarm_l']
IDLE_WINDOW = (1.45, 1.60)
ENTRY_WINDOW = (0.0, 0.25)


def delta_deg(q_prev, q_now):
    a = math.degrees(q_prev.rotation_difference(q_now).angle)
    return 360.0 - a if a > 180.0 else a


def profile(path, label):
    bpy.ops.wm.open_mainfile(filepath=str(path))
    rig = bpy.data.objects['SK_RuneSword_Rig']
    scene = bpy.context.scene
    fps = scene.render.fps
    last = int(rig.animation_data.action.frame_range[1])
    prev = {}
    rows = []
    for f in range(0, last + 1):
        scene.frame_set(f)
        row = {'f': f, 't': round(f / fps, 4)}
        for b in BONES:
            q = rig.pose.bones[b].matrix.to_quaternion()
            row[b] = round(delta_deg(prev[b], q), 4) if b in prev else 0.0
            prev[b] = q.copy()
        rows.append(row)
    res = {'label': label, 'fps': fps, 'last': last, 'rows': rows}
    for tag, (t0, t1) in (('tail', IDLE_WINDOW), ('entry', ENTRY_WINDOW)):
        res[tag] = {}
        for b in BONES:
            sel = [r[b] for r in rows if t0 <= r['t'] <= t1]
            res[tag][b] = {'max': round(max(sel), 3), 'last': round(sel[-1], 3),
                           'sum': round(sum(sel), 2)}
    res['whole'] = {b: round(max(r[b] for r in rows[1:]), 3) for b in BONES}
    return res


base = profile(BASELINE, 'V46_baseline')
fixed = profile(FIXED, 'V47_recover_fix')
OUT.write_text(json.dumps({'baseline': base, 'fixed': fixed}, ensure_ascii=False), encoding='utf-8')

print('bone          V46 tail_max  V47 tail_max   V46 entry_max  V47 entry_max   V46 whole  V47 whole')
for b in BONES:
    print('%-11s %10.3f  %11.3f   %12.3f  %13.3f   %8.3f  %8.3f'
          % (b, base['tail'][b]['max'], fixed['tail'][b]['max'],
             base['entry'][b]['max'], fixed['entry'][b]['max'],
             base['whole'][b], fixed['whole'][b]))
print('-- V47 recover tail, per-frame deg (f%d..%d) --' % (fixed['last'] - 72, fixed['last']))
for b in ('upperarm_r', 'lowerarm_r', 'upperarm_l', 'lowerarm_l'):
    sel = [r for r in fixed['rows'] if r['f'] >= fixed['last'] - 72]
    print('%-11s' % b, ' '.join('%.2f' % r[b] for r in sel))
print('-- V46 recover tail, same frames --')
for b in ('upperarm_r', 'lowerarm_r', 'upperarm_l', 'lowerarm_l'):
    sel = [r for r in base['rows'] if r['f'] >= base['last'] - 72]
    print('%-11s' % b, ' '.join('%.2f' % r[b] for r in sel))
print('WROTE', OUT)