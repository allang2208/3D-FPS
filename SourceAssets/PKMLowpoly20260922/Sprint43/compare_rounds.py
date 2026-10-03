"""Which round is actually best for the PKM sprint trio?

Two questions per round, per clip:
  * surface quality - worst backward step and total variation of the surface roll
    profile (wrap-safe: the circular quantity is unwrapped before differencing)
  * bone continuity - the largest per-frame change in any left-forearm bone's roll.
    A sweep of hundreds of degrees in one frame at 120 fps is a snap, and it is what
    the tactical sprint entry shows; the original authoring does not have it.
"""
import json
import math
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector

ROOT = Path(r'D:\FPS3D\FPSGAME\SourceAssets')
PKM = ROOT / 'PKMLowpoly20260922'
E39 = PKM / 'Elbow39'
HERE = PKM / 'Sprint43'
SRC = PKM / 'Combat17' / 'PKM_base_Combat_Editable.blend'

CHAIN = ['upperarm_l', 'upperarm_twist_01_l', 'upperarm_twist_02_l', 'lowerarm_l',
         'lowerarm_twist_02_l', 'lowerarm_twist_01_l', 'hand_l']
ROUNDS = ('original', 'elbow41', 'sprint43', 'sprint44')
CASES = (('sprint_enter', 'PKM17_base_sprint_enter', 'PKM_sprint_enter_Elbow41',
          'PKM_sprint_enter_Sprint43', 'PKM_sprint_enter_Sprint44'),
         ('sprint_loop', 'PKM17_base_sprint_loop', 'PKM_sprint_loop_Elbow41',
          'PKM_sprint_loop_Sprint43', 'PKM_sprint_loop_Sprint44'),
         ('sprint_exit', 'PKM17_base_sprint_exit', 'PKM_sprint_exit_Elbow41',
          'PKM_sprint_exit_Sprint43', 'PKM_sprint_exit_Sprint44'))
BLENDS = {'original': SRC,
          'elbow41': PKM / 'Elbow41' / 'Edit',
          'sprint43': PKM / 'Sprint43' / 'Edit',
          'sprint44': PKM / 'Sprint44' / 'Edit'}

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

RINGS = {}
for n in CHAIN:
    c = REST[IDX[n]][:3, 3]
    pts = [c + math.cos(2 * math.pi * i / 24) * Q1 * 0.045
           + math.sin(2 * math.pi * i / 24) * Q2 * 0.045 for i in range(24)]
    ph = []
    for p in pts:
        dd = p - E_R
        dd = dd - (dd @ B0) * B0
        ph.append(math.atan2(dd @ Q2, dd @ Q1))
    RINGS[n] = (pts, ph)


def unwrap_chain(vals):
    out = np.array(vals, dtype=np.float64)
    for i in range(1, len(out)):
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
    profs, rolls = [], []
    for frame in range(start, end + 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        pose = {b.name: rig.pose.bones[b.name].matrix.copy() for b in rig.pose.bones}
        e = np.array(pose['lowerarm_l'].translation)
        s = np.array(pose['upperarm_l'].translation)
        w = np.array(pose['hand_l'].translation)
        u = (e - s) / np.linalg.norm(e - s)
        f = (w - e) / np.linalg.norm(w - e)
        delta = {n: pose[n] @ AU_REST_M[AU_INDEX[n]].inverted() for n in AU_BONES}
        # per-bone roll
        p1 = u - (u @ f) * f
        p1 /= np.linalg.norm(p1)
        p2 = np.cross(f, p1)
        row = []
        for n in CHAIN:
            pts, ph = RINGS[n]
            vals = []
            for p, rp in zip(pts, ph):
                h = delta[n] @ Vector((float(p[0]), float(p[1]), float(p[2])))
                dd = np.array([h.x, h.y, h.z]) - e
                dd = dd - (dd @ f) * f
                vals.append(math.degrees((math.atan2(dd @ p2, dd @ p1) - rp
                                          + math.pi) % (2 * math.pi) - math.pi))
            row.append(sum(vals) / len(vals))
        rolls.append(unwrap_chain(row))
        # blended surface
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
        dphi = np.degrees((np.arctan2(pp @ p2, pp @ p1) - PHI0 + np.pi)
                          % (2 * np.pi) - np.pi)
        prof = np.full(NB, np.nan)
        for b in range(NB):
            sel = BIN == b
            if sel.sum() >= 8:
                prof[b] = dphi[sel].mean()
        profs.append(prof)
    return np.array(profs), np.array(rolls), start, end


summary = {}
for label, a0, a1, a2, a3 in CASES:
    print('\n=== %s ===' % label)
    print('  %-9s %10s %8s   %s' % ('round', 'worst_step', 'TV', 'max bone jump/frame (deg)'))
    for rnd, aname in zip(ROUNDS, (a0, a1, a2, a3)):
        blend = BLENDS[rnd]
        path = blend if blend.is_file() else blend / (aname + '.blend')
        profs, rolls, start, end = measure(path, aname)
        # unwrap each bone's roll across frames before differencing, otherwise the
        # +/-180 crossing of a circular quantity reads as a 350 deg snap
        rr = np.array(rolls, dtype=np.float64)
        for j in range(rr.shape[1]):
            for i in range(1, len(rr)):
                while rr[i, j] - rr[i - 1, j] > 180.0:
                    rr[i, j] -= 360.0
                while rr[i - 1, j] - rr[i, j] > 180.0:
                    rr[i, j] += 360.0
        worst = tv = 0.0
        for prof in profs:
            v = unwrap_chain(np.nan_to_num(prof[FIT], nan=0.0))
            d = np.diff(v)
            worst = max(worst, float(np.clip(d, 0, None).max()))
            tv = max(tv, float(np.abs(d).sum()))
        jump = float(np.abs(np.diff(rr, axis=0)).max())
        summary['%s/%s' % (label, rnd)] = {
            'worst_step': round(worst, 1), 'tv': round(tv, 1),
            'max_bone_jump_per_frame': round(jump, 1), 'frames': end - start + 1}
        print('  %-9s %10.1f %8.1f   %8.1f' % (rnd, worst, tv, jump))

(HERE / 'compare_rounds.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
print('\nCOMPARE_ROUNDS_DONE')