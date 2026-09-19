"""Per-frame tail deltas in the pistol quick-combat AUTHOR blends.

Decides whether the late re-acceleration the UE clip shows near the end
(715/1911: ~4.6 deg/frame on lowerarm_r in the last 60 ms; M4 rifle: ~0.9)
comes from the authored bake or from import/compression. Same convention as the
sword probe: armature-space rotation delta per frame at the bake rate, folded to
[0,180].

Read-only.
"""
import bpy
import json
import math
from pathlib import Path

P = Path(__file__).parent
OUT = P / 'pistol_author_tail.json'

SOURCES = [
    ('pistol_715', Path(r'D:\FPS3D\FPSGAME\SourceAssets\DanWesson715QuickCombat20260918\DanWesson715_QuickCombat_Editable.blend'),
     'DW715_quickcombat'),
    ('pistol_1911', Path(r'D:\FPS3D\FPSGAME\SourceAssets\M1911QuickCombat20260919\M1911_QuickCombat_Editable.blend'),
     'M1911_quickcombat'),
]

BONES = ['hand_r', 'hand_l', 'lowerarm_r', 'lowerarm_l', 'upperarm_r', 'upperarm_l']


def delta_deg(q_prev, q_now):
    a = math.degrees(q_prev.rotation_difference(q_now).angle)
    return 360.0 - a if a > 180.0 else a


res = {}
for name, path, clip in SOURCES:
    if not path.exists():
        res[name] = {'error': 'blend missing: %s' % path}
        continue
    bpy.ops.wm.open_mainfile(filepath=str(path))
    scene = bpy.context.scene
    fps = scene.render.fps
    rig = None
    for ob in bpy.data.objects:
        if ob.type == 'ARMATURE':
            rig = ob
            break
    if rig is None:
        res[name] = {'error': 'no armature'}
        continue
    acts = [a for a in bpy.data.actions if clip.lower() in a.name.lower()]
    if not acts:
        res[name] = {'error': 'action missing', 'actions': [a.name for a in bpy.data.actions]}
        continue
    act = acts[0]
    rig.animation_data_create()
    rig.animation_data.action = act
    if act.slots:
        rig.animation_data.action_slot = act.slots[0]
    last = int(act.frame_range[1])
    prev = {}
    rows = []
    for f in range(0, last + 1):
        scene.frame_set(f)
        row = {'f': f, 't': round(f / fps, 5)}
        for b in BONES:
            if b not in rig.pose.bones:
                continue
            q = rig.pose.bones[b].matrix.to_quaternion()
            row[b] = round(delta_deg(prev[b], q), 4) if b in prev else 0.0
            prev[b] = q.copy()
        rows.append(row)
    res[name] = {'blend': str(path), 'action': act.name, 'fps': fps, 'last': last, 'rows': rows}

OUT.write_text(json.dumps(res, ensure_ascii=False), encoding='utf-8')
for name, e in res.items():
    if 'rows' not in e:
        print(name, 'ERROR', e)
        continue
    print('==', name, 'fps=%s frames=%s action=%s' % (e['fps'], e['last'], e['action']))
    tail0 = e['last'] - int(0.12 * e['fps'])
    for b in BONES:
        sel = [r for r in e['rows'] if r['f'] >= tail0]
        mx = max(sel, key=lambda r: r[b])
        print('  %-11s max=%.3f @f%d (t=%.4f)  last=%.3f' % (b, mx[b], mx['f'], mx['t'], sel[-1][b]))
    print('  lowerarm_r tail per frame:',
          ' '.join('%.2f' % r['lowerarm_r'] for r in e['rows'][tail0:]))
print('WROTE', OUT)