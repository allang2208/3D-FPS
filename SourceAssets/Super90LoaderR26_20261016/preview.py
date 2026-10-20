"""Author-side numbers for one clip/family: layer angles, wrist speed and knob clearance."""
import sys
import numpy as np
from scipy.spatial.transform import Rotation as R
import author_r26 as A
from r26_core import *

role = sys.argv[1] if len(sys.argv) > 1 else 'normal_7'
family = sys.argv[2] if len(sys.argv) > 2 else 'base'
setups, axes, tau, hang = A.clip_inputs(role)
conv, snap = setups[family]
print('conventions', {k: float(conv[k]) for k in ('s_in', 's_tw', 's_open')}, 'snap', {k: snap[k] for k in ('gain', 'sign')})
print('family snap gains (shared min)', {f: s[1]['gain'] for f, s in setups.items()}, 'hang', hang)
rows, new, metrics = A.author(role, family, conv, axes, tau, snap)
print('metrics', metrics)
W0 = [world(r) for r in rows]; W1 = [world(r) for r in new]
def gun_hand(W):
    return np.array([(np.linalg.inv(w[GUN]) @ w['hand_l'])[:3, 3] for w in W])
def gun_rot(W):
    return [R.from_matrix((np.linalg.inv(w[GUN]) @ w['hand_l'])[:3, :3]) for w in W]
P0, P1 = gun_hand(W0), gun_hand(W1)
Q0, Q1 = gun_rot(W0), gun_rot(W1)
lo = int(sys.argv[3]) if len(sys.argv) > 3 else 84
hi = int(sys.argv[4]) if len(sys.argv) > 4 else 140
for f in range(lo, min(len(rows) - 1, hi)):
    p = A.pace(f)
    dp = A.pace(f + 1) - A.pace(f - 1)
    v0 = np.linalg.norm(P0[f + 1] - P0[f - 1]) / dp * 60
    v1 = np.linalg.norm(P1[f + 1] - P1[f - 1]) / dp * 60
    w1 = np.degrees((Q1[f + 1] * Q1[f - 1].inv()).magnitude()) / dp * 60
    w0 = np.degrees((Q0[f + 1] * Q0[f - 1].inv()).magnitude()) / dp * 60
    dq = np.degrees((Q1[f] * Q0[f].inv()).magnitude())
    c0, c1 = A.knob_clearance(W0[f]), A.knob_clearance(W1[f])
    print(f'{f:4d} pace {p:6.2f} roll {A.push_roll(p):6.2f} snap {A.flick_snap(p) * snap["gain"]:6.2f} '
          f'tau {tau.get(f, f):7.2f} | v {v0:5.2f}->{v1:5.2f} m/s  w {w0:6.1f}->{w1:6.1f} d/s  dRot {dq:5.2f}  '
          f'clear {c0:6.1f}->{c1:6.1f} mm')
