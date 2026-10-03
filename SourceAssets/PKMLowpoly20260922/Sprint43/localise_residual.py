"""Where exactly is the surviving 71.2 deg step in the PKM sprint entry?"""
import json
import math
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix

ROOT = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922')
E39 = ROOT / 'Elbow39'
HERE = ROOT / 'Sprint43'

BLEND = HERE / 'Edit' / 'PKM_sprint_enter_Sprint43.blend'
ACTION = 'PKM_sprint_enter_Sprint43'

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

W = np.zeros((len(V), len(BONES)))
for k in range(WIDX.shape[1]):
    idx, w = WIDX[:, k], WVAL[:, k]
    a = (idx >= 0) & (w > 0)
    np.add.at(W, (np.where(a)[0], idx[a]), w[a])

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
CENT = EDGES[:-1] + 0.025

bpy.ops.wm.open_mainfile(filepath=str(BLEND))
scene = bpy.context.scene
rig = bpy.data.objects['PKM_Manny_Rig']
act = bpy.data.actions[ACTION]
rig.animation_data.action = act
rig.animation_data.action_slot = act.slots[0]
scene.render.fps = 120
start, end = map(int, act.frame_range)

print('frame  worst_step  at t    |  profile across the fitted band')
for frame in range(start, end + 1):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    pose = {b.name: rig.pose.bones[b.name].matrix.copy() for b in rig.pose.bones}
    e = np.array(pose['lowerarm_l'].translation)
    s = np.array(pose['upperarm_l'].translation)
    w = np.array(pose['hand_l'].translation)
    u = (e - s) / np.linalg.norm(e - s)
    f = (w - e) / np.linalg.norm(w - e)
    bend = math.degrees(math.acos(max(-1, min(1, float(u @ f)))))
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
    dphi = np.degrees((np.arctan2(pp @ p2, pp @ p1) - PHI0 + np.pi) % (2 * np.pi) - np.pi)
    prof = np.full(NB, np.nan)
    for b in range(NB):
        sel = BIN == b
        if sel.sum() >= 8:
            prof[b] = dphi[sel].mean()
    v = prof[OK]
    t = CENT[OK]
    dv = np.diff(v)
    i = int(np.argmax(dv))
    print('%5d  %10.1f  %+.3f  bend %5.1f | %s'
          % (frame, float(np.clip(dv, 0, None).max()), t[i],
             bend, ' '.join('%.0f' % x for x in v)))

print('\nSPRINT43_LOCALISE_DONE')