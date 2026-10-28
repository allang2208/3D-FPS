"""R4 sprint hold, right arm (user 2026-10-26: "the right weapon points the wrong way -- it should point straight ahead,
thrust semantics; make the right grip match the weapon direction").  The left arm keeps R3 (Work/fit_run_r12.json).

Reference (BV19dUqBJECT 握持姿势 奔跑, still 17.50 s, full-res crop Work/r4/R525.png): the right fist sits in the top-right
corner, the forearm runs straight down the right edge, and the blade line on the screen, grip (0.84, -0.53) -> tip
(0.25, -0.22), runs through (0.0, -0.09): almost through the vanishing point, i.e. the blade points straight AHEAD
(slightly up), it only looks "across" because it starts in the corner.  R1-R3 read it as a blade lying left across the
screen; R3 held it there with the forearm at full supination (rho 86), the arm near straight (reach 0.90) and the
blade edge-on (palm . view -0.45).
A blade straight ahead from a fist on a vertical forearm leaves the fist at right angles to the forearm, from the
little-finger side with the palm turned in (reverse grip, flip 'y', edge to the wrist = down as in the reference):
that is the forearm's neutral roll, so the hand needs no wring.  The forward grip and flip 'x' are tried as well.
Fitted from random starts (5 arm parameters + 3 clavicle angles).
Run:  python -I fit_run_r4.py [--accept]   -> Work/fit_run_r4.json (+ run_keys.json with --accept; left = R3)
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

GRIP = np.array([0.90, -0.50])                  # fist centre between the knuckle plates (R3 read the finger edge)
FORE = unit_px(-86.0, False)                    # forearm leaves the fist straight down the right edge
AHEAD = np.array([1.0, 0.0, 0.07])              # blade line through NDC (0, -0.09): ahead, 4 deg up
AHEAD = AHEAD / np.linalg.norm(AHEAD)
LIMITS = dict(ext=(-20.0, 20.0), uln=(-5.0, 22.0), twist=(-70.0, 70.0), rho=(-60.0, 60.0), roll_u=(-75.0, 60.0),
              reach=(0.36, 0.85), depth=(18.0, 50.0), clav=(-15.0, 15.0))
# Near (~20 cm): the fist reads as large as the left one, and only that close does the reach-limited elbow let the
# forearm stand so that the blade is level with a near-neutral wrist (at 25-30 cm: ext 25 / radial 13, cocked).
DEPTH = 21.0
W_AHEAD = 0.08
SLOTS = list(range(0, 7)) + list(range(14, 17))
LEFT_R3 = P / 'Work' / 'fit_run_r12.json'


class ThrustFitter(Fitter):
    def terms(self, x):
        g = self.geometry(x)
        t = {}
        grip, base, tip = g['grip_r'], g['base_r'], g['tip_r']
        W, E, d = g['Wr'], g['Er'], g['dr']
        view = grip / np.linalg.norm(grip)
        t['grip'] = 40.0 * float(np.sum((scr(grip) - GRIP) ** 2)) * 100
        b = (tip - base) / np.linalg.norm(tip - base)
        t['ahead'] = W_AHEAD * math.degrees(math.acos(max(-1.0, min(1.0, float(np.dot(b, AHEAD)))))) ** 2
        fdir = (E - W) / np.linalg.norm(E - W)
        t['fore'] = 0.03 * ang(scr(W + fdir * 10.0) - scr(W), FORE) ** 2
        if E[0] > 1.0:
            en = scr(E)
            t['elbow'] = 30.0 * max(0.0, min(1.12 - abs(en[0]), 1.12 - abs(en[1]))) ** 2 * 100
        # The curled fingers (palm side) and the blade flat face in, towards the camera.
        t['palm'] = 60.0 * band(float(np.dot(g['palm_r'], view)), -1.0, -0.45) ** 2
        mid = (base + tip) * 0.5
        t['flat'] = 40.0 * max(0.0, 0.45 - abs(float(np.dot(g['flat_r'], mid / np.linalg.norm(mid))))) ** 2
        e_scr = (scr(mid + g['edge_r'] * 3.0) - scr(mid)) * PX
        t['edge'] = 20.0 * band(float(e_scr[1]) / max(np.linalg.norm(e_scr), 1e-6), 0.30, 1.0) ** 2   # edge down
        t['wrist'] = 0.3 * (band(d['ext'], *LIMITS['ext']) ** 2 + band(d['uln'], *LIMITS['uln']) ** 2)
        t['twist'] = 0.2 * band(math.degrees(d['theta']), *LIMITS['twist']) ** 2
        t['rho'] = 0.1 * band(g['rho_r'], *LIMITS['rho']) ** 2
        t['rollu'] = 0.05 * band(d['roll_u'], *LIMITS['roll_u']) ** 2
        t['reach'] = 400.0 * band(d['reach'], *LIMITS['reach']) ** 2
        t['depth'] = 2.0 * band(grip[0], *LIMITS['depth']) ** 2 + 0.2 * (grip[0] - DEPTH) ** 2
        t['lens'] = 5.0 * max(0.0, 16.0 - min(tip[0], base[0], W[0])) ** 2
        prm = unpack(x)[0]
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
    d = g['dr']
    b = (g['tip_r'] - g['base_r']) / np.linalg.norm(g['tip_r'] - g['base_r'])
    mid = (g['base_r'] + g['tip_r']) * 0.5
    return dict(total=total, terms={k: round(v, 4) for k, v in t.items() if v > 1e-4}, x=[float(v) for v in x],
                flip=list(F.flip), right=conv(r), left_mirrored=conv(l),
                diag_r=dict(ext=round(d['ext'], 1), uln=round(d['uln'], 1), twist=round(math.degrees(d['theta']), 1),
                            rho=round(g['rho_r'], 1), reach=round(d['reach'], 3), roll_u=round(d['roll_u'], 1),
                            palm_view=round(float(np.dot(g['palm_r'], g['grip_r'] / np.linalg.norm(g['grip_r']))), 3),
                            flat_view=round(float(np.dot(g['flat_r'], mid / np.linalg.norm(mid))), 3),
                            ahead_deg=round(math.degrees(math.acos(min(1.0, float(np.dot(b, AHEAD))))), 1)),
                ndc_r={k: [round(float(v), 3) for v in scr(g[k + '_r'])] for k in ('grip', 'base', 'tip')},
                cam_r=dict(grip=[round(float(v), 2) for v in g['grip_r']], tip=[round(float(v), 2) for v in g['tip_r']],
                           W=[round(float(v), 2) for v in g['Wr']], E=[round(float(v), 2) for v in g['Er']]))


def fit(F, flip, x_full, rng, n_starts=40):
    F.flip = (flip, x_full_flip_l(F))

    def f(v):
        x = x_full.copy()
        x[SLOTS] = v
        return F.cost(x)
    grip = np.array([DEPTH, GRIP[0] * DEPTH * 1.3643, -GRIP[1] * DEPTH * 0.7673])
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


def x_full_flip_l(F):
    return getattr(F, 'flip_l', None)


def main():
    F = ThrustFitter()
    left = json.loads(LEFT_R3.read_text('utf-8'))
    F.flip_l = left['flip'][1]                              # R3 left: forward grip (None)
    x = np.array(left['x'], float)
    rng = np.random.default_rng(4)
    results = []
    for flip in ('y', 'x', None):
        c, xs = fit(F, flip, x, rng)
        F.flip = (flip, F.flip_l)
        out = describe(F, xs)
        print('flip %s  cost %.3f' % (flip or 'forward', c), out['diag_r'], {k: round(v, 2) for k, v in out['terms'].items() if v > 0.05},
              flush=True)
        results.append((c, flip, xs))
    c, flip, xs = min(results, key=lambda t: t[0])
    F.flip = (flip, F.flip_l)
    out = describe(F, xs)
    (P / 'Work' / 'fit_run_r4.json').write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({k: out[k] for k in ('total', 'flip', 'terms', 'diag_r', 'ndc_r', 'cam_r')}, ensure_ascii=False))
    if '--accept' in sys.argv:
        keys = dict(source='R4 fit_run_r4.py (Work/fit_run_r4.json): right thrust-ahead reverse grip; left = R3 (fit_run_r12)',
                    right=out['right'], left_mirrored=out['left_mirrored'])
        (P / 'run_keys.json').write_text(json.dumps(keys, indent=1), encoding='utf-8')
        print('wrote run_keys.json')


if __name__ == '__main__':
    main()
