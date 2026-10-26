"""Off-hand uppercut grip audit: clip matrix scale, mirrored hand rotation, kukri-in-hand offset, finger mirror.

Checks (a) whether the clip's world matrices carry scale (qfrommat assumes a pure rotation), (b) how far the authored
left-hand rotation is from the properly normalised mirror, (c) the grip point's offset from the wrist, (d) which
local mirror maps the clip's right-hand finger binds onto the V7 left-hand finger binds, and (e) fingertip positions of
our solved left hand vs the mirrored clip right hand at the contact frame.
Run:  python -I diag_grip.py
"""
import sys
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R

P = Path(__file__).resolve().parent
sys.path.insert(0, str(P))
import author_upper as U
A = U.A


def unit_rot(m):
    m = np.asarray(m, float)[:3, :3]
    return m / np.linalg.norm(m, axis=0)


def ang(a, b):
    return float(np.degrees(R.from_matrix(unit_rot(a) @ unit_rot(b).T).magnitude()))


i = int(0.35 * U.FPS)
w = U.world_at(i)
for n in ('root', 'upperarm_r', 'hand_r', 'WPN_root'):
    if n in w:
        m = U.mat_of(w[n])
        print('%-10s column norms %s' % (n, np.round(np.linalg.norm(m[:3, :3], axis=0), 3)))
swing = U.mir(w['hand_r'])
q_bad = U.qmat(U.qfrommat(swing[:3, :3]))
q_good = unit_rot(swing)
print('authored hand rotation vs normalised mirror: %.1f deg' % ang(q_bad, q_good))
grip = U.grip_of(w)
print('grip point - wrist (true): %s cm   |   KIH translation used: %s' % (
    np.round(grip[:3, 3] - swing[:3, 3], 2), np.round(U.KIH[:3, 3], 3)))

# (d) local mirror convention: clip right finger bind locals vs V7 left finger bind locals
ref = U.rig.ref_local
LR, LP = A.LR, A.LP
cands = {'S3 diag(-1,1,1)': np.diag([-1, 1, 1.]), 'diag(1,-1,1)': np.diag([1, -1, 1.]), 'diag(1,1,-1)': np.diag([1, 1, -1.])}
for name, S in cands.items():
    errs = []
    for f in U.FINGERS + ['hand']:
        rl = U.qmat(ref[f + '_r'].q)
        mirrored = S @ rl @ S
        par = LP[f + '_l']
        v7 = (np.linalg.inv(LR[par]) @ LR[f + '_l'])[:3, :3]
        errs.append(ang(mirrored, v7))
    print('local mirror %-16s bind error mean %.1f max %.1f deg' % (name, np.mean(errs), np.max(errs)))

# (e) fingertips at the contact frame: ours (authored pipeline) vs mirrored clip
t = i / U.FPS
wL = U.ss(t / 0.12) * (1 - U.ss((t - 0.97) / 0.30))
sh_clip = U.mir(w['upperarm_r'])[:3, 3]
shoulder = (1 - wL) * U.LS_REST + wL * sh_clip
pole = (1 - wL) * U.LP_REST + wL * U.mir(w['lowerarm_r'])[:3, 3]
wrist = (1 - wL) * U.LW_REST[:3, 3] + wL * swing[:3, 3]
for label, hand in (('authored (qfrommat on scaled)', U.qmat(U.qslerp(U.QLW, U.qfrommat(swing[:3, :3]), wL))),
                    ('normalised mirror', unit_rot(swing))):
    l, _ = A.solve_arm(A.LR, U.SRCU, A.LP, 'l', shoulder, wrist, pole, hand)
    d = []
    for f in ('index_03', 'middle_03', 'ring_03', 'pinky_03', 'thumb_03', 'index_01', 'pinky_01'):
        ours = l[f + '_l'][:3, 3] - l['hand_l'][:3, 3]
        clip = U.mir(w[f + '_r'])[:3, 3] - swing[:3, 3]
        d.append(np.linalg.norm(ours - clip))
    print('%-30s finger joint error vs mirrored clip: mean %.2f max %.2f cm' % (label, np.mean(d), np.max(d)))
