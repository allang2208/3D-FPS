"""Sprint attack (dash attack) for the kukri: fit the right-arm keys to the reference two-handed jump chop.

Reference: BV1CeYUeSE7b 112.47-113.80 s ("近战动作（跳跃）#11 跳劈"), t = 0 at frame 3374 (the last stance frame).  Frames
are read on the NDC grid sheets (Reference/extract_sprint.py, grid_sprint.py; x right, y down):
  0.03-0.07  the fist lifts from the stance, the blade turns upright; the left hand comes up from the lower left;
  0.10       both hands meet on the handle at the top centre, forearms rising from both lower corners;
  0.13       the arms leave the frame upwards; 0.17-0.33 cocked overhead out of view (the view tilts up with the jump);
  0.37       both forearms come down from the top; 0.40 the fists are at the bottom with the blade driving forward;
  0.43       the hit flash at the crosshair; 0.43-1.03 the arms stay below the frame;
  1.07-1.27  the right fist comes back up from the bottom into the stance (back by ~1.33 s).
The left hand joins on the pommel (kukri_rig.left_press_hand, keyed in author_kukri_sprint.py) from 0.07 to 0.45 s.

Fit terms on top of fit_reference.Fitter:
  above  -- the grip and the whole blade above the top edge of the frame (overhead cock);
  the "elbow in front of the face" penalty is lifted while the elbow is above the frame (overhead).
The hammer grip (accepted stance fist) puts the edge on the knuckle side, which leads naturally in an overhead chop.

Run:  python fit_sprint.py [--accept]   -> Work/sprint/fit_sprint.json (sprint_keys.json with --accept)
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

from kukri_rig import ndc, TIP
from kmath import mesh_to_cam
from fit_reference import Fitter, idle_x, REF, _tip

P = Path(__file__).resolve().parent
WORK = P / 'Work' / 'sprint'
LENGTH = 40 / 30            # back on the stance at 1.333 s (reference ~1.30-1.33 s)
CONTACT = (0.367, 0.467)    # blade passes the target zone; hit flash at 0.433 in the reference
# wrist x forward, y right, z up (camera cm) -- z opened to 35 cm for the overhead cock
BOUNDS = [(8, 60), (-45, 55), (-50, 35), (-200, 200), (-260, 320), (-25, 40), (-55, 50), (-12, 28), (-16, 12)]

BACK_UP = (-0.55, -0.05, 0.83)      # blade pointing up and back over the head (cocked)
WIDE = (-110.0, 120.0)
REF_SPRINT = [
    (0.033, dict(g=(0.47, 0.62), bdir=(0.15, -0.45, 0.88), w=0.6, cw=6, mind=24.0, lens=True, th=WIDE)),
    (0.067, dict(g=(0.40, 0.38), bdir=(-0.05, -0.15, 0.99), w=0.6, cw=5, mind=24.0, lens=True, th=WIDE)),
    (0.100, dict(g=(0.15, -0.28), bdir=(-0.40, -0.10, 0.91), w=0.6, cw=3, mind=22.0, th=WIDE)),
    (0.133, dict(g=(0.12, -0.95), bdir=BACK_UP, above=0.95, upperout=1.15, w=0.5, cw=3, th=WIDE)),
    (0.167, dict(g=(0.10, -1.30), bdir=BACK_UP, above=1.1, armout=1.15, w=0.4, cw=3, th=WIDE)),
    (0.233, dict(g=(0.08, -1.40), bdir=(-0.65, -0.05, 0.76), above=1.1, armout=1.15, w=0.4, cw=5, th=WIDE)),
    (0.300, dict(g=(0.08, -1.45), bdir=(-0.72, -0.05, 0.69), above=1.1, armout=1.15, w=0.4, cw=5, th=WIDE)),
    (0.333, dict(g=(0.08, -1.25), bdir=(-0.45, -0.05, 0.89), above=1.1, armout=1.15, w=0.4, cw=4, th=WIDE)),
    # the chop: both arms come down through the frame in two frames, the blade swings over to drive forward-down
    (0.367, dict(g=(0.02, -0.55), bdir=(0.40, -0.05, 0.92), upperout=1.15, w=0.6, cw=2, mind=24.0, th=WIDE)),
    (0.400, dict(g=(-0.02, 0.62), bdir=(0.78, 0.00, -0.62), w=0.7, cw=2, mind=28.0, fwd=10.0, th=WIDE)),
    (0.433, dict(g=(-0.02, 1.15), bdir=(0.35, 0.00, -0.94), off=True, hide=2, w=0.5, cw=2, th=WIDE)),
    (0.500, dict(g=(0.02, 1.40), off=True, hide=2, w=0.5, cw=3, th=WIDE)),
    # below the frame: the forearm rolls back towards the stance, every blade sample hidden, elbow kept out of the corner
    (0.700, dict(g=(0.18, 1.50), phi=-20.0, off=True, hide=2, elbowoff=1.4, w=0.5, cw=3, th=(-60.0, 80.0))),
    (0.900, dict(g=(0.22, 1.55), phi=10.0, off=True, hide=2, elbowoff=1.4, w=0.5, cw=3, th=(-20.0, 70.0))),
    (0.967, dict(g=(0.26, 1.32), phi=25.0, off=True, hide=2, elbowoff=1.3, mind=26.0, w=0.5, cw=3, th=(0.0, 60.0))),
] + [(t, dict(k, th=(15.0, 50.0), lens=True, mind=max(k.get('mind', 0.0), 27.0)))
     for t, k in REF[-4:]]       # the first hit's re-raise into the stance, on the reference's own timing (1.03-1.17 s);
#                                  V1 (+0.1 s) let the knife come up 15 cm from the lens -- the fist now stays >= 27 cm out
RESUME_T = 0.90                  # --resume: keep the accepted keys up to here, refit the re-raise


class SprintFitter(Fitter):
    def cost(self, x, target, prev_x, prev_theta):
        c = super().cost(x, target, prev_x, prev_theta)
        if c >= 1e5:
            return c
        o = self.evaluate(x, prev_theta)
        ex, ey = o['elbow_ndc']
        if o['elbow'][0] > 4 and abs(ex) < 0.8 and ey < 0.6 and ey < -1.05:
            c -= 8.0                     # overhead: the elbow is above the frame, not in front of the face
        for key, parts in (('armout', 'all'), ('upperout', 'upper')):
            if key not in target:
                continue
            # the arm out of view (any edge): upper arm and elbow, plus the forearm for 'armout'
            m = float(target[key])
            S, E, Wc = self.shoulder_cam(self.unpack(x)[5]), o['elbow'], o['wrist']
            pts = [S + (E - S) * f for f in (0.35, 0.7, 1.0)]
            if parts == 'all':
                pts += [E + (Wc - E) * f for f in (0.33, 0.66)]
            for p in pts:
                if p[0] > 2.0:
                    px, py = ndc(p)
                    c += 30.0 * max(0.0, m - max(abs(px), abs(py))) ** 2
        if 'above' in target:
            m = float(target['above'])
            pts = [o['K'].p] + [o['K'].point(np.asarray(TIP) * f) for f in np.linspace(0.2, 1.0, 9)]
            for p in pts:
                pc = mesh_to_cam(p)
                if pc[0] > 3.0:
                    tx, ty = ndc(pc)
                    c += 15.0 * max(0.0, ty + m) ** 2 if abs(tx) < 1.05 else 0.0
                elif pc[0] > -2.0:
                    c += 4.0             # beside the lens: keep the blade clear of the head
        return c


def fit(F, x_prev, theta_prev, ref, keys):
    for t, target in ref:
        target = dict(target, _t=t)
        best = None
        rng = np.random.default_rng(int(t * 1000) + 7)
        starts = [x_prev] + [np.array(x_prev, float) + rng.normal(0, 1, 9) * np.array([6, 8, 8, 40, 50, 8, 10, 4, 3]) for _ in range(14)]
        for s in starts:
            s = np.clip(s, [b[0] for b in BOUNDS], [b[1] for b in BOUNDS])
            res = minimize(F.cost, s, args=(target, x_prev, theta_prev), method='Powell', bounds=BOUNDS,
                           options=dict(maxiter=4000, xtol=1e-2, ftol=1e-4))
            if best is None or res.fun < best.fun:
                best = res
        x = best.x
        o = F.evaluate(x, theta_prev)
        r = o['r']
        theta_prev = r['theta']
        keys.append(dict(t=t, x=list(map(float, x)), cost=float(best.fun), theta=math.degrees(r['theta']),
                         g=list(map(float, o['g'])), tip=list(map(float, o['tip'])), elbow=list(map(float, o['elbow_ndc'])),
                         target={k: v for k, v in target.items() if not k.startswith('_')}))
        print('t %.3f cost %6.2f | g %s tip %s elbow %s | theta %6.1f ext %5.1f uln %5.1f rollU %6.1f reach %.2f | W %s'
              % (t, best.fun, np.round(o['g'], 2), np.round(o['tip'], 2), np.round(o['elbow_ndc'], 2), math.degrees(r['theta']),
                 r['ext'], r['uln'], r['roll_u'], r['reach'], np.round(x[:3], 1)), flush=True)
        x_prev = x
    return keys


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    F = SprintFitter()
    x0 = idle_x(F)
    o = F.evaluate(x0)
    keys = [dict(t=0.0, x=list(map(float, x0)), theta=math.degrees(o['r']['theta']), note='stance')]
    only = next((a.split('=')[1] for a in sys.argv if a.startswith('--until=')), None)
    ref = [k for k in REF_SPRINT if only is None or k[0] <= float(only) + 1e-6]
    theta, x_start = o['r']['theta'], x0
    resume = next((a for a in sys.argv if a.startswith('--resume')), None)
    if resume:
        t_keep = float(resume.split('=')[1]) if '=' in resume else RESUME_T
        old = json.loads((P / 'sprint_keys.json').read_text('utf-8'))['keys']
        keep = [k for k in old if 0.0 < k['t'] <= t_keep + 1e-6]
        for k in keep:
            theta = F.evaluate(np.array(k['x'], float), theta)['r']['theta']
        keys += keep
        x_start = np.array(keep[-1]['x'], float)
        ref = [k for k in ref if k[0] > t_keep + 1e-6]
        print('resume after %.3f s with %d kept keys' % (t_keep, len(keep)))
    fit(F, x_start, theta, ref, keys)
    out = dict(source='fit_sprint.py', reference='BV1CeYUeSE7b 112.467-113.800 (近战动作（跳跃）#11 跳劈)', start='stance',
               length=LENGTH, contact=list(CONTACT), keys=keys)
    (WORK / 'fit_sprint.json').write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding='utf-8')
    if '--accept' in sys.argv:
        (P / 'sprint_keys.json').write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding='utf-8')
        print('accepted -> sprint_keys.json')


if __name__ == '__main__':
    main()
