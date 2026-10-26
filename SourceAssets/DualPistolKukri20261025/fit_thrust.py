"""Fit the thrust keys of author_strike.py under native wrist limits (writes Work/strike/thrust_fit.json).

Reference (1080p, cycles B and C): on the drive-in and at full length the forearm crosses the view from the LEFT edge
at mid height (the upper arm is raised out to the side, elbow near fist height), the back of the left hand faces
right and toward the eye, and the reversed blade leaves the fist pointing away (it reads up-left of the fist on
screen). Pointing the blade along the forearm needs ~50 deg radial deviation, so the fit keeps each fist where the
reference puts it and finds the nearest blade / knuckle / elbow / shoulder inside the wrist range used by
fit_idle.py (deviation + radial <= ~15, ulnar >= -30; flexion +-40; forearm roll moderate).
Run:  python -I fit_thrust.py   then   python -I author_strike.py
"""
import json, sys
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from scipy.spatial.transform import Rotation as R

P = Path(__file__).resolve().parent
sys.path.insert(0, str(P))
import author_idle as A
import author_strike as S

source, fist = A.FIST
KNUCKLE_IN_HAND = np.linalg.inv(source['hand_l']) @ A.kukri_frame(fist['centre'], fist['axis'], fist['edge'], 0.)
TV = np.tan(np.radians(37.5)); TH = TV * 16 / 9
DEV = (-30., 15.); FLEX = (-40., 40.); ROLL = (-60., 110.)


def ndc(p):
    return np.array([p[1] / (p[0] * TH), -p[2] / (p[0] * TV)])


def frame_of(blade, knuckle, w):
    b = A.unit(blade); k = np.asarray(knuckle, float); k = A.unit(k - b * np.dot(k, b))
    rot = R.from_rotvec(w).as_matrix()
    return rot @ b, rot @ k


def evaluate(key, x):
    lp = np.array(key['pole'] or S.LP, float)
    blade = key['blade'] or S.REST_BLADE; knuckle = key['knuckle'] or S.REST_KNUCKLE
    w, pole_yz, dsh_fit = x[:3], x[3:5], x[5:8]
    b, k = frame_of(blade, knuckle, w)
    centre = np.array(S.at(key['fist'], key['depth']))
    K = A.kukri_frame(centre, b, k, 0.)
    hand = K @ np.linalg.inv(KNUCKLE_IN_HAND)
    shoulder = np.array(S.LSH) + np.array(key['dsh'], float) + dsh_fit
    pole = np.array([lp[0], pole_yz[0], pole_yz[1]])
    l, d = A.solve_arm(A.LR, source, A.LP, 'l', shoulder, hand[:3, 3], pole, hand[:3, :3])
    sig, _ = A.wrist_signature(l, S.REST['r'])
    elbow, flex, dev, roll = (float(v) for v in sig['l'])
    return dict(b=b, k=k, l=l, d=d, flex=flex, dev=dev, roll=roll, centre=centre, shoulder=shoulder, pole=pole)


def over(v, lo, hi):
    return max(0., lo - v) + max(0., v - hi)


def cost(key, x, intent):
    e = evaluate(key, x)
    c = 4 * over(e['dev'], *DEV) ** 2 + 2 * over(e['flex'], *FLEX) ** 2 + over(e['roll'], *ROLL) ** 2
    c += 600 * np.dot(x[:3], x[:3])                         # stay near the designed blade/knuckle
    lp = np.array(key['pole'] or S.LP, float)
    c += .5 * np.dot(x[3:5] - lp[1:], x[3:5] - lp[1:]) + 20 * np.dot(x[5:8], x[5:8])
    if intent.get('away'):                                   # blade leaves the fist away from the eye
        c += 400 * max(0., intent['away'] - e['b'][0]) ** 2
    if intent.get('elbow_left'):                             # forearm enters from the left edge at mid height
        el = e['l']['lowerarm_l'][:3, 3]
        n = ndc(el) if el[0] > 2 else np.array([-3., 0.])
        lo, hi = intent['elbow_left']
        c += 60 * (max(0., n[0] + .45) ** 2 + over(n[1], lo, hi) ** 2)
    if intent.get('tip_up'):                                 # the blade reads up-left of the fist (1080p crop)
        tip = ndc(e['centre'] + 20 * e['b']) - ndc(e['centre'])
        tip = tip / max(np.linalg.norm(tip), 1e-6)
        c += 300 * max(0., tip[1] + .25) ** 2
    return c


THRUST = dict(away=.55, elbow_left=(.05, .30), tip_up=True)   # forearm nearly level from the left edge (1218)
INTENT = {0.200: dict(away=.55, elbow_left=(.10, .40)), 0.233: THRUST, 0.250: THRUST, 0.267: THRUST,
          0.300: dict(away=.55, elbow_left=(.08, .38), tip_up=True), 0.333: dict(away=.5, elbow_left=(.15, .55)),
          0.167: dict(away=.45), 0.367: dict(away=.4)}


def main():
    out = {}
    for key in S.KEYS:
        t = key['t']
        if key['fist'] == 'rest':
            continue
        lp = key['pole'] or S.LP
        x0 = np.array([0, 0, 0, lp[1], lp[2], 0, 0, 0], float)
        r = minimize(lambda x: cost(key, x, INTENT.get(round(t, 3), {})), x0, method='Powell',
                     options=dict(maxiter=8000, xtol=1e-3, ftol=1e-4))
        e = evaluate(key, r.x)
        el = e['l']['lowerarm_l'][:3, 3]
        tip = ndc(e['centre'] + 20 * e['b']) - ndc(e['centre'])
        print('t=%.3f cost %6.2f | dev %+.0f flex %+.0f roll %+.0f reach %.2f | blade %s | elbow ndc %s | tip %s | shoulder %s' % (
            t, r.fun, e['dev'], e['flex'], e['roll'], e['d']['reach'], np.round(e['b'], 2),
            np.round(ndc(el), 2) if el[0] > 2 else 'behind', np.round(tip / max(np.linalg.norm(tip), 1e-6), 2),
            np.round(e['shoulder'], 1)))
        out['%.3f' % t] = dict(blade=e['b'].round(4).tolist(), knuckle=e['k'].round(4).tolist(),
                               pole=e['pole'].round(3).tolist(), shoulder_delta=(r.x[5:8]).round(3).tolist())
    (S.OUT / 'thrust_fit.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
    print('WROTE', S.OUT / 'thrust_fit.json')


if __name__ == '__main__':
    main()
