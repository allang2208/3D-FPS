"""Off-hand uppercut arm audit: per key, our solved left arm vs the main-hand clip's right arm.

Reports reach (fraction of native arm length), shoulder pull from the reach clamp, elbow flexion, and the
upper-arm roll relative to the clavicle (swing-twist about the upper-arm bone): the shoulder skin is weighted
to clavicle + upperarm + upperarm_twist_01, so a large roll with a bind-local twist bone pinches the upper arm.
Run:  python -I diag_upper_arm.py
"""
import sys
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R

P = Path(__file__).resolve().parent
sys.path.insert(0, str(P))
import author_upper as U
A = U.A


def twist_about(rot, axis):
    q = R.from_matrix(rot).as_quat()
    if q[3] < 0: q = -q
    return float(np.degrees(2 * np.arctan2(np.dot(q[:3], axis), q[3])))


def flex(sh, el, wr):
    a, b = sh - el, wr - el
    return 180 - float(np.degrees(np.arccos(np.clip(np.dot(a, b) / np.linalg.norm(a) / np.linalg.norm(b), -1, 1))))


def local_roll(world, ref_world, child, parent):
    """Twist of child's local rotation (in parent) vs its bind local, about the child bone axis."""
    now = np.linalg.inv(world[parent]) @ world[child]
    ref = np.linalg.inv(ref_world[parent]) @ ref_world[child]
    d = now[:3, :3] @ ref[:3, :3].T
    axis = ref[:3, :3] @ np.array([1., 0, 0])   # UE arm bones point down local X
    return twist_about(d, axis / np.linalg.norm(axis))


def mats(world):
    return {n: U.mat_of(t) for n, t in world.items()}


names = U.rig.names
print('clip arm bones:', [n for n in names if n.endswith('_r') and ('arm' in n or 'clav' in n)])
ref_clip = mats(U.rig.world({n: U.rig.ref_local[n] for n in names}))
LR = A.LR
a = np.linalg.norm(LR['lowerarm_l'][:3, 3] - LR['upperarm_l'][:3, 3])
b = np.linalg.norm(LR['hand_l'][:3, 3] - LR['lowerarm_l'][:3, 3])
ca = np.linalg.norm(ref_clip['lowerarm_r'][:3, 3] - ref_clip['upperarm_r'][:3, 3])
cb = np.linalg.norm(ref_clip['hand_r'][:3, 3] - ref_clip['lowerarm_r'][:3, 3])
print('native upper/lower: ours %.2f/%.2f  clip %.2f/%.2f' % (a, b, ca, cb))
print('%5s | %5s %5s %5s %6s | %5s %5s %6s %6s' % ('t', 'reach', 'pull', 'flex', 'roll', 'cReach', 'cFlex', 'cRoll', 'cTw01'))
for i in range(0, len(U.clip['frames']), 4):
    t = min(i / U.FPS, U.LENGTH)
    w = U.world_at(i)
    swing = U.mir(w['hand_r'])
    elb = U.mir(w['lowerarm_r'])[:3, 3]
    sh_clip = U.mir(w['upperarm_r'])[:3, 3]
    wL = U.ss(t / 0.12) * (1 - U.ss((t - 0.97) / 0.30))
    wrist = (1 - wL) * U.LW_REST[:3, 3] + wL * swing[:3, 3]
    hq = U.qslerp(U.QLW, U.qfrommat(swing[:3, :3]), wL)
    shoulder = U.LS_REST + wL * (sh_clip - U.SH0)
    pole = (1 - wL) * U.LP_REST + wL * elb
    fwd = U.DIGITS_AT <= t <= U.DIGITS_END
    l, d = A.solve_arm(LR, U.SRCU if fwd else A.FIST[0], A.LP, 'l', shoulder, wrist, pole, U.qmat(hq))
    sh, el, wr = (l[n][:3, 3] for n in ('upperarm_l', 'lowerarm_l', 'hand_l'))
    pull = float(np.linalg.norm(sh - shoulder))
    roll = local_roll(l, LR, 'upperarm_l', 'clavicle_l')
    cw = mats(w)
    c_sh, c_el, c_wr = (cw[n][:3, 3] for n in ('upperarm_r', 'lowerarm_r', 'hand_r'))
    c_reach = np.linalg.norm(c_wr - c_sh) / (ca + cb)
    c_roll = local_roll(cw, ref_clip, 'upperarm_r', 'clavicle_r')
    c_tw = local_roll(cw, ref_clip, 'upperarm_twist_01_r', 'upperarm_r') if 'upperarm_twist_01_r' in cw else float('nan')
    print('%5.3f | %5.2f %5.1f %5.0f %6.0f | %5.2f %5.0f %6.0f %6.0f' % (
        t, d['reach'], pull, flex(sh, el, wr), roll, c_reach, flex(c_sh, c_el, c_wr), c_roll, c_tw))
