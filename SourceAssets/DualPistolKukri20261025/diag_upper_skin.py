"""Skinned upper-arm thickness audit for the off-hand uppercut (V9 surface LBS + JC_, as in game).

Per key: radius profile of the upper-arm skin along shoulder->elbow, as a ratio to the bind profile.
Variants: cur = authored keys; sh = shoulder on the mirrored clip shoulder; clav = sh + clavicle turned to
the mirrored clip clavicle.  Run:  python -I diag_upper_skin.py
"""
import sys
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R

P = Path(__file__).resolve().parent
sys.path.insert(0, str(P))
import author_upper as U
A = U.A

LR = A.LR
W = A.surface['W']
X0 = A.surface['X']
ARM = ('upperarm_l', 'upperarm_twist_01_l', 'upperarm_twist_02_l')
share = np.array([sum(w.get(n, 0.) for n in ARM) for w in W])
clav_share = np.array([w.get('clavicle_l', 0.) for w in W])
sel = share >= .6
print('upper-arm verts %d, clavicle-weighted verts %d' % (sel.sum(), (clav_share > .05).sum()))
print('clavicle_l children:', [n for n, p in A.LP.items() if p == 'clavicle_l'])
BINS = np.linspace(0., 1., 6)


def profile(X, sh, el):
    ax = el - sh
    L = np.linalg.norm(ax); ax /= L
    v = X[sel] - sh
    s = v @ ax / L
    r = np.linalg.norm(v - np.outer(v @ ax, ax), axis=1)
    out = []
    for a, b in zip(BINS[:-1], BINS[1:]):
        m = (s >= a) & (s < b)
        out.append(np.median(r[m]) if m.sum() > 8 else np.nan)
    return np.array(out)


BIND = profile(X0, LR['upperarm_l'][:3, 3], LR['lowerarm_l'][:3, 3])
print('bind radius cm per fifth (shoulder->elbow):', np.round(BIND, 2))

Rb = LR['clavicle_l'][:3, :3]
o_up = Rb.T @ (LR['upperarm_l'][:3, 3] - LR['clavicle_l'][:3, 3])


def unitrot(m):
    m = m[:3, :3]
    return m / np.linalg.norm(m, axis=0)


def pose_for(i, variant):
    t = min(i / U.FPS, U.LENGTH)
    w = U.world_at(i)
    swing = U.mir(w['hand_r'])
    elb = U.mir(w['lowerarm_r'])[:3, 3]
    sh_clip = U.mir(w['upperarm_r'])[:3, 3]
    wL = U.ss(t / 0.12) * (1 - U.ss((t - 0.97) / 0.30))
    wrist = (1 - wL) * U.LW_REST[:3, 3] + wL * swing[:3, 3]
    hq = U.qslerp(U.QLW, U.qfrommat(swing[:3, :3]), wL)
    if variant == 'cur':
        shoulder = U.LS_REST + wL * (sh_clip - U.SH0)
    else:
        shoulder = (1 - wL) * U.LS_REST + wL * sh_clip
    pole = (1 - wL) * U.LP_REST + wL * elb
    fwd = U.DIGITS_AT <= t <= U.DIGITS_END
    l, d = A.solve_arm(LR, U.SRCU if fwd else A.FIST[0], A.LP, 'l', shoulder, wrist, pole, U.qmat(hq))
    if variant.startswith('k'):
        # Clavicle takes a share of the upper arm's deformation (shoulder pinch relief).
        k = float(variant[1:]) * wL
        deform = R.from_matrix(l['upperarm_l'][:3, :3] @ LR['upperarm_l'][:3, :3].T)
        Rn = R.from_rotvec(deform.as_rotvec() * k).as_matrix() @ Rb
        sh = l['upperarm_l'][:3, 3]
        l['clavicle_l'] = A.matrix(Rn, sh - Rn @ o_up)
    pose = dict(U.REST['pose'])
    for n in pose:
        if A.chain(n, 'clavicle_l', A.LP) and n in l:
            pose[n] = l[n]
    return t, pose, d


VARIANTS = sys.argv[1:] or ['cur', 'sh', 'k0.5', 'k0.7', 'k1.0']
for i in (0, 12, 24, 36, 40, 44, 52, 64, 80, 88, 104):
    row = []
    for variant in VARIANTS:
        t, pose, d = pose_for(i, variant)
        X, _, _ = A.skin(pose)
        pr = profile(X, pose['upperarm_l'][:3, 3], pose['lowerarm_l'][:3, 3]) / BIND
        row.append('%s %s' % (variant, ' '.join('%.2f' % v for v in pr[:3])))
    print('t=%.3f | %s' % (t, ' | '.join(row)))
