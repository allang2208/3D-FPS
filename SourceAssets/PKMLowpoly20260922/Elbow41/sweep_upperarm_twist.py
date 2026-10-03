"""Test the fix hypothesis for the PKM idle left forearm.

The elbow band is skinned by three bones whose surface rolls span ~80 deg
(upperarm_twist_02_l -26.6, lowerarm_l -106.8, lowerarm_twist_02_l -94.8), so
the blended surface collapses and tears (edges stretch up to 12.9x, against
4.2x on the right arm which deforms cleanly).

Hypothesis: adding world-space twist to the *upper-arm* twist helpers, about the
live upper-arm axis through each bone's own head, brings them onto the forearm's
roll without touching any descendant (they are siblings of lowerarm_l, so the
hand cannot move at all).  Sweep the amount and measure the resulting surface.
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

BLEND = E39 / 'Edit' / 'PKM_idle_Elbow39.blend'
ACTION = 'PKM_idle_Elbow39'
FRAME = 0

d = np.load(E39 / 'v7_mesh.npz', allow_pickle=True)
author = np.load(E39 / 'author_rig.npz', allow_pickle=True)
V = d['verts'].astype(np.float64)
T = d['tris'].astype(np.int64)
WIDX, WVAL = d['w_idx'], d['w_val'].astype(np.float64)
BONES = list(d['bones'])
REST = d['rest'].astype(np.float64)
AU_BONES = list(author['bones'])
AU_REST_M = [Matrix(m.tolist()) for m in author['rest'].astype(np.float64)]
AU_INDEX = {n: i for i, n in enumerate(AU_BONES)}
IDX = {n: i for i, n in enumerate(BONES)}
HOMO = np.concatenate([V, np.ones((len(V), 1))], axis=1)

wsum = np.zeros((len(V), len(BONES)))
for k in range(WIDX.shape[1]):
    idx, w = WIDX[:, k], WVAL[:, k]
    a = (idx >= 0) & (w > 0)
    np.add.at(wsum, (np.where(a)[0], idx[a]), w[a])

edges = np.array(sorted({(min(a, b), max(a, b)) for a, b, c in T
                         for a, b in ((a, b), (b, c), (c, a))}), dtype=np.int64)
REST_LEN = np.linalg.norm(V[edges[:, 0]] - V[edges[:, 1]], axis=1)


def side_mask(s):
    e = REST[IDX['lowerarm_%s' % s]][:3, 3]
    sh = REST[IDX['upperarm_%s' % s]][:3, 3]
    w = REST[IDX['hand_%s' % s]][:3, 3]
    f0 = (w - e) / np.linalg.norm(w - e)
    flen = float(np.linalg.norm(w - e))
    rel = V - e
    t = rel @ f0 / flen
    rad = np.linalg.norm(rel - np.outer(t * flen, f0), axis=1)
    return (rad < 0.075) & (t > -0.60) & (t < 0.92)


ARM_L = side_mask('l')
ARM_R = side_mask('r')
EDGE_L = ARM_L[edges[:, 0]] & ARM_L[edges[:, 1]]
EDGE_R = ARM_R[edges[:, 0]] & ARM_R[edges[:, 1]]

bpy.ops.wm.open_mainfile(filepath=str(BLEND))
scene = bpy.context.scene
rig = bpy.data.objects['PKM_Manny_Rig']
act = bpy.data.actions[ACTION]
rig.animation_data.action = act
rig.animation_data.action_slot = act.slots[0]
scene.render.fps = 60
scene.frame_set(FRAME)
bpy.context.view_layer.update()

pose = {b.name: b.matrix.copy() for b in rig.pose.bones}
base = {n: pose[n] @ AU_REST_M[AU_INDEX[n]].inverted() for n in AU_BONES}
sh = np.array(pose['upperarm_l'].translation)
el = np.array(pose['lowerarm_l'].translation)
wr = np.array(pose['hand_l'].translation)
U = Vector(((el - sh) / np.linalg.norm(el - sh)).tolist())

print('station positions along the forearm axis (forearm units):')
e_r = REST[IDX['lowerarm_l']][:3, 3]
w_r = REST[IDX['hand_l']][:3, 3]
f0 = (w_r - e_r) / np.linalg.norm(w_r - e_r)
flen = float(np.linalg.norm(w_r - e_r))
for n in ('upperarm_l', 'upperarm_twist_01_l', 'upperarm_twist_02_l',
          'lowerarm_l', 'lowerarm_twist_02_l', 'lowerarm_twist_01_l', 'hand_l'):
    p = REST[IDX[n]][:3, 3]
    print('  %-22s t = %+.3f' % (n, float((p - e_r) @ f0 / flen)))

TWIST_BONES = ('upperarm_twist_01_l', 'upperarm_twist_02_l')


def build(a1, a2):
    dl = dict(base)
    for name, ang in zip(TWIST_BONES, (a1, a2)):
        if abs(ang) < 1e-9:
            continue
        h = pose[name].translation
        dl[name] = (Matrix.Translation(h) @ Matrix.Rotation(math.radians(ang), 4, U)
                    @ Matrix.Translation(-h) @ base[name])
    return dl


def deform(dl):
    skin = np.tile(np.eye(4), (len(BONES), 1, 1))
    for i, n in enumerate(BONES):
        if n in dl:
            skin[i] = np.array(dl[n])
    out = np.zeros_like(V)
    for k in range(WIDX.shape[1]):
        idx, w = WIDX[:, k], WVAL[:, k]
        a = (idx >= 0) & (w > 0.0)
        out[a] += w[a, None] * np.einsum('nij,nj->ni', skin[idx[a]], HOMO[a])[:, :3]
    return out


def normals(P):
    n = np.cross(P[T[:, 1]] - P[T[:, 0]], P[T[:, 2]] - P[T[:, 0]])
    return n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)


P0 = deform(base)
N0 = normals(P0)
r0 = np.linalg.norm(P0[edges[:, 0]] - P0[edges[:, 1]], axis=1) / REST_LEN


def score(P, mask_edges, mask_tris):
    r = np.linalg.norm(P[edges[:, 0]] - P[edges[:, 1]], axis=1)[mask_edges] / REST_LEN[mask_edges]
    turn = np.degrees(np.arccos(np.clip((normals(P)[mask_tris] * N0[mask_tris]).sum(axis=1), -1, 1)))
    return r, turn


TRI_L = np.array([ARM_L[a] and ARM_L[b] and ARM_L[c] for a, b, c in T])
TRI_R = np.array([ARM_R[a] and ARM_R[b] and ARM_R[c] for a, b, c in T])

print('\nreference (unmodified):')
for tag, P, em, tm in (('LEFT', P0, EDGE_L, TRI_L), ('RIGHT', P0, EDGE_R, TRI_R)):
    r, turn = score(P, em, tm)
    print('  %-6s stretch mean %.4f p99 %.3f p99.9 %.3f max %7.3f | normal turn mean %5.1f'
          % (tag, r.mean(), np.percentile(r, 99), np.percentile(r, 99.9), r.max(), turn.mean()))

rows = []
print('\nsweep: extra twist on upperarm_twist_01_l / _02_l')
print('   a1     a2 | L stretch p99.9     max | L turn mean | hand drift')
for a1, a2 in ((0, 0), (0, 15), (0, 30), (0, 45), (0, 60), (0, 75), (0, 90),
               (10, 40), (15, 45), (20, 60), (10, 60), (20, 80), (15, 75),
               (25, 65), (30, 90), (0, -30), (0, -60)):
    dl = build(a1, a2)
    P = deform(dl)
    r, turn = score(P, EDGE_L, TRI_L)
    drift = np.abs(P[IDX['hand_l']] - P0[IDX['hand_l']]).max()
    rows.append({'a1': a1, 'a2': a2, 'p999': float(np.percentile(r, 99.9)),
                 'max': float(r.max()), 'turn': float(turn.mean()),
                 'drift': float(drift)})
    print('  %4d  %5d | %14.3f %7.3f | %11.1f | %.3e'
          % (a1, a2, np.percentile(r, 99.9), r.max(), turn.mean(), drift))

best = min(rows, key=lambda x: x['p999'])
print('\nbest by p99.9: a1=%d a2=%d  p99.9 %.3f  max %.3f  turn %.1f'
      % (best['a1'], best['a2'], best['p999'], best['max'], best['turn']))
(HERE / 'upperarm_twist_sweep.json').write_text(
    json.dumps({'rows': rows, 'best': best}, indent=2), encoding='utf-8')
print('\nSWEEP_DONE')