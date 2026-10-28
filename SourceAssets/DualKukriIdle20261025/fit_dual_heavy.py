"""Key poses of the dual kukri heavy strike (charge + release), reference BV19dUqBJECT 近战动作 #3「X」, file 78.20-79.30 s
(user 2026-10-27: "1:19-1:20, the X-pose simultaneous chop, as a dual heavy release, ~100 %; the charge's hands and arms
must connect naturally too"; R12: "it is a left/right CROSSING X slash -- look at the reference again").
Reference read-out (Saved/Reference/DualKukriBV19dUqBJECT20261025/heavy_frames, t = 0 at frame 2345, the last stance frame;
NDC x right / y down; the right arm has the dark armoured sleeve and the spiked knuckles, the left the light grey sleeve):
  0.033-0.133  the X opens: each blade whips out to its own side and up        -> our charge raise
  0.167-0.300  both arms up out of the top of the frame (the wind-up)           -> our charge load (held)
  0.333 (2355) both fists high in front: right (0.33, -0.64), left (-0.41, -0.25); the blades back over the shoulders
  0.367 (2356) the right fist already on the centre (0.04, 0.00), the left lower on its own side (-0.12, 0.32); each blade
               trails back up toward its own side (a V from the centre), the hit flash
  0.400 (2357) the arms have CROSSED: the right fist at the lower left (-0.44, 0.64), the left at the lower right
               (0.22, 0.68); each blade still trails up toward the side it came from, so the blades cross in an X above
  0.433-0.467  the fists leave by the opposite bottom corners, the blades pointing back in at the centre; 1.00-1.13 back
So the right slashes upper right -> lower left and the left upper left -> lower right at once, the right a little ahead
and higher; each blade trails behind its fist.  (R11 read it as each arm chopping on its own side.)  On this hammer grip a
trailing blade is the natural one -- the blade stands off the thumb side of a forearm rising from a low elbow -- so
the right's keys sit at the joint rest or near it (the leading back-chop blade at the lower left cost 24 deg).
Keys: the right arm on camera-frame targets (fit_dual_thrust.cost / fit: the single kukri's arm parameters, wrist ext
-15..30 / ulnar 0..28 -- the release -20..30 --, skin twist +-50, clavicle bands); the left as a virtual right arm on its
mirrored target, its release keys with an arm / blade / pommel clearance term against the right key at the same time
(capsules, PAIR): the elbows meet at the body's centre line once the arms cross, so the left passes a little lower and
deeper; R14 widens the cross and carries it on out of the bottom of the frame, uncrossed below it.  The charge keys are one table, the left its mirror.
Run:  python -I fit_dual_heavy.py [side.key ...]   -> heavy_keys.json   (tuning workers: Work/r4/heavy_fit_*.py)
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

P = Path(__file__).resolve().parent
sys.path.insert(0, str(P))
import fit_dual_thrust as M  # noqa: E402
from fit_idle import seg_dist  # noqa: E402
from kmath import mesh_to_cam  # noqa: E402
from kukri_rig import TIP, POMMEL  # noqa: E402

REL = dict(band=dict(uln=(-20.0, 30.0)))
OFF = dict(band=dict(uln=(-25.0, 32.0), theta=(-60.0, 60.0)))   # below the frame (R15): a little more joint range
# Charge (author s of DualHeavyCharge; 0-0.40 the raise on the martial clock, 0.40-2.00 the load stretched); the left
# uses the same targets mirrored.
CHARGE = {
    'open': dict(t=0.10, g=(0.62, 0.30), depth=36.0, blade=(0.20, 0.35, 0.92), reach=(0.45, 0.85), elbow_out=4.0, elbow_below=6.0),
    'up': dict(t=0.20, g=(0.68, -0.50), depth=40.0, blade=(-0.15, 0.25, 0.95), reach=(0.70, 0.98), elbow_out=2.0, elbow_below=8.0),
    'load': dict(t=0.40, g=(0.62, -0.55), depth=28.0, blade=(-0.60, 0.20, 0.78), reach=(0.50, 0.85), elbow_out=2.0, elbow_below=8.0),
    'deep': dict(t=2.00, g=(0.66, -0.62), depth=25.0, blade=(-0.70, 0.25, 0.66), reach=(0.45, 0.82), elbow_out=2.0, elbow_below=8.0),
}
# Release (author s of DualHeavyRelease; starts on 'deep'), camera frame per side.  R14 (user: "the crossing is right but
# not wide enough; after the X both hands and blades should end below the bottom of the screen, then back to the idle"):
# a wider cross (right fist to the far lower left, left past the centre to the lower right), on down out of the bottom
# of the frame, crossed below it; the arms uncross unseen there (author_dual_heavy).  The
# crossed forearms touch (pair clearance -0.5 cm on the conservative capsules; crossed arms rest on each other).
# R15 (user: "exit further below the screen; the cut stutters"): the keys re-timed to the reference's even fist speed
# (author_dual_heavy interpolates them with one C2 curve), the fists carried to 1.8 below the frame with the blades turning
# forward-down so they leave too (the left's end key sits at the joint bands -- unseen).
RELEASE_T = {'over': 0.037, 'cross': 0.068, 'x': 0.109, 'low': 0.136, 'end': 0.158}
RELEASE_R = {
    'over': dict(g=(0.33, -0.64), depth=30.0, blade=(-0.20, 0.25, 0.95), elbow_out=2.0, elbow_below=6.0),
    'cross': dict(g=(0.04, 0.00), depth=36.0, blade=(0.10, 0.55, 0.83), elbow_out=-10.0, **REL),
    'x': dict(g=(-0.60, 0.72), depth=28.0, blade=(0.30, 0.62, 0.72), elbow_out=-35.0, **REL),
    'low': dict(g=(-0.95, 1.30), depth=26.0, blade=(0.45, 0.50, 0.74), elbow_out=-40.0, **OFF),
    # R15: below the screen the blade turns forward and down so it leaves the frame with the fist
    'end': dict(g=(-1.00, 1.85), depth=22.0, blade=(0.75, 0.45, -0.48), elbow_out=-40.0, **OFF),
}
RELEASE_L = {
    'over': dict(g=(-0.41, -0.25), depth=32.0, blade=(-0.20, -0.30, 0.93), elbow_out=2.0, elbow_below=6.0),
    'cross': dict(g=(-0.12, 0.32), depth=40.0, blade=(0.10, -0.55, 0.83), elbow_out=-10.0, pair=2.0, **REL),
    'x': dict(g=(0.42, 0.85), depth=32.0, blade=(0.30, -0.62, 0.72), elbow_out=-35.0, pair=-0.5, **REL),
    'low': dict(g=(0.50, 1.25), depth=32.0, blade=(0.45, -0.50, 0.74), elbow_out=-40.0, pair=-0.5, **OFF),
    'end': dict(g=(0.40, 1.80), depth=32.0, blade=(0.80, -0.30, -0.52), elbow_out=-40.0, pair=-0.5, **OFF),
}
HELD = {}                                 # derived keys (both sides): source key, wrist offset (camera cm)
LEFT_HELD = {}                            # (R12-R14: the left held 'end' while the right tucked in -- R15 dropped the tuck)
RAD = dict(up=5.5, fore=4.5, hand=4.0, blade=3.5, pommel=2.5)   # blade: the kukri's belly reaches ~3.5 cm off its spine line
BASE = np.array([0.0, 0.0, 7.5])


def defaults(t):
    t = dict(t)
    t.setdefault('reach', (0.5, 0.97))
    t.setdefault('elbow_out', 0.0)
    t.setdefault('elbow_below', 0.0)
    return t


def segments(F, x, mirror=False):
    """Camera-space capsule axes of one fitted arm (mirror: the virtual right arm shown as the left)."""
    o = F.evaluate(np.asarray(x, float))
    K = o['K']
    S = F.shoulder_cam(F.unpack(x)[5])
    E, W, G = o['elbow'], o['wrist'], mesh_to_cam(K.p)
    seg = dict(up=(S, E), fore=(E, W), hand=(W, G), blade=(mesh_to_cam(K.point(BASE)), mesh_to_cam(K.point(TIP))),
               pommel=(G, mesh_to_cam(K.point(POMMEL))))
    if mirror:
        f = np.array([1.0, -1.0, 1.0])
        seg = {k: (a * f, b * f) for k, (a, b) in seg.items()}
    return seg


def clearance(sr, sl):
    best = (1e9, '')
    for a in sr:
        for b in sl:
            if a == 'up' and b == 'up':
                continue
            best = min(best, (seg_dist(*sr[a], *sl[b])[0] - RAD[a] - RAD[b], a + '/' + b))
    return best


def fit_pair(F, t, xr, need, starts=30):
    """The left key (virtual target t) with the clearance term against the right key xr (same start draws as M.fit)."""
    sr = segments(F, xr)

    def cost(x):
        c = M.cost(F, x, t)
        if c >= 1e5:
            return c
        try:
            g = clearance(sr, segments(F, x, mirror=True))[0]
        except Exception:
            return 1e6
        return c + 20.0 * max(0.0, need - g) ** 2

    rng = np.random.default_rng(3)
    gw = np.array([t['depth'] * 0.92, t['g'][0] * t['depth'] * 1.3643, -t['g'][1] * t['depth'] * 0.7673])
    best = None
    for k in range(starts):
        xs = np.r_[gw + rng.normal(0, 4, 3), rng.uniform(-120, 120), rng.uniform(-180, 180), rng.normal(0, 10),
                   rng.normal(0, 10), rng.normal(0, 5, 2)]
        res = minimize(cost, xs, method='Powell', options=dict(maxiter=8000, xtol=1e-3, ftol=1e-8))
        if best is None or res.fun < best.fun:
            best = res
    return best, clearance(sr, segments(F, best.x, mirror=True))


def target(side, key):
    """Camera-frame target of side.key (the charge table mirrored for the left)."""
    if key in CHARGE:
        t = dict(CHARGE[key])
        t.pop('t')
        if side == 'left':
            t['g'] = (-t['g'][0], t['g'][1])
            t['blade'] = (t['blade'][0], -t['blade'][1], t['blade'][2])
        return defaults(t)
    t = (RELEASE_R if side == 'right' else RELEASE_L)[key]
    return defaults({k: v for k, v in t.items() if k != 'pair'})


def main():
    F = M.FR.Fitter()
    keys = list(CHARGE) + [k for k in RELEASE_T if k not in HELD]
    left_keys = [k for k in keys if k not in LEFT_HELD]
    names = [a for a in sys.argv[1:] if not a.startswith('--')] or (['right.' + k for k in keys] + ['left.' + k for k in left_keys])
    out_path = P / 'heavy_keys.json'
    out = json.loads(out_path.read_text('utf-8')) if out_path.exists() else {'right': {}, 'left': {}}
    for name in names:
        side, key = name.split('.')
        spec = RELEASE_L.get(key) if side == 'left' else None
        t = M.virtual(target(side, key), side)
        if spec and spec.get('pair'):
            best, clear = fit_pair(F, t, out['right'][key]['x'], spec['pair'])
        else:
            best, clear = M.fit(F, t, starts=30), None
        rec = M.describe(F, best.x, t)
        rec['t'] = CHARGE[key]['t'] if key in CHARGE else RELEASE_T[key]
        if clear:
            rec['clearance'] = clear
        out[side][key] = rec
        print(name, json.dumps({k: v for k, v in rec.items() if k != 'x'}, default=float), flush=True)
    for key, src in LEFT_HELD.items():
        if src in out['left']:
            out['left'][key] = dict(out['left'][src], t=RELEASE_T[key], note='%s held' % src)
    for key, (src, dw) in HELD.items():
        for side in out:
            if src in out[side]:
                x = np.array(out[side][src]['x'], float)
                x[:3] += dw
                out[side][key] = dict(out[side][src], x=list(map(float, x)), t=RELEASE_T[key], note='%s held, wrist %s cm' % (src, dw))
    out_path.write_text(json.dumps(out, indent=1, default=float), encoding='utf-8')


if __name__ == '__main__':
    main()
