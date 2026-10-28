"""Key poses of the dual kukri combo stage 3 (double thrust, reference BV19dUqBJECT 近战动作 #5「双刃断川·破军势」,
file 84.20-85.33 s; the user called it "1:25-1:26").  Each arm is fitted in the single kukri's arm parameters
(SourceAssets/Kukri20261020/fit_reference.py Fitter: W, phi, psi, du, de, clavicle z / y); the left arm is fitted as
a virtual right arm on the mirrored target and mirrored onto the left chain (dual_rig), so both fists keep the accepted
hammer grip.

R8 (user: "slow the thrust a little; is the blade direction wrong; are the grip and the wrist handled?"): R7 drove both
blades straight into the screen (seen end-on, two small hooks above two upright forearms) and that needed the wrist at
43 deg ulnar -- past the joint's range, the fist folded over the forearm.  The reference does not point the blades
ahead: at the hit (frames 2534-2539) the right fist punches in from the lower right to just right of the crosshair with
its blade lying across the view, tip at the centre; the left fist rises from below, right of centre, its blade pointing
up and in at the same point.  Both are plain punches with the blade leaving the thumb side of the fist -- the hammer
grip with the wrist near its accepted rest (ext 14.7 / uln 15.1), so the wrists stay inside ext -15..30 / uln 0..28 and
the forearm skin twist inside +-50 and the clavicle inside the single moves' range.  During the lunge (2528-2533) the right is drawn out to the right edge with
the blade already lying across; the left waits low with the blade up (the reference holds it low across the bottom).
Keys (camera cm, NDC y down; the left in its own frame), R10:
  right  chamber  fist low at the right edge (0.96, 0.29) ~26 cm, blade pointing in (~64 deg off ahead)
         impact   fist (0.44, 0.03) at ~53 cm, the arm nearly locked, blade ~48 deg in and 16 deg up, tip above right of
                  the crosshair
         drop     out past the lower right
  left   the exact mirror of the right (R9 sat it 4 cm lower; R8 raised it from below with the blade up)
  coil = chamber with the wrist 3 cm further back; press = impact driven deeper (the locked arm gives ~1.5 cm)
Run:  python -I fit_dual_thrust.py [key ...]  (keys right.impact etc.; all by default)  -> thrust_keys.json
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

P = Path(__file__).resolve().parent
KUKRI = P.parent / 'Kukri20261020'
sys.path.insert(0, str(KUKRI))
sys.path.insert(0, str(P))
import fit_reference as FR  # noqa: E402
from kukri_rig import ndc, TIP  # noqa: E402
from kmath import mesh_to_cam  # noqa: E402


def unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


BAND = dict(theta=(-50.0, 50.0), ext=(-15.0, 30.0), uln=(0.0, 28.0), roll_u=(-80.0, 60.0),
            cz=(-12.0, 20.0), cy=(-4.0, 6.0))      # clavicle protraction / elevation: the accepted single moves' range
# g: fist NDC (y down); blade: camera direction; elbow_out / elbow_below: cm the elbow sits outside / under the wrist.
TARGETS = {
    # R10 (user: "blades more forward, wrists connecting naturally, a stronger thrust, both hands"): the blade turned from
    # ~70 deg across to ~48 deg off straight ahead.  On the hammer grip the blade sits ~67 - ulnar deg off the forearm, so
    # the forearm now points straight ahead (a jab: elbow under and just outside the wrist, the arm nearly locked) instead
    # of angling in, rising a little from the lower corner to a fist just under eye level, the blade rising ~16 deg to the
    # crosshair (level blades at eye height are seen edge-on and vanish; Work/r4/sheet_thrust_cmp*.jpg) -- the wrist stays
    # at ulnar 24 / ext -1.5 with 17 deg of skin twist (R8/R9: 21-28 / 30-46).  The
    # chamber is pulled back low at the edge (fist ~26 cm from the eye) with the blade already pointing in, so the drive is
    # a straight stab along the blade, ~23 cm forward.  The left is the exact mirror: the tips stop 8 cm apart either side
    # of the crosshair (blade SDF >= 3.6 cm through the drive, Work/r4/thrust_pair_gap.py).  Variants:
    # Work/r4/thrust_fit_right.impact_R1..R4 / chamber_K1..K2.
    'right.chamber': dict(g=(0.92, 0.30), depth=26.0, blade=(0.50, -0.86, 0.0), reach=(0.40, 0.75), elbow_out=2.0, elbow_below=6.0),
    'right.impact': dict(g=(0.38, 0.10), depth=48.0, blade=(0.70, -0.66, 0.25), reach=(0.75, 0.98), elbow_out=-7.0,
                         elbow_below=10.0, band=dict(uln=(0.0, 25.0)), starts=24),
    'right.drop': dict(g=(1.25, 0.60), depth=26.0, blade=(0.30, -1.0, -0.30), reach=(0.45, 0.85), elbow_out=4.0, elbow_below=4.0),
    'left.chamber': dict(g=(-0.92, 0.30), depth=26.0, blade=(0.50, 0.86, 0.0), reach=(0.40, 0.75), elbow_out=2.0, elbow_below=6.0),
    'left.impact': dict(g=(-0.38, 0.10), depth=48.0, blade=(0.70, 0.66, 0.25), reach=(0.75, 0.98), elbow_out=-7.0,
                        elbow_below=10.0, band=dict(uln=(0.0, 25.0)), starts=24),
    'left.drop': dict(g=(-1.25, 0.60), depth=26.0, blade=(0.30, 1.0, -0.30), reach=(0.45, 0.85), elbow_out=4.0, elbow_below=4.0),
}


def virtual(t, side):
    """The target as seen by the fitted (right) arm: the left's targets mirrored across the view's centre line."""
    t = dict(t)
    t['blade'] = unit(t['blade'])
    if side == 'left':
        t['g'] = (-t['g'][0], t['g'][1])
        t['blade'] = t['blade'] * np.array([1.0, -1.0, 1.0])
        if 'elbow_at' in t:
            t['elbow_at'] = (t['elbow_at'][0], -t['elbow_at'][1], t['elbow_at'][2])
    return t


def band(v, lo, hi):
    return (lo - v) if v < lo else (v - hi) if v > hi else 0.0


def cost(F, x, t, report=False):
    try:
        o = F.evaluate(x)
    except Exception:
        return 1e6
    r = o['r']
    if not np.isfinite(r['theta']):
        return 1e6
    K = o['K']
    g = np.array(o['g'])
    b = unit(mesh_to_cam(K.point(TIP)) - mesh_to_cam(K.point([0, 0, 7.5])))
    E, W = o['elbow'], o['wrist']
    terms = {}
    terms['grip'] = 400.0 * float(np.sum((g - np.array(t['g'])) ** 2))
    terms['blade'] = 0.05 * math.degrees(math.acos(max(-1.0, min(1.0, float(b @ t['blade']))))) ** 2
    terms['depth'] = 0.2 * (float(mesh_to_cam(K.p)[0]) - t['depth']) ** 2
    B = {**BAND, **{k: tuple(v) for k, v in t.get('band', {}).items()}}   # per-key overrides of the joint bands
    terms['theta'] = 0.5 * band(math.degrees(r['theta']), *B['theta']) ** 2
    terms['ext'] = 0.5 * band(r['ext'], *B['ext']) ** 2
    terms['uln'] = 0.5 * band(r['uln'], *B['uln']) ** 2
    terms['rollu'] = 0.1 * band(r['roll_u'], *B['roll_u']) ** 2
    terms['clav'] = 2.0 * (band(x[7], *B['cz']) ** 2 + band(x[8], *B['cy']) ** 2)
    terms['twist'] = 0.002 * math.degrees(r['theta']) ** 2              # the less skin wrung, the better
    terms['reach'] = 400.0 * band(r['reach'], *t['reach']) ** 2
    terms['out'] = 0.5 * max(0.0, t['elbow_out'] - float(E[1] - W[1])) ** 2
    terms['below'] = 0.5 * max(0.0, t['elbow_below'] - float(W[2] - E[2])) ** 2
    if E[0] > 1.0:                              # the elbow stays off the screen
        en = ndc(E)
        terms['onscreen'] = 3000.0 * max(0.0, min(1.05 - abs(en[0]), 1.05 - abs(en[1]))) ** 2
    terms['lens'] = 5.0 * max(0.0, 15.0 - float(min(W[0], mesh_to_cam(K.p)[0]))) ** 2
    terms['wrist'] = 0.01 * ((r['ext'] - 14.7) ** 2 + (r['uln'] - 15.1) ** 2)   # prefer the accepted rest
    if 'elbow_at' in t:                         # optional elbow placement (camera cm), e.g. the crossed arms of the dual heavy
        terms['elbow_at'] = float(t.get('elbow_w', 0.05)) * float(np.sum((np.asarray(E) - np.asarray(t['elbow_at'])) ** 2))
    total = float(sum(terms.values()))
    if report:
        return total, terms, o, b
    return total


def fit(F, t, seed=3, starts=40):
    rng = np.random.default_rng(seed)
    gw = np.array([t['depth'] * 0.92, t['g'][0] * t['depth'] * 1.3643, -t['g'][1] * t['depth'] * 0.7673])
    best = None
    for k in range(int(t.get('starts', starts))):
        xs = np.r_[gw + rng.normal(0, 4, 3), rng.uniform(-120, 120), rng.uniform(-180, 180), rng.normal(0, 10),
                   rng.normal(0, 10), rng.normal(0, 5, 2)]
        res = minimize(lambda x: cost(F, x, t), xs, method='Powell', options=dict(maxiter=8000, xtol=1e-3, ftol=1e-8))
        if best is None or res.fun < best.fun:
            best = res
    return best


def describe(F, x, t):
    total, terms, o, b = cost(F, np.asarray(x, float), t, report=True)
    r = o['r']
    return dict(x=list(map(float, x)), cost=round(total, 4), terms={k: round(v, 3) for k, v in terms.items() if v > 1e-3},
                grip=[round(float(v), 3) for v in o['g']], tip=[round(float(v), 3) for v in o['tip']],
                blade=[round(float(v), 3) for v in b], wrist=[round(float(v), 1) for v in o['wrist']],
                elbow=[round(float(v), 1) for v in o['elbow']],
                anatomy=dict(theta=round(math.degrees(r['theta']), 1), ext=round(r['ext'], 1), uln=round(r['uln'], 1),
                             roll_u=round(r['roll_u'], 1), reach=round(r['reach'], 3)))


def main():
    F = FR.Fitter()
    names = [a for a in sys.argv[1:] if not a.startswith('--')] or list(TARGETS)
    out_path = P / 'thrust_keys.json'
    old = json.loads(out_path.read_text('utf-8')) if out_path.exists() else {}
    out = {s: dict(old.get(s, {})) for s in ('right', 'left')} if 'right' in old else {'right': {}, 'left': {}}
    for name in names:
        side, key = name.split('.')
        t = virtual(TARGETS[name], side)
        best = fit(F, t)
        rec = describe(F, best.x, t)
        rec['note'] = 'fitted (virtual right arm, mirrored onto the left)' if side == 'left' else 'fitted'
        out[side][key] = rec
        print(name, json.dumps({k: v for k, v in rec.items() if k != 'x'}), flush=True)
    for side in ('right', 'left'):
        S = out[side]
        if 'chamber' in S:
            xc = np.array(S['chamber']['x']); xc[0] -= 3.0
            S['coil'] = dict(x=list(map(float, xc)), note='chamber with the wrist drawn 3 cm back')
        if 'impact' in S:
            xp = np.array(S['impact']['x']); xp[0] += 2.5
            S['press'] = dict(x=list(map(float, xp)), note='impact driven deeper (2.5 cm asked; the locked arm gives ~1.5)')
    out_path.write_text(json.dumps(out, indent=1), encoding='utf-8')
    print('wrote thrust_keys.json')


if __name__ == '__main__':
    main()
