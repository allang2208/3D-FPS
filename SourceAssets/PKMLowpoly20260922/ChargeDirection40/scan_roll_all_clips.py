"""Authoritative left-elbow wring scan over every PKM clip.

Uses the validated Elbow39 metric (surface roll profile along the limb, its
worst adjacent-bin step, RMS against the frame's own pronation ramp, and total
variation).  For each clip it reports the AS-AUTHORED numbers and the numbers
the Elbow39 correction would produce, so a clip that is genuinely wrung shows up
as a large drop.

Nothing is written to any asset here: this is measurement only.
"""
import json
import math
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector

ROOT = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922')
HERE = ROOT / 'ChargeDirection40'
E39 = ROOT / 'Elbow39'

STATION = {'upperarm_twist_02_l': -0.18, 'lowerarm_l': 0.23,
           'lowerarm_twist_02_l': 0.35, 'lowerarm_twist_01_l': 0.85,
           'hand_l': 1.00}
RAMPED = ('lowerarm_l', 'lowerarm_twist_02_l', 'lowerarm_twist_01_l')
ORDER = ['lowerarm_l', 'lowerarm_twist_02_l', 'lowerarm_twist_01_l', 'hand_l']
ANCHOR = 'upperarm_twist_02_l'
CAP = {'lowerarm_l': 75.0, 'lowerarm_twist_02_l': 35.0, 'lowerarm_twist_01_l': 30.0}
FIT_LO, FIT_HI = -0.10, 0.90

# (label, blend, action substring, fps, stride)
CLIPS = (
    ('idle', ROOT / 'Wrist12' / 'PKM_WristContact_Editable.blend', 'idle', 60, 1),
    ('aim', ROOT / 'Wrist12' / 'PKM_WristContact_Editable.blend', 'aim', 60, 1),
    ('inspect', ROOT / 'Wrist12' / 'PKM_WristContact_Editable.blend', 'inspect', 60, 4),
    ('fire', ROOT / 'Feed13' / 'PKM_FiringFeed_Editable.blend', 'fire', 120, 1),
    ('aim_fire', ROOT / 'Feed13' / 'PKM_FiringFeed_Editable.blend', 'aim_fire', 120, 1),
    ('reload', ROOT / 'Reload16' / 'PKM_base_Reload_Editable.blend', 'reload', 120, 4),
    ('reload_empty', ROOT / 'Charge34' / 'PKM_base_ChargePush_Editable.blend', 'reload_empty', 120, 4),
    ('equip', ROOT / 'EquipCharge31' / 'PKM_base_EquipCharge_Editable.blend', 'equip', 120, 2),
    ('quick_melee', ROOT / 'Melee24' / 'PKM_base_Melee24.blend', 'melee', 120, 2),
    ('sprint_enter', ROOT / 'Combat17' / 'PKM_base_Combat_Editable.blend', 'sprint_enter', 120, 2),
    ('sprint_loop', ROOT / 'Combat17' / 'PKM_base_Combat_Editable.blend', 'sprint_loop', 120, 2),
    ('sprint_exit', ROOT / 'Combat17' / 'PKM_base_Combat_Editable.blend', 'sprint_exit', 120, 2),
)

mesh_data = np.load(E39 / 'v7_mesh.npz', allow_pickle=True)
author = np.load(E39 / 'author_rig.npz', allow_pickle=True)
V7_VERTS = mesh_data['verts'].astype(np.float64)
V7_WIDX = mesh_data['w_idx']
V7_WVAL = mesh_data['w_val'].astype(np.float64)
V7_BONES = list(mesh_data['bones'])
V7_REST = mesh_data['rest'].astype(np.float64)
AU_BONES = list(author['bones'])
AU_REST_M = [Matrix(m.tolist()) for m in author['rest'].astype(np.float64)]
AU_INDEX = {n: i for i, n in enumerate(AU_BONES)}
INDEX = {n: i for i, n in enumerate(V7_BONES)}

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


def stats(v, r0, slope, t0):
    d = np.diff(v[BIN_OK])
    return (float(np.clip(d, 0, None).max()),
            float(np.sqrt(((v[FIT] - (r0 + slope * (BIN_T - t0))[FIT]) ** 2).mean())),
            float(np.abs(d).sum()))


report = {}
cache = {}
for label, blend, token, fps, stride in CLIPS:
    if not blend.exists():
        report[label] = {'error': 'missing blend'}
        continue
    key = str(blend)
    if key not in cache:
        bpy.ops.wm.open_mainfile(filepath=key)
        cache[key] = [a.name for a in bpy.data.actions]
    names = [n for n in cache[key] if token.lower() in n.lower()]
    if not names:
        report[label] = {'error': 'no action matching %r' % token, 'actions': cache[key]}
        print('%-13s NO ACTION  %s' % (label, cache[key]))
        continue

    bpy.ops.wm.open_mainfile(filepath=key)
    scene = bpy.context.scene
    rig = bpy.data.objects['PKM_Manny_Rig']
    action = bpy.data.actions[names[0]]
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
    for frame in range(start, end + 1, stride):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        pose = {b.name: b.matrix.copy() for b in rig.pose.bones}
        delta = {n: pose[n] @ AU_REST_M[AU_INDEX[n]].inverted() for n in AU_BONES}
        s = np.array(pose['upperarm_l'].translation)
        e = np.array(pose['lowerarm_l'].translation)
        w = np.array(pose['hand_l'].translation)
        u = (e - s) / np.linalg.norm(e - s)
        f = (w - e) / np.linalg.norm(w - e)

        rolls = {}
        for name in (ANCHOR,) + tuple(ORDER):
            rolls[name] = roll_probe(delta[name], rings[name], rphis[name], e, u, f)
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
        va = roll_profile(deform(skin_a, THOMO, TI, TW, len(TV)), e, u, f)
        vb = roll_profile(deform(skin_b, THOMO, TI, TW, len(TV)), e, u, f)
        ba, ra, ta = stats(va, r0, slope, t0)
        bb, rb, tb = stats(vb, r0, slope, t0)
        rows.append({'frame': frame, 'seconds': round(frame / fps, 3),
                     'a_step': round(ba, 1), 'a_rms': round(ra, 1), 'a_tv': round(ta, 1),
                     'b_step': round(bb, 1), 'b_rms': round(rb, 1), 'b_tv': round(tb, 1)})

    sumr = {
        'action': names[0], 'fps': fps, 'frames': [start, end], 'samples': len(rows),
        'a_worst_step': max(r['a_step'] for r in rows),
        'a_mean_rms': round(sum(r['a_rms'] for r in rows) / len(rows), 1),
        'a_mean_tv': round(sum(r['a_tv'] for r in rows) / len(rows), 1),
        'b_worst_step': max(r['b_step'] for r in rows),
        'b_mean_rms': round(sum(r['b_rms'] for r in rows) / len(rows), 1),
        'b_mean_tv': round(sum(r['b_tv'] for r in rows) / len(rows), 1),
        'rows': rows,
    }
    report[label] = sumr
    print('%-13s %-26s %5d samp | as-authored  step %6.1f rms %5.1f tv %6.1f'
          ' | corrected  step %6.1f rms %5.1f tv %6.1f'
          % (label, names[0], sumr['samples'], sumr['a_worst_step'], sumr['a_mean_rms'],
             sumr['a_mean_tv'], sumr['b_worst_step'], sumr['b_mean_rms'],
             sumr['b_mean_tv']))

(HERE / 'left_roll_all_clips.json').write_text(
    json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
print('\nROLL_SCAN_DONE')