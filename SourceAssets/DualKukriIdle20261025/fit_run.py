"""Fit the dual-kukri sprint pose to the reference (BV19dUqBJECT, 握持姿势 奔跑, file 16.75-18.4 s, still 17.50 s).

Screen targets read on Saved/Reference/DualKukriBV19dUqBJECT20261025/sheets/grid_run_525.jpg (NDC, x right, y down)
and the zooms sheets/run_rfist_zoom.jpg / run_lfist_zoom.jpg (17.4-18.4 s):
  right fist   raised to the right edge, grip (0.86, -0.30); forearm runs straight down the right edge.  REVERSE grip:
               knuckles up, the curled fingers (palm side) face the camera, the blade leaves the little-finger side
  right blade  left across the upper half, 6 deg below horizontal, tip (0.25, -0.21); glowing edge down
  left fist    low centre, grip (-0.14, 0.74); forearm from below.  The reference holds it reverse too (back of the
               hand to the camera, blade from the little-finger side), but on this rig that needs a 107-113 deg
               forearm wring (Work/left_options.py), so the left keeps the forward grip with the palm to the camera
  left blade   left, 15 deg above horizontal (tip (-0.70, 0.48)); flat to the camera, edge up
  size         left fist near (~28 cm), right fist ~34 cm
The run starts with a flourish (16.3-16.7 s) that turns both swords into these reverse grips.  R1 kept the forward
grip, which needed a ~96 deg forearm wring on the raised right arm (user: the hands and wrists are twisted).

The cost has no terms between the arms, so each arm is fitted alone: its 5 arm parameters + 3 clavicle angles from
random starts.  Right: both reverse flips (dual_rig 'x': edge on the knuckle side, 'y': edge on the palm side), the
better wins ('y').  Left: forward grip; its elbow stays in front of the chest (runs 7-8 folded it under the chin, 4-7 cm
from the eye) and its wrist within ext 20 / radial 12 deg.  Skin twist (forearm roll vs bind) is held within +-70 deg,
anatomical rotation within +-85.  R3 (corrected read-out, TARGET below): left from run 11 (forward grip still
scores far better than reverse: 14.8 vs 38.8 / 81.7), right from Work/right_wrist_r12.py (wrist within 25 deg, flip 'y';
run 11's right sat at ext 40 / ulnar 32), assembled in Work/fit_run_r12.json.
Run:  python -I fit_run.py [--accept]     -> Work/fit_run.json (+ run_keys.json with --accept)
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

# R3 read-out (sheets/grid_run_TR.jpg, grid_run_B.jpg at full resolution; R1/R2 put the right fist 0.23 NDC too low,
# the right blade too level and the left forearm too steep):
#   right  fist (0.84, -0.53) in the top-right corner, handle left to the guard (0.60, -0.50), blade curving down-left
#          to (0.25, -0.22): ~17 deg below horizontal; forearm straight down the right edge
#   left   fist (-0.10, 0.79) (back of the hand at (-0.12, 0.72)), pommel out to the lower right, blade up-left to
#          (-0.71, 0.48): ~15 deg; forearm in from the lower left at ~45 deg
TARGET = dict(
    grip_r=np.array([0.84, -0.53]), blade_r=unit_px(-17.0, True), fore_r=unit_px(-85.0, False),
    grip_l=np.array([-0.10, 0.79]), blade_l=unit_px(15.0, True), fore_l=unit_px(-45.0, True),
    # The near left fist makes the kukri as long on the screen as the reference blade; the right kukri at ~36 cm ends
    # on the reference blade line short of its tip.
    tip_r=np.array([0.32, -0.27]), tip_l=np.array([-0.71, 0.48]),
)
LIMITS = dict(ext=(-40.0, 40.0), uln=(-15.0, 32.0), twist=(-70.0, 70.0), rho=(-85.0, 85.0), roll_u=(-100.0, 70.0),
              reach=(0.36, 0.93), depth=(20.0, 50.0), clav=(-15.0, 15.0))
DEPTH = dict(l=26.0, r=36.0)
# Palm normal . view ray: both palms to the camera (<= -0.25; the right reverse, the left forward grip).
PALM = dict(r=(-1.0, -0.25), l=(-1.0, -0.25))
PALM_REVERSE_L = (0.30, 1.0)   # reference left: back of the hand to the camera
# Edge direction on the screen (normalised y, + = down): right edge down, left edge up.
EDGE = dict(r=(0.30, 1.0), l=(-1.0, -0.30))
SLOTS = dict(r=list(range(0, 7)) + list(range(14, 17)), l=list(range(7, 14)) + list(range(17, 20)))


class RunFitter(Fitter):
    def side_terms(self, g, s, x):
        terms = {}
        grip, base, tip = g['grip_' + s], g['base_' + s], g['tip_' + s]
        W, E = g['W' + s], g['E' + s]
        terms['grip'] = 40.0 * float(np.sum((scr(grip) - TARGET['grip_' + s]) ** 2)) * 100
        terms['blade'] = 0.08 * ang(scr(tip) - scr(base), TARGET['blade_' + s]) ** 2
        fdir = (E - W) / np.linalg.norm(E - W)
        terms['fore'] = 0.006 * ang(scr(W + fdir * 10.0) - scr(W), TARGET['fore_' + s]) ** 2
        if E[0] > 1.0:
            en = scr(E)
            terms['elbow'] = 30.0 * max(0.0, min(1.15 - abs(en[0]), 1.15 - abs(en[1]))) ** 2 * 100
        d = g['d' + s]
        terms['wrist'] = 0.05 * (band(d['ext'], *LIMITS['ext']) ** 2 + band(d['uln'], *LIMITS['uln']) ** 2)
        terms['twist'] = 0.1 * band(math.degrees(d['theta']), *LIMITS['twist']) ** 2
        terms['rho'] = 0.05 * band(g['rho_' + s], *LIMITS['rho']) ** 2
        terms['rollu'] = 0.05 * band(d['roll_u'], *LIMITS['roll_u']) ** 2
        terms['reach'] = 400.0 * band(d['reach'], *LIMITS['reach']) ** 2
        terms['depth'] = 2.0 * band(grip[0], *LIMITS['depth']) ** 2 + 0.2 * (grip[0] - DEPTH[s]) ** 2
        terms['lens'] = 5.0 * max(0.0, 16.0 - min(tip[0], base[0], W[0])) ** 2
        terms['tip'] = (2.0 if s == 'r' else 10.0) * float(np.sum((scr(tip) - TARGET['tip_' + s]) ** 2)) * 100
        terms['fwd'] = 2.0 * max(0.0, grip[0] - tip[0] - 2.0) ** 2   # blades point away, not at the lens
        pv = float(np.dot(g['palm_' + s], grip / np.linalg.norm(grip)))
        palm = PALM_REVERSE_L if s == 'l' and self.flip[1] else PALM[s]
        terms['palm'] = 40.0 * band(pv, *palm) ** 2
        mid = (base + tip) * 0.5
        e_scr = (scr(mid + g['edge_' + s] * 3.0) - scr(mid)) * PX
        terms['edge'] = 20.0 * band(float(e_scr[1]) / max(np.linalg.norm(e_scr), 1e-6), *EDGE[s]) ** 2
        if s == 'l':
            terms['flat'] = 20.0 * max(0.0, 0.60 - abs(float(np.dot(g['flat_l'], mid / np.linalg.norm(mid))))) ** 2
            # The low left fist must not fold the elbow into the chest under the chin (run 7/8: elbow 4-7 cm in front
            # of the eye on the midline -- inside the body, and its skin cut by the near plane at the screen bottom).
            terms['chest'] = 2.0 * (max(0.0, 13.0 - E[0]) ** 2 + max(0.0, E[1] + 7.0) ** 2)
            terms['wrist'] += 0.2 * (band(d['ext'], -40.0, 20.0) ** 2 + band(d['uln'], -12.0, 25.0) ** 2)
        prm = unpack(x)[0 if s == 'r' else 1]
        terms['prior'] = 0.002 * (prm['de'] ** 2 + (prm['du'] - 12) ** 2)
        c = np.array(prm['C'])
        terms['clav'] = 0.01 * float(np.sum(c ** 2)) + 2.0 * sum(band(v, *LIMITS['clav']) ** 2 for v in c)
        return terms

    def cost(self, x, report=False, sides='rl'):
        g = self.geometry(x)
        terms = {}
        for s in sides:
            terms.update({k + '_' + s: v for k, v in self.side_terms(g, s, x).items()})
        total = float(sum(terms.values()))
        return (total, terms, g) if report else total


def describe(F, x):
    total, terms, g = F.cost(x, report=True)
    r, l = unpack(x)
    r['flip'], l['flip'] = F.flip
    conv = lambda d: {k: (list(map(float, v)) if isinstance(v, tuple) else v if v is None or isinstance(v, str) else float(v))
                      for k, v in d.items()}
    out = dict(total=total, terms={k: round(v, 4) for k, v in terms.items() if v > 1e-4}, x=[float(v) for v in x],
               flip=list(F.flip), right=conv(r), left_mirrored=conv(l))
    for s in 'rl':
        d = g['d' + s]
        out['diag_' + s] = dict(ext=round(d['ext'], 1), uln=round(d['uln'], 1), twist=round(math.degrees(d['theta']), 1),
                                rho=round(g['rho_' + s], 1), reach=round(d['reach'], 3), roll_u=round(d['roll_u'], 1),
                                palm_view=round(float(np.dot(g['palm_' + s], g['grip_' + s] / np.linalg.norm(g['grip_' + s]))), 3))
        out['ndc_' + s] = {k: [round(float(v), 3) for v in scr(g[k + '_' + s])] for k in ('grip', 'base', 'tip')}
        out['ndc_' + s]['wrist'] = [round(float(v), 3) for v in scr(g['W' + s])]
        out['cam_' + s] = {k: [round(float(v), 2) for v in g[k + '_' + s]] for k in ('grip', 'tip')}
        out['blade_deg_' + s] = round(ang(scr(g['tip_' + s]) - scr(g['base_' + s]), TARGET['blade_' + s]), 1)
    return out


def fit_side(F, s, flip, x_full, rng, n_starts=36):
    """Fit one arm's 8 parameters (the other arm stays as in x_full); returns (cost, full vector)."""
    F.flip = (flip, F.flip[1]) if s == 'r' else (F.flip[0], flip)
    idx = SLOTS[s]

    def f(v):
        x = x_full.copy()
        x[idx] = v
        return F.cost(x, sides=s)
    tg = TARGET['grip_' + s]
    d0 = DEPTH[s]
    grip = np.array([d0, tg[0] * d0 * 1.3643, -tg[1] * d0 * 0.7673])                          # actual camera cm
    if s == 'l':
        grip[1] = -grip[1]                                                                       # mirrored space
    found = []
    for _ in range(n_starts):
        W = grip + rng.normal(0, 5.0, 3)
        v0 = np.r_[W, rng.uniform(-40, 150), rng.uniform(-180, 180), rng.normal(0, 10), rng.normal(10, 10), rng.normal(0, 4, 3)]
        res = minimize(f, v0, method='L-BFGS-B', options=dict(maxiter=400))
        found.append((res.fun, res.x))
    found.sort(key=lambda t: t[0])
    best = None
    for c, v in found[:4]:
        res = minimize(f, v, method='Powell', options=dict(maxiter=8000, xtol=1e-3, ftol=1e-7))
        if best is None or res.fun < best[0]:
            best = (res.fun, res.x)
    x = x_full.copy()
    x[idx] = best[1]
    return best[0], x


def main():
    F = RunFitter()
    F.flip = (None, None)
    rng = np.random.default_rng(11)
    x = np.array(json.loads((P / 'Work' / 'fit_run_r6.json').read_text('utf-8'))['x'], float)   # R1 pose as filler
    choice = {}
    for s in 'rl':
        results = []
        for flip in (('x', 'y') if s == 'r' else (None, 'x', 'y')):
            c, xs = fit_side(F, s, flip, x, rng)
            print('%s flip %s  cost %.3f' % (s, flip or 'forward', c), flush=True)
            results.append((c, flip, xs))
        c, flip, xs = min(results, key=lambda t: t[0])
        choice[s] = flip
        x[SLOTS[s]] = xs[SLOTS[s]]
        F.flip = (choice.get('r'), choice.get('l'))
    F.flip = (choice['r'], choice['l'])
    out = describe(F, x)
    (P / 'Work').mkdir(exist_ok=True)
    (P / 'Work' / 'fit_run.json').write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({k: out[k] for k in ('total', 'flip', 'terms', 'diag_r', 'diag_l', 'ndc_r', 'ndc_l', 'cam_r', 'cam_l',
                                          'blade_deg_r', 'blade_deg_l')}, ensure_ascii=False))
    if '--accept' in sys.argv:
        keys = dict(source='fit_run.py', right=out['right'], left_mirrored=out['left_mirrored'])
        (P / 'run_keys.json').write_text(json.dumps(keys, indent=1), encoding='utf-8')
        print('wrote run_keys.json')


if __name__ == '__main__':
    main()
