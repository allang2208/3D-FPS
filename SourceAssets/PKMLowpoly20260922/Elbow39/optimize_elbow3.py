"""Spread the left-arm pronation evenly, then optimize the twist timing.

Target: the surface roll should ramp linearly in arc-length station from the
elbow (where it must match the upper arm) to the wrist, so no band is wrung.
Operation: extra world-space twist on helper bones about their own live limb
axis through their own head, descendants' world matrices preserved.
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
A_LO, A_HI = -0.05, 0.02      # elbow-side anchor bins
B_LO, B_HI = 0.83, 0.90       # wrist-side anchor bins
FIT_LO, FIT_HI = -0.12, 0.90  # where the ramp is enforced

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
      ('upperarm_l', 'lowerarm_l', 'hand_l', *TOUCH)}

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
BIN_T = EDGES[:-1] + 0.025
BIN_OK = np.array([(BIN == b).sum() >= 8 for b in range(NB)])
FIT = BIN_OK & (BIN_T >= FIT_LO) & (BIN_T <= FIT_HI)
A_SEL = BIN_OK & (BIN_T >= A_LO) & (BIN_T <= A_HI)
B_SEL = BIN_OK & (BIN_T >= B_LO) & (BIN_T <= B_HI)


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


def cost(vals, twists):
    A = float(vals[A_SEL].mean())
    B = float(vals[B_SEL].mean())
    tA, tB = float(BIN_T[A_SEL].mean()), float(BIN_T[B_SEL].mean())
    ref = A + (B - A) * (BIN_T - tA) / (tB - tA)
    c = float(((vals[FIT] - ref[FIT]) ** 2).sum())
    d = np.diff(vals[BIN_OK])
    c += 4.0 * float((np.clip(d, 0.0, None) ** 2).sum())
    c += 3e-4 * sum(x * x for x in twists.values())
    return c


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
HEADS = {n: np.array(rig.pose.bones[n].matrix.translation).copy() for n in TOUCH}
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


def apply(twists):
    ov = np.copy(BASE_SKIN)
    for n, d in twists.items():
        if abs(d) < 1e-9:
            continue
        axis = FORE_AXIS if n in IS_FOREARM else UP_AXIS
        h = Vector(HEADS[n].tolist())
        R = (Matrix.Translation(h) @ Matrix.Rotation(math.radians(d), 4, axis)
             @ Matrix.Translation(-h))
        ov[BI[n]] = np.array(R @ delta[n])
    return ov


base_vals = profile(deform(BASE_SKIN), e, u, f)


def ref_of(vals):
    A = float(vals[A_SEL].mean())
    B = float(vals[B_SEL].mean())
    tA, tB = float(BIN_T[A_SEL].mean()), float(BIN_T[B_SEL].mean())
    return A + (B - A) * (BIN_T - tA) / (tB - tA)


best = {n: 0.0 for n in TOUCH}
best_c = cost(base_vals, best)
r0 = ref_of(base_vals)
print('== before ==')
print('  profile ' + ' '.join('%6.1f' % v for v in base_vals))
print('  target  ' + ' '.join('%6.1f' % v for v in r0))
print('  rms to ramp %.2f  cost %.1f' % (
    float(np.sqrt(((base_vals[FIT] - r0[FIT]) ** 2).mean())), best_c))

for n in TOUCH:
    step = 64.0
    while step >= 2.0:
        improved = False
        for cand in (best[n] - step, best[n] + step):
            if abs(cand) > 150:
                continue
            trial = dict(best)
            trial[n] = cand
            c = cost(profile(deform(apply(trial)), e, u, f), trial)
            if c < best_c - 1e-9:
                best_c, best, improved = c, trial, True
        if not improved:
            step *= 0.5
for _ in range(4):
    for n in TOUCH:
        step = 8.0
        while step >= 1.0:
            improved = False
            for cand in (best[n] - step, best[n] + step):
                trial = dict(best)
                trial[n] = cand
                c = cost(profile(deform(apply(trial)), e, u, f), trial)
                if c < best_c - 1e-9:
                    best_c, best, improved = c, trial, True
            if not improved:
                step *= 0.5

vals = profile(deform(apply(best)), e, u, f)
r1 = ref_of(vals)
print('\n== after ==')
print('  profile ' + ' '.join('%6.1f' % v for v in vals))
print('  weights ' + ' '.join('%6.2f' % v for v in BIN_T))
print('  rms to ramp %.2f  cost %.1f' % (
    float(np.sqrt(((vals[FIT] - r1[FIT]) ** 2).mean())), best_c))
d = np.diff(vals[BIN_OK])
print('  max backward step %.2f deg' % float(np.clip(d, 0, None).max()))
print('\ncorrection (deg about the live limb axis, through the bone head):')
for n in TOUCH:
    print('   %-24s %+8.1f' % (n, best[n]))

posed0, posed1 = deform(BASE_SKIN), deform(apply(best))
mv = np.linalg.norm(posed1 - posed0, axis=1)
print('\nsurface displacement: mean %.2f mm  max %.2f mm' % (mv.mean() * 1000,
                                                             mv.max() * 1000))
# non-arm surface must not move at all
OTHER = np.where(~ARM)[0]
sk = np.copy(BASE_SKIN)
o0 = np.zeros((len(OTHER), 3))
o1 = np.zeros((len(OTHER), 3))
homo = np.concatenate([V7_VERTS[OTHER], np.ones((len(OTHER), 1))], axis=1)
ws = V7_WVAL[OTHER]
wi = V7_WIDX[OTHER]
for k in range(wi.shape[1]):
    idx, ww = wi[:, k], ws[:, k]
    act = (idx >= 0) & (ww > 0)
    o0[act] += ww[act, None] * np.einsum('nij,nj->ni', BASE_SKIN[idx[act]],
                                         homo[act])[:, :3]
    o1[act] += ww[act, None] * np.einsum('nij,nj->ni', apply(best)[idx[act]],
                                         homo[act])[:, :3]
print('off-arm surface moved: mean %.4f mm  max %.4f mm' % (
    np.linalg.norm(o1 - o0, axis=1).mean() * 1000,
    np.linalg.norm(o1 - o0, axis=1).max() * 1000))

(HERE / 'elbow_optimize.json').write_text(json.dumps({
    'before': [None if np.isnan(v) else round(float(v), 2) for v in base_vals],
    'after': [None if np.isnan(v) else round(float(v), 2) for v in vals],
    'target': [None if np.isnan(v) else round(float(v), 2) for v in r0],
    'correction_deg': {n: round(float(v), 2) for n, v in best.items()},
    'edges': [round(float(x), 3) for x in BIN_T],
    'rms_before': float(np.sqrt(((base_vals[FIT] - r0[FIT]) ** 2).mean())),
    'rms_after': float(np.sqrt(((vals[FIT] - r1[FIT]) ** 2).mean())),
    'max_surface_move_mm': round(float(mv.max() * 1000), 3),
    'off_arm_move_mm': round(float(np.linalg.norm(o1 - o0, axis=1).max() * 1000), 6),
}, indent=2), encoding='utf-8')
print('\nOPT3_DONE')