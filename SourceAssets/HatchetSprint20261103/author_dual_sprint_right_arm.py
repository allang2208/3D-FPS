"""Right-hand trigger pose for the dual-hatchet sprint-ready run "HatchetDualSprintReady" (2026-11-03).

User 2026-11-03: "我指的是持续奔跑时，触发冲刺攻击的奔跑动作，调整为前面我说的举起斧子刃口向前的动作，不是进行冲刺攻击触发攻击的动作"
-- while sprinting with the sprint attack ready, the run carries the raised hatchet with the edge forward.  The attack
itself is unchanged.

This module solves that one pose on the kukri rig: the right fist raised (camera cm), the hatchet's head up and a little
back, the edge forward.  author_hatchet_ready_run.py animates it through the dual run's cycle and adds the left hand
(dual hold).
"""
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

P = Path(__file__).resolve().parent
sys.path.insert(0, str(P.parent / 'HatchetChop20261102'))
import author_hatchet_chop as C  # noqa: E402  (puts Kukri20261020 and HatchetEquip20261101 on the path)
from kukri_rig import KukriRig, ndc  # noqa: E402
from kmath import mesh_to_cam  # noqa: E402

# fist = grip centre (camera cm: x away, y right, z up), d = handle direction to the head, e = the edge direction
# wanted (camera); the solver turns the edge about the handle and tips the handle slightly.
LIFT = dict(fist=(30.0, 19.0, -9.0), d=(-0.10, -0.10, 0.99), e=(0.90, 0.00, -0.20))     # coming up from the carry
TRIGGER = dict(fist=(30.0, 18.0, -4.0), d=(0.15, -0.10, 0.98), e=(1.00, 0.10, 0.00))     # raised, head up, edge forward
# The sprint-ready run's hold (2026-11-03, user: "右手再往上方举起一些"): a little higher than the attack's trigger key --
# the head just under the top of the frame, the elbow still in front of the shoulder plane (Work/probe_raise_more.py).
RAISE = dict(fist=(30.0, 18.0, 1.0), d=(0.15, -0.10, 0.98), e=(1.00, 0.10, 0.00))


def solve(R, keys):
    """Solve each key in order (twist continuity between them); returns the grip frames."""
    out, prev = [], None
    for key in keys:
        best = None
        for psi in (-60.0, -30.0, 0.0, 30.0, 60.0):
            r = minimize(C.key_cost, np.array([psi, 0.0, 0.0]), args=(key, R, prev), method='Nelder-Mead',
                         options=dict(maxiter=2000, xatol=1e-2, fatol=1e-5))
            if best is None or r.fun < best.fun:
                best = r
        K = C.key_frame(best.x, key)
        a, _ = C.arm_diag(R, K)
        prev = a['twist']
        out.append(K)
        head = ndc(mesh_to_cam(K.point([0.0, 0.0, 23.5])))
        print('  key %-12s cost %5.2f psi %4.0f tip %3.0f/%3.0f | wrist %4.1f twist %6.1f reach %.2f fist %s head %s' % (
            'lift' if key is LIFT else 'trigger', best.fun, best.x[0], best.x[1], best.x[2], a['wrist'], a['twist'],
            a['reach'], np.round(a['grip'], 2), np.round(head, 2)), flush=True)
    return out


def trigger_frames():
    """The two solved keys (lift, trigger) on a fresh rig."""
    R = KukriRig()
    return solve(R, [LIFT, TRIGGER]), R


def ready_frame():
    """The sprint-ready run's raised hold, solved after the trigger key (twist continuity)."""
    R = KukriRig()
    return solve(R, [LIFT, TRIGGER, RAISE])[2], R
