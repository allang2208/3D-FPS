"""Final elbow twist timing: forearm bones only, fixed pronation-ramp target."""
import json
import math
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector

ROOT = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922')
HERE = ROOT / 'Elbow39'
TOUCH = ['lowerarm_l', 'lowerarm_twist_02_l', 'lowerarm_twist_01_l']
FIT_LO, FIT_HI = -0.10, 0.90

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
      ('upperarm_l', 'lowerarm_l', 'hand_l', *TOUCH, 'upperarm_twist_02_l')}

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

# dominant bone per arm vertex, for reporting
DOM = {}
for name in ('upperarm_twist_01_l', 'upperarm_twist_02_l', 'lowerarm_l',
             'lowerarm_twist_02_l', 'lowerarm_twist_01_l', 'hand_l'):
    if name in V7_BONES:
        j = BI.get(name, V7_BONES.index(name))
        w = np.where(V7_WIDX == j, V7_WVAL, 0.0).sum(axis=1)
        DOM[name] = w > 0.5

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

BASE_SKIN = np.tile(np.eye(4), (len(V7_BONES), 1, 1))
for i, n in enumerate(V7_BONES):
    if n in delta:
        BASE_SKIN[i] = np.array(delta[n])


def apply(twists, skin=None):
    ov = np.copy(BASE_SKIN if skin is None else skin)
    for n, d in twists.items():
        if abs(d) < 1e-9:
            continue
        h = Vector(HEADS[n].tolist())
        R = (Matrix.Translation(h) @ Matrix.Rotation(math.radians(d), 4, FORE_AXIS)
             @ Matrix.Translation(-h))
        ov[BI[n]] = np.array(R @ delta[n])
    return ov


base_vals = profile(deform(BASE_SKIN), e, u, f)

# fixed target: linear pronation ramp between the elbow-side and wrist-side
# values of the *current* surface (both are accepted and stay put)
A = float(base_vals[(BIN_T > -0.05) & (BIN_T < 0.06) & BIN_OK].mean())
B = float(base_vals[(BIN_T > 0.82) & (BIN_T < 0.90) & BIN_OK].mean())
tA = float(BIN_T[(BIN_T > -0.05) & (BIN_T < 0.06) & BIN_OK].mean())
tB = float(BIN_T[(BIN_T > 0.82) & (BIN_T < 0.90) & BIN_OK].mean())
REF = A + (B - A) * (BIN_T - tA) / (tB - tA)


def cost(vals, twists):
    c = float(((vals[FIT] - REF[FIT]) ** 2).sum())
    d = np.diff(vals[BIN_OK])
    c += 4.0 * float((np.clip(d, 0.0, None) ** 2).sum())
    c += 3e-4 * sum(x * x for x in twists.values())
    return c


best = {n: 0.0 for n in TOUCH}
best_c = cost(base_vals, best)
print('anchors: A=%.1f at t=%.2f   B=%.1f at t=%.2f' % (A, tA, B, tB))
print('== before ==')
print('  profile ' + ' '.join('%6.1f' % v for v in base_vals))
print('  target  ' + ' '.join('%6.1f' % v for v in REF))
print('  rms %.2f  cost %.1f' % (
    float(np.sqrt(((base_vals[FIT] - REF[FIT]) ** 2).mean())), best_c))

for n in TOUCH:
    step = 64.0
    while step >= 2.0:
        improved = False
        for cand in (best[n] - step, best[n] + step):
            if abs(cand) > 140:
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
print('\n== after ==')
print('  profile ' + ' '.join('%6.1f' % v for v in vals))
d = np.diff(vals[BIN_OK])
print('  rms %.2f  max backward step %.2f  cost %.1f' % (
    float(np.sqrt(((vals[FIT] - REF[FIT]) ** 2).mean())),
    float(np.clip(d, 0, None).max()), best_c))
print('\ncorrection (deg, about the live forearm axis through each bone head):')
for n in TOUCH:
    print('   %-24s %+8.1f' % (n, best[n]))

posed0, posed1 = deform(BASE_SKIN), deform(apply(best))
mv = np.linalg.norm(posed1 - posed0, axis=1)
print('\narm surface displacement by dominant bone:')
for name, mask in DOM.items():
    sel = mask[AIDX]
    if sel.sum():
        print('   %-24s n=%4d  mean %6.2f  max %6.2f mm' % (
            name, sel.sum(), mv[sel].mean() * 1000, mv[sel].max() * 1000))

(HERE / 'elbow_optimize.json').write_text(json.dumps({
    'before': [None if np.isnan(v) else round(float(v), 2) for v in base_vals],
    'after': [None if np.isnan(v) else round(float(v), 2) for v in vals],
    'target': [round(float(v), 2) for v in REF],
    'correction_deg': {n: round(float(v), 2) for n, v in best.items()},
    'edges': [round(float(x), 3) for x in BIN_T],
    'rms_before': float(np.sqrt(((base_vals[FIT] - REF[FIT]) ** 2).mean())),
    'rms_after': float(np.sqrt(((vals[FIT] - REF[FIT]) ** 2).mean())),
    'max_surface_move_mm': round(float(mv.max() * 1000), 3),
}, indent=2), encoding='utf-8')
print('\nOPT4_DONE')