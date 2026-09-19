"""Whole-clip per-frame armature-space deltas of the SHIPPED pommel bake.

Answers "which peaks are authored motion and which are artefacts" by measuring
the actual clip that is in the game (AzureRunesword_PommelStrikeV46.blend), not
a re-solve:

  * max delta and its frame, for each arm bone
  * the delta profile over the recover half (0.98 s -> 1.60 s), sampled
  * the profile around 1.05-1.15 s (the withdraw whip) to see whether the fast
    pull-back is authored

Read-only.
"""
import bpy
import json
import math
from pathlib import Path

P = Path(__file__).parent
OUT = P / 'shipped_profile.json'

bpy.ops.wm.open_mainfile(filepath=str(P / 'AzureRunesword_PommelStrikeV46.blend'))
rig = bpy.data.objects['SK_RuneSword_Rig']
scene = bpy.context.scene
FPS = scene.render.fps
LAST = int(rig.animation_data.action.frame_range[1])

BONES = ['hand_r', 'hand_l', 'lowerarm_r', 'lowerarm_l', 'upperarm_r', 'upperarm_l']


def delta_deg(q_prev, q_now):
    a = math.degrees(q_prev.rotation_difference(q_now).angle)
    return 360.0 - a if a > 180.0 else a


prev = {}
rows = []
for f in range(0, LAST + 1):
    scene.frame_set(f)
    row = {'f': f, 't': round(f / FPS, 4)}
    for b in BONES:
        q = rig.pose.bones[b].matrix.to_quaternion()
        row[b] = round(delta_deg(prev[b], q), 4) if b in prev else 0.0
        prev[b] = q.copy()
    rows.append(row)

summary = {}
for b in BONES:
    sel = rows[1:]
    mx = max(sel, key=lambda r: r[b])
    summary[b] = {'max': mx[b], 'f': mx['f'], 't': mx['t'],
                  'max_after_1s': max((r[b] for r in sel if r['t'] >= 1.0), default=0),
                  'max_tail': max((r[b] for r in sel if r['t'] >= 1.45), default=0),
                  'last': rows[-1][b]}

OUT.write_text(json.dumps({'rows': rows, 'summary': summary}, ensure_ascii=False), encoding='utf-8')
print('FPS', FPS, 'LAST', LAST)
for b, v in summary.items():
    print('%-11s max=%7.3f @f%4d (t=%.3f)  after1s=%7.3f  tail(>=1.45)=%7.3f  last=%.3f'
          % (b, v['max'], v['f'], v['t'], v['max_after_1s'], v['max_tail'], v['last']))
print('--- withdraw hand/lowerarm profile 480..600 every 6 ---')
for b in ('hand_r', 'lowerarm_r', 'upperarm_r'):
    print('%-11s' % b, ' '.join('%.2f' % rows[f][b] for f in range(480, 601, 6)))
print('--- recover profile 600..768 every 8 ---')
for b in ('hand_r', 'lowerarm_r', 'upperarm_r', 'upperarm_l'):
    print('%-11s' % b, ' '.join('%.2f' % rows[f][b] for f in range(600, 769, 8)))
print('WROTE', OUT)