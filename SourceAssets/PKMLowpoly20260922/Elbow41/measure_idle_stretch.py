"""Physical measure of the visible crease: per-edge stretch in the shipped idle.

For every mesh edge, compare its posed length with its rest length.  A fold or
tear shows up as edges that collapse or blow up.  Run on both arms: the right one
deforms cleanly, so it is the control for what "acceptable" looks like.
"""
import json
import math
from collections import defaultdict
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix

ROOT = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922')
E39 = ROOT / 'Elbow39'
HERE = ROOT / 'Elbow41'

BLEND = E39 / 'Edit' / 'PKM_idle_Elbow39.blend'
ACTION = 'PKM_idle_Elbow39'

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

bpy.ops.wm.open_mainfile(filepath=str(BLEND))
scene = bpy.context.scene
rig = bpy.data.objects['PKM_Manny_Rig']
act = bpy.data.actions[ACTION]
rig.animation_data.action = act
rig.animation_data.action_slot = act.slots[0]
scene.render.fps = 60


def deformed(frame):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    pose = {b.name: b.matrix.copy() for b in rig.pose.bones}
    delta = {n: pose[n] @ AU_REST_M[AU_INDEX[n]].inverted() for n in AU_BONES}
    skin = np.tile(np.eye(4), (len(BONES), 1, 1))
    for i, n in enumerate(BONES):
        if n in delta:
            skin[i] = np.array(delta[n])
    out = np.zeros_like(V)
    for k in range(WIDX.shape[1]):
        idx, w = WIDX[:, k], WVAL[:, k]
        a = (idx >= 0) & (w > 0.0)
        out[a] += w[a, None] * np.einsum('nij,nj->ni', skin[idx[a]], HOMO[a])[:, :3]
    return out


def bands(s):
    e = REST[IDX['lowerarm_%s' % s]][:3, 3]
    sh = REST[IDX['upperarm_%s' % s]][:3, 3]
    w = REST[IDX['hand_%s' % s]][:3, 3]
    f0 = (w - e) / np.linalg.norm(w - e)
    flen = float(np.linalg.norm(w - e))
    u0 = (e - sh) / np.linalg.norm(e - sh)
    rel = V - e
    t = rel @ f0 / flen
    rad = np.linalg.norm(rel - np.outer(t * flen, f0), axis=1)
    arm = (rad < 0.075) & (t > -0.30) & (t < 0.92)
    return t, arm


report = {}
for frame in (0, 30):
    P = deformed(frame)
    rest_len = np.linalg.norm(V[edges[:, 0]] - V[edges[:, 1]], axis=1)
    pose_len = np.linalg.norm(P[edges[:, 0]] - P[edges[:, 1]], axis=1)
    ok = rest_len > 1e-6
    ratio = np.ones(len(edges))
    ratio[ok] = pose_len[ok] / rest_len[ok]

    print('\n================ frame %d ================' % frame)
    for s, label in (('l', 'LEFT'), ('r', 'RIGHT')):
        t, arm = bands(s)
        # edges whose both ends are on this arm
        on = arm[edges[:, 0]] & arm[edges[:, 1]]
        r = ratio[on]
        et = t[edges[on, 0]]
        print('  %s arm edges %d | stretch mean %.4f  p99 %.3f  p99.9 %.3f  max %.3f  '
              'min %.3f' % (label, int(on.sum()), r.mean(),
                            np.percentile(r, 99), np.percentile(r, 99.9),
                            r.max(), r.min()))
        # worst compressors and stretchers, with their position along the limb
        for tag, sel in (('most compressed', np.argsort(r)[:400]),
                         ('most stretched', np.argsort(-r)[:400])):
            tt = et[sel]
            hist, edges_ = np.histogram(tt, bins=np.arange(-0.30, 0.95, 0.05))
            top = np.argsort(-hist)[:3]
            print('    %-15s worst %.3f  concentrated at t = %s'
                  % (tag, r[sel[0]] if tag.startswith('most c') else r[sel[0]],
                     ', '.join('%.2f..%.2f (n=%d)' % (edges_[i], edges_[i + 1], hist[i])
                               for i in top if hist[i] > 0)))
        report['%s_%s' % (label, frame)] = {
            'edges': int(on.sum()), 'mean': float(r.mean()),
            'p999': float(np.percentile(r, 99.9)), 'max': float(r.max()),
            'min': float(r.min()),
        }

    # a fold shows as neighbouring triangles facing opposite ways
    n = np.cross(P[T[:, 1]] - P[T[:, 0]], P[T[:, 2]] - P[T[:, 0]])
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    nr = np.cross(V[T[:, 1]] - V[T[:, 0]], V[T[:, 2]] - V[T[:, 0]])
    nr /= np.maximum(np.linalg.norm(nr, axis=1, keepdims=True), 1e-12)
    flip = np.degrees(np.arccos(np.clip((n * nr).sum(axis=1), -1, 1)))
    for s, label in (('l', 'LEFT'), ('r', 'RIGHT')):
        t, arm = bands(s)
        cent = V[T].mean(axis=1)
        sel = np.array([arm[a] and arm[b] and arm[c] for a, b, c in T])
        f = flip[sel]
        print('  %s triangles %d | normal turned mean %5.1f deg  p99 %5.1f  max %5.1f'
              % (label, int(sel.sum()), f.mean(), np.percentile(f, 99), f.max()))

(HERE / 'idle_stretch.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('\nIDLE_STRETCH_DONE')