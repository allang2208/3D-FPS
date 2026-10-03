"""Which edges tear in the shipped PKM idle left arm, and what drives them."""
import json
import math
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix

ROOT = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922')
E39 = ROOT / 'Elbow39'
HERE = ROOT / 'Elbow41'

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

W = np.zeros((len(V), len(BONES)))
for k in range(WIDX.shape[1]):
    idx, w = WIDX[:, k], WVAL[:, k]
    a = (idx >= 0) & (w > 0)
    np.add.at(W, (np.where(a)[0], idx[a]), w[a])

edges = np.array(sorted({(min(a, b), max(a, b)) for a, b, c in T
                         for a, b in ((a, b), (b, c), (c, a))}), dtype=np.int64)
RL = np.linalg.norm(V[edges[:, 0]] - V[edges[:, 1]], axis=1)


def band(s):
    e = REST[IDX['lowerarm_%s' % s]][:3, 3]
    sh = REST[IDX['upperarm_%s' % s]][:3, 3]
    w = REST[IDX['hand_%s' % s]][:3, 3]
    f0 = (w - e) / np.linalg.norm(w - e)
    flen = float(np.linalg.norm(w - e))
    rel = V - e
    t = rel @ f0 / flen
    rad = np.linalg.norm(rel - np.outer(t * flen, f0), axis=1)
    return t, rad, (rad < 0.075) & (t > -0.80) & (t < 0.95)


bpy.ops.wm.open_mainfile(filepath=str(E39 / 'Edit' / 'PKM_idle_Elbow39.blend'))
scene = bpy.context.scene
rig = bpy.data.objects['PKM_Manny_Rig']
act = bpy.data.actions['PKM_idle_Elbow39']
rig.animation_data.action = act
rig.animation_data.action_slot = act.slots[0]
scene.render.fps = 60
scene.frame_set(0)
bpy.context.view_layer.update()
pose = {b.name: b.matrix.copy() for b in rig.pose.bones}
delta = {n: pose[n] @ AU_REST_M[AU_INDEX[n]].inverted() for n in AU_BONES}
skin = np.tile(np.eye(4), (len(BONES), 1, 1))
for i, n in enumerate(BONES):
    if n in delta:
        skin[i] = np.array(delta[n])
P = np.zeros_like(V)
for k in range(WIDX.shape[1]):
    idx, w = WIDX[:, k], WVAL[:, k]
    a = (idx >= 0) & (w > 0.0)
    P[a] += w[a, None] * np.einsum('nij,nj->ni', skin[idx[a]], HOMO[a])[:, :3]

ratio = np.linalg.norm(P[edges[:, 0]] - P[edges[:, 1]], axis=1) / np.maximum(RL, 1e-9)

for s, label in (('l', 'LEFT'), ('r', 'RIGHT')):
    t, rad, arm = band(s)
    on = arm[edges[:, 0]] & arm[edges[:, 1]]
    idxs = np.where(on)[0]
    order = idxs[np.argsort(-ratio[idxs])]
    print('\n=== %s arm: top tearing edges ===' % label)
    print('  ratio   rest_mm  posed_mm    t_a     t_b    r_a    r_b  bones at a / at b')
    for k in order[:12]:
        a, b = edges[k]
        wa = np.argsort(-W[a])[:3]
        wb = np.argsort(-W[b])[:3]
        fmt = lambda wi: '/'.join('%s%.2f' % (BONES[i].replace('_l', '').replace('_r', ''), W[a if wi is wa else b, i])
                                  for i in wi)
        print('  %6.2f  %7.2f %8.2f %7.3f %7.3f %6.3f %6.3f  %s | %s'
              % (ratio[k], RL[k] * 1000, RL[k] * ratio[k] * 1000,
                 t[a], t[b], rad[a], rad[b], fmt(wa), fmt(wb)))

    # histogram of where the damage is
    dmg = np.clip(ratio[idxs] - 1.5, 0, None)
    edges_bins = np.arange(-0.80, 1.00, 0.10)
    hist, _ = np.histogram(t[edges[idxs, 0]], bins=edges_bins, weights=dmg)
    tot = hist.sum()
    print('  damage (sum of ratio-1.5 above threshold) by t:')
    for i in range(len(hist)):
        if hist[i] > 0.01 * tot:
            print('    t %+.1f..%+.1f : %5.1f%%' % (edges_bins[i], edges_bins[i + 1],
                                                    100.0 * hist[i] / tot))

    # which bones sit on the damaged vertices
    bad = np.unique(edges[idxs][ratio[idxs] > 2.0])
    if len(bad):
        wb = W[bad].mean(axis=0)
        top = np.argsort(-wb)[:8]
        print('  bones on vertices of edges stretched >2x (n=%d):' % len(bad))
        print('    ' + ', '.join('%s %.3f' % (BONES[i], wb[i]) for i in top if wb[i] > 0.005))
print('\nTEAR_LOCALIZE_DONE')