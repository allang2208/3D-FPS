"""Pre-fix source vs shipped edit, identical probes, PKM idle left arm.

Elbow39's repair ramps lowerarm_l / lowerarm_twist_02_l / lowerarm_twist_01_l onto
a straight line from upperarm_twist_02_l to hand_l.  Measure both actions with the
same rings so it is clear what that correction did and what it left behind.
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

CASES = [('pre-fix', ROOT / 'Wrist12' / 'PKM_WristContact_Editable.blend',
          'PKM_Game_idle_Wrist12'),
         ('shipped', E39 / 'Edit' / 'PKM_idle_Elbow39.blend', 'PKM_idle_Elbow39')]

# Elbow39's ring stations, and the true bone-head stations, in forearm lengths
STATION = {'upperarm_twist_01_l': -0.528, 'upperarm_twist_02_l': -0.264,
           'lowerarm_l': 0.000, 'lowerarm_twist_02_l': 0.333,
           'lowerarm_twist_01_l': 0.667, 'hand_l': 1.000}
E39_STATION = {'upperarm_twist_02_l': -0.18, 'lowerarm_l': 0.23,
               'lowerarm_twist_02_l': 0.35, 'lowerarm_twist_01_l': 0.85,
               'hand_l': 1.00}
CHAIN = ['upperarm_twist_01_l', 'upperarm_twist_02_l', 'lowerarm_l',
         'lowerarm_twist_02_l', 'lowerarm_twist_01_l', 'hand_l']

d = np.load(E39 / 'v7_mesh.npz', allow_pickle=True)
author = np.load(E39 / 'author_rig.npz', allow_pickle=True)
V = d['verts'].astype(np.float64)
WIDX, WVAL = d['w_idx'], d['w_val'].astype(np.float64)
BONES = list(d['bones'])
REST = d['rest'].astype(np.float64)
AU_BONES = list(author['bones'])
AU_REST_M = [Matrix(m.tolist()) for m in author['rest'].astype(np.float64)]
AU_INDEX = {n: i for i, n in enumerate(AU_BONES)}
IDX = {n: i for i, n in enumerate(BONES)}
HOMO = np.concatenate([V, np.ones((len(V), 1))], axis=1)

E_R = REST[IDX['lowerarm_l']][:3, 3]
S_R = REST[IDX['upperarm_l']][:3, 3]
W_R = REST[IDX['hand_l']][:3, 3]
B0 = (W_R - E_R) / np.linalg.norm(W_R - E_R)
FLEN = float(np.linalg.norm(W_R - E_R))
A0 = (E_R - S_R) / np.linalg.norm(E_R - S_R)
Q1 = A0 - (A0 @ B0) * B0
Q1 /= np.linalg.norm(Q1)
Q2 = np.cross(B0, Q1)

EDGES = np.arange(-0.45, 0.95, 0.05)
REL = V - E_R
TT = REL @ B0 / FLEN
RAD = np.linalg.norm(REL - np.outer(TT * FLEN, B0), axis=1)
BAND = (RAD < 0.075) & (TT > -0.45) & (TT < 0.95)
VS = np.where(BAND)[0]
BIN = np.digitize(TT[VS], EDGES) - 1
PERP = REL[VS] - np.outer((REL[VS] @ B0), B0)
PHI0 = np.arctan2(PERP @ Q2, PERP @ Q1)


def unwrap(v, ref, period=360.0):
    while v - ref > period / 2:
        v -= period
    while ref - v > period / 2:
        v += period
    return v


rows = {}
for tag, blend, action_name in CASES:
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    scene = bpy.context.scene
    rig = bpy.data.objects['PKM_Manny_Rig']
    act = bpy.data.actions[action_name]
    rig.animation_data.action = act
    rig.animation_data.action_slot = act.slots[0]
    scene.render.fps = 60
    scene.frame_set(int(act.frame_range[0]))
    bpy.context.view_layer.update()
    pose = {b.name: rig.pose.bones[b.name].matrix.copy() for b in rig.data.bones}
    delta = {n: pose[n] @ AU_REST_M[AU_INDEX[n]].inverted() for n in AU_BONES}

    e = np.array(pose['lowerarm_l'].translation)
    s = np.array(pose['upperarm_l'].translation)
    w = np.array(pose['hand_l'].translation)
    u = (e - s) / np.linalg.norm(e - s)
    f = (w - e) / np.linalg.norm(w - e)
    bend = math.degrees(math.acos(max(-1, min(1, float(u @ f)))))
    p1 = (u - (u @ f) * f)
    p1 /= np.linalg.norm(p1)
    p2 = np.cross(f, p1)

    out = {'bend': round(bend, 1), 'stations': {}, 'e39_stations': {}}
    for table, key in ((STATION, 'stations'), (E39_STATION, 'e39_stations')):
        prev, vals = None, {}
        for n in CHAIN:
            if n not in table:
                continue
            c = E_R + B0 * (table[n] * FLEN)
            ring = [c + math.cos(2 * math.pi * i / 24) * Q1 * 0.045
                    + math.sin(2 * math.pi * i / 24) * Q2 * 0.045 for i in range(24)]
            ph = []
            for p in ring:
                dd = p - E_R
                dd = dd - (dd @ B0) * B0
                ph.append(math.atan2(dd @ Q2, dd @ Q1))
            rs = []
            for p, rp in zip(ring, ph):
                h = delta[n] @ Vector((float(p[0]), float(p[1]), float(p[2])))
                dd = np.array([h.x, h.y, h.z]) - e
                dd = dd - (dd @ f) * f
                rs.append(math.degrees((math.atan2(dd @ p2, dd @ p1) - rp
                                        + math.pi) % (2 * math.pi) - math.pi))
            v = sum(rs) / len(rs)
            vals[n] = v if prev is None else unwrap(v, prev)
            prev = vals[n]
        out[key] = {n: round(vals[n], 1) for n in vals}
        out[key + '_steps'] = [round(vals[CHAIN[i + 1]] - vals[CHAIN[i]], 1)
                               for i in range(len(CHAIN) - 1)
                               if CHAIN[i] in vals and CHAIN[i + 1] in vals]

    # blended surface profile
    skin = np.tile(np.eye(4), (len(BONES), 1, 1))
    for i, n in enumerate(BONES):
        if n in delta:
            skin[i] = np.array(delta[n])
    P = np.zeros((len(VS), 3))
    hom = HOMO[VS]
    for k in range(WIDX.shape[1]):
        idx, wv = WIDX[VS, k], WVAL[VS, k]
        a = (idx >= 0) & (wv > 0)
        P[a] += wv[a, None] * np.einsum('nij,nj->ni', skin[idx[a]], hom[a])[:, :3]
    rp = P - e
    pp = rp - np.outer(rp @ f, f)
    phip = np.arctan2(pp @ p2, pp @ p1)
    dphi = np.degrees((phip - PHI0 + np.pi) % (2 * np.pi) - np.pi)
    prof = np.full(len(EDGES) - 1, np.nan)
    for b in range(len(EDGES) - 1):
        sel = BIN == b
        if sel.sum() >= 8:
            prof[b] = dphi[sel].mean()
    steps = np.diff(prof[~np.isnan(prof)])
    out['surface'] = [None if np.isnan(x) else round(float(x), 1) for x in prof]
    out['worst_step'] = round(float(np.clip(steps, 0, None).max()), 1)
    out['tv'] = round(float(np.abs(steps).sum()), 1)
    out['tv_signed'] = round(float(steps.sum()), 1)
    rows[tag] = out
    print('\n### %s (%s)  bend %.1f' % (tag, action_name, bend))
    print('  bone rolls at TRUE stations: ' +
          '  '.join('%s %+.1f' % (n.replace('_l', ''), out['stations'][n])
                    for n in out['stations']))
    print('    steps: ' + '  '.join('%+.1f' % x for x in out['stations_steps']))
    print('  bone rolls at E39 stations : ' +
          '  '.join('%s %+.1f' % (n.replace('_l', ''), out['e39_stations'][n])
                    for n in out['e39_stations']))
    print('    steps: ' + '  '.join('%+.1f' % x for x in out['e39_stations_steps']))
    print('  blended surface: worst step %.1f  TV %.1f  net %.1f'
          % (out['worst_step'], out['tv'], out['tv_signed']))

print('\n  t      pre-fix   shipped')
for b in range(len(EDGES) - 1):
    a = rows['pre-fix']['surface'][b]
    c = rows['shipped']['surface'][b]
    if a is None and c is None:
        continue
    print('  %+.3f  %8s %9s' % (EDGES[b] + 0.025,
                                'nan' if a is None else '%.1f' % a,
                                'nan' if c is None else '%.1f' % c))

(HERE / 'idle_prefix_vs_shipped.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
print('\nPREFIX_VS_SHIPPED_DONE')