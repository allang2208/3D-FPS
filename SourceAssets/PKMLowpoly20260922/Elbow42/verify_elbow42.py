"""Independent verification of Elbow42 on the PKM idle left forearm.

Re-measures the surface roll profile of all three rounds with the same probes,
and checks the hand chain frame by frame against the shipped round.
"""
import json
import math
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix

ROOT = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922')
E39 = ROOT / 'Elbow39'
HERE = ROOT / 'Elbow42'

CASES = [
    ('pre-fix', ROOT / 'Wrist12' / 'PKM_WristContact_Editable.blend',
     'PKM_Game_idle_Wrist12'),
    ('shipped', E39 / 'Edit' / 'PKM_idle_Elbow39.blend', 'PKM_idle_Elbow39'),
    ('elbow42', HERE / 'Edit' / 'PKM_idle_Elbow42.blend', 'PKM_idle_Elbow42'),
]
HAND_CHAIN = ['lowerarm_l', 'lowerarm_twist_01_l', 'lowerarm_twist_02_l',
              'hand_l', 'thumb_01_l', 'thumb_02_l', 'thumb_03_l',
              'index_01_l', 'index_02_l', 'index_03_l',
              'middle_01_l', 'middle_02_l', 'middle_03_l',
              'ring_01_l', 'ring_02_l', 'ring_03_l',
              'pinky_01_l', 'pinky_02_l', 'pinky_03_l']

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

EDGES = np.arange(-0.30, 0.92, 0.05)
REL = V - E_R
TT = REL @ B0 / FLEN
RAD = np.linalg.norm(REL - np.outer(TT * FLEN, B0), axis=1)
BAND = (RAD < 0.070) & (TT > -0.30) & (TT < 0.92)
VS = np.where(BAND)[0]
BIN = np.digitize(TT[VS], EDGES) - 1
PERP = REL[VS] - np.outer((REL[VS] @ B0), B0)
PHI0 = np.arctan2(PERP @ Q2, PERP @ Q1)
NB = len(EDGES) - 1
BIN_OK = np.array([(BIN == b).sum() >= 8 for b in range(NB)])
FIT = BIN_OK & (EDGES[:-1] + 0.025 >= -0.10) & (EDGES[:-1] + 0.025 <= 0.90)

results = {}
hands = {}
for tag, blend, action_name in CASES:
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    scene = bpy.context.scene
    rig = bpy.data.objects['PKM_Manny_Rig']
    act = bpy.data.actions[action_name]
    rig.animation_data.action = act
    rig.animation_data.action_slot = act.slots[0]
    scene.render.fps = 60
    start, end = map(int, act.frame_range)

    profs, hand_mats = [], []
    for frame in range(start, end + 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        pose = {b.name: rig.pose.bones[b.name].matrix.copy() for b in rig.pose.bones}
        hand_mats.append({n: np.array(pose[n]) for n in HAND_CHAIN})
        if frame in (start, (start + end) // 2, end):
            e = np.array(pose['lowerarm_l'].translation)
            s = np.array(pose['upperarm_l'].translation)
            w = np.array(pose['hand_l'].translation)
            u = (e - s) / np.linalg.norm(e - s)
            f = (w - e) / np.linalg.norm(w - e)
            delta = {n: pose[n] @ AU_REST_M[AU_INDEX[n]].inverted() for n in AU_BONES}
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
            p1 = u - (u @ f) * f
            p1 /= np.linalg.norm(p1)
            p2 = np.cross(f, p1)
            rp = P - e
            pp = rp - np.outer(rp @ f, f)
            dphi = np.degrees((np.arctan2(pp @ p2, pp @ p1) - PHI0 + np.pi)
                              % (2 * np.pi) - np.pi)
            prof = np.full(NB, np.nan)
            for b in range(NB):
                sel = BIN == b
                if sel.sum() >= 8:
                    prof[b] = dphi[sel].mean()
            profs.append((frame, prof))
    hands[tag] = hand_mats
    worst = max(float(np.clip(np.diff(p[FIT]), 0, None).max()) for _, p in profs)
    tv = max(float(np.abs(np.diff(p[FIT])).sum()) for _, p in profs)
    net = np.diff(profs[0][1][FIT]).sum()
    results[tag] = {'frames': end - start + 1, 'action': action_name,
                    'worst_step': round(worst, 2), 'tv': round(tv, 2),
                    'net': round(float(net), 2),
                    'profile': [None if np.isnan(x) else round(float(x), 1)
                                for x in profs[0][1]]}
    print('%-8s %-22s frames %3d | worst backward step %5.2f | TV %6.2f | net %7.2f'
          % (tag, action_name, end - start + 1, worst, tv, net))

# hand chain must be bit-identical between shipped and elbow42
a, b = hands['shipped'], hands['elbow42']
worst = 0.0
worst_bone = ''
for fa, fb in zip(a, b):
    for n in HAND_CHAIN:
        dd = float(np.abs(fa[n] - fb[n]).max())
        if dd > worst:
            worst, worst_bone = dd, n
print('\nhand chain max |matrix delta| shipped -> elbow42: %.3e  (%s)' % (worst, worst_bone))
results['hand_chain_max_delta'] = worst
results['hand_chain_worst_bone'] = worst_bone

print('\n  t      pre-fix   shipped   elbow42')
for i in range(NB):
    p = [results[k]['profile'][i] for k in ('pre-fix', 'shipped', 'elbow42')]
    if all(x is None for x in p):
        continue
    print('  %+.3f  %8s %9s %9s'
          % (EDGES[i] + 0.025,
             *['nan' if x is None else '%.1f' % x for x in p]))

(HERE / 'verify_elbow42.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
print('\nVERIFY_ELBOW42_DONE')