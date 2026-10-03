"""Compare every left-arm idle pose available, to isolate what the shipped one does wrong.

Same measurement for each action: the surface roll at every station along the
left arm, the total pronation it carries, and whether the roll ramp reverses.
"""
import json
import math
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector

ROOT = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922')
E39 = ROOT / 'Elbow39'
HERE = ROOT / 'Elbow41'

BLEND = ROOT / 'Wrist12' / 'PKM_WristContact_Editable.blend'
ACTIONS = ['PKM_Game_idle', 'PKM_Game_idle_Wrist12', 'PKM_Idle',
           'PKM_Game_aim', 'PKM_Game_aim_Wrist12', 'PKM_Game_inspect']
FPS = 60

d = np.load(E39 / 'v7_mesh.npz', allow_pickle=True)
author = np.load(E39 / 'author_rig.npz', allow_pickle=True)
V = d['verts'].astype(np.float64)
WIDX, WVAL = d['w_idx'], d['w_val'].astype(np.float64)
BONES = list(d['bones'])
REST = d['rest'].astype(np.float64)
AU_BONES = list(author['bones'])
AU_REST_M = [Matrix(m.tolist()) for m in author['rest'].astype(np.float64)]
AU_INDEX = {n: i for i, n in enumerate(AU_BONES)}
IDX = {n: i for i, n in enumerate(BONES)}

STATIONS = ['upperarm_twist_01_l', 'upperarm_twist_02_l', 'lowerarm_l',
            'lowerarm_twist_02_l', 'lowerarm_twist_01_l', 'hand_l']

bpy.ops.wm.open_mainfile(filepath=str(BLEND))
scene = bpy.context.scene
rig = bpy.data.objects['PKM_Manny_Rig']
scene.render.fps = FPS


def probe(matrix, pts, ph, e, u, f):
    p1 = (Vector(u) - Vector(u).dot(Vector(f)) * Vector(f)).normalized()
    p2 = Vector(f).cross(p1)
    out = []
    for v, rp in zip(pts, ph):
        h = matrix @ Vector((float(v[0]), float(v[1]), float(v[2])))
        dd = Vector((h.x, h.y, h.z)) - Vector(e)
        dd = dd - dd.dot(Vector(f)) * Vector(f)
        out.append(math.degrees((math.atan2(dd.dot(p2), dd.dot(p1)) - rp
                                 + math.pi) % (2 * math.pi) - math.pi))
    return sum(out) / len(out)


def unwrap(v, ref, period=360.0):
    while v - ref > period / 2:
        v -= period
    while ref - v > period / 2:
        v += period
    return v


rows = {}
for action_name in ACTIONS:
    act = bpy.data.actions.get(action_name)
    if act is None:
        continue
    rig.animation_data.action = act
    rig.animation_data.action_slot = act.slots[0]
    scene.frame_set(int(act.frame_range[0]))
    bpy.context.view_layer.update()
    pose = {b.name: rig.pose.bones[b.name].matrix.copy() for b in rig.data.bones}
    delta = {n: pose[n] @ AU_REST_M[AU_INDEX[n]].inverted() for n in AU_BONES}

    e = np.array(pose['lowerarm_l'].translation)
    sh = np.array(pose['upperarm_l'].translation)
    w = np.array(pose['hand_l'].translation)
    u = (e - sh) / np.linalg.norm(e - sh)
    f = (w - e) / np.linalg.norm(w - e)
    bend = math.degrees(math.acos(max(-1, min(1, float(u @ f)))))

    # station rings in the *rest* frame, parameterised from the elbow
    e_r = REST[IDX['lowerarm_l']][:3, 3]
    w_r = REST[IDX['hand_l']][:3, 3]
    s_r = REST[IDX['upperarm_l']][:3, 3]
    f0 = (w_r - e_r) / np.linalg.norm(w_r - e_r)
    flen = float(np.linalg.norm(w_r - e_r))
    a0 = (e_r - s_r) / np.linalg.norm(e_r - s_r)
    q1 = a0 - (a0 @ f0) * f0
    q1 /= np.linalg.norm(q1)
    q2 = np.cross(f0, q1)

    rolls_raw = {}
    for n in STATIONS:
        c = REST[IDX[n]][:3, 3]
        ring, ph = [], []
        for i in range(24):
            p = c + math.cos(2 * math.pi * i / 24) * q1 * 0.045 \
                + math.sin(2 * math.pi * i / 24) * q2 * 0.045
            ring.append(p)
            dd = p - e_r
            dd = dd - (dd @ f0) * f0
            ph.append(math.atan2(dd @ q2, dd @ q1))
        rolls_raw[n] = probe(delta[n], ring, ph, e, u, f)

    rolls = {}
    prev = None
    for n in STATIONS:
        rolls[n] = rolls_raw[n] if prev is None else unwrap(rolls_raw[n], rolls[n and prev])
        prev = n

    chain = [rolls[n] for n in STATIONS]
    diffs = [round(chain[i + 1] - chain[i], 1) for i in range(len(chain) - 1)]
    rev = sum(1 for x in diffs if x > 0)  # steps that go backwards
    rows[action_name] = {
        'bend': round(bend, 1),
        'stations': {n: round(rolls[n], 1) for n in STATIONS},
        'steps': diffs,
        'pronation': round(rolls['hand_l'] - rolls['upperarm_twist_02_l'], 1),
        'span': round(max(chain) - min(chain), 1),
        'backward_steps': rev,
        'total_variation': round(sum(abs(x) for x in diffs), 1),
    }
    print('%-26s bend %5.1f | pronation %7.1f | span %6.1f | TV %6.1f | backward steps %d'
          % (action_name, bend, rows[action_name]['pronation'], rows[action_name]['span'],
             rows[action_name]['total_variation'], rev))
    print('    ' + '  '.join('%s %+.1f' % (n.replace('_l', ''), rolls[n]) for n in STATIONS))
    print('    steps: ' + '  '.join('%+.1f' % x for x in diffs))

(HERE / 'idle_action_compare.json').write_text(
    json.dumps(rows, indent=2, ensure_ascii=False), encoding='utf-8')
print('\nIDLE_ACTION_COMPARE_DONE')