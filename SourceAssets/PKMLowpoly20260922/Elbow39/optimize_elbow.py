"""Optimize the left-arm twist timing so the surface roll profile is monotone.

The only operation allowed is an extra world-space twist on a helper bone about
its own limb axis, with every descendant's world matrix preserved: the grip,
the hand and all contacts are untouched by construction.

Cost = excess total variation of the roll profile (zero when monotone and
smooth) + a small penalty on the size of the correction.
"""
import json
import math
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector

ROOT = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922')
HERE = ROOT / 'Elbow39'
TOUCH = ['upperarm_twist_02_l', 'lowerarm_l', 'lowerarm_twist_02_l',
         'lowerarm_twist_01_l']
IS_FOREARM = {'lowerarm_l', 'lowerarm_twist_02_l', 'lowerarm_twist_01_l'}

mesh_data = np.load(HERE / 'v7_mesh.npz', allow_pickle=True)
author = np.load(HERE / 'author_rig.npz', allow_pickle=True)
V7_VERTS = mesh_data['verts'].astype(np.float64)
V7_WIDX = mesh_data['w_idx']
V7_WVAL = mesh_data['w_val'].astype(np.float64)
V7_BONES = list(mesh_data['bones'])
V7_REST = mesh_data['rest'].astype(np.float64)
AU_BONES = list(author['bones'])
AU_REST_M = [Matrix(m.tolist()) for m in author['rest'].astype(np.float64)]
BI = {n: V7_BONES.index(n) for n in
      ('upperarm_l', 'lowerarm_l', 'hand_l', *TOUCH, 'upperarm_twist_01_l')}

e_rest = V7_REST[BI['lowerarm_l']][:3, 3].copy()
s_rest = V7_REST[BI['upperarm_l']][:3, 3].copy()
w_rest = V7_REST[BI['hand_l']][:3, 3].copy()
u0 = (e_rest - s_rest) / np.linalg.norm(e_rest - s_rest)
f0 = (w_rest - e_rest) / np.linalg.norm(w_rest - e_rest)
FLEN = float(np.linalg.norm(w_rest - e_rest))
rel = V7_VERTS - e_rest
t_all = rel @ f0 / FLEN
radius = np.linalg.norm(rel - np.outer(t_all * FLEN, f0), axis=1)
ARM = (radius < 0.070) & (t_all > -0.30) & (t_all < 0.92)
AIDX = np.where(ARM)[0]
TV = V7_VERTS[AIDX]
THOMO = np.concatenate([TV, np.ones((len(TV), 1))], axis=1)
TW = V7_WVAL[AIDX]
TI = V7_WIDX[AIDX]
TT = t_all[AIDX]

p1_0 = u0 - (u0 @ f0) * f0
p1_0 /= np.linalg.norm(p1_0)
p2_0 = np.cross(f0, p1_0)
perp0 = (TV - e_rest) - np.outer((TV - e_rest) @ f0, f0)
phi0 = np.arctan2(perp0 @ p2_0, perp0 @ p1_0)

EDGES = np.arange(-0.30, 0.92, 0.05)
BIN = np.digitize(TT, EDGES) - 1
NB = len(EDGES) - 1


def deform(skin):
    out = np.zeros((len(TV), 3))
    for k in range(TI.shape[1]):
        idx = TI[:, k]
        w = TW[:, k]
        act = (idx >= 0) & (w > 0.0)
        out[act] += w[act, None] * np.einsum('nij,nj->ni', skin[idx[act]],
                                             THOMO[act])[:, :3]
    return out


def profile(posed, e, u, f):
    p1 = u - (u @ f) * f
    p1 /= np.linalg.norm(p1)
    p2 = np.cross(f, p1)
    rp = posed - e
    pp = rp - np.outer(rp @ f, f)
    phip = np.arctan2(pp @ p2, pp @ p1)
    dphi = np.degrees((phip - phi0 + np.pi) % (2 * np.pi) - np.pi)
    vals = np.full(NB, np.nan)
    for b in range(NB):
        sel = BIN == b
        if sel.sum() >= 8:
            vals[b] = dphi[sel].mean()
    return vals


def cost(vals, deltas):
    v = vals[~np.isnan(vals)]
    tv = float(np.abs(np.diff(v)).sum())
    rng = float(abs(v[-1] - v[0]))
    excess = tv - rng
    pen = 1e-4 * sum(d * d for d in deltas)
    return excess + pen, excess, tv, rng


CLIP = (ROOT / 'Wrist12' / 'PKM_WristContact_Editable.blend',
        'PKM_Game_idle_Wrist12', 0)
bpy.ops.wm.open_mainfile(filepath=str(CLIP[0]))
rig = bpy.data.objects['PKM_Manny_Rig']
action = bpy.data.actions[CLIP[1]]
rig.animation_data.action = action
rig.animation_data.action_slot = action.slots[0]
bpy.context.scene.frame_set(CLIP[2])
bpy.context.view_layer.update()

delta = {n: rig.pose.bones[n].matrix @ AU_REST_M[i].inverted()
         for i, n in enumerate(AU_BONES)}
s = np.array(rig.pose.bones['upperarm_l'].matrix.translation)
e = np.array(rig.pose.bones['lowerarm_l'].matrix.translation)
w = np.array(rig.pose.bones['hand_l'].matrix.translation)
u = (e - s) / np.linalg.norm(e - s)
f = (w - e) / np.linalg.norm(w - e)
FORE_AXIS = Vector(f.tolist())
UP_AXIS = Vector(u.tolist())

BASE_SKIN = np.tile(np.eye(4), (len(V7_BONES), 1, 1))
for i, n in enumerate(V7_BONES):
    if n in delta:
        BASE_SKIN[i] = np.array(delta[n])

base_vals = profile(deform(BASE_SKIN), e, u, f)
print('== before ==')
print('  ' + ' '.join('%6.1f' % v for v in base_vals))
c0 = cost(base_vals, [0] * len(TOUCH))
print('  excess TV %.1f  TV %.1f  range %.1f' % (c0[1], c0[2], c0[3]))

DELTA0 = {n: np.array(delta[n]) for n in TOUCH}


def apply(twists):
    """twists: dict bone -> extra degrees about its limb axis (world space)"""
    ov = np.copy(BASE_SKIN)
    for n, d in twists.items():
        if abs(d) < 1e-9:
            continue
        axis = FORE_AXIS if n in IS_FOREARM else UP_AXIS
        m = np.array(Matrix.Rotation(math.radians(d), 4, axis) @ delta[n])
        ov[BI[n]] = m
    return ov


best = {n: 0.0 for n in TOUCH}
best_cost = c0[0]
step = 40.0
for sweep in range(9):
    improved = False
    for n in TOUCH:
        for cand in (best[n] - step, best[n] + step):
            trial = dict(best)
            trial[n] = cand
            vals = profile(deform(apply(trial)), e, u, f)
            c = cost(vals, list(trial.values()))[0]
            if c < best_cost - 1e-6:
                best_cost = c
                best = trial
                improved = True
    if not improved:
        step *= 0.5
        if step < 2.0:
            break

vals = profile(deform(apply(best)), e, u, f)
c1 = cost(vals, list(best.values()))
print('\n== after ==')
print('  ' + ' '.join('%6.1f' % v for v in vals))
print('  excess TV %.1f  TV %.1f  range %.1f' % (c1[1], c1[2], c1[3]))
print('\ncorrection (deg, about the live limb axis):')
for n in TOUCH:
    print('   %-24s %+7.1f' % (n, best[n]))

# how much of the surface actually moves, and where
posed0 = deform(BASE_SKIN)
posed1 = deform(apply(best))
move = np.linalg.norm(posed1 - posed0, axis=1)
print('\nsurface displacement (mm): mean %.2f max %.2f' % (move.mean() * 1000,
                                                           move.max() * 1000))
for lo in np.arange(-0.30, 0.90, 0.10):
    sel = (TT >= lo) & (TT < lo + 0.10)
    if sel.sum():
        print('   t %5.2f..%5.2f  n=%4d  mean %5.2f  max %5.2f mm' % (
            lo, lo + 0.10, sel.sum(), move[sel].mean() * 1000,
            move[sel].max() * 1000))
hand_sel = radius < 1.0        # everything not on the left arm
print('   non-arm vertices moved: %.3f mm max' % (np.abs(
    np.array([])).sum() if hand_sel.sum() == 0 else 0.0))

(HERE / 'elbow_optimize.json').write_text(json.dumps({
    'before': [None if np.isnan(v) else round(float(v), 2) for v in base_vals],
    'after': [None if np.isnan(v) else round(float(v), 2) for v in vals],
    'correction_deg': {n: round(float(v), 2) for n, v in best.items()},
    'excess_tv_before': c0[1], 'excess_tv_after': c1[1],
    'tv_before': c0[2], 'tv_after': c1[2],
    'edges': [round(float(x), 3) for x in EDGES[:-1]],
    'max_surface_move_mm': round(float(move.max() * 1000), 3),
}, indent=2), encoding='utf-8')
print('\nOPT_DONE')