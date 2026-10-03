"""Full-clip verification of the Elbow39 pronation re-timing.

Re-derives the correction in memory from the source blends (same rule as
author_elbow39.py) and measures, on the real V7 PKM arm surface with its own
weights, for every frame of all three clips:
  * the roll profile along the limb and its worst backward step
  * RMS against the frame's own linear pronation ramp
  * hand / elbow / wrist drift and off-arm surface movement
"""
import json
import math
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector

ROOT = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922')
HERE = ROOT / 'Elbow39'

STATION = {'upperarm_twist_02_l': -0.18, 'lowerarm_l': 0.23,
           'lowerarm_twist_02_l': 0.35, 'lowerarm_twist_01_l': 0.85,
           'hand_l': 1.00}
RAMPED = ('lowerarm_l', 'lowerarm_twist_02_l', 'lowerarm_twist_01_l')
ORDER = ['lowerarm_l', 'lowerarm_twist_02_l', 'lowerarm_twist_01_l', 'hand_l']
ANCHOR = 'upperarm_twist_02_l'
CAP = {'lowerarm_l': 75.0, 'lowerarm_twist_02_l': 35.0, 'lowerarm_twist_01_l': 30.0}
FIT_LO, FIT_HI = -0.10, 0.90

CLIPS = (
    (ROOT / 'Wrist12' / 'PKM_WristContact_Editable.blend',
     'PKM_Game_idle_Wrist12', 60, 1),
    (ROOT / 'Reload16' / 'PKM_base_Reload_Editable.blend',
     'PKM16_base_reload', 120, 4),
    (ROOT / 'Charge34' / 'PKM_base_ChargePush_Editable.blend',
     'PKM34_base_reload_empty', 120, 4),
)

mesh_data = np.load(HERE / 'v7_mesh.npz', allow_pickle=True)
author = np.load(HERE / 'author_rig.npz', allow_pickle=True)
V7_VERTS = mesh_data['verts'].astype(np.float64)
V7_WIDX = mesh_data['w_idx']
V7_WVAL = mesh_data['w_val'].astype(np.float64)
V7_BONES = list(mesh_data['bones'])
V7_REST = mesh_data['rest'].astype(np.float64)
AU_BONES = list(author['bones'])
AU_REST = author['rest'].astype(np.float64)
AU_REST_M = [Matrix(m.tolist()) for m in AU_REST]
INDEX = {n: i for i, n in enumerate(V7_BONES)}
HOMO = np.concatenate([V7_VERTS, np.ones((len(V7_VERTS), 1))], axis=1)

e_rest = V7_REST[INDEX['lowerarm_l']][:3, 3].copy()
s_rest = V7_REST[INDEX['upperarm_l']][:3, 3].copy()
w_rest = V7_REST[INDEX['hand_l']][:3, 3].copy()
u0 = (e_rest - s_rest) / np.linalg.norm(e_rest - s_rest)
f0 = (w_rest - e_rest) / np.linalg.norm(w_rest - e_rest)
FLEN = float(np.linalg.norm(w_rest - e_rest))
rel = V7_VERTS - e_rest
t_all = rel @ f0 / FLEN
radius = np.linalg.norm(rel - np.outer(t_all * FLEN, f0), axis=1)
ARM = (radius < 0.070) & (t_all > -0.30) & (t_all < 0.92)
AIDX = np.where(ARM)[0]
TV, TI, TW, TT = V7_VERTS[AIDX], V7_WIDX[AIDX], V7_WVAL[AIDX], t_all[AIDX]
THOMO = np.concatenate([TV, np.ones((len(TV), 1))], axis=1)
OFFIDX = np.where(~ARM)[0]
OHOMO = np.concatenate([V7_VERTS[OFFIDX], np.ones((len(OFFIDX), 1))], axis=1)
OW, OI = V7_WVAL[OFFIDX], V7_WIDX[OFFIDX]

perp0 = (TV - e_rest) - np.outer((TV - e_rest) @ f0, f0)
p1_0 = u0 - (u0 @ f0) * f0
p1_0 /= np.linalg.norm(p1_0)
p2_0 = np.cross(f0, p1_0)
phi0 = np.arctan2(perp0 @ p2_0, perp0 @ p1_0)
EDGES = np.arange(-0.30, 0.92, 0.05)
BIN = np.digitize(TT, EDGES) - 1
NB = len(EDGES) - 1
BIN_T = EDGES[:-1] + 0.025
BIN_OK = np.array([(BIN == b).sum() >= 8 for b in range(NB)])
FIT = BIN_OK & (BIN_T >= FIT_LO) & (BIN_T <= FIT_HI)


def deform(skin, homo, wi, ww, n):
    out = np.zeros((n, 3))
    for k in range(wi.shape[1]):
        idx, w = wi[:, k], ww[:, k]
        act = (idx >= 0) & (w > 0.0)
        out[act] += w[act, None] * np.einsum('nij,nj->ni', skin[idx[act]],
                                             homo[act])[:, :3]
    return out


def roll_profile(posed, e, u, f):
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


def unwrap(v, ref, period=360.0):
    while v - ref > period / 2:
        v -= period
    while ref - v > period / 2:
        v += period
    return v


def roll_probe(matrix, ring, rest_phi, e, u, f):
    p1 = (Vector(u) - Vector(u).dot(Vector(f)) * Vector(f)).normalized()
    p2 = Vector(f).cross(p1)
    out = []
    for v, rp in zip(ring, rest_phi):
        h = matrix @ v
        d = Vector((h.x, h.y, h.z)) - Vector(e)
        d = d - d.dot(Vector(f)) * Vector(f)
        out.append(math.degrees((math.atan2(d.dot(p2), d.dot(p1)) - rp
                                 + math.pi) % (2 * math.pi) - math.pi))
    return sum(out) / len(out)


summary = {}
for blend, action_name, fps, stride in CLIPS:
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    scene = bpy.context.scene
    rig = bpy.data.objects['PKM_Manny_Rig']
    action = bpy.data.actions[action_name]
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    scene.render.fps = int(fps)
    scene.render.fps_base = 1.0
    rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
    start, end = map(int, action.frame_range)

    e_r = rest['lowerarm_l'].translation
    s_r = rest['upperarm_l'].translation
    w_r = rest['hand_l'].translation
    a0 = (e_r - s_r).normalized()
    b0 = (w_r - e_r).normalized()
    flen = (w_r - e_r).length
    q1 = (a0 - a0.dot(b0) * b0).normalized()
    q2 = b0.cross(q1)
    rings, rphis = {}, {}
    for name in STATION:
        c = e_r + b0 * (STATION[name] * flen)
        ring = [c + math.cos(2 * math.pi * i / 24) * q1 * 0.045
                + math.sin(2 * math.pi * i / 24) * q2 * 0.045 for i in range(24)]
        rings[name] = ring
        rphis[name] = []
        for v in ring:
            d = v - e_r
            d = d - d.dot(b0) * b0
            rphis[name].append(math.atan2(d.dot(q2), d.dot(q1)))

    rows = []
    worst_before = worst_after = 0.0
    worst_frame = None
    for frame in range(start, end + 1, stride):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        pose = {b.name: b.matrix.copy() for b in rig.pose.bones}
        delta = {n: pose[n] @ AU_REST_M[AU_BONES.index(n)].inverted()
                 for n in AU_BONES}
        s = np.array(pose['upperarm_l'].translation)
        e = np.array(pose['lowerarm_l'].translation)
        w = np.array(pose['hand_l'].translation)
        u = (e - s) / np.linalg.norm(e - s)
        f = (w - e) / np.linalg.norm(w - e)

        rolls = {}
        for name in (ANCHOR,) + tuple(ORDER):
            rolls[name] = roll_probe(delta[name], rings[name], rphis[name],
                                     e, u, f)
        chain = [ANCHOR] + list(ORDER)
        for i in range(1, len(chain)):
            rolls[chain[i]] = unwrap(rolls[chain[i]], rolls[chain[i - 1]])
        t0, r0 = STATION[ANCHOR], rolls[ANCHOR]
        t1, r1 = STATION['hand_l'], rolls['hand_l']
        slope = (r1 - r0) / (t1 - t0)
        corr = {}
        for name in RAMPED:
            want = (r0 + slope * (STATION[name] - t0)) - rolls[name]
            corr[name] = max(-CAP[name], min(CAP[name], want))

        fv = Vector(f.tolist())
        delta2 = dict(delta)
        for name in RAMPED:
            if abs(corr[name]) < 1e-9:
                continue
            h = pose[name].translation
            delta2[name] = (Matrix.Translation(h)
                            @ Matrix.Rotation(math.radians(corr[name]), 4, fv)
                            @ Matrix.Translation(-h) @ delta[name])

        skin_a = np.tile(np.eye(4), (len(V7_BONES), 1, 1))
        skin_b = np.tile(np.eye(4), (len(V7_BONES), 1, 1))
        for i, n in enumerate(V7_BONES):
            if n in delta:
                skin_a[i] = np.array(delta[n])
                skin_b[i] = np.array(delta2[n])

        pa = deform(skin_a, THOMO, TI, TW, len(TV))
        pb = deform(skin_b, THOMO, TI, TW, len(TV))
        va = roll_profile(pa, e, u, f)
        vb = roll_profile(pb, e, u, f)

        def stats(v):
            d = np.diff(v[BIN_OK])
            return (float(np.clip(d, 0, None).max()),
                    float(np.sqrt(((v[FIT] - (r0 + slope * (BIN_T - t0))[FIT]) ** 2).mean())),
                    float(np.abs(d).sum()))

        ba, ra, ta = stats(va)
        bb, rb, tb = stats(vb)
        hand_move = float(np.linalg.norm(
            deform(skin_b, np.concatenate([V7_VERTS[[INDEX['hand_l']]],
                                           np.ones((1, 1))], axis=1),
                   np.array([[INDEX['hand_l']]]), np.array([[1.0]]), 1)
            - deform(skin_a, np.concatenate([V7_VERTS[[INDEX['hand_l']]],
                                             np.ones((1, 1))], axis=1),
                     np.array([[INDEX['hand_l']]]), np.array([[1.0]]), 1)))
        oa = deform(skin_a, OHOMO, OI, OW, len(OFFIDX))
        ob = deform(skin_b, OHOMO, OI, OW, len(OFFIDX))
        off_move = float(np.linalg.norm(ob - oa, axis=1).max())
        rows.append({'frame': frame, 'sec': round(frame / fps, 3),
                     'back_before': round(ba, 2), 'back_after': round(bb, 2),
                     'rms_before': round(ra, 2), 'rms_after': round(rb, 2),
                     'tv_before': round(ta, 1), 'tv_after': round(tb, 1),
                     'corr': {k: round(v, 1) for k, v in corr.items()},
                     'off_move_mm': round(off_move * 1000, 4)})
        if ba > worst_before:
            worst_before, worst_frame = ba, len(rows) - 1
        worst_after = max(worst_after, bb)

    n = len(rows)
    summary[action_name] = {
        'frames': n, 'fps': fps,
        'worst_backward_before': round(max(r['back_before'] for r in rows), 2),
        'worst_backward_after': round(max(r['back_after'] for r in rows), 2),
        'mean_rms_before': round(float(np.mean([r['rms_before'] for r in rows])), 2),
        'mean_rms_after': round(float(np.mean([r['rms_after'] for r in rows])), 2),
        'max_off_arm_move_mm': round(max(r['off_move_mm'] for r in rows), 4),
        'rows': rows,
    }
    print('\n=== %s (%d sampled frames, %g Hz) ===' % (action_name, n, fps))
    print('  worst backward step : %.1f -> %.1f deg' % (
        summary[action_name]['worst_backward_before'],
        summary[action_name]['worst_backward_after']))
    print('  mean RMS to ramp    : %.1f -> %.1f deg' % (
        summary[action_name]['mean_rms_before'],
        summary[action_name]['mean_rms_after']))
    print('  max off-arm move    : %.4f mm' % summary[action_name]['max_off_arm_move_mm'])
    for r in sorted(rows, key=lambda r: -r['back_before'])[:5]:
        print('   worst @ %6.2fs  back %6.1f -> %5.1f  rms %5.1f -> %5.1f  corr %s' % (
            r['sec'], r['back_before'], r['back_after'], r['rms_before'],
            r['rms_after'], r['corr']))

(HERE / 'verify_elbow39.json').write_text(json.dumps(summary, indent=2),
                                          encoding='utf-8')
print('\nVERIFY39_DONE')