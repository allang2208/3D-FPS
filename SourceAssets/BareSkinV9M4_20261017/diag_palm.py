"""Diagnose the left-palm 'holes' seen in game (M4 idle): folds / inverted faces in rest and in the idle pose."""
import json, sys
import numpy as np
from scipy.spatial.transform import Rotation as Rot
src = open(__file__.replace('diag_palm.py', 'correctives.py')).read().split('shapes = {}; meta = {}')[0].replace('M4()', 'M4(check_asset=False)')
exec(src)
meta = json.loads((R / 'Work/correctives.json').read_text()); shp = np.load(R / 'Work/correctives.npz')
va = open(__file__.replace('diag_palm.py', 'validate_anim.py')).read()
exec(va[va.index('def tent('):va.index('report = {}')])
tw = wv[m.T]
ref_mats = {n: (ref_q[n].as_matrix(), ref_t[n]) for n in names}


def pose(clip, fi=0):
    fr = rd['clips'][clip]['frames'][fi]
    t = np.array([b['t'] for b in fr]); q = Rot.from_quat([b['q'] for b in fr])
    Rm = np.zeros((len(bones_used), 3, 3)); Tv = np.zeros((len(bones_used), 3))
    for k, b in enumerate(bones_used):
        j = names.index(b); Mp = q[j].as_matrix(); Mr, tr = ref_mats[b]
        Rm[k] = Mp @ Mr.T; Tv[k] = t[j] - Rm[k] @ tr
    return Rm, Tv


def face_n(X):
    f = np.cross(X[tw[:, 1]] - X[tw[:, 0]], X[tw[:, 2]] - X[tw[:, 0]])
    return f / np.maximum(np.linalg.norm(f, axis=1, keepdims=True), 1e-12)


def vertex_n(X):
    f = np.cross(X[tw[:, 1]] - X[tw[:, 0]], X[tw[:, 2]] - X[tw[:, 0]]); n = np.zeros_like(X)
    for k in range(3): np.add.at(n, tw[:, k], f)
    return n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)


def report(X, tag):
    fn = face_n(X); vn = vertex_n(X)
    against = np.einsum('ij,ij->i', fn, vn[tw].mean(axis=1)) < 0
    cent = X[tw].mean(axis=1); left = P[tw].mean(axis=1)[:, 0] < 0
    sel = np.nonzero(against & left & (m.region == 2))[0]
    W_ = ref_t['hand_l']
    rows = [dict(t=int(t), dist_wrist=round(float(np.linalg.norm(P[tw[t]].mean(0) - W_)), 2), area=round(float(np.linalg.norm(np.cross(P[tw[t, 1]] - P[tw[t, 0]], P[tw[t, 2]] - P[tw[t, 0]])) / 2), 5),
                 dom=max(W[tw[t, 0]], key=W[tw[t, 0]].get)) for t in sel]
    print(tag, 'left-hand faces against their vertex normals:', len(sel))
    for r in rows[:40]: print('   ', r)
    return set(sel.tolist())


r0 = report(P, 'REST V9')
P8 = np.zeros_like(P); P8[wv] = m.X; r8 = report(P8, 'REST V8')
Rm, Tv = pose('/Game/Weapons/M4ContactImpactFinal/A_AKM_idle')
Xb, _ = lbs(P, Rm, Tv); rb = report(Xb, 'IDLE LBS')
fr = rd['clips']['/Game/Weapons/M4ContactImpactFinal/A_AKM_idle']['frames'][0]
t = np.array([b['t'] for b in fr]); q = Rot.from_quat([b['q'] for b in fr])
delta = np.zeros_like(P)
for s in ('l', 'r'):
    w, *_ = drive(t, q, s)
    for n_, x in w.items():
        if x > 0: delta += shp[n_] * x; print('  weight', n_, round(float(x), 3))
Xc, _ = lbs(P + delta, Rm, Tv); rc = report(Xc, 'IDLE LBS+JC')
X8, _ = lbs(P8, Rm, Tv); r8p = report(X8, 'IDLE V8 (old shape, old weights not applied)')
# open edges on the welded left hand
edges = {}
for ti, tt in enumerate(tw):
    for k in range(3):
        a, b = int(tt[k]), int(tt[(k + 1) % 3]); edges.setdefault((min(a, b), max(a, b)), []).append(ti)
open_hand = [e for e, ts in edges.items() if len(ts) == 1 and m.region[ts[0]] == 2 and P[e[0]][0] < 0]
print('welded open edges on left hand:', len(open_hand))
loops = {}
np.save(R / 'Work/diag_idle_X.npy', Xc)
json.dump(dict(rest=sorted(r0), idle=sorted(rc), open=[list(e) for e in open_hand]), open(R / 'Work/diag_palm.json', 'w'))
