"""Elbow placement audit: our solved elbow vs the mirrored clip elbow, current shoulder vs clip-shoulder root."""
import sys
from pathlib import Path
import numpy as np

P = Path(__file__).resolve().parent
sys.path.insert(0, str(P))
import author_upper as U
A = U.A


def bend_dir(sh, el, wr):
    ax = (wr - sh) / np.linalg.norm(wr - sh)
    v = el - sh
    v = v - ax * np.dot(v, ax)
    return v / np.linalg.norm(v)


prev = {}
print('%5s | %-26s | %-26s' % ('t', 'cur: elbow err / bend err / step', 'sh: elbow err / bend err / step'))
for i in range(0, len(U.clip['frames']), 4):
    t = min(i / U.FPS, U.LENGTH)
    w = U.world_at(i)
    swing = U.mir(w['hand_r'])
    elb = U.mir(w['lowerarm_r'])[:3, 3]
    sh_clip = U.mir(w['upperarm_r'])[:3, 3]
    wL = U.ss(t / 0.12) * (1 - U.ss((t - 0.97) / 0.30))
    wrist = (1 - wL) * U.LW_REST[:3, 3] + wL * swing[:3, 3]
    hq = U.qslerp(U.QLW, U.qfrommat(swing[:3, :3]), wL)
    pole = (1 - wL) * U.LP_REST + wL * elb
    cb = bend_dir(sh_clip, elb, swing[:3, 3])
    cols = []
    for v, shoulder in (('cur', U.LS_REST + wL * (sh_clip - U.SH0)), ('sh', (1 - wL) * U.LS_REST + wL * sh_clip)):
        l, d = A.solve_arm(A.LR, A.FIST[0], A.LP, 'l', shoulder, wrist, pole, U.qmat(hq))
        sh, el, wr = (l[n][:3, 3] for n in ('upperarm_l', 'lowerarm_l', 'hand_l'))
        b = bend_dir(sh, el, wr)
        step = np.degrees(np.arccos(np.clip(np.dot(b, prev.get(v, b)), -1, 1)))
        prev[v] = b
        cols.append('%6.1f cm %6.0f deg %5.0f' % (np.linalg.norm(el - elb), np.degrees(np.arccos(np.clip(np.dot(b, cb), -1, 1))), step))
    print('%5.3f | %s | %s' % (t, cols[0], cols[1]))
