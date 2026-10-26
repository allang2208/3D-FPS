"""Off-hand uppercut wrist + shoulder audit after the V3 mirror.

Per key: our left wrist signature [elbow, flexion, deviation, roll] (C++ corrective convention) vs the main-hand clip's
right wrist (the mirror should match), and upper-arm skin radius near the shoulder for the clavicle share vs the
clip's own mirrored clavicle.  Run:  python -I diag_wrist.py
"""
import sys
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R

P = Path(__file__).resolve().parent
sys.path.insert(0, str(P))
import author_upper as U
import diag_upper_skin as S
A = U.A

ARM = ['clavicle', 'upperarm', 'lowerarm', 'hand', 'lowerarm_twist_01', 'lowerarm_twist_02'] + U.FINGERS


def clip_right_pose(w):
    """The clip's right arm as a V9 signature pose (normalised rotations, camera basis)."""
    pose = dict(U.REST['pose'])
    for f in ARM:
        n = f + '_r'
        if n in w:
            m = U.mat_of(w[n])
            pose[n] = A.matrix(U.C3 @ U.unit3(m), U.C3 @ m[:3, 3])
    return pose


def sig(pose, side):
    s = {n: (m[:3, 3], R.from_matrix(m[:3, :3]).as_quat()) for n, m in pose.items()}
    return np.array(A.DRIVER.signature(s, side)[:4], float)


rb = A.LR['clavicle_l'][:3, :3]
o_up = rb.T @ (A.LR['upperarm_l'][:3, 3] - A.LR['clavicle_l'][:3, 3])
print('%5s | %-26s | %-26s | radius share / clip-clav' % ('t', 'ours elbow flex dev roll', 'clip elbow flex dev roll'))
for i in range(0, len(U.clip['frames']), 6):
    t = min(i / U.FPS, U.LENGTH)
    w = U.world_at(i)
    swing = U.mframe(w, 'hand_r', 'hand_l')
    wL = U.ss(t / 0.12) * (1 - U.ss((t - 0.97) / 0.30))
    wrist = (1 - wL) * U.LW_REST[:3, 3] + wL * swing[:3, 3]
    hq = U.qmat(U.qslerp(U.QLW, U.qfrommat(swing[:3, :3]), wL))
    shoulder = (1 - wL) * U.LS_REST + wL * U.mir(w['upperarm_r'])[:3, 3]
    pole = (1 - wL) * U.LP_REST + wL * U.mir(w['lowerarm_r'])[:3, 3]
    fwd = U.DIGITS_AT <= t <= U.DIGITS_END
    l, _ = A.solve_arm(A.LR, U.SRCU if fwd else A.FIST[0], A.LP, 'l', shoulder, wrist, pole, hq)
    radii = []
    for mode in ('share', 'clip'):
        ll = {n: m.copy() for n, m in l.items()}
        if mode == 'share':
            A.clavicle_share(ll, U.CLAV_SHARE * wL)
        else:
            cc = U.mframe(w, 'clavicle_r', 'clavicle_l')[:3, :3]
            q0 = R.from_matrix(rb); q1 = R.from_matrix(cc)
            from scipy.spatial.transform import Slerp
            rn = Slerp([0, 1], R.concatenate([q0, q1]))(wL).as_matrix()
            ll['clavicle_l'] = A.matrix(rn, ll['upperarm_l'][:3, 3] - rn @ o_up)
        pose = dict(U.REST['pose'])
        for n in pose:
            if A.chain(n, 'clavicle_l', A.LP) and n in ll:
                pose[n] = ll[n]
        if mode == 'share':
            ours = sig(pose, 'l')
        X, _, _ = A.skin(pose)
        pr = S.profile(X, pose['upperarm_l'][:3, 3], pose['lowerarm_l'][:3, 3]) / S.BIND
        radii.append(pr[0])
    clip = sig(clip_right_pose(w), 'r')
    print('%5.3f | %s | %s | %.2f / %.2f' % (t, np.round(ours).astype(int), np.round(clip).astype(int), *radii))
