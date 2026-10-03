"""Measure the roll each left-arm bone imposes, then test the elbow fix.

The fix is one operation: an extra world-space twist on `lowerarm_l` about the
live forearm axis, with every descendant's world matrix preserved.  That leaves
the grip, the hand and the distal forearm untouched and only re-times the
pronation ramp across the band the elbow actually skins.
"""
import json
import math
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector

ROOT = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922')
HERE = ROOT / 'Elbow39'

CHAIN = ['upperarm_twist_01_l', 'upperarm_twist_02_l', 'lowerarm_l',
         'lowerarm_twist_02_l', 'lowerarm_twist_01_l']
STATION = {'upperarm_twist_01_l': -0.31, 'upperarm_twist_02_l': -0.18,
           'lowerarm_l': 0.23, 'lowerarm_twist_02_l': 0.35,
           'lowerarm_twist_01_l': 0.85, 'hand_l': 1.00}

mesh_data = np.load(HERE / 'v7_mesh.npz', allow_pickle=True)
author = np.load(HERE / 'author_rig.npz', allow_pickle=True)
V7_VERTS = mesh_data['verts'].astype(np.float64)
V7_WIDX = mesh_data['w_idx']
V7_WVAL = mesh_data['w_val'].astype(np.float64)
V7_BONES = list(mesh_data['bones'])
V7_REST = mesh_data['rest'].astype(np.float64)
AU_BONES = list(author['bones'])
AU_REST_M = [Matrix(m.tolist()) for m in author['rest'].astype(np.float64)]
AU_INDEX = {n: i for i, n in enumerate(AU_BONES)}
N_V7 = len(V7_BONES)
BI = {n: V7_BONES.index(n) for n in
      ('upperarm_l', 'lowerarm_l', 'hand_l', *CHAIN)}

e_rest = V7_REST[BI['lowerarm_l']][:3, 3].copy()
s_rest = V7_REST[BI['upperarm_l']][:3, 3].copy()
w_rest = V7_REST[BI['hand_l']][:3, 3].copy()
u0 = (e_rest - s_rest) / np.linalg.norm(e_rest - s_rest)
f0 = (w_rest - e_rest) / np.linalg.norm(w_rest - e_rest)
FLEN = float(np.linalg.norm(w_rest - e_rest))
rel = V7_VERTS - e_rest
t_all = rel @ f0 / FLEN
radius = np.linalg.norm(rel - np.outer(t_all * FLEN, f0), axis=1)
ARM = (radius < 0.070) & (t_all > -0.60) & (t_all < 1.05)

p1_0 = u0 - (u0 @ f0) * f0
p1_0 /= np.linalg.norm(p1_0)
p2_0 = np.cross(f0, p1_0)
perp0 = rel - np.outer(rel @ f0, f0)
phi0 = np.arctan2(perp0 @ p2_0, perp0 @ p1_0)
HOMO = np.concatenate([V7_VERTS, np.ones((len(V7_VERTS), 1))], axis=1)


def skin_verts(skin):
    out = np.zeros((len(V7_VERTS), 3))
    for k in range(V7_WIDX.shape[1]):
        idx = V7_WIDX[:, k]
        w = V7_WVAL[:, k]
        act = (idx >= 0) & (w > 0.0)
        out[act] += w[act, None] * np.einsum('nij,nj->ni', skin[idx[act]],
                                             HOMO[act])[:, :3]
    return out


def roll_of(posed, e, u, f, rest_phi=None):
    p1 = u - (u @ f) * f
    p1 /= np.linalg.norm(p1)
    p2 = np.cross(f, p1)
    rp = posed - e
    pp = rp - np.outer(rp @ f, f)
    phip = np.arctan2(pp @ p2, pp @ p1)
    ref = phi0 if rest_phi is None else rest_phi
    return np.degrees((phip - ref + np.pi) % (2 * np.pi) - np.pi)


def rest_phi_of(points):
    d = points - e_rest
    pp = d - np.outer(d @ f0, f0)
    return np.arctan2(pp @ p2_0, pp @ p1_0)


def frame_axes(rig):
    s = np.array(rig.pose.bones['upperarm_l'].matrix.translation)
    e = np.array(rig.pose.bones['lowerarm_l'].matrix.translation)
    w = np.array(rig.pose.bones['hand_l'].matrix.translation)
    return s, e, w, (e - s) / np.linalg.norm(e - s), (w - e) / np.linalg.norm(w - e)


def load(blend, action_name, frame):
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    scene = bpy.context.scene
    rig = bpy.data.objects['PKM_Manny_Rig']
    action = bpy.data.actions[action_name]
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    return rig


def delta_of(rig):
    return {n: (rig.pose.bones[n].matrix @ AU_REST_M[i].inverted())
            for i, n in enumerate(AU_BONES)}


def skin_from(delta, overrides=None):
    skin = np.tile(np.eye(4), (N_V7, 1, 1))
    for i, n in enumerate(V7_BONES):
        if n in delta:
            skin[i] = np.array((overrides or {}).get(n, delta[n]))
    return skin


def profile(posed, e, u, f, edges=np.arange(-0.25, 1.05, 0.05)):
    d = roll_of(posed, e, u, f)
    rows = []
    for lo in edges:
        sel = ARM & (t_all >= lo) & (t_all < lo + 0.05)
        if sel.sum() < 8:
            continue
        rows.append((round(float(lo + 0.025), 3), int(sel.sum()),
                     round(float(d[sel].mean()), 1),
                     round(float(d[sel].mean()), 1)))
    return rows


def roughness(rows):
    v = np.array([r[2] for r in rows])
    return float(np.abs(np.diff(v)).sum()), float(np.abs(np.diff(v)).max())


CLIP = (ROOT / 'Wrist12' / 'PKM_WristContact_Editable.blend',
        'PKM_Game_idle_Wrist12', 0)
rig = load(*CLIP)
delta = delta_of(rig)
s, e, w, u, f = frame_axes(rig)
base = skin_verts(skin_from(delta))
cur = profile(base, e, u, f)

# roll imposed by a single bone, probed on a synthetic ring at its station
probe_roll = {}
for name in CHAIN + ['hand_l']:
    t_b = STATION[name]
    c = e_rest + f0 * (t_b * FLEN)
    ang = np.linspace(0, 2 * np.pi, 24, endpoint=False)
    ring = c + np.outer(np.cos(ang), p1_0) * 0.045 + np.outer(np.sin(ang), p2_0) * 0.045
    hom = np.concatenate([ring, np.ones((len(ring), 1))], axis=1)
    p = (np.array(delta[name]) @ hom.T).T[:, :3]
    probe_roll[name] = float(roll_of(p, e, u, f, rest_phi_of(ring)).mean())

print('== bone-imposed roll at idle (about the live forearm axis) ==')
print('%6s %8s %10s' % ('station', 'roll', 'bone'))
for n, r in probe_roll.items():
    print('%6.2f %8.1f  %s' % (STATION[n], r, n))

print('\n== current surface roll profile ==')
for t, n, r, _ in cur:
    print('  t=%6.2f  n=%4d  roll=%7.1f' % (t, n, r))
tv, mx = roughness(cur)
print('total variation %.1f   max step %.1f' % (tv, mx))

# candidate: re-time the pronation ramp so it is linear in station from the
# elbow to the hand, anchored on the current hand roll
r_hand = probe_roll['hand_l']
rows = []
for frac_name, anchor in [('from_zero', 0.0),
                          ('from_elbow', cur[len(cur) // 2][2])]:
    for alpha in (0.5, 0.75, 1.0):
        t_la = STATION['lowerarm_l']
        target = anchor + (r_hand - anchor) * (t_la / STATION['hand_l']) * alpha
        d_extra = target - probe_roll['lowerarm_l']
        axis = Vector(f.tolist())
        extra = Matrix.Rotation(math.radians(d_extra), 4, axis)
        ov = {'lowerarm_l': extra @ delta['lowerarm_l']}
        posed = skin_verts(skin_from(delta, ov))
        pr = profile(posed, e, u, f)
        tv2, mx2 = roughness(pr)
        rows.append({'anchor': frac_name, 'alpha': alpha, 'd_extra': round(d_extra, 1),
                     'target': round(target, 1), 'tv': round(tv2, 1),
                     'max_step': round(mx2, 1),
                     'profile': [r[2] for r in pr]})
        print('\n-- %s alpha=%.2f  d(lowerarm_l)=%+.1f deg -> TV %.1f (was %.1f), '
              'max step %.1f (was %.1f)' % (frac_name, alpha, d_extra, tv2, tv, mx2, mx))
        print('   ' + ' '.join('%6.1f' % r[2] for r in pr))

(HERE / 'elbow_fit.json').write_text(
    json.dumps({'probe_roll': {k: round(v, 2) for k, v in probe_roll.items()},
                'current': cur, 'candidates': rows}, indent=2), encoding='utf-8')
print('\nFIT_DONE')