"""R4 sprint hold, left arm (user 2026-10-26: "the left hand isn't right either -- make it a forward grip with the blade
pointing forward, a little different from the video").  The right arm stays the R4 thrust-ahead reverse grip
(Work/fit_run_r4.json, fit_run_r4.py).

Design (not a copy of the reference, whose left fist sits low centre, reverse grip, blade up-left):
  grip    forward grip (the accepted fist, mirrored; edge on the knuckle side), so left_kukri.json and the runtime attach
          stay as they are -- only the right kukri turns at runtime
  blade   into the screen (a thrust, like the right blade), converging on the centre line
  fist    low left, forearm in from the left
What the rig allows: the accepted fist holds the blade ~84 deg off the hand's long axis, so even at full ulnar deviation
the blade stays >= 40 deg off the forearm; and to show the fist on screen it sits ABOVE the viewmodel shoulder (22 cm under
the eye).  A level blade straight ahead then needs a vertical forearm with the thumb forward (impossible) or the elbow
over the fist.  Random scans of natural arms (skin twist <= 70, wrist in range, elbow off screen and outside the chest)
put the best blade at ~35 deg up.  This random-start fitter alone converged to near fists with the blade standing up
(25 deg off), so the accepted R4 left came from the scan + polish in Work/r4/:
  python -I Work/r4/left_guard_scan.py 32 50000      (pitch/yaw window 10-35 / -5..20; candidate dS2)
  python -I Work/r4/left_polish.py Work/r4/dS2.json pA grip=-0.52,0.78 depth=38 elev=28 conv=15 flat=0.35
  -> Work/r4/pA.json = Work/fit_run_r4l.json: fist (-0.53, 0.79) at ~42 cm, blade 36 deg up / 20 deg towards the centre,
     skin twist -33, wrist ext 16 / ulnar 27, forearm rotation 74 (palm half up), elbow out left at shoulder height.
Parameters are dual_rig's mirrored-space left arm (W, phi, psi, de, du + 3 clavicle angles).
Run:  python -I fit_run_r4_left.py [--tag=t] [--accept]   -> Work/fit_run_<t>.json (default r4l_fit; Work/fit_run_r4l.json
      is the accepted pA and is not overwritten unless --tag=r4l)
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

P = Path(__file__).resolve().parent
sys.path.insert(0, str(P))
from fit_idle import Fitter, scr, ang, band, unit_px, unpack, PX  # noqa: E402

GRIP = np.array([-0.38, 0.62])
FORE = unit_px(-40.0, True)                     # forearm leaves the fist down-left
AHEAD = np.array([1.0, 0.06, 0.10])             # ahead, converging on the centre line, slightly up (actual camera)
AHEAD = AHEAD / np.linalg.norm(AHEAD)
LIMITS = dict(ext=(-20.0, 25.0), uln=(-20.0, 25.0), twist=(-70.0, 70.0), rho=(-60.0, 60.0), roll_u=(-75.0, 60.0),
              reach=(0.36, 0.85), depth=(20.0, 50.0), clav=(-15.0, 15.0))
DEPTH = 28.0
W_EDGE = 20.0
PALM_MIN = 0.15
SLOTS = list(range(7, 14)) + list(range(17, 20))
RIGHT_R4 = P / 'Work' / 'fit_run_r4.json'


class LeftFitter(Fitter):
    def terms(self, x):
        g = self.geometry(x)
        t = {}
        grip, base, tip = g['grip_l'], g['base_l'], g['tip_l']
        W, E, d = g['Wl'], g['El'], g['dl']
        view = grip / np.linalg.norm(grip)
        t['grip'] = 40.0 * float(np.sum((scr(grip) - GRIP) ** 2)) * 100
        b = (tip - base) / np.linalg.norm(tip - base)
        t['ahead'] = 0.08 * math.degrees(math.acos(max(-1.0, min(1.0, float(np.dot(b, AHEAD)))))) ** 2
        fdir = (E - W) / np.linalg.norm(E - W)
        t['fore'] = 0.02 * ang(scr(W + fdir * 10.0) - scr(W), FORE) ** 2
        if E[0] > 1.0:
            en = scr(E)
            t['elbow'] = 30.0 * max(0.0, min(1.12 - abs(en[0]), 1.12 - abs(en[1]))) ** 2 * 100
        t['palm'] = 40.0 * band(float(np.dot(g['palm_l'], view)), PALM_MIN, 1.0) ** 2   # back of the hand to the camera
        mid = (base + tip) * 0.5
        t['flat'] = 30.0 * max(0.0, 0.30 - abs(float(np.dot(g['flat_l'], mid / np.linalg.norm(mid))))) ** 2
        e_scr = (scr(mid + g['edge_l'] * 3.0) - scr(mid)) * PX
        t['edge'] = W_EDGE * band(float(e_scr[1]) / max(np.linalg.norm(e_scr), 1e-6), 0.0, 1.0) ** 2   # edge not up
        # The blade must not run behind the left forearm on the screen.
        ws, es = scr(W), scr(W + fdir * 12.0)
        half = 4.5 / (max(W[0], 5.0) * 0.7673)
        for q in ((base + tip) * 0.5, tip):
            qs = scr(q)
            u = es - ws
            v = qs - ws
            along = float(np.dot(v, u) / max(np.dot(u, u), 1e-9))
            if along > 0.0:
                off = abs(float(v[0] * u[1] - v[1] * u[0])) / max(np.linalg.norm(u), 1e-9)
                t['hidden'] = t.get('hidden', 0.0) + 200.0 * max(0.0, half + 0.03 - off) ** 2
        t['wrist'] = 0.3 * (band(d['ext'], *LIMITS['ext']) ** 2 + band(d['uln'], *LIMITS['uln']) ** 2)
        t['twist'] = 0.2 * band(math.degrees(d['theta']), *LIMITS['twist']) ** 2
        t['rho'] = 0.1 * band(g['rho_l'], *LIMITS['rho']) ** 2
        t['rollu'] = 0.05 * band(d['roll_u'], *LIMITS['roll_u']) ** 2
        t['reach'] = 400.0 * band(d['reach'], *LIMITS['reach']) ** 2
        t['depth'] = 2.0 * band(grip[0], *LIMITS['depth']) ** 2 + 0.2 * (grip[0] - DEPTH) ** 2
        t['lens'] = 5.0 * max(0.0, 16.0 - min(tip[0], base[0], W[0])) ** 2
        # Elbow out to the left of the chest, not folded into it (R1 folded it under the chin).
        t['chest'] = 2.0 * (max(0.0, 12.0 - E[0]) ** 2 * (1.0 if E[1] > -20.0 else 0.0) + max(0.0, E[1] + 7.0) ** 2)
        prm = unpack(x)[1]
        t['prior'] = 0.002 * (prm['de'] ** 2 + (prm['du'] - 12) ** 2)
        c = np.array(prm['C'])
        t['clav'] = 0.01 * float(np.sum(c ** 2)) + 2.0 * sum(band(v, *LIMITS['clav']) ** 2 for v in c)
        return t, g

    def cost(self, x, report=False):
        t, g = self.terms(x)
        total = float(sum(t.values()))
        if not np.isfinite(total):
            total = 1e9
        return (total, t, g) if report else total


def describe(F, x):
    total, t, g = F.cost(x, report=True)
    r, l = unpack(x)
    r['flip'], l['flip'] = F.flip
    conv = lambda d: {k: (list(map(float, v)) if isinstance(v, tuple) else v if v is None or isinstance(v, str) else float(v))
                      for k, v in d.items()}
    d = g['dl']
    b = (g['tip_l'] - g['base_l']) / np.linalg.norm(g['tip_l'] - g['base_l'])
    mid = (g['base_l'] + g['tip_l']) * 0.5
    return dict(total=total, terms={k: round(v, 4) for k, v in t.items() if v > 1e-4}, x=[float(v) for v in x],
                flip=list(F.flip), right=conv(r), left_mirrored=conv(l),
                diag_l=dict(ext=round(d['ext'], 1), uln=round(d['uln'], 1), twist=round(math.degrees(d['theta']), 1),
                            rho=round(g['rho_l'], 1), reach=round(d['reach'], 3), roll_u=round(d['roll_u'], 1),
                            palm_view=round(float(np.dot(g['palm_l'], g['grip_l'] / np.linalg.norm(g['grip_l']))), 3),
                            flat_view=round(float(np.dot(g['flat_l'], mid / np.linalg.norm(mid))), 3),
                            ahead_deg=round(math.degrees(math.acos(min(1.0, float(np.dot(b, AHEAD))))), 1)),
                ndc_l={k: [round(float(v), 3) for v in scr(g[k + '_l'])] for k in ('grip', 'base', 'tip')},
                cam_l=dict(grip=[round(float(v), 2) for v in g['grip_l']], tip=[round(float(v), 2) for v in g['tip_l']],
                           W=[round(float(v), 2) for v in g['Wl']], E=[round(float(v), 2) for v in g['El']]))


def fit(F, x_full, rng, n_starts=40):
    def f(v):
        x = x_full.copy()
        x[SLOTS] = v
        return F.cost(x)
    grip = np.array([DEPTH, -GRIP[0] * DEPTH * 1.3643, -GRIP[1] * DEPTH * 0.7673])   # mirrored space (y flipped)
    found = []
    for _ in range(n_starts):
        v0 = np.r_[grip + rng.normal(0, 5.0, 3), rng.uniform(-60, 160), rng.uniform(-180, 180), rng.normal(0, 10),
                   rng.normal(10, 10), rng.normal(0, 4, 3)]
        res = minimize(f, v0, method='L-BFGS-B', options=dict(maxiter=400))
        found.append((res.fun, res.x))
    found.sort(key=lambda t: t[0])
    best = None
    for c, v in found[:5]:
        res = minimize(f, v, method='Powell', options=dict(maxiter=8000, xtol=1e-3, ftol=1e-7))
        if best is None or res.fun < best[0]:
            best = (res.fun, res.x)
    x = x_full.copy()
    x[SLOTS] = best[1]
    return best[0], x


def arg(name, default):
    return next((a.split('=', 1)[1] for a in sys.argv if a.startswith('--%s=' % name)), default)


def main():
    global AHEAD, GRIP, DEPTH, W_EDGE
    elev = float(arg('elev', 5.7))                              # blade elevation above the horizon (deg)
    conv = float(arg('conv', 3.4))                              # convergence on the centre line (deg)
    AHEAD = np.array([math.cos(math.radians(elev)) * math.cos(math.radians(conv)),
                      math.cos(math.radians(elev)) * math.sin(math.radians(conv)), math.sin(math.radians(elev))])
    GRIP = np.array([float(v) for v in arg('grip', '-0.38,0.62').split(',')])
    DEPTH = float(arg('depth', 28.0))
    W_EDGE = float(arg('wedge', 20.0))
    global FORE, PALM_MIN
    FORE = unit_px(float(arg('fore', -40.0)), True)
    PALM_MIN = float(arg('palm', 0.15))
    LIMITS['rho'] = tuple(float(v) for v in arg('rho', '-60,60').split(','))
    F = LeftFitter()
    right = json.loads(RIGHT_R4.read_text('utf-8'))
    F.flip = (right['flip'][0], None)                          # right R4 reverse 'y'; left forward grip
    x = np.array(right['x'], float)
    c, x = fit(F, x, np.random.default_rng(int(arg('seed', 6))), n_starts=int(arg('starts', 40)))
    out = describe(F, x)
    tag = arg('tag', 'r4l_fit')
    (P / 'Work' / ('fit_run_%s.json' % tag)).write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({k: out[k] for k in ('total', 'flip', 'terms', 'diag_l', 'ndc_l', 'cam_l')}, ensure_ascii=False))
    if '--accept' in sys.argv:
        keys = dict(source='R4 right fit_run_r4.py (Work/fit_run_r4.json) + R4 left fit_run_r4_left.py (Work/fit_run_%s.json): '
                           'right reverse grip thrust ahead, left forward grip blade ahead' % tag,
                    right=out['right'], left_mirrored=out['left_mirrored'])
        (P / 'run_keys.json').write_text(json.dumps(keys, indent=1), encoding='utf-8')
        print('wrote run_keys.json')


if __name__ == '__main__':
    main()
