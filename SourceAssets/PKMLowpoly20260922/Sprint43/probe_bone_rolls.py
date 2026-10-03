"""Which bone channel flips during the PKM sprint entry? (source, Elbow41 state)

Per frame, the surface roll applied by each left-arm bone, probed on a ring at that
bone's own head.  A sudden jump between two frames is a channel discontinuity, not
a pose change.
"""
import math
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector

ROOT = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922')
E39 = ROOT / 'Elbow39'
HERE = ROOT / 'Sprint43'

BLEND = ROOT / 'Elbow41' / 'Edit' / 'PKM_sprint_enter_Elbow41.blend'
ACTION = 'PKM_sprint_enter_Elbow41'
import sys
if '--' in sys.argv:
    _a = sys.argv[sys.argv.index('--') + 1:]
    if len(_a) >= 2:
        BLEND, ACTION = Path(_a[0]), _a[1]
CHAIN = ['clavicle_l', 'upperarm_l', 'upperarm_twist_01_l', 'upperarm_twist_02_l',
         'lowerarm_l', 'lowerarm_twist_02_l', 'lowerarm_twist_01_l', 'hand_l']

d = np.load(E39 / 'v7_mesh.npz', allow_pickle=True)
author = np.load(E39 / 'author_rig.npz', allow_pickle=True)
BONES = list(d['bones'])
REST = d['rest'].astype(np.float64)
AU_BONES = list(author['bones'])
AU_REST_M = [Matrix(m.tolist()) for m in author['rest'].astype(np.float64)]
AU_INDEX = {n: i for i, n in enumerate(AU_BONES)}
IDX = {n: i for i, n in enumerate(BONES)}

E_R = REST[IDX['lowerarm_l']][:3, 3]
S_R = REST[IDX['upperarm_l']][:3, 3]
W_R = REST[IDX['hand_l']][:3, 3]
B0 = (W_R - E_R) / np.linalg.norm(W_R - E_R)
A0 = (E_R - S_R) / np.linalg.norm(E_R - S_R)
Q1 = A0 - (A0 @ B0) * B0
Q1 /= np.linalg.norm(Q1)
Q2 = np.cross(B0, Q1)


def ring_at(c, r=0.045, n=24):
    pts = [c + math.cos(2 * math.pi * i / n) * Q1 * r
           + math.sin(2 * math.pi * i / n) * Q2 * r for i in range(n)]
    ph = []
    for p in pts:
        dd = p - E_R
        dd = dd - (dd @ B0) * B0
        ph.append(math.atan2(dd @ Q2, dd @ Q1))
    return pts, ph


RINGS = {n: ring_at(REST[IDX[n]][:3, 3]) for n in CHAIN}


def unwrap(v, ref):
    while v - ref > 180.0:
        v -= 360.0
    while ref - v > 180.0:
        v += 360.0
    return v


bpy.ops.wm.open_mainfile(filepath=str(BLEND))
scene = bpy.context.scene
rig = bpy.data.objects['PKM_Manny_Rig']
act = bpy.data.actions[ACTION]
rig.animation_data.action = act
rig.animation_data.action_slot = act.slots[0]
scene.render.fps = 120
start, end = map(int, act.frame_range)

prev = None
print('frame  bend |  ' + '  '.join('%-9s' % n.replace('_l', '') for n in CHAIN))
rows = []
for frame in range(start, end + 1):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    pose = {b.name: rig.pose.bones[b.name].matrix.copy() for b in rig.pose.bones}
    e = np.array(pose['lowerarm_l'].translation)
    s = np.array(pose['upperarm_l'].translation)
    w = np.array(pose['hand_l'].translation)
    u = (e - s) / np.linalg.norm(e - s)
    f = (w - e) / np.linalg.norm(w - e)
    bend = math.degrees(math.acos(max(-1, min(1, float(u @ f)))))
    p1 = (u - (u @ f) * f)
    p1 /= np.linalg.norm(p1)
    p2 = np.cross(f, p1)
    rolls, ref = {}, None
    for n in CHAIN:
        delta = pose[n] @ AU_REST_M[AU_INDEX[n]].inverted()
        pts, ph = RINGS[n]
        vals = []
        for p, rp in zip(pts, ph):
            h = delta @ Vector((float(p[0]), float(p[1]), float(p[2])))
            dd = np.array([h.x, h.y, h.z]) - e
            dd = dd - (dd @ f) * f
            vals.append(math.degrees((math.atan2(dd @ p2, dd @ p1) - rp
                                      + math.pi) % (2 * math.pi) - math.pi))
        v = sum(vals) / len(vals)
        rolls[n] = v if ref is None else unwrap(v, ref)
        ref = rolls[n]
    rows.append({'frame': frame, 'bend': bend, 'rolls': dict(rolls)})
    if frame <= 24 or frame % 6 == 0:
        print('%5d %5.1f | ' % (frame, bend)
              + '  '.join('%9.1f' % rolls[n] for n in CHAIN))
    prev = rolls

print('\nper-frame change in each bone roll (deg), frames where |change| > 15:')
hdr = '  '.join('%-9s' % n.replace('_l', '') for n in CHAIN)
print('frame |  ' + hdr)
for a, b in zip(rows, rows[1:]):
    dv = {n: b['rolls'][n] - a['rolls'][n] for n in CHAIN}
    if max(abs(x) for x in dv.values()) > 15:
        print('%5d | ' % b['frame'] + '  '.join('%9.1f' % dv[n] for n in CHAIN))

print('\nSPRINT43_BONE_ROLL_DONE')