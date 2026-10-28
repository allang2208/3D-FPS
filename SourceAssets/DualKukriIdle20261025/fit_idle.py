"""Fit the dual-kukri idle hold to the reference (BV19dUqBJECT, 握持姿势（站立）, file 2.3-4.1 s, still frame 3.5 s).

Screen targets are read on Saved/Reference/DualKukriBV19dUqBJECT20261025/sheets/grid_105_*.jpg (NDC, x right,
y down, frame f00105 = 3.50 s).  The reference blades are long Apex swords; only the fist positions, blade and
forearm screen directions, the blade faces and the crossing (left blade over the right blade root) are fitted.

  right fist   grip on the handle axis (0.19, 0.72); visible fist bulk (0.185, 0.77)
  right blade  up-left, 22.7 deg above horizontal (px), straight line through the tip (-0.68, 0.04)
  right arm    forearm leaves the fist down-right ~20 deg below horizontal, elbow off screen
  left fist    grip (-0.43, 0.84) (handle leaves the fist at (-0.36, 0.82)); back of the hand up, knuckles forward
  left blade   right, 11 deg overall / 19 deg near the fist (target 17); flat seen from above, edge forward (up)
  left arm     forearm leaves the fist down-left ~32 deg below horizontal, elbow off screen
  crossing     left blade over the right blade root (right guard at (0.0, 0.50)); left blade nearer the camera,
               passing above the right fist
  size         the left gauntlet reads ~1.8x the right fist: left fist near (~27-29 cm), right far (~37 cm)

The kukri is about half the reference blade length on screen, so with the fists and blade directions pinned the
left blade crosses the right kukri at ~64 % of its own blade (reference: ~45 %) and ~40 % up the right kukri.
Accepted: run 10 (Work/fit_idle_run10.json -> pose_keys.json).  Runs 1-9 tuned the terms: back of both hands to
the camera (run 4), right blade face (run 3), fist screen clearance (runs 6-8; run 7 had a point-segment NaN bug),
nearer depth priors (runs 9-10).
Parameters: dual_rig arm parameters for the right arm and the mirrored left arm (W, phi, psi, de, du).
Run:  python -I fit_idle.py [--refine] [--accept]     -> Work/fit_idle.json (+ pose_keys.json with --accept)
      --refine starts from run 10 (accepted look) and adds only the mesh clearance (run 11).
      --hunter (R16, 2026-10-27, user: "tilt the blades a little forward and part them a little more; the new 猎手刀身
      long blade makes the dual hold clip") starts from run 11 and checks the clearance on the hunter blade envelope
      (kukri_sdf KUKRI_SDF_VARIANT=hunter: run 11 cuts it by 0.5 cm), 2.5 cm instead of 1.5, its 10 cm longer blade
      also kept off the other fist, and tilts both blades forward (run 11 pointed them back toward the eye, view-x
      -0.40 / -0.32).
"""
import json
import math
import os
import sys
from pathlib import Path

if '--hunter' in sys.argv:
    os.environ['KUKRI_SDF_VARIANT'] = 'hunter'

import numpy as np
from scipy.optimize import minimize

P = Path(__file__).resolve().parent
sys.path.insert(0, str(P))
from dual_rig import DualRig, ndc, TIP, BLADE_BASE  # noqa: E402
import kukri_sdf as S  # noqa: E402
from kmath import mesh_to_cam  # noqa: E402

PX = np.array([960.0, 540.0])   # NDC -> px half extents (1920x1080)


def unit_px(deg_up, leftwards):
    a = math.radians(deg_up)
    return np.array([-math.cos(a) if leftwards else math.cos(a), -math.sin(a)])


TARGET = dict(
    grip_r=np.array([0.19, 0.72]), blade_r=unit_px(22.7, True), fore_r=unit_px(-20.0, False),
    grip_l=np.array([-0.43, 0.84]), blade_l=unit_px(17.0, False), fore_l=unit_px(-32.0, True),
    wrist_r=np.array([0.28, 0.72]), wrist_l=np.array([-0.66, 0.92]),
)
LIMITS = dict(ext=(-40.0, 40.0), uln=(-15.0, 32.0), twist=(-95.0, 80.0), reach=(0.36, 0.93), depth=(22.0, 56.0))
if '--hunter' in sys.argv:
    LIMITS['twist'] = (-95.0, 65.0)     # R16: the forward tilt must not come from a wrung forearm (run 11: 46 / 57)
# Apparent size: the left gauntlet reads ~1.8x the right fist -> left near, right far (soft).
DEPTH = dict(l=27.0, r=37.0)
FIST_BONES = ('index_01_r', 'index_02_r', 'index_03_r', 'middle_01_r', 'middle_02_r', 'thumb_02_r', 'thumb_03_r')
# Real-mesh clearance between the two kukris (kukri_sdf.py).  The segment clearance alone ignored the blade width and
# curve: run 10 left 0.03 cm at the hold and -0.5 cm in the walk (user: the two blades clip).
GAP_MIN = 2.5 if '--hunter' in sys.argv else 1.5
GAP_PTS = S.SURFACE[::4]
HUNTER = '--hunter' in sys.argv
HUNTER_TIP = np.array([6.18, 0.0, 36.135])   # KukriHunterBlade20261027/hunter.json trace_tip_cm
# R16: blade direction view-x (camera forward component) at least this much (run 11: -0.40 right, -0.32 left).
FWD_MIN = dict(r=-0.12, l=-0.15)
# R16: the forward tilt costs ulnar deviation on the hammer grip; a stiffer wrist band keeps the hold natural.
WRIST_W = 0.25 if HUNTER else 0.05
NAMES = ['rWx', 'rWy', 'rWz', 'rphi', 'rpsi', 'rde', 'rdu', 'lWx', 'lWy', 'lWz', 'lphi', 'lpsi', 'lde', 'ldu']


def unpack(x):
    """14 arm parameters, optionally followed by the right and left clavicle angles (fit_run.py)."""
    r = dict(W=tuple(x[0:3]), phi=x[3], psi=x[4], de=x[5], du=x[6])
    l = dict(W=tuple(x[7:10]), phi=x[10], psi=x[11], de=x[12], du=x[13])
    if len(x) >= 20:
        r['C'], l['C'] = tuple(x[14:17]), tuple(x[17:20])
    return r, l


def scr(cam):
    return np.array(ndc(cam))


def ang(v, u):
    v = v * PX
    n = np.linalg.norm(v)
    if not np.isfinite(n) or n < 1e-6:
        return 180.0
    return math.degrees(math.acos(max(-1.0, min(1.0, float(np.dot(v / n, u))))))


def band(v, lo, hi):
    return (lo - v) if v < lo else (v - hi) if v > hi else 0.0


def seg_dist(a0, a1, b0, b1):
    """Closest distance between 3D segments and the parameters."""
    d1, d2, r = a1 - a0, b1 - b0, a0 - b0
    a, e, f = np.dot(d1, d1), np.dot(d2, d2), np.dot(d2, r)
    c, b = np.dot(d1, r), np.dot(d1, d2)
    den = a * e - b * b
    s = np.clip((b * f - c * e) / den, 0, 1) if den > 1e-9 else 0.0
    t = (b * s + f) / e
    if t < 0:
        t, s = 0.0, np.clip(-c / a, 0, 1)
    elif t > 1:
        t, s = 1.0, np.clip((b - c) / a, 0, 1)
    return float(np.linalg.norm(a0 + d1 * s - b0 - d2 * t)), s, t


def pt_seg_px(p, a, b):
    """Screen distance (px) from NDC point p to the NDC segment a-b."""
    p, a, b = p * PX, a * PX, b * PX
    d = b - a
    u = float(np.clip(np.dot(p - a, d) / max(np.dot(d, d), 1e-9), 0.0, 1.0))
    return float(np.linalg.norm(a + d * u - p))


def cross2(p0, p1, q0, q1):
    """Screen intersection parameters (s along p, t along q) of two 2D lines."""
    d, e = (p1 - p0) * PX, (q1 - q0) * PX
    den = d[0] * e[1] - d[1] * e[0]
    if abs(den) < 1e-9:
        return None
    w = (q0 - p0) * PX
    return (w[0] * e[1] - w[1] * e[0]) / den, (w[0] * d[1] - w[1] * d[0]) / den


class Fitter:
    def __init__(self):
        self.D = DualRig()
        # Right fist outline points, rigid in the grip frame (the fist never moves on the handle).
        R = self.D.R
        K0 = R.hand_rel.inverse() * R.base['hand_r']
        K0 = type(K0)(K0.p, K0.q, (1, 1, 1))
        self.fist_pts = [K0.inverse().point(R.base[n].p) for n in FIST_BONES]

    def geometry(self, x):
        D = self.D
        r, l = unpack(x)
        r['flip'], l['flip'] = getattr(self, 'flip', (None, None))
        Kr, Er, dr = D.arm(r)
        Kv, Ev, dl = D.arm(l)
        Kl = D.left_kukri(Kv)
        g = dict(dr=dr, dl=dl, Kr=Kr, Kl=Kl)
        # Palm normals (right hand +Y; the left palm is the mirror of the virtual right palm).
        g['palm_r'] = mesh_to_cam((D.R.hand_rel * dr['K_hand']).axis(1))
        g['palm_l'] = mesh_to_cam(np.diag([-1.0, 1.0, 1.0]) @ (D.R.hand_rel * dl['K_hand']).axis(1))
        # Anatomical forearm rotation (kukri_rig.solve_arm's rho: 0 thumb up / palm medial, + supination), per arm in
        # its own (virtual right) space.
        for s, K, E, d in (('r', Kr, Er, dr), ('l', Kv, Ev, dl)):
            uc, fc = mesh_to_cam(E - d['S']), mesh_to_cam(d['W'] - E)
            uc, fc = uc / np.linalg.norm(uc), fc / np.linalg.norm(fc)
            med = np.cross(uc, fc); med = med / max(np.linalg.norm(med), 1e-9)
            up_side = -uc - fc * np.dot(-uc, fc); up_side = up_side / max(np.linalg.norm(up_side), 1e-9)
            palm = mesh_to_cam((D.R.hand_rel * d['K_hand']).axis(1)); palm = palm - fc * np.dot(palm, fc)
            g['rho_' + s] = math.degrees(math.atan2(np.dot(palm, up_side), np.dot(palm, med)))
        g['Wr'], g['Er'] = mesh_to_cam(dr['W']), mesh_to_cam(Er)
        g['Wl'], g['El'] = mesh_to_cam(D.to_left(dl['W'])), mesh_to_cam(D.to_left(Ev))
        for s in 'rl':
            K = g['K' + s]
            g['grip_' + s] = mesh_to_cam(K.p)
            g['base_' + s] = mesh_to_cam(K.point(BLADE_BASE))
            g['tip_' + s] = mesh_to_cam(K.point(TIP))
            g['tipx_' + s] = mesh_to_cam(K.point(HUNTER_TIP if HUNTER else TIP))
            g['flat_' + s] = mesh_to_cam(K.axis(1))
            g['edge_' + s] = mesh_to_cam(K.axis(0))
        return g

    def cost(self, x, report=False):
        g = self.geometry(x)
        terms = {}
        for s in 'rl':
            grip, base, tip = g['grip_' + s], g['base_' + s], g['tip_' + s]
            W, E = g['W' + s], g['E' + s]
            terms['grip_' + s] = 40.0 * float(np.sum((scr(grip) - TARGET['grip_' + s]) ** 2)) * 100
            terms['blade_' + s] = 0.08 * ang(scr(tip) - scr(base), TARGET['blade_' + s]) ** 2
            fdir = (E - W) / np.linalg.norm(E - W)
            terms['fore_' + s] = (0.03 if s == 'r' else 0.01) * ang(scr(W + fdir * 10.0) - scr(W), TARGET['fore_' + s]) ** 2
            terms['wristpos_' + s] = 0.3 * float(np.sum((scr(W) - TARGET['wrist_' + s]) ** 2)) * 100
            # Back of the hand towards the camera: the palm faces along the view ray.
            vf = grip / np.linalg.norm(grip)
            terms['palm_' + s] = 60.0 * max(0.0, (0.60 if s == 'l' else 0.45) - float(np.dot(g['palm_' + s], vf))) ** 2
            # Elbow off screen (or behind the eye).
            if E[0] > 1.0:
                en = scr(E)
                inside = min(1.15 - abs(en[0]), 1.15 - en[1])
                terms['elbow_' + s] = 30.0 * max(0.0, inside) ** 2 * 100
            d = g['d' + s]
            terms['wrist_' + s] = WRIST_W * (band(d['ext'], *LIMITS['ext']) ** 2 + band(d['uln'], *LIMITS['uln']) ** 2)
            terms['twist_' + s] = 0.05 * band(math.degrees(d['theta']), *LIMITS['twist']) ** 2
            terms['reach_' + s] = 400.0 * band(d['reach'], *LIMITS['reach']) ** 2
            terms['depth_' + s] = 2.0 * band(grip[0], *LIMITS['depth']) ** 2 + 0.3 * (grip[0] - DEPTH[s]) ** 2
            terms['lens_' + s] = 5.0 * max(0.0, 16.0 - min(tip[0], base[0], W[0])) ** 2
        # Left blade: flat seen from above, edge forward (up on the screen).
        mid = (g['base_l'] + g['tip_l']) * 0.5
        view = mid / np.linalg.norm(mid)
        terms['flat_l'] = 40.0 * max(0.0, 0.80 - abs(float(np.dot(g['flat_l'], view)))) ** 2
        e_scr = scr(mid + g['edge_l'] * 3.0) - scr(mid)
        terms['edge_l'] = 20.0 * max(0.0, float(e_scr[1] * PX[1]) / max(np.linalg.norm(e_scr * PX), 1e-6) + 0.5) ** 2
        # Right blade: flat partly towards the camera, edge up on the screen (reference blade A shows its face).
        mid_r = (g['base_r'] + g['tip_r']) * 0.5
        terms['flat_r'] = 20.0 * max(0.0, 0.55 - abs(float(np.dot(g['flat_r'], mid_r / np.linalg.norm(mid_r))))) ** 2
        e_scr = scr(mid_r + g['edge_r'] * 3.0) - scr(mid_r)
        terms['edge_r'] = 20.0 * max(0.0, float(e_scr[1] * PX[1]) / max(np.linalg.norm(e_scr * PX), 1e-6) + 0.3) ** 2
        # The left blade runs above the right fist, not into it.
        bl, tl, gr = scr(g['base_l']), scr(g['tip_l']), scr(g['grip_r'])
        if tl[0] > gr[0] - 0.05 and abs(tl[0] - bl[0]) > 1e-3:
            y_at = bl[1] + (tl[1] - bl[1]) * (gr[0] - 0.05 - bl[0]) / (tl[0] - bl[0])
            terms['above_fist'] = 40.0 * max(0.0, y_at - (gr[1] - 0.10)) ** 2 * 100
        # ... and its tip stays clear of the right fist on the screen (reference: blade B passes well above it).
        terms['fist_gap'] = 0.004 * max(0.0, 105.0 - pt_seg_px(gr, bl, tl)) ** 2
        for q in self.fist_pts:
            fp = scr(mesh_to_cam(g['Kr'].point(q)))
            terms['fist_gap'] += 0.004 * max(0.0, 65.0 - pt_seg_px(fp, bl, tl)) ** 2
        # Crossing: the left blade passes over the right kukri above its root, with blade to spare.
        st = cross2(scr(g['base_l']), scr(g['tip_l']), scr(g['grip_r']), scr(g['tip_r']))
        if st is None:
            terms['cross'] = 50.0
        else:
            s_, t_ = st
            terms['cross'] = 200.0 * (band(s_, 0.45, 0.70) ** 2 + band(t_, 0.40, 0.60) ** 2)
            pl = g['base_l'] + (g['tip_l'] - g['base_l']) * s_
            pr = g['grip_r'] + (g['tip_r'] - g['grip_r']) * t_
            terms['over'] = 2.0 * max(0.0, np.linalg.norm(pl) - np.linalg.norm(pr) + 2.0) ** 2
        # 3D clearances: blades, left blade vs right fist, forearms.
        dist, _, _ = seg_dist(g['base_l'], g['tip_l'], g['grip_r'] - (g['base_r'] - g['grip_r']) * 1.6, g['tip_r'])
        terms['clear_blades'] = 4.0 * max(0.0, 1.6 - dist) ** 2
        dist, _, _ = seg_dist(g['base_l'], g['tipx_l'], g['Wr'], g['grip_r'])
        terms['clear_fist'] = 4.0 * max(0.0, 4.5 - dist) ** 2
        if HUNTER:
            # The long right blade kept off the left fist / wrist too, and both blades tilted forward.
            dist, _, _ = seg_dist(g['base_r'], g['tipx_r'], g['Wl'], g['grip_l'])
            terms['clear_fist_l'] = 4.0 * max(0.0, 4.5 - dist) ** 2
            for s in 'rl':
                b = (g['tip_' + s] - g['base_' + s]) / np.linalg.norm(g['tip_' + s] - g['base_' + s])
                terms['forward_' + s] = 300.0 * max(0.0, FWD_MIN[s] - float(b[0])) ** 2
        dist, _, _ = seg_dist(g['Wl'], g['El'], g['Wr'], g['Er'])
        terms['clear_arms'] = 2.0 * max(0.0, 9.0 - dist) ** 2
        gap = min(S.kukri_gap(g['Kl'], g['Kr'], GAP_PTS), S.kukri_gap(g['Kr'], g['Kl'], GAP_PTS))
        terms['mesh_gap'] = 30.0 * max(0.0, GAP_MIN - gap) ** 2
        # Mild priors: wrists near the accepted fist relation, clean twist.
        r, l = unpack(x)
        terms['prior'] = 0.002 * (r['de'] ** 2 + l['de'] ** 2 + (r['du'] - 12) ** 2 + (l['du'] - 12) ** 2)
        total = float(sum(terms.values()))
        if report:
            return total, terms, g
        return total


def describe(F, x):
    total, terms, g = F.cost(x, report=True)
    r, l = unpack(x)
    out = dict(total=total, terms={k: round(v, 4) for k, v in terms.items() if v > 1e-4}, x=[float(v) for v in x],
               right={k: (list(map(float, v)) if isinstance(v, tuple) else float(v)) for k, v in r.items()},
               left_mirrored={k: (list(map(float, v)) if isinstance(v, tuple) else float(v)) for k, v in l.items()})
    for s in 'rl':
        d = g['d' + s]
        out['diag_' + s] = dict(ext=round(d['ext'], 1), uln=round(d['uln'], 1), twist=round(math.degrees(d['theta']), 1),
                                reach=round(d['reach'], 3), roll_u=round(d['roll_u'], 1),
                                palm_view=round(float(np.dot(g['palm_' + s], g['grip_' + s] / np.linalg.norm(g['grip_' + s]))), 3))
        out['ndc_' + s] = {k: [round(float(v), 3) for v in scr(g[k + '_' + s])] for k in ('grip', 'base', 'tip')}
        out['ndc_' + s]['wrist'] = [round(float(v), 3) for v in scr(g['W' + s])]
        out['cam_' + s] = {k: [round(float(v), 2) for v in g[k + '_' + s]] for k in ('grip', 'tip')}
        out['blade_deg_' + s] = round(ang(scr(g['tip_' + s]) - scr(g['base_' + s]), TARGET['blade_' + s]), 1)
        b = (g['tip_' + s] - g['base_' + s]) / np.linalg.norm(g['tip_' + s] - g['base_' + s])
        out['blade_dir_' + s] = [round(float(v), 3) for v in b]
    st = cross2(scr(g['base_l']), scr(g['tip_l']), scr(g['grip_r']), scr(g['tip_r']))
    out['cross_st'] = [round(float(v), 3) for v in st] if st else None
    out['kukri_gap_cm'] = round(min(S.kukri_gap(g['Kl'], g['Kr']), S.kukri_gap(g['Kr'], g['Kl'])), 2)
    out['sdf_variant'] = S.VARIANT
    return out


def main():
    F = Fitter()
    starts = []
    if '--refine' in sys.argv or HUNTER:
        # Keep the accepted look (run 10; R16: run 11) and only open the blades apart (R16: and tilt them forward).
        x0 = np.array(json.loads((P / 'Work' / ('fit_idle_run11.json' if HUNTER else 'fit_idle_run10.json')).read_text('utf-8'))['x'])
        rng = np.random.default_rng(3)
        starts = [x0] + [x0 + rng.normal(0, 1, x0.size) * np.r_[[1.0] * 3, 4, 4, 2, 2, [1.0] * 3, 4, 4, 2, 2] for _ in range(5)]
    for rpsi in (() if ('--refine' in sys.argv or HUNTER) else (60.0, 100.0, 140.0)):
        for lpsi in (-10.0, 30.0, 70.0, 110.0):
            for lphi in (20.0, 60.0):
                starts.append([33.0, 15.0, -22.0, 40.0, rpsi, 0.0, 12.0, 31.0, 25.0, -24.0, lphi, lpsi, 0.0, 12.0])
    best = None
    for i, x0 in enumerate(starts):
        res = minimize(F.cost, np.array(x0), method='L-BFGS-B', options=dict(maxiter=600))
        res = minimize(F.cost, res.x, method='Powell', options=dict(maxiter=6000, xtol=1e-3, ftol=1e-6))
        print('start %2d  cost %9.3f' % (i, res.fun), flush=True)
        if best is None or res.fun < best.fun:
            best = res
    out = describe(F, best.x)
    (P / 'Work').mkdir(exist_ok=True)
    (P / 'Work' / 'fit_idle.json').write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(out, indent=1, ensure_ascii=False))
    if '--accept' in sys.argv:
        keys = dict(source='fit_idle.py', right=out['right'], left_mirrored=out['left_mirrored'])
        (P / 'pose_keys.json').write_text(json.dumps(keys, indent=1), encoding='utf-8')
        print('wrote pose_keys.json')


if __name__ == '__main__':
    main()
