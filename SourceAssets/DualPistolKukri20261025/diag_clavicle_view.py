"""Does the clavicle share bring shoulder skin on screen? Visible clavicle-weighted vertices, before vs after."""
import sys
from pathlib import Path
import numpy as np

P = Path(__file__).resolve().parent
sys.path.insert(0, str(P))
import author_upper as U
A = U.A

W = A.surface['W']
clav = np.array([w.get('clavicle_l', 0.) for w in W]) > .3
TV = np.tan(np.radians(37.5)); TH = TV * 16 / 9


def visible(X):
    x, y, z = X[:, 0], X[:, 1], X[:, 2]
    return (x > 8) & (np.abs(y) < x * TH) & (np.abs(z) < x * TV)


for i in range(0, len(U.clip['frames']), 8):
    t = min(i / U.FPS, U.LENGTH)
    w = U.world_at(i)
    swing = U.mir(w['hand_r'])
    elb = U.mir(w['lowerarm_r'])[:3, 3]
    sh_clip = U.mir(w['upperarm_r'])[:3, 3]
    wL = U.ss(t / 0.12) * (1 - U.ss((t - 0.97) / 0.30))
    wrist = (1 - wL) * U.LW_REST[:3, 3] + wL * swing[:3, 3]
    hq = U.qslerp(U.QLW, U.qfrommat(swing[:3, :3]), wL)
    pole = (1 - wL) * U.LP_REST + wL * elb
    out = []
    for name, shoulder, k in (('old', U.LS_REST + wL * (sh_clip - U.SH0), 0.), ('new', (1 - wL) * U.LS_REST + wL * sh_clip, U.CLAV_SHARE * wL)):
        l, _ = A.solve_arm(A.LR, A.FIST[0], A.LP, 'l', shoulder, wrist, pole, U.qmat(hq))
        A.clavicle_share(l, k)
        pose = dict(U.REST['pose'])
        for n in pose:
            if A.chain(n, 'clavicle_l', A.LP) and n in l:
                pose[n] = l[n]
        X, _, _ = A.skin(pose)
        v = visible(X)
        out.append('%s arm %4d clav %3d' % (name, v.sum(), (v & clav).sum()))
    print('t=%.3f | %s' % (t, ' | '.join(out)))
