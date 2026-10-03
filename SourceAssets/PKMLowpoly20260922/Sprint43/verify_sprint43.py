"""Verify Sprint43 on the PKM tactical sprint, wrap-safe.

The raw band-to-band difference in a circular quantity explodes whenever the
profile crosses +/-180, which is what the 76.3 reading is suspected to be.  This
re-measures both rounds and reports the raw and the unwrapped step, plus the hand
chain, so a wrap cannot be mistaken for a defect (or a fix).
"""
import json
import math
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix

ROOT = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922')
E39 = ROOT / 'Elbow39'
HERE = ROOT / 'Sprint43'

CASES = (
    ('sprint_enter', ROOT / 'Elbow41' / 'Edit' / 'PKM_sprint_enter_Elbow41.blend',
     'PKM_sprint_enter_Elbow41', HERE / 'Edit' / 'PKM_sprint_enter_Sprint43.blend',
     'PKM_sprint_enter_Sprint43'),
    ('sprint_loop', ROOT / 'Elbow41' / 'Edit' / 'PKM_sprint_loop_Elbow41.blend',
     'PKM_sprint_loop_Elbow41', HERE / 'Edit' / 'PKM_sprint_loop_Sprint43.blend',
     'PKM_sprint_loop_Sprint43'),
    ('sprint_exit', ROOT / 'Elbow41' / 'Edit' / 'PKM_sprint_exit_Elbow41.blend',
     'PKM_sprint_exit_Elbow41', HERE / 'Edit' / 'PKM_sprint_exit_Sprint43.blend',
     'PKM_sprint_exit_Sprint43'),
)
HAND = ['hand_l', 'thumb_01_l', 'thumb_02_l', 'thumb_03_l', 'index_01_l',
        'index_02_l', 'index_03_l', 'middle_01_l', 'middle_02_l', 'middle_03_l',
        'ring_01_l', 'ring_02_l', 'ring_03_l', 'pinky_01_l', 'pinky_02_l',
        'pinky_03_l']

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
OK = np.array([(BIN == b).sum() >= 8 for b in range(NB)])
FIT = OK & (EDGES[:-1] + 0.025 >= -0.10) & (EDGES[:-1] + 0.025 <= 0.90)


def unwrap_prof(vals):
    """Take the branch of each band that keeps steps small (circular quantity)."""
    out = np.array(vals, dtype=np.float64)
    for i in range(1, len(out)):
        if np.isnan(out[i]) or np.isnan(out[i - 1]):
            continue
        while out[i] - out[i - 1] > 180.0:
            out[i] -= 360.0
        while out[i - 1] - out[i] > 180.0:
            out[i] += 360.0
    return out


def measure(blend, action_name):
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    scene = bpy.context.scene
    rig = bpy.data.objects['PKM_Manny_Rig']
    act = bpy.data.actions[action_name]
    rig.animation_data.action = act
    rig.animation_data.action_slot = act.slots[0]
    scene.render.fps = 120
    start, end = map(int, act.frame_range)
    per_frame, hands = [], []
    for frame in range(start, end + 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        pose = {b.name: rig.pose.bones[b.name].matrix.copy() for b in rig.pose.bones}
        hands.append({n: np.array(pose[n]) for n in HAND if n in pose})
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
        per_frame.append(prof)
    return per_frame, hands, start, end


def stats(per_frame):
    raw = unwrapped = tv = 0.0
    worst_frame = None
    for i, prof in enumerate(per_frame):
        v = prof[FIT]
        dv = np.diff(v)
        r = float(np.clip(dv, 0, None).max())
        u = unwrap_prof(np.nan_to_num(v, nan=0.0))
        du = np.diff(u)
        ub = float(np.clip(du, 0, None).max())
        t = float(np.abs(du).sum())
        if ub > unwrapped:
            unwrapped, worst_frame = ub, i
        raw = max(raw, r)
        tv = max(tv, t)
    return raw, unwrapped, tv, worst_frame


summary = {}
for label, src_blend, src_act, new_blend, new_act in CASES:
    print('\n=== %s ===' % label)
    res = {}
    for tag, blend, act in (('before', src_blend, src_act), ('after', new_blend, new_act)):
        pf, hands, start, end = measure(blend, act)
        raw, unw, tv, wf = stats(pf)
        res[tag] = {'raw_worst_step': round(raw, 1), 'worst_step': round(unw, 1),
                    'tv': round(tv, 1), 'worst_frame': wf, 'frames': end - start + 1}
        res[tag + '_hands'] = hands
        print('  %-7s %3d frames | raw worst step %7.1f | unwrapped %6.1f | TV %6.1f'
              % (tag, end - start + 1, raw, unw, tv))
    a, b = res['before_hands'], res['after_hands']
    worst, wb = 0.0, ''
    for fa, fb in zip(a, b):
        for n in fa:
            dd = float(np.abs(fa[n] - fb[n]).max())
            if dd > worst:
                worst, wb = dd, n
    res['hand_chain_max_delta'] = worst
    res['hand_chain_worst_bone'] = wb
    print('  hand chain max |matrix delta| before -> after: %.3e  (%s)' % (worst, wb))
    summary[label] = res

(HERE / 'verify_sprint43.json').write_text(
    json.dumps({k: {kk: vv for kk, vv in v.items() if not kk.endswith('_hands')}
                for k, v in summary.items()}, indent=2, ensure_ascii=False),
    encoding='utf-8')
print('\nVERIFY_SPRINT43_DONE')