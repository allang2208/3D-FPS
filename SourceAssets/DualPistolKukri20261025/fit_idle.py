"""Fit the dual pistol + kukri controls under native reach, wrist limits and forearm clearance.

Hip (default): reference layout — right wrist keeps the M1911 source wrist relation; the left forearm runs
under (behind, on screen) the right forearm with >= 6 cm bone clearance; the left fist sits right of the pistol
hand in full view, back of the hand to the eye; forearms run flat like the reference; blade into the view.
ADS (`--ads`): no reference shot. Harries-style support — sights on the eye axis, no cant; the left wrist
stays crossed under the right wrist, backs of the hands close; the kukri points forward-down and stays out
of the sight picture. Writes pose_controls.json (`--accept`; ADS goes to its `ads` block).
"""
import json, sys
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from scipy.spatial.transform import Rotation as R
sys.path.insert(0, str(Path(__file__).resolve().parent))
import author_idle as A

ADS = '--ads' in sys.argv
HIP = A.controls
BASE = HIP.get('ads') if ADS and 'ads' in HIP else HIP
# Fitted shoulder offsets are relative to these shared first-person arm roots (V4 controls), never to a prior fit.
ROOTS = {k: np.array(HIP['shoulder_roots'][k], float) for k in ('left', 'right')}
FIST_FROM_HAND = np.array([0.25, 0.04])   # reference: fist centre relative to the pistol hand's middle knuckle
FOREARM_DEG = (18, 22)                    # screen angle below horizontal, right / left forearm (reference ~15 / ~18; right relaxed for the wrist)
SRC_R = np.array([15.2, -22.4, 14.6])     # M1911 idle right wrist: flexion, deviation, roll
ORDER = 'fist xyz, knuckle roll, blade yaw, blade pitch, left pole yz, left shoulder dxyz, right shoulder dxyz, right pole yz, rear sight yz, cant, bore yaw'
# Shoulders may protract/settle only a few centimetres around the shared first-person arm roots.
BOUNDS = np.array([[19, 32], [3, 20], [-18, -2], [-90, 90], [-20, 20], [-20, 20], [-50, 10], [-50, -5],
                   [-2, 2], [-2, 2], [-2, 2], [-2, 2], [-2, 2], [-2, 2], [0, 50], [-50, -5],
                   [1, 5], [-3, 1.5], [14, 24], [-6, 8]], float)
if ADS:
    # Sights on the eye axis at the calibrated distance; the gun does not move or cant in this fit.
    BOUNDS[0:3] = [[24, 40], [-2, 16], [-22, -6]]
    BOUNDS[5] = [-20, 8]
    BOUNDS[16:20] = [[-1e-3, 1e-3], [-1e-3, 1e-3], [-1e-3, 1e-3], [-1e-3, 1e-3]]


def ads_base():
    c = json.loads(json.dumps(HIP))
    for k in ('fit', 'ads'): c.pop(k, None)
    c['vertical_fov'] = 55
    c['gun'] = {'rear_sight': [38, 0, 0], 'aim_point': [1000, 0, 0], 'cant_degrees': 0}   # M1911 ADSRearEyeDistance
    c['status'] = 'ADS authoring candidate; Harries-style crossed support, no reference shot'
    return c


def controls(x, base=None):
    base = base or BASE
    c = json.loads(json.dumps(base))
    for k in ('fit', 'ads'): c.pop(k, None)
    fx, fy, fz, roll, yaw, pitch, lpy, lpz, lsx, lsy, lsz, rsx, rsy, rsz, rpy, rpz, gy, gz, cant, gyaw = x
    rear = np.array(base['gun']['rear_sight'], float)
    if not ADS: rear[1:] = gy, gz
    c['gun']['rear_sight'] = rear.tolist()
    c['gun']['cant_degrees'] = 0.0 if ADS else cant
    c['gun']['aim_point'] = (rear + R.from_euler('z', 0 if ADS else gyaw, degrees=True).apply([1000, 0, 0])).tolist()
    c['kukri']['fist_centre'] = [fx, fy, fz]
    d = R.from_euler('zy', [yaw, -pitch], degrees=True).apply([1, 0, 0])
    c['kukri']['blade_direction'] = d.tolist()
    side = np.cross([0, 0, 1], d); side /= np.linalg.norm(side); side = -side if side[1] < 0 else side
    up = np.cross(d, side)
    c['kukri']['knuckle_direction'] = (np.cos(np.radians(roll)) * side + np.sin(np.radians(roll)) * up).tolist()
    c['left_pole'] = [12, lpy, lpz]
    c['left_shoulder'] = (ROOTS['left'] + [lsx, lsy, lsz]).tolist()
    c['right_shoulder'] = (ROOTS['right'] + [rsx, rsy, rsz]).tolist()
    c['right_pole'] = [8, rpy, rpz]
    return c


def screen_order(b):
    """Depth of each forearm where they cross on screen (positive = left lies behind the right)."""
    def proj(p): return np.array([p[1] / p[0], -p[2] / p[0]])
    l0, l1 = b['l']['lowerarm_l'][:3, 3], b['l']['hand_l'][:3, 3]
    r0, r1 = b['r']['lowerarm_r'][:3, 3], b['r']['hand_r'][:3, 3]
    a0, a1, c0, c1 = proj(l0), proj(l1), proj(r0), proj(r1)
    m = np.column_stack((a1 - a0, c0 - c1))
    if abs(np.linalg.det(m)) < 1e-9: return 0.0, False
    s, t = np.linalg.solve(m, c0 - a0)
    if not (0 <= s <= 1 and 0 <= t <= 1): return 0.0, False
    pl, pr = l0 + (l1 - l0) * s, r0 + (r1 - r0) * t
    return float(np.linalg.norm(pl) - np.linalg.norm(pr)), True


def common(x, b, terms):
    lw, rw = b['wrists']['l'], b['wrists']['r']
    terms['right_wrist'] = ((rw[1] - SRC_R[0]) / 10) ** 2 + ((rw[2] - SRC_R[1]) / 8) ** 2 + ((rw[3] - SRC_R[2]) / 20) ** 2 \
        + max(0, abs(rw[3] - SRC_R[2]) - 35) ** 2 / 25 + max(0, -34 - rw[2]) ** 2 / 2 + max(0, abs(rw[1]) - 40) ** 2 / 4
    # Signature signs: flexion + = palmar, - = dorsal; deviation + = radial (limits ~20 radial / ~35 ulnar).
    terms['left_wrist'] = (lw[1] / 30) ** 2 * .5 + (lw[2] / 15) ** 2 + max(0, abs(lw[3]) - 60) ** 2 / 100 + max(0, abs(lw[1]) - 40) ** 2 / 10 \
        + (max(0, -55 - lw[1]) ** 2 + max(0, lw[1] - 60) ** 2 + max(0, -30 - lw[2]) ** 2 + max(0, lw[2] - 18) ** 2) / 4
    terms['clearance'] = sum(max(0, 6.0 - g) ** 2 * 4 for g in b['gaps'])
    depth, crossed = screen_order(b)
    terms['under'] = (max(0, 3.0 - depth) ** 2) if crossed else 4.0
    terms['reach'] = sum(max(0, d['reach'] - 0.94) ** 2 * 400 for d in (b['rdiag'], b['ldiag']))
    fist = b['K'][:3, 3]; tip = b['Kc'] @ np.array([6.18, 0, 26.29, 1])
    gun0, gun1 = b['gun']['WPN_RearSight'][:3, 3], b['gun']['WPN_FrontSight'][:3, 3]
    terms['blade_gun'] = max(0, 4.5 - A.segment_gap(fist, tip[:3], gun0, gun1)[0]) ** 2 * 4
    terms['blade_hand'] = max(0, 4.0 - A.segment_gap(fist, tip[:3], b['r']['hand_r'][:3, 3], b['r']['middle_01_r'][:3, 3])[0]) ** 2 * 4
    terms['shoulders'] = float(np.sum(np.square(x[8:14]) / 25)) * .2
    return depth, crossed


def hip_terms(x, c, b, terms):
    fist = b['K'][:3, 3]
    hand_ndc = np.array(A.ndc(b['r']['middle_01_r'][:3, 3]))
    terms['fist_ndc'] = float(np.sum(((np.array(A.ndc(fist)) - hand_ndc - FIST_FROM_HAND) / 0.06) ** 2)) * .3
    ray = fist / np.linalg.norm(fist); blockers = []
    for a0, a1 in ((b['r']['lowerarm_r'][:3, 3], b['r']['hand_r'][:3, 3]), (b['r']['hand_r'][:3, 3], b['r']['middle_01_r'][:3, 3])):
        for t in np.linspace(0, 1, 24):
            q = a0 + (a1 - a0) * t
            if np.dot(q, ray) < np.linalg.norm(fist) - 2: blockers.append(np.linalg.norm(q - ray * np.dot(q, ray)))
    terms['fist_visible'] = max(0, 6.5 - min(blockers)) ** 2 if blockers else 0.0
    # Crossed forearms: on screen the left wrist sits right of the right wrist, the left elbow left of it.
    lw_x, rw_x = A.ndc(b['l']['hand_l'][:3, 3])[0], A.ndc(b['r']['hand_r'][:3, 3])[0]
    terms['cross'] = max(0, rw_x + 0.04 - lw_x) ** 2 * 400 + max(0, rw_x + 0.15 - A.ndc(fist)[0]) ** 2 * 400
    terms['blade'] = (x[4] / 10) ** 2 + (x[5] / 10) ** 2
    terms['dorsal'] = max(0, 0.6 - b['dorsal_to_eye']) ** 2 * 60
    terms['elbow_off'] = max(0, 1.08 - A.ndc(b['l']['lowerarm_l'][:3, 3])[1]) ** 2 * 10
    for side, target in (('r', FOREARM_DEG[0]), ('l', FOREARM_DEG[1])):
        arm = b[side]; w, e = arm['hand_' + side][:3, 3], arm['lowerarm_' + side][:3, 3]
        e = w + (e - w) * min(1.0, (w[0] - 4) / max(w[0] - e[0], 1e-3))   # clip the elbow end at the near plane
        (wx, wy), (ex, ey) = A.ndc(w), A.ndc(e)
        deg = np.degrees(np.arctan2((ey - wy), abs(ex - wx) * 16 / 9))
        terms['forearm_' + side] = ((deg - target) / 12) ** 2 + (0 if (ex - wx) * (1 if side == 'r' else -1) > 0 else 4)
    # Reference gun: centred just right of the crosshair, canted about 20 degrees, bore into the view.
    terms['gun'] = ((x[16] - 3) / 2) ** 2 * .3 + ((x[17] + 0.5) / 1.5) ** 2 * .3 + ((x[18] - 20) / 3) ** 2 + (x[19] / 4) ** 2 * .5


def ads_terms(x, c, b, terms):
    fov = c['vertical_fov']; ndc = lambda p: A.ndc(p, fov)
    lh, rh = b['l']['hand_l'][:3, 3], b['r']['hand_r'][:3, 3]
    # Harries: the left wrist crosses directly under the right wrist, the backs of the hands nearly touching.
    terms['support'] = ((np.linalg.norm(lh - rh) - 6.8) / 1.0) ** 2 + max(0, lh[2] - (rh[2] - 3.5)) ** 2
    # Sight picture: nothing of the kukri or the left fist above the lower band near the screen centre.
    pts = [b['Kc'] @ np.array([px, 0, pz, 1]) for px, pz in ((0.4, -15.6), (0, -8), (0, 0), (0.5, 8), (1.5, 13), (2.8, 17), (4.2, 21), (5.6, 24), (6.18, 26.29))]
    pts = [p[:3] for p in pts] + [b['K'][:3, 3]]
    terms['sight_clear'] = sum(max(0, 0.3 - ndc(p)[1]) ** 2 * (abs(ndc(p)[0]) < 0.5) * 300 for p in pts)
    terms['blade'] = (x[4] / 10) ** 2 + ((x[5] + 6) / 8) ** 2
    terms['elbow_off'] = max(0, 1.08 - ndc(b['l']['lowerarm_l'][:3, 3])[1]) ** 2 * 10


def cost(x, verbose=False):
    c = controls(x)
    b = A.build(c)
    terms = {}
    depth, crossed = common(x, b, terms)
    (ads_terms if ADS else hip_terms)(x, c, b, terms)
    if verbose:
        print({k: round(float(v), 3) for k, v in terms.items()})
        print('left wrist', np.round(b['wrists']['l'], 1), 'right wrist', np.round(b['wrists']['r'], 1), 'gaps', np.round(b['gaps'], 2),
              'depth', round(depth, 2), crossed, 'dorsal', round(b['dorsal_to_eye'], 2))
    return float(sum(terms.values()))


def main():
    global BASE
    if ADS and 'ads' not in HIP: BASE = ads_base()
    x0 = np.array((BASE.get('fit') or HIP['fit'])['x'], float)
    x0 = np.clip(x0, BOUNDS[:, 0], BOUNDS[:, 1])
    cost(x0, True)
    best = None
    for start in range(6):
        xs = x0 + (np.random.default_rng(start).normal(0, 1, len(x0)) * [2, 2, 2, 15, 4, 4, 6, 6, 1, 1, 1, 1, 1, 1, 6, 6, 1, 1, 2, 2] if start else 0)
        xs = np.clip(xs, BOUNDS[:, 0], BOUNDS[:, 1])
        res = minimize(cost, xs, method='Powell', bounds=BOUNDS, options={'maxiter': 6000, 'xtol': 1e-3, 'ftol': 1e-5})
        print('start', start, 'cost', round(res.fun, 4), flush=True)
        if best is None or res.fun < best.fun: best = res
    cost(best.x, True)
    c = controls(best.x)
    c['fit'] = {'x': best.x.round(4).tolist(), 'cost': round(float(best.fun), 4), 'order': ORDER}
    if '--accept' in sys.argv:
        out = json.loads(json.dumps(HIP))
        if ADS: out['ads'] = c
        else: c['ads'] = HIP.get('ads'); out = {k: v for k, v in c.items() if v is not None}
        (A.P / 'pose_controls.json').write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding='utf-8', newline='\n')
        print('ACCEPTED', 'ads' if ADS else 'hip')


if __name__ == '__main__':
    main()
