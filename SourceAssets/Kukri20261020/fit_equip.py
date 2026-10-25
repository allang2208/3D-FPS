"""Toss-and-catch draw (V2 Equip, 2026-10-22): fit the knife flight and the right-arm keys to the reference.

Reference: BV1CeYUeSE7b 52.13-52.93 s (切刀 #5 抛刀), t = 0 at frame 1564.  Frames are read on the NDC grid sheets
(Reference/grid_equip.py, crop_equip.py; x right, y down) and the camera by background registration
(Reference/camera_equip.py).  What the reference shows:
  0.00-0.10  empty view (the hand flicks the knife up from below the frame; camera roll kick at the switch);
  0.13-0.23  the knife rises from the bottom (x ~ 0.28) handle first, blade hanging down, passing close to the lens;
  0.23-0.43  it tumbles counter-clockwise on screen near the top right: the handle swings up -> left -> down-left while
             the hooked tip stays around (0.30, -0.25);
  0.20-0.43  the open right hand rises from the bottom right, palm towards the camera, fingers up, thumb to the right;
  0.433      the handle drops into the palm (pommel lower-left, blade up-right); 0.47 fist closed, blade up;
  0.50-0.60  the fist drops to the lower right and rolls the blade (edge-on at 0.53-0.57) into the stance.
Camera: rises ~1.5 deg following the toss, dips ~1.3 deg with the catch (camera_equip.py, converted in curve_equip.py).

Knife model: one rigid body between the release (TR) and the catch (TC): the centre of mass follows a ballistic arc
(fitted gravity, ~2.2 g like the reference's stylised toss), the body spins at a constant angular velocity, and two
small offsets that vanish at both ends absorb where the hand-keyed reference departs from physics.  The end state is
the catching hand's grip, so the catch lands exactly in the hammer-grip relation.  Before the release the knife rides
in the flicking fist below the frame (its handle in the fist, 'release_hold').  Our kukri has a much longer handle
than the Apex blade, so the fit matches the guard and tip and only the direction of the handle.

Run:  python fit_equip.py [--restarts=N] [--keys-only] [--accept]
      -> Work/equip/fit_equip.json (and equip_keys.json with --accept); --keys-only refits the hand keys on the
      last catch + flight (Work/equip/seed.json)
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

from kukri_rig import KukriRig, ndc, TIP, POMMEL
from kmath import T, mesh_to_cam, cam_to_mesh, qmat, qfrommat, qrot
from fit_reference import Fitter, idle_x

P = Path(__file__).resolve().parent
WORK = P / 'Work' / 'equip'
LENGTH = 24 / 30            # clip length (stance at 0.80 s; the reference camera settles at ~0.77 s)
TR = 10 / 120               # release, below the frame (frame 1567 at 0.10 s is still empty)
TC = 13 / 30                # catch: the handle reaches the palm (frame 1577)
M = np.array([[0, -1, 0], [1, 0, 0], [0, 0, 1]], float)   # mesh -> camera rotation
COM = np.array([2.5, 0.0, 10.0])   # kukri centre of mass in the grip frame (blade-heavy: steel blade vs wooden grip)
GUARD = np.array([0.0, 0.0, 7.5])
PTS = dict(pom=np.asarray(POMMEL, float), guard=GUARD, tip=np.asarray(TIP, float))

# Reference knife readings (NDC).  'below'/'above' = that end is outside the frame.
OBS = [
    (4 / 30, dict(pom=(0.23, 0.45), guard=(0.31, 0.67), tip='below')),
    (5 / 30, dict(pom=(0.19, 0.12), guard=(0.25, 0.44), tip='below')),
    (6 / 30, dict(pom=(0.19, -0.59), guard=(0.28, -0.18), tip=(0.23, 0.97))),
    (7 / 30, dict(pom='above', guard=(0.29, -0.61), tip=(0.30, 0.11))),
    (8 / 30, dict(pom=(0.10, -0.90), guard=(0.26, -0.69), tip=(0.30, -0.19))),
    (9 / 30, dict(pom=(0.005, -0.78), guard=(0.30, -0.64), tip=(0.31, -0.21))),
    (10 / 30, dict(pom=(0.03, -0.72), guard=(0.26, -0.50), tip=(0.28, -0.26))),
    (11 / 30, dict(pom=(0.08, -0.50), tip=(0.33, -0.33))),
    (12 / 30, dict(pom=(0.06, -0.19), tip=(0.29, -0.33))),
]

# Hand keys: t, targets (grip/palm NDC 'g', depth cm, palm normal / finger direction / blade direction in camera
# space, twist corridor 'th' vs bind, 'off' = below the frame).  Readings of the reference palm centre per frame.
PALM_CAM = (-0.85, -0.25, 0.35)     # open palm towards the camera, a little left and up
FING_UP = (0.15, -0.35, 0.92)       # fingers up, slightly left
HAND_KEYS = [
    # the arm comes up from straight below the frame (from the right, the elbow would sweep across the right edge)
    (0.000, dict(g=(0.40, 2.6), off=True, depth=22.0, hide_arm=1.15, th=(-60.0, 80.0), cw=0.3)),
    (0.040, dict(g=(0.22, 2.0), off=True, depth=28.0, hide_arm=1.12, th=(-80.0, 80.0), cw=0.3)),
    (0.065, dict(off=True, hide_arm=1.1, th=(-80.0, 80.0), cw=0.6)),
    (TR, dict(off=True, hide_arm=1.06, th=(-90.0, 80.0), cw=0.3)),     # + 'grab': the knife handle (main)
    (0.150, dict(g=(0.42, 1.40), off=True, depth=30.0, hide_arm=1.04, palm=PALM_CAM, th=(-90.0, 70.0), cw=0.5)),
    (0.200, dict(g=(0.36, 1.12), depth=30.0, palm=PALM_CAM, fing=FING_UP, th=(-90.0, 70.0), cw=1.0)),
    (8 / 30, dict(g=(0.30, 0.80), depth=30.0, palm=PALM_CAM, fing=FING_UP, th=(-90.0, 70.0), cw=2.0)),
    (9 / 30, dict(g=(0.27, 0.62), depth=30.0, palm=PALM_CAM, fing=FING_UP, th=(-90.0, 70.0), cw=3.0)),
    (10 / 30, dict(g=(0.25, 0.47), depth=30.0, palm=PALM_CAM, fing=FING_UP, th=(-90.0, 70.0), cw=3.0)),
    (11 / 30, dict(g=(0.22, 0.38), depth=30.0, palm=PALM_CAM, fing=FING_UP, th=(-90.0, 70.0), cw=4.0)),
    (12 / 30, dict(g=(0.19, 0.33), depth=30.0, palm=PALM_CAM, fing=FING_UP, th=(-90.0, 70.0), cw=4.0)),
    # TC: catch pose (joint fit with the flight)
    (14 / 30, dict(g=(0.19, 0.36), tip=(0.42, -0.36), depth=30.0, th=(-90.0, 70.0), cw=4.0)),   # fist closed, a little give
    (15 / 30, dict(g=(0.22, 0.42), tip=(0.36, -0.30), depth=31.0, th=(-80.0, 70.0), cw=3.0)),
    # the fist drops to the lower right and rolls the blade edge-on, tip swinging over to the upper left
    (16 / 30, dict(g=(0.27, 0.66), tip=(-0.02, -0.16), depth=33.0, th=(5.0, 40.0), cw=2.0, edge_on=True)),
    (17 / 30, dict(g=(0.31, 0.77), tip=(-0.05, 0.04), depth=35.0, th=(15.0, 45.0), cw=2.0)),
    (19 / 30, dict(g=(0.315, 0.745), tip=(-0.08, 0.13), depth=35.5, th=(25.0, 45.0), cw=3.0)),
]
CATCH_T = dict(g=(0.17, 0.31), palm=PALM_CAM, fing=FING_UP, depth=30.0, th=(-90.0, 70.0))
HANDLE_MID = np.array([0.0, 0.0, -4.0])   # where the fist holds the handle for the flick (grip frame, cm)


def rodrigues(w, dt):
    th = float(np.linalg.norm(w)) * dt
    if abs(th) < 1e-12:
        return np.eye(3)
    k = w / np.linalg.norm(w)
    K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + math.sin(th) * K + (1 - math.cos(th)) * K @ K


NP = 19   # flight parameters: v_catch 3, omega 3, gravity 1, path offset 2x3, spin offset 2x3


def bases(t):
    """Two smooth offsets that vanish at the release and the catch (B1 symmetric, B2 antisymmetric, peak 1)."""
    s = min(max((t - TR) / (TC - TR), 0.0), 1.0)
    return 4.0 * s * (1.0 - s), 6.93 * s * (1.0 - s) * (2.0 * s - 1.0)


class Flight:
    """Rigid flight ending on the catch grip frame Kc (mesh space T): a ballistic centre-of-mass arc and a constant
    spin, plus two small hand-keyed offsets (position and rotation) that vanish at both ends -- the reference toss is
    animated, not simulated.  p = v_catch (cam cm/s, 3), omega (cam rad/s, 3), gravity (cm/s^2), path offset
    amplitudes (cm, 2x3), spin offset amplitudes (rad, 2x3)."""

    def __init__(self, Kc, p):
        p = np.concatenate([np.asarray(p, float), np.zeros(max(0, NP - len(p)))])
        self.Rc = M @ qmat(Kc.q)
        self.pc = mesh_to_cam(Kc.p)
        self.v, self.w, self.g = p[0:3], p[3:6], float(p[6])
        self.a1, self.a2, self.b1, self.b2 = p[7:10], p[10:13], p[13:16], p[16:19]

    def state(self, t):
        dt = t - TC
        B1, B2 = bases(t)
        Rt = rodrigues(self.b1 * B1 + self.b2 * B2, 1.0) @ rodrigues(self.w, dt) @ self.Rc
        com = (self.pc + self.Rc @ COM + self.v * dt + 0.5 * np.array([0.0, 0.0, -self.g]) * dt * dt
               + self.a1 * B1 + self.a2 * B2)
        return Rt, com

    def point(self, t, local):
        Rt, com = self.state(t)
        return com + Rt @ (np.asarray(local, float) - COM)

    def frame(self, t):
        """Grip frame K (mesh space) at time t."""
        Rt, com = self.state(t)
        p = com - Rt @ COM
        return T(cam_to_mesh(p), qfrommat(M.T @ Rt), (1, 1, 1))


class EquipFitter(Fitter):
    """fit_reference.Fitter plus open-hand terms: palm normal, finger direction, blade direction, depth."""

    def hand_axes(self, x):
        W, phi, psi, du, de, C = self.unpack(x)
        K, E = self.R.arm_to_kukri(W, self.hint(W, phi, C), psi, de, du, C)
        q = (self.R.hand_rel * K).q
        return K, dict(palm=mesh_to_cam(qrot(q, [0, 1, 0])), fing=mesh_to_cam(qrot(q, [-1, 0, 0])),
                       blade=mesh_to_cam(K.axis(2)), depth=float(mesh_to_cam(K.p)[0]))

    def arm_visibility(self, x):
        """Screen margin (max(|x|, y) NDC; > 1 is outside the frame) of points along the right upper arm, forearm and
        open hand; points behind the near plane count as hidden."""
        W, phi, psi, du, de, C = self.unpack(x)
        o = self.evaluate(x)
        K, a = self.hand_axes(x)
        S, E, Wr, G = self.shoulder_cam(C), o['elbow'], o['wrist'], mesh_to_cam(K.p)
        # (point, skin radius cm): upper arm, forearm, hand (open fingers included)
        pts = [(S + (E - S) * f, 5.5) for f in (0.2, 0.4, 0.6, 0.8, 1.0)]
        pts += [(E + (Wr - E) * f, 4.5) for f in (0.25, 0.5, 0.75, 1.0)]
        pts += [(G, 4.0), (G + a['fing'] * 9.0, 2.5), (G + a['fing'] * 5.0 + a['palm'] * 2.0, 3.0)]
        out = []
        for q, r in pts:
            # pull the point towards the view axis by its skin radius: the surface nearest the frame
            lat = np.array([0.0, q[1], q[2]])
            n = float(np.linalg.norm(lat))
            q = q - lat / n * min(r, n) if n > 1e-6 else q
            if q[0] + r <= 1.0:          # behind the 1 cm near plane
                continue
            nx, ny = ndc(np.array([max(q[0], 1.0), q[1], q[2]]))
            # the arm enters from below and from the sides; > 1 is outside the frame
            out.append(max(ny, abs(nx)))
        return out

    def cost(self, x, target, prev_x, prev_theta):
        c = super().cost(x, target, prev_x, prev_theta)
        if c >= 1e5:
            return c
        K, a = self.hand_axes(x)
        for key, wgt in (('palm', 8.0), ('fing', 4.0), ('blade', 8.0)):
            if key in target:
                v = np.asarray(target[key], float)
                c += wgt * (1.0 - float(np.dot(a[key], v / np.linalg.norm(v))))
        if 'depth' in target:
            c += 0.03 * (a['depth'] - target['depth']) ** 2
        if 'grab' in target:
            # the fist closes on this camera-space point (the knife handle at the release)
            e = mesh_to_cam(K.p) - np.asarray(target['grab'], float)
            c += 0.2 * float(np.dot(e, e))
        if 'hide_arm' in target:
            c += 30.0 * sum(max(0.0, target['hide_arm'] - v) ** 2 for v in self.arm_visibility(x))
        if target.get('edge_on'):
            # the blade plane passes through the view ray: the flat faces the side, the edge/spine the camera
            view = mesh_to_cam(K.p); view = view / np.linalg.norm(view)
            c += 4.0 * abs(float(np.dot(mesh_to_cam(K.axis(1)), view)))
        return c


def catch_frame(F, x):
    W, phi, psi, du, de, C = F.unpack(x)
    return F.R.arm_to_kukri(W, F.hint(W, phi, C), psi, de, du, C)[0]


def handle_dir_err(fl, t, tgt_pom, tgt_guard):
    a = ndc(fl.point(t, PTS['guard']))
    b = ndc(fl.point(t, PTS['pom']))
    d = np.array([(b[0] - a[0]) * 16 / 9, b[1] - a[1]])
    r = np.array([(tgt_pom[0] - tgt_guard[0]) * 16 / 9, tgt_pom[1] - tgt_guard[1]])
    if not np.all(np.isfinite(d)) or np.linalg.norm(d) < 1e-6:
        return 2.0
    return 1.0 - float(np.dot(d, r) / (np.linalg.norm(d) * np.linalg.norm(r)))


def flight_cost(fl, verbose=False):
    c = 0.0
    for t, obs in OBS:
        for k in ('guard', 'tip'):
            tgt = obs.get(k)
            if tgt is None:
                continue
            q = fl.point(t, PTS[k])
            if q[0] < 3:
                c += 50.0
                continue
            n = ndc(q)
            if tgt == 'below':
                c += 20.0 * max(0.0, 1.02 - n[1]) ** 2
            else:
                e = np.subtract(n, tgt)
                c += 10.0 * float(np.dot(e, e))
            if verbose:
                print('  %.3f %-5s ref %-14s ours %s' % (t, k, tgt, np.round(n, 2)))
        pom = obs.get('pom')
        if isinstance(pom, tuple) and t < 0.18:
            # emerging from the bottom edge the handle end is what shows: match where it is, not only its direction
            q = fl.point(t, PTS['pom'])
            if q[0] > 3:
                e = np.subtract(ndc(q), pom)
                c += 5.0 * float(np.dot(e, e))
        if isinstance(pom, tuple):
            g = obs['guard'] if isinstance(obs.get('guard'), tuple) else ndc(fl.point(t, PTS['guard']))
            e = handle_dir_err(fl, t, pom, g)
            c += 3.0 * e
            if verbose:
                print('  %.3f handle direction error %.3f (our pommel %s)' % (t, e, np.round(ndc(fl.point(t, PTS['pom'])), 2)))
        elif pom == 'above':
            c += 20.0 * max(0.0, ndc(fl.point(t, PTS['pom']))[1] + 1.0) ** 2
    # hidden at the release
    for t in (TR, TR + 0.01, 3 / 30):    # frame 1567 (0.10 s) is still empty
        for local in list(PTS.values()) + [COM, np.array([4.0, 0.0, 18.0])]:
            q = fl.point(t, local)
            if q[0] > 2:
                n = ndc(q)
                c += 30.0 * max(0.0, 1.04 - max(n[1], abs(n[0]))) ** 2
    # the flicking fist holds the handle low and close enough for the whole arm to stay below the frame
    grab = fl.point(TR, HANDLE_MID)
    c += 0.05 * (max(0.0, grab[0] - 36.0) ** 2 + max(0.0, 22.0 - grab[0]) ** 2)
    c += 40.0 * max(0.0, 1.45 - ndc(grab)[1]) ** 2 if grab[0] > 2 else 0.0
    # never through the lens
    for t in np.linspace(TR, TC, 21):
        for local in PTS.values():
            c += 0.5 * max(0.0, 12.0 - fl.point(t, local)[0]) ** 2
    c += 1e-7 * (max(0.0, 1500.0 - fl.g) ** 2 + max(0.0, fl.g - 4500.0) ** 2)
    # prefer the physical toss: offsets only where the reference clearly departs from it
    c += 0.002 * float(np.dot(fl.a1, fl.a1) + np.dot(fl.a2, fl.a2)) + 2.0 * float(np.dot(fl.b1, fl.b1) + np.dot(fl.b2, fl.b2))
    return c


def fit_catch_and_flight(F, x_seed, p_seed, restarts=16):
    """Joint fit: catching-hand arm parameters (9) + flight (7)."""
    x_idle = idle_x(F)

    def total(z):
        x, p = z[:9], z[9:]
        try:
            fl = Flight(catch_frame(F, x), p)
        except Exception:
            return 1e6
        tgt = dict(CATCH_T, _t=TC)
        return flight_cost(fl) + 1.0 * F.cost(x, tgt, None, None) + 0.0002 * float(np.dot(x - x_idle, x - x_idle))

    p_seed = np.concatenate([np.asarray(p_seed, float), np.zeros(max(0, NP - len(p_seed)))])
    z0 = np.concatenate([x_seed, p_seed])
    best = None
    rs = np.random.RandomState(7)
    for i in range(restarts):
        zs = z0 if i == 0 else z0 + np.concatenate([rs.randn(9) * [2, 2, 2, 15, 15, 5, 5, 1, 1],
                                                    rs.randn(3) * [40, 40, 60], rs.randn(3) * 3, [rs.randn() * 300],
                                                    rs.randn(6) * 2.0, rs.randn(6) * 0.1])
        r = minimize(total, zs, method='Powell', options=dict(maxiter=40000, xtol=1e-4, ftol=1e-7))
        if best is None or r.fun < best.fun:
            best = r
            print('  restart %d cost %.4f' % (i, r.fun), flush=True)
    return best.x[:9], best.x[9:]


def fit_hand_keys(F, x_catch, grab):
    """Sequential arm fit through HAND_KEYS (continuity to the previous key); the catch is pinned and the release
    key closes the fist on the knife handle (grab, camera cm) below the frame."""
    keys = []
    x_prev, th_prev = None, None
    pinned = {TC: x_catch}
    sched = sorted([(t, dict(tg, grab=grab) if abs(t - TR) < 1e-6 else tg) for t, tg in HAND_KEYS] +
                   [(t, None) for t in pinned], key=lambda a: a[0])
    seed = np.array([16.0, 26.0, -52.0, 60.0, 60.0, 0.0, -20.0, 0.0, 0.0])
    for t, tg in sched:
        if tg is None:
            x = np.asarray(pinned[t], float)
        else:
            tgt = dict(tg, _t=t)
            start = x_prev if x_prev is not None else seed
            best = None
            for j in range(6):
                xs = start if j == 0 else start + np.random.RandomState(j + int(t * 1000)).randn(9) * [3, 3, 3, 20, 20, 6, 6, 1.5, 1.5]
                r = minimize(lambda v: F.cost(v, tgt, x_prev, th_prev), xs, method='Powell',
                             options=dict(maxiter=8000, xtol=1e-3, ftol=1e-6))
                if best is None or r.fun < best.fun:
                    best = r
            x = best.x
        o = F.evaluate(x, th_prev)
        th_prev = o['r']['theta']
        vis = F.arm_visibility(x)
        keys.append(dict(t=round(float(t), 5), x=list(map(float, x)), theta=round(math.degrees(th_prev), 2),
                         g=[round(v, 3) for v in o['g']], tip=[round(v, 3) for v in o['tip']],
                         ext=round(o['r']['ext'], 1), uln=round(o['r']['uln'], 1), arm_margin=round(min(vis), 3) if vis else None))
        print('  key %.3f g %s twist %.1f ext %.1f uln %.1f arm margin %s' % (
            t, np.round(o['g'], 2), math.degrees(th_prev), o['r']['ext'], o['r']['uln'],
            round(min(vis), 2) if vis else '-'), flush=True)
        x_prev = x
    return keys


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    R = KukriRig()
    F = EquipFitter(R)
    seed = WORK / 'seed.json'
    if seed.exists():
        s = json.loads(seed.read_text('utf-8'))
        x_seed, p_seed = np.array(s['x_catch']), np.array(s['p'])
    else:
        x_seed = np.array([29.6, 7.9, -14.6, 7.8, 40.5, 1.2, 3.6, -8.7, -0.9])
        p_seed = np.array([-1.3, -1.9, -306.0, 9.1, -5.0, -2.1, 2563.0])
    if '--keys-only' in sys.argv and seed.exists():
        x_catch, p = x_seed, np.concatenate([p_seed, np.zeros(max(0, NP - len(p_seed)))])
    else:
        print('catch + flight', flush=True)
        x_catch, p = fit_catch_and_flight(F, x_seed, p_seed, restarts=int(next((a.split('=')[1] for a in sys.argv if a.startswith('--restarts=')), 12)))
    (WORK / 'seed.json').write_text(json.dumps(dict(x_catch=list(map(float, x_catch)), p=list(map(float, p))), indent=1), encoding='utf-8')
    Kc = catch_frame(F, x_catch)
    fl = Flight(Kc, p)
    flight_cost(fl, verbose=True)
    print('  v_catch %s cm/s, spin %.0f deg/s about %s, gravity %.0f cm/s2, flight spin %.0f deg' % (
        np.round(fl.v, 1), math.degrees(np.linalg.norm(fl.w)), np.round(fl.w / np.linalg.norm(fl.w), 2), fl.g,
        math.degrees(np.linalg.norm(fl.w) * (TC - TR))))
    Kr = fl.frame(TR)
    grab = mesh_to_cam(Kr.point(HANDLE_MID))
    print('hand keys (release grab at %s cm)' % np.round(grab, 1), flush=True)
    keys = fit_hand_keys(F, x_catch, grab)
    # Before the release the knife rides in the flicking fist with the relation it leaves with.
    x_release = np.array(next(k['x'] for k in keys if abs(k['t'] - TR) < 1e-4))
    held = Kr.relative_to(catch_frame(F, x_release))
    out = dict(source='fit_equip.py', reference='BV1CeYUeSE7b 52.133-52.933 (切刀 #5 抛刀)', length=LENGTH, release=TR, catch=TC,
               com=list(COM), flight=dict(p=list(map(float, p)), v_catch=list(map(float, fl.v)), omega=list(map(float, fl.w)),
                                          gravity=fl.g),
               catch_frame=Kc.pack(), release_hold=held.pack(), x_catch=list(map(float, x_catch)), keys=keys)
    (WORK / 'fit_equip.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
    if '--accept' in sys.argv:
        (P / 'equip_keys.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
        print('accepted -> equip_keys.json')


if __name__ == '__main__':
    main()
