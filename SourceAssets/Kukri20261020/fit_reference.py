"""Fit anatomical arm keys to the reference swing (BV1CeYUeSE7b 1:27.00-1:28.27, melee #2 ←).

Each key: screen targets read from Saved/Reference/KukriBV1CeYUeSE7b20261020/sheets/grid_*.jpg
(NDC, x right, y down) for the fist centre, blade tip and/or pommel, optional edge/palm direction
and forearm targets.  Parameters per key: wrist point (camera cm), elbow swivel angle about the
shoulder-wrist line, forearm roll psi, wrist deltas (ext/uln), clavicle protraction/elevation.
Sequential fit with continuity to the previous key so roll and swivel never jump.
Output: Work/fit_keys.json (consumed by author_kukri_clips.py clip 'Attack').
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

from kukri_rig import KukriRig, ndc, TIP, POMMEL
from kmath import mesh_to_cam, cam_to_mesh

P = Path(__file__).resolve().parent
(P / 'Work').mkdir(exist_ok=True)  # scratch outputs are optional; recreate on demand
IDLE = dict(W=(30.0, 20.0, -21.0), E=(25.0, 60.0, -35.0), psi=100.0, du=12.0, de=0.0, C=(0.0, 0.0, 0.0))

# t, targets.  g=grip(fist) NDC, tip, pom=pommel, edge/palm=camera unit vectors, fm=forearm mid NDC,
# fd=forearm mid depth (cm), off=grip must be off-screen.  w scales the screen terms.
def _tip(g, tip, k=0.72):
    """Our kukri reads shorter than the Apex blade at a natural depth: keep the direction, shorten the offset."""
    return (g[0] + k * (tip[0] - g[0]), g[1] + k * (tip[1] - g[1]))


REF = [
    (0.033, dict(g=(0.62, 0.48), tip=_tip((0.62, 0.48), (-0.24, 0.32)), w=0.6, cw=12, mind=27.0)),
    (0.067, dict(g=(0.72, 0.38), tip=_tip((0.72, 0.38), (-0.14, 0.38)), w=0.6, cw=12, mind=27.0)),
    (0.100, dict(g=(0.78, 0.38), tip=_tip((0.78, 0.38), (-0.05, 0.40)), w=0.6, cw=12, mind=27.0)),
    (0.133, dict(g=(0.95, 0.72), tip=_tip((0.95, 0.72), (0.24, 0.10)), w=0.6, cw=12, mind=24.0)),
    (0.167, dict(g=(1.10, 1.05), tip=_tip((1.10, 1.05), (0.47, 0.02)), w=0.6, cw=10, mind=20.0)),
    (0.200, dict(g=(1.22, 1.22), tip=_tip((1.22, 1.22), (0.62, -0.02)), w=0.6, cw=10, mind=18.0)),
    (0.233, dict(g=(1.45, 1.25), tip=(1.10, 0.45), w=0.4, cw=6)),
    (0.267, dict(g=(0.88, 0.82), pom=(0.62, 0.72), flat=0.75, cw=2)),
    (0.300, dict(g=(0.72, 0.50), pom=(0.48, 0.43), fm=(0.92, 0.88), flat=0.75, cw=2)),
    (0.333, dict(g=(0.30, 0.10), pom=(0.05, 0.05), tip=(0.62, -0.18), fm=(0.55, 0.55), flat=0.75)),
    (0.367, dict(g=(-0.15, 0.05), pom=(-0.55, 0.08), tip=(0.05, -0.08), fm=(0.15, 0.52), flat=0.7)),
    (0.400, dict(g=(-0.45, -0.08), pom=(-0.80, 0.05), tip=(-0.12, -0.15), fm=(-0.07, 0.42), flat=0.6)),
    (0.433, dict(g=(-1.15, 0.45), fm=(-0.40, 0.70), fd=22.0, w=0.6)),
    (0.500, dict(g=(-1.30, 0.55), fm=(-0.05, 0.65), fd=17.0, w=0.6, cw=3, hide=True)),
    (0.600, dict(g=(-0.95, 0.55), fm=(0.20, 0.62), fd=17.0, w=0.6, cw=3, hide=True)),
    (0.700, dict(g=(-0.75, 0.85), fm=(-0.15, 0.85), fd=18.0, w=0.6, cw=3, hide=True)),
    (0.767, dict(g=(0.00, 0.98), w=0.6, cw=3, hide=True)),
    (0.900, dict(g=(0.20, 1.55), off=True, w=0.4, cw=6, hide=True)),
    (1.033, dict(g=(0.32, 0.95), tip=(-0.30, 0.95), w=0.5, cw=0.5, th=(-55.0, 0.0), mind=18.0)),
    (1.100, dict(g=(0.38, 0.62), tip=(-0.40, 0.66), w=0.6, cw=4, th=(-30.0, 20.0), mind=20.0)),
    (1.133, dict(g=(0.42, 0.42), tip=(-0.38, 0.38), w=0.6, cw=6, th=(-10.0, 35.0), mind=22.0)),
    (1.167, dict(g=(0.45, 0.55), tip=(-0.20, 0.20), w=0.6, cw=6, th=(10.0, 45.0), mind=24.0)),
]

# Forearm twist (deg vs bind) corridor per phase: idle +37, palm-down strike about -70.  The roll
# between them happens once in the windup and once in the re-raise, never the long way round.
TWIST_BANDS = [(0.0, 0.215, (-30.0, 75.0)), (0.215, 0.32, (-95.0, 45.0)), (0.32, 0.95, (-100.0, 15.0)),
               (0.95, 1.3, (-60.0, 50.0))]

# V3 (user, 2026-10-20 12:15): V2 swung "towards the player" -- the windup pulled the fist into the
# shoulder, the trailing blade pointed back at the lens and the follow-through wrapped the forearm
# across the face.  Keep the reference timing, framing of the first frames, re-raise and camera, but
# carry the arc OUT in front: the windup opens to the right at arm's length, the sweep runs at 40-50 cm
# with the tip pointing away from the player and the edge leading leftwards, and the follow-through
# exits left-forward before the drop.  mind = minimum fist depth (cm); fwd = blade tip deeper than the
# fist by at least this many cm; edge = camera-space edge direction.
EDGE_LEFT = (0.30, -0.94, 0.12)
EDGE_CUT = (0.25, -0.88, -0.40)   # palm-up cross-body cut: edge leads left and slightly down
REF_OUTWARD = REF[:3] + [
    (0.133, dict(g=(0.98, 0.60), tip=_tip((0.98, 0.60), (0.40, 0.05)), w=0.6, cw=10, mind=27.0)),
    (0.167, dict(g=(1.15, 0.72), tip=_tip((1.15, 0.72), (0.62, -0.05)), w=0.6, cw=8, mind=27.0)),
    (0.200, dict(g=(1.35, 0.78), off=True, w=0.5, cw=4, mind=26.0, th=(5.0, 30.0))),
    (0.233, dict(g=(1.50, 0.75), off=True, w=0.4, cw=4, mind=26.0, th=(-15.0, 10.0))),
    (0.267, dict(g=(1.00, 0.50), mind=28.0, fwd=4.0, edge=EDGE_CUT, th=(-30.0, -5.0), cw=2)),
    (0.300, dict(g=(0.66, 0.30), mind=33.0, fwd=6.0, edge=EDGE_CUT, right=0.0, th=(-25.0, 30.0), cw=2)),
    (0.333, dict(g=(0.28, 0.16), mind=37.0, fwd=8.0, edge=EDGE_CUT, right=0.05, th=(-40.0, 10.0), cw=2)),
    (0.367, dict(g=(-0.08, 0.14), mind=36.0, fwd=8.0, edge=EDGE_CUT, right=0.05, th=(-45.0, 5.0), cw=3)),
    (0.400, dict(g=(-0.40, 0.16), mind=33.0, fwd=7.0, edge=EDGE_CUT, right=0.05, th=(-45.0, 5.0), cw=3)),
    (0.433, dict(g=(-0.62, 0.26), mind=30.0, fwd=5.0, edge=EDGE_CUT, th=(-45.0, 10.0), cw=3)),
    (0.500, dict(g=(-0.85, 0.50), mind=27.0, w=0.7, th=(-40.0, 20.0), cw=3)),
    (0.600, dict(g=(-0.90, 0.85), mind=25.0, w=0.6, th=(-30.0, 30.0), cw=3)),
    (0.700, dict(g=(-0.75, 1.15), mind=25.0, w=0.6, cw=3, hide=True, th=(-20.0, 40.0))),
    (0.767, dict(g=(-0.45, 1.35), w=0.5, cw=3, hide=True, off=True, th=(-10.0, 45.0))),
] + [(t, dict(k, th=(15.0, 50.0))) for t, k in REF[-4:]]


# V4 (user, 2026-10-20 14:16): V3 lost the impact -- the extended arm reads small on screen.  Go back to
# the reference path of V2 (fist and forearm screen positions, big close whip, forearm sweeping low across
# the lens), but keep V3's outward blade: in the hidden part of the windup the forearm rolls palm-up, so
# through the sweep the tip points away from the player and the edge leads to the left.
def _impact(t, k):
    k = dict(k)
    if 0.26 <= t <= 0.41:
        for drop in ('pom', 'tip', 'flat'):
            k.pop(drop, None)
        if t > 0.32:
            k.update(edge=EDGE_CUT, fwd=4.0, th=(-60.0, 5.0))
        elif t > 0.28:
            # Whip entry: the fist leaves the shoulder and extends while the forearm rolls palm-up.
            k = dict(g=(0.62, 0.42), mind=24.0, maxd=34.0, th=(-45.0, -10.0), lens=True, cw=2)
        else:
            k.update(th=(-30.0, 0.0), lens=True)
    if abs(t - 0.200) < 1e-3:
        k.update(th=(5.0, 30.0), cw=4)
    if abs(t - 0.233) < 1e-3:
        k.update(th=(-20.0, 10.0), mind=14.0, cw=4)
    if 0.42 <= t <= 0.95:
        k.setdefault('th', (-60.0, 40.0))
    return t, k


REF_IMPACT = [_impact(t, k) for t, k in REF[:-4]] + [(t, dict(k, th=(15.0, 50.0))) for t, k in REF[-4:]]

# V6 (user, 2026-10-20 23:16): "a horizontal right-to-left chop; V4 pulls back too much and reads like
# stabbing up-left at my own head".  V4's forearm rose from the lower-right corner, the blade stood up and the
# follow-through came back to the lens.  Keep the reference timing, first frames, screen speed, drop and
# re-raise, but make the cut itself horizontal and out in front:
#   wind-up cocks out to the right at chest height (fist 24-27 cm deep, not into the shoulder), rolling
#   palm-up while off screen; the sweep runs level across the frame (fist y 0.22-0.28 NDC) at 30-44 cm with
#   the blade horizontal and pointing forward (horiz/fwd) and the edge leading left; the follow-through keeps
#   travelling left and a little down out of frame at >= 26 cm before the drop.
HORIZ = 0.30   # max |vertical component| of the blade direction for a level cut
REF_CHOP = REF[:3] + [
    (0.133, dict(g=(0.98, 0.52), tip=_tip((0.98, 0.52), (0.40, 0.10)), w=0.6, cw=10, mind=26.0)),
    (0.167, dict(g=(1.15, 0.55), w=0.6, cw=8, mind=25.0)),
    (0.200, dict(g=(1.35, 0.52), off=True, w=0.5, cw=3, mind=24.0, th=(-10.0, 20.0))),
    (0.233, dict(g=(1.50, 0.45), off=True, w=0.4, cw=3, mind=24.0, th=(-45.0, -15.0))),
    (0.267, dict(g=(1.05, 0.30), mind=27.0, horiz=0.5, th=(-60.0, -30.0), lens=True, cw=3)),
    (0.300, dict(g=(0.62, 0.24), mind=27.0, maxd=35.0, horiz=0.45, fwd=5.0, th=(-70.0, -40.0), lens=True, cw=3)),
    (0.333, dict(g=(0.25, 0.22), mind=28.0, maxd=35.0, horiz=HORIZ, fwd=10.0, edge=EDGE_CUT, th=(-70.0, -15.0), cw=2)),
    (0.367, dict(g=(-0.12, 0.22), mind=28.0, maxd=35.0, horiz=HORIZ, fwd=10.0, edge=EDGE_CUT, th=(-70.0, -15.0), cw=3)),
    (0.400, dict(g=(-0.45, 0.24), mind=27.0, maxd=34.0, horiz=HORIZ, fwd=8.0, edge=EDGE_CUT, th=(-70.0, -15.0), cw=3)),
    (0.433, dict(g=(-0.78, 0.28), mind=29.0, horiz=HORIZ + .1, fwd=6.0, edge=EDGE_CUT, th=(-70.0, -10.0), cw=3)),
    (0.500, dict(g=(-1.10, 0.38), mind=27.0, w=0.7, th=(-65.0, 0.0), cw=3)),
    (0.600, dict(g=(-1.30, 0.55), mind=26.0, off=True, w=0.6, th=(-55.0, 10.0), cw=3)),
    (0.700, dict(g=(-1.10, 0.95), mind=24.0, off=True, hide=True, w=0.6, th=(-40.0, 30.0), cw=3)),
    (0.767, dict(g=(-0.60, 1.30), off=True, hide=True, w=0.5, th=(-25.0, 40.0), cw=3)),
] + [(t, dict(k, th=(15.0, 50.0))) for t, k in REF[-5:]]
TWIST_BANDS_OUTWARD = [(0.0, 0.215, (-30.0, 75.0)), (0.215, 0.32, (0.0, 90.0)), (0.32, 0.62, (20.0, 95.0)),
                       (0.62, 0.95, (-40.0, 80.0)), (0.95, 1.3, (-60.0, 50.0))]
VARIANT = 'chop'

LIMITS = dict(ext=(-60.0, 55.0), uln=(-18.0, 40.0), theta=(-150.0, 120.0), roll_u=(-95.0, 60.0), reach=0.97)


class Fitter:
    def __init__(self, R=None):
        self.R = R or KukriRig()

    def shoulder_cam(self, C):
        R = self.R
        b = R.base
        S = b['upperarm_r'].p.copy()
        if any(C):
            piv = b['clavicle_r'].p
            from kmath import qrot
            S = qrot(R.clavicle_rotation(C), S - piv) + piv
        return mesh_to_cam(S)

    def unpack(self, x):
        W = (x[0], x[1], x[2])
        phi, psi, du, de, cz, cy = x[3:9]
        return W, phi, psi, du, de, (0.0, cy, cz)

    def hint(self, W, phi, C):
        S = self.shoulder_cam(C)
        n = np.asarray(W, float) - S
        n = n / np.linalg.norm(n)
        down = np.array([0.0, 0.0, -1.0])
        d1 = down - n * np.dot(down, n)
        d1 = d1 / np.linalg.norm(d1)
        d2 = np.cross(n, d1)
        mid = S + (np.asarray(W) - S) * 0.5
        return tuple(mid + 100.0 * (math.cos(math.radians(phi)) * d1 + math.sin(math.radians(phi)) * d2))

    def evaluate(self, x, prev_theta=None, full=False):
        R = self.R
        W, phi, psi, du, de, C = self.unpack(x)
        Eh = self.hint(W, phi, C)
        K, E, r = R.arm_eval(W, Eh, psi, de, du, C, prev_theta)
        world = None
        if full:
            R.twist_memory = {} if prev_theta is None else {'r': prev_theta}
            world, d = R.pose(K, clav_r=C, pole_r=E, pole_r_weight=1.0)
        out = dict(K=K, E=E, world=world, r=r, hint=Eh,
                   g=ndc(mesh_to_cam(K.p)), tip=ndc(mesh_to_cam(K.point(TIP))), pom=ndc(mesh_to_cam(K.point(POMMEL))),
                   edge=mesh_to_cam(K.axis(0)), wrist=mesh_to_cam(r['W']), elbow=mesh_to_cam(E))
        mid = (out['wrist'] + out['elbow']) * 0.5
        out['fm'] = ndc(mid)
        out['fd'] = float(mid[0])
        out['elbow_ndc'] = ndc(out['elbow']) if out['elbow'][0] > 1 else (9.0, 9.0)
        return out

    def cost(self, x, target, prev_x, prev_theta):
        try:
            o = self.evaluate(x, prev_theta)
        except Exception:
            return 1e6
        if not np.isfinite(o['r']['theta']):
            return 1e6
        r = o['r']
        w = target.get('w', 1.0)
        c = 0.0
        for key in ('g', 'tip', 'pom', 'fm'):
            if key in target:
                e = np.subtract(o[key], target[key])
                if not np.all(np.isfinite(e)):
                    c += 60.0
                    continue
                c += w * 40.0 * min(float(np.dot(e, e)), 4.0) * (1.0 if key != 'g' else 1.4)
        if 'edge' in target:
            c += 6.0 * (1.0 - float(np.dot(o['edge'], target['edge']) / np.linalg.norm(target['edge'])))
        if 'fd' in target:
            c += 0.02 * (o['fd'] - target['fd']) ** 2
        if 'right' in target and np.all(np.isfinite(o['tip'])):
            c += 30.0 * max(0.0, (o['g'][0] + target['right']) - o['tip'][0]) ** 2
        if 'up' in target:
            c += 30.0 * max(0.0, o['tip'][1] - (o['g'][1] - target['up'])) ** 2 if np.all(np.isfinite(o['tip'])) else 10.0
        if 'aim' in target:
            bd = mesh_to_cam(o['K'].axis(2))
            want = np.asarray(target['aim'], float) - mesh_to_cam(o['K'].p)
            c += 8.0 * (1.0 - float(np.dot(bd, want) / (np.linalg.norm(bd) * np.linalg.norm(want))))
        if 'bdir' in target:
            bd = mesh_to_cam(o['K'].axis(2))
            c += 6.0 * (1.0 - float(np.dot(bd, target['bdir']) / (np.linalg.norm(bd) * np.linalg.norm(target['bdir']))))
        if 'horiz' in target:
            bz = float(mesh_to_cam(o['K'].axis(2))[2])
            c += 40.0 * max(0.0, abs(bz) - target['horiz']) ** 2
        if 'extr' in target:
            lo, hi = target['extr']
            c += 0.05 * (max(0.0, lo - r['ext']) ** 2 + max(0.0, r['ext'] - hi) ** 2)
        if target.get('lens'):
            for frac in (0.5, 1.0):
                depth = float(mesh_to_cam(o['K'].point(np.asarray(TIP) * frac))[0])
                c += 0.4 * max(0.0, 9.0 - depth) ** 2
        if 'fwd' in target:
            dz = float(mesh_to_cam(o['K'].point(TIP))[0] - mesh_to_cam(o['K'].p)[0])
            c += 0.06 * max(0.0, target['fwd'] - dz) ** 2
        if 'minreach' in target:
            c += 200.0 * max(0.0, target['minreach'] - r['reach']) ** 2
        if 'maxd' in target:
            c += 0.05 * max(0.0, float(mesh_to_cam(o['K'].p)[0]) - target['maxd']) ** 2
        if 'mind' in target:
            c += 0.05 * max(0.0, target['mind'] - float(mesh_to_cam(o['K'].p)[0])) ** 2
        if 'flat' in target:
            view = mesh_to_cam(o['K'].p)
            view = view / np.linalg.norm(view)
            c += 8.0 * max(0.0, target['flat'] - abs(float(np.dot(mesh_to_cam(o['K'].axis(1)), view))))
        if target.get('hide'):
            for frac in (0.35, 0.7, 1.0):
                pc = mesh_to_cam(o['K'].point(np.asarray(TIP) * frac))
                if pc[0] > 4.0:
                    tx, ty = ndc(pc)
                    c += 15.0 * max(0.0, 1.08 - max(ty, abs(tx) - 0.08)) ** 2
                else:
                    c += 12.0      # the blade would pass through the lens
        if target.get('off'):
            gx, gy = o['g']
            c += 20.0 * max(0.0, 1.1 - max(abs(gx), gy)) ** 2
        # anatomy (soft walls)
        def wall(v, lo, hi, k=0.02):
            return k * (max(0.0, lo - v) ** 2 + max(0.0, v - hi) ** 2)
        c += wall(r['ext'], *LIMITS['ext']) + wall(r['uln'], *LIMITS['uln'])
        c += wall(math.degrees(r['theta']), *LIMITS['theta']) + wall(r['roll_u'], *LIMITS['roll_u'], k=0.01)
        bands = TWIST_BANDS_OUTWARD if VARIANT in ('outward', 'impact', 'chop') else TWIST_BANDS
        band = target.get('th') or next(b for t0, t1, b in bands if t0 <= target['_t'] < t1)
        c += wall(math.degrees(r['theta']), *band, k=0.3)
        c += 200.0 * max(0.0, r['reach'] - LIMITS['reach']) ** 2
        # elbow must not sit in front of the face
        ex, ey = o['elbow_ndc']
        if o['elbow'][0] > 4 and abs(ex) < 0.8 and ey < 0.6:
            c += 8.0
        # continuity with the previous key (the swing is one continuous arm motion)
        if prev_x is not None:
            dx = np.subtract(x, prev_x)
            c += target.get('cw', 1.0) * (0.0004 * float(np.dot(dx[0:3], dx[0:3])) + 0.0002 * dx[3] ** 2 + 0.0003 * dx[4] ** 2
                                          + 0.0004 * (dx[5] ** 2 + dx[6] ** 2) + 0.0006 * (dx[7] ** 2 + dx[8] ** 2))
        # mild preference for small wrist deltas and clavicle motion
        c += 0.0004 * (x[5] ** 2 + x[6] ** 2) + 0.0002 * (x[7] ** 2 + x[8] ** 2)
        return float(c) if np.isfinite(c) else 1e6


def idle_x(F):
    W = IDLE['W']
    # recover the swivel angle of the idle elbow hint
    best = None
    for phi in range(-180, 180, 2):
        o = F.evaluate(np.array([*W, phi, IDLE['psi'], IDLE['du'], IDLE['de'], 0.0, 0.0]))
        ref = F.R.arm_to_kukri(W, IDLE['E'], IDLE['psi'], IDLE['de'], IDLE['du'], (0, 0, 0))[1]
        dist = float(np.linalg.norm(o['E'] - ref))
        if best is None or dist < best[0]:
            best = (dist, phi)
    return np.array([*W, best[1], IDLE['psi'], IDLE['du'], IDLE['de'], 0.0, 0.0])


def main():
    F = Fitter()
    x_prev = idle_x(F)
    o = F.evaluate(x_prev)
    theta_prev = o['r']['theta']
    keys = [dict(t=0.0, x=list(map(float, x_prev)), theta=math.degrees(theta_prev), note='idle')]
    print('idle phi %.0f theta %.1f g %s tip %s' % (x_prev[3], math.degrees(theta_prev), np.round(o['g'], 2), np.round(o['tip'], 2)))
    fit_keys(F, x_prev, theta_prev, {'outward': REF_OUTWARD, 'impact': REF_IMPACT, 'chop': REF_CHOP}.get(VARIANT, REF), keys)
    (P / 'Work' / 'fit_keys.json').write_text(json.dumps(dict(keys=keys), indent=1), encoding='utf-8')
    if '--accept' in sys.argv:
        (P / 'attack_keys.json').write_text(json.dumps(dict(source='fit_reference.py', variant=VARIANT, reference='BV1CeYUeSE7b 1:27.00-1:28.27',
                                                             keys=keys), indent=1), encoding='utf-8')


# ------------------------------------------------------------------------------------------------ attack 2
# Second hit (user, 2026-10-20 22:25): from where the first sweep finishes on the left, swing back to the
# right with almost the same speed and weight.  No reference footage exists for this direction, so it is
# the first sweep's rhythm mirrored: attack 2 takes over from attack 1 at CHAIN_T (forearm across the lower
# left, palm up), cocks up-left while the forearm pronates to a knuckles-leading backhand (thumb and blade
# up, back of the hand facing right), whips across the centre at the first sweep's screen speed with the
# edge leading to the right, follows through off the right edge and settles into the stance.
CHAIN_T = 17.0 / 30.0
ATTACK2_SECONDS = 30.0 / 30.0
EDGE_RIGHT = (0.50, 0.82, 0.28)
# V6: the backhand stays at chest height (fist y 0.21-0.28, no cock up by the head) with the tip kept ahead of
# the fist (fwd) and the edge leading right.  A fully level forward blade for the backhand was tried and is not
# reachable from the chain pose without the elbow folding the blade back at the lens, so the blade stays upright-forward.
REF_ATTACK2_LEVEL = [
    (0.067, dict(g=(-0.95, 0.42), mind=20.0, th=(-55.0, 0.0), cw=4)),
    (0.133, dict(g=(-0.80, 0.28), mind=22.0, th=(-20.0, 30.0), lens=True, cw=4)),
    (0.167, dict(g=(-0.62, 0.24), mind=24.0, th=(0.0, 45.0), lens=True, cw=3)),
    (0.200, dict(g=(-0.25, 0.22), mind=26.0, maxd=40.0, fwd=5.0, minreach=0.8, th=(0.0, 70.0), extr=(-25.0, 28.0), lens=True, cw=2)),
    (0.233, dict(g=(0.15, 0.21), mind=28.0, maxd=42.0, fwd=6.0, minreach=0.82, th=(0.0, 75.0), extr=(-25.0, 28.0), lens=True, cw=2)),
    (0.267, dict(g=(0.52, 0.23), mind=28.0, maxd=42.0, fwd=6.0, minreach=0.82, th=(0.0, 75.0), extr=(-25.0, 28.0), lens=True, cw=2)),
    (0.300, dict(g=(0.90, 0.28), mind=24.0, maxd=40.0, fwd=3.0, minreach=0.75, th=(0.0, 75.0), extr=(-25.0, 28.0), lens=True, cw=3)),
    (0.367, dict(g=(1.25, 0.40), mind=24.0, off=True, w=0.6, fwd=0.0, th=(0.0, 70.0), lens=True, cw=3)),
    (0.467, dict(g=(1.20, 0.65), off=True, w=0.5, fwd=0.0, th=(10.0, 60.0), lens=True, cw=4)),
    (0.600, dict(g=(0.80, 0.85), w=0.6, fwd=0.0, th=(20.0, 55.0), lens=True, cw=6)),
    (0.733, dict(g=(0.45, 0.80), tip=(0.20, 0.20), w=0.6, fwd=0.0, th=(25.0, 50.0), cw=8)),
    (0.867, dict(g=(0.34, 0.74), tip=(0.02, 0.16), w=0.6, fwd=0.0, th=(30.0, 45.0), cw=10)),
]

# V7 (user, 2026-10-21 12:26): the second hit is a diagonal cut from the upper left to the lower right, same
# speed and weight as the first.  From the chain pose (forearm across the lower left) the fist rises to the upper
# left OUT IN FRONT (>= 27 cm, blade tip ahead of the fist, never back at the head), holds a beat at the apex,
# then cuts through the centre down-right with the edge leading along the cut (contact 0.19-0.31 s) at the first
# sweep's screen speed (~1.8 NDC in 0.133 s), exits the lower-right corner, and rises back into the stance.
EDGE_DOWNRIGHT = (0.25, 0.65, -0.72)
BLADE_DIAG = (0.45, 0.85, 0.25)    # blade held pointing right-forward from the cock through the cut
EDGE_DIAG = (0.30, 0.00, -0.95)    # edge facing down: leads the down-right cut (lead ~0.7)
REF_ATTACK2 = [
    (0.067, dict(g=(-0.98, 0.10), mind=22.0, fwd=0.0, th=(-60.0, 10.0), lens=True, cw=4)),
    (0.133, dict(g=(-0.78, -0.36), mind=27.0, fwd=2.0, th=(-70.0, 40.0), lens=True, cw=3)),
    (0.167, dict(bdir=BLADE_DIAG, g=(-0.64, -0.46), mind=28.0, fwd=3.0, th=(-70.0, 50.0), lens=True, cw=3)),
    (0.200, dict(bdir=BLADE_DIAG, g=(-0.30, -0.22), mind=29.0, maxd=42.0, fwd=5.0, edge=EDGE_DIAG, minreach=0.78, extr=(-25.0, 30.0), th=(-75.0, 75.0), lens=True, cw=2)),
    (0.233, dict(bdir=BLADE_DIAG, g=(0.05, 0.06), mind=30.0, maxd=42.0, fwd=6.0, edge=EDGE_DIAG, minreach=0.8, extr=(-25.0, 30.0), th=(-75.0, 80.0), lens=True, cw=2)),
    (0.267, dict(bdir=BLADE_DIAG, g=(0.40, 0.36), mind=29.0, maxd=42.0, fwd=6.0, edge=EDGE_DIAG, minreach=0.8, extr=(-25.0, 30.0), th=(-75.0, 80.0), lens=True, cw=2)),
    (0.300, dict(bdir=BLADE_DIAG, g=(0.74, 0.66), mind=27.0, maxd=40.0, fwd=4.0, minreach=0.75, extr=(-25.0, 30.0), th=(-70.0, 80.0), lens=True, cw=3)),
    (0.367, dict(g=(1.05, 1.05), mind=24.0, off=True, w=0.6, fwd=0.0, th=(-60.0, 75.0), lens=True, cw=3)),
    (0.467, dict(g=(0.95, 1.35), off=True, hide=True, w=0.5, th=(-40.0, 65.0), lens=True, cw=4)),
    (0.600, dict(g=(0.72, 1.12), w=0.5, fwd=0.0, th=(-25.0, 55.0), lens=True, cw=6)),
    (0.733, dict(g=(0.46, 0.86), tip=(0.12, 0.30), w=0.6, fwd=0.0, th=(5.0, 50.0), cw=8)),
    (0.867, dict(g=(0.34, 0.75), tip=(0.00, 0.17), w=0.6, fwd=0.0, th=(30.0, 45.0), cw=10)),
]


def attack1_x(t):
    """Arm parameters of the accepted attack 1 at time t (same spline as author_kukri_clips.clip_attack)."""
    from author_kukri_clips import spline
    data = json.loads((P / 'attack_keys.json').read_text('utf-8'))
    keys = [dict(t=k['t'], hold=(i == 0), x=np.array(k['x'], float)) for i, k in enumerate(data['keys'])]
    keys.append(dict(t=38.0 / 30.0, hold=True, x=np.array(data['keys'][0]['x'], float)))
    return np.array(spline(keys, t, ('x',))['x'], float)


def main_attack2():
    F = Fitter()
    x0 = attack1_x(CHAIN_T)
    # theta continuity: walk attack 1 up to the chain point so the unwrap matches its clip
    theta = None
    for k in range(0, 18):
        theta = F.evaluate(attack1_x(k / 30.0), theta)['r']['theta']
    o = F.evaluate(x0, theta)
    keys = [dict(t=0.0, x=list(map(float, x0)), theta=math.degrees(o['r']['theta']), note='attack1 @ %.4f' % CHAIN_T)]
    print('attack2 start g %s tip %s theta %.1f' % (np.round(o['g'], 2), np.round(o['tip'], 2), math.degrees(o['r']['theta'])))
    seeds = {}
    seed_file = P / 'Work' / 'attack2_keys_v5.json'
    if seed_file.exists():
        seeds = {k['t']: k['x'] for k in json.loads(seed_file.read_text('utf-8'))['keys'][1:]}
    fit_keys(F, x0, o['r']['theta'], REF_ATTACK2, keys, seeds)
    (P / 'Work' / 'fit_keys_attack2.json').write_text(json.dumps(dict(keys=keys), indent=1), encoding='utf-8')
    if '--accept' in sys.argv:
        (P / 'attack2_keys.json').write_text(json.dumps(dict(source='fit_reference.py --attack2', chain_from_attack1=CHAIN_T,
                                                              length=ATTACK2_SECONDS, keys=keys), indent=1), encoding='utf-8')


# ------------------------------------------------------------------------------------------------ attack 3
# Third hit (user, 2026-10-21 13:16): two-handed forward thrust -- the left palm presses on the pommel while the
# right fist drives the kukri straight forward.  Takes over from attack 2 at CHAIN2_T (fist just out of the lower
# right after the diagonal cut).  The right arm brings the knife to centre-low with the tip pointing into the
# screen, cocks back close to the chest (18-23 cm) while the left hand arrives on the pommel (left_press keyed in
# author_kukri_clips.clip_attack3), then drives out to 44-48 cm along the line of sight (contact 0.26-0.38 s),
# holds the extension a beat, pulls back, releases the left hand and settles into the stance.
CHAIN2_T = 0.40
ATTACK3_SECONDS = 33.0 / 30.0
BLADE_FWD = (1.0, 0.0, 0.06)        # tip straight into the screen, a hair up (V8a)
AIM3 = (110.0, -2.0, 1.0)           # camera-space aim point of the thrust (cm)
REF_ATTACK3 = [
    # V8b: thrust from the lower right toward an aim point ~0.9 m ahead on the crosshair, so the blade reads as a
    # foreshortened line up-left of the fists instead of hiding straight behind them (V8a).  The cock stays
    # >= 29 cm out so the pommel -- and the left palm behind it -- keep clear of the lens.
    (0.100, dict(g=(0.34, 0.78), mind=22.0, fwd=4.0, th=(-75.0, 60.0), lens=True, cw=4)),
    (0.167, dict(aim=AIM3, g=(0.30, 0.60), mind=29.0, maxd=33.0, fwd=12.0, th=(-85.0, 70.0), lens=True, cw=3)),
    (0.200, dict(aim=AIM3, g=(0.29, 0.58), mind=29.0, maxd=33.0, fwd=12.0, th=(-85.0, 70.0), lens=True, cw=4)),
    (0.267, dict(aim=AIM3, g=(0.21, 0.44), mind=40.0, maxd=45.0, fwd=14.0, th=(-85.0, 70.0), cw=2)),
    (0.300, dict(aim=AIM3, g=(0.17, 0.37), mind=47.0, maxd=52.0, fwd=15.0, th=(-85.0, 70.0), cw=2)),
    (0.367, dict(aim=AIM3, g=(0.17, 0.36), mind=48.0, maxd=53.0, fwd=15.0, th=(-85.0, 70.0), cw=3)),
    (0.467, dict(aim=AIM3, g=(0.24, 0.50), mind=36.0, maxd=41.0, fwd=11.0, th=(-85.0, 70.0), cw=3)),
    (0.600, dict(g=(0.28, 0.66), mind=26.0, maxd=36.0, fwd=4.0, th=(-75.0, 30.0), lens=True, cw=4)),
    (0.733, dict(g=(0.31, 0.71), maxd=34.0, fwd=0.0, th=(-30.0, 45.0), lens=True, cw=3)),
    # 0.733 -> 1.1 s: the clip spline eases straight into the stance key (elbow swivel and roll unwind together).
]


def attack2_x(t):
    """Arm parameters of the accepted attack 2 at time t (same spline as author_kukri_clips.clip_attack2)."""
    from author_kukri_clips import spline
    data = json.loads((P / 'attack2_keys.json').read_text('utf-8'))
    keys = [dict(t=k['t'], hold=False, x=np.array(k['x'], float)) for k in data['keys']]
    keys.append(dict(t=data['length'], hold=True, x=np.array(json.loads((P / 'attack_keys.json').read_text('utf-8'))['keys'][0]['x'], float)))
    return np.array(spline(keys, t, ('x',))['x'], float)


def main_attack3():
    F = Fitter()
    theta = None
    for k in range(0, 18):
        theta = F.evaluate(attack1_x(k / 30.0), theta)['r']['theta']
    for k in range(0, int(round(CHAIN2_T * 30)) + 1):
        theta = F.evaluate(attack2_x(min(k / 30.0, CHAIN2_T)), theta)['r']['theta']
    x0 = attack2_x(CHAIN2_T)
    o = F.evaluate(x0, theta)
    keys = [dict(t=0.0, x=list(map(float, x0)), theta=math.degrees(o['r']['theta']), note='attack2 @ %.4f' % CHAIN2_T)]
    print('attack3 start g %s tip %s theta %.1f' % (np.round(o['g'], 2), np.round(o['tip'], 2), math.degrees(o['r']['theta'])))
    fit_keys(F, x0, o['r']['theta'], REF_ATTACK3, keys)
    (P / 'Work' / 'fit_keys_attack3.json').write_text(json.dumps(dict(keys=keys), indent=1), encoding='utf-8')
    if '--accept' in sys.argv:
        (P / 'attack3_keys.json').write_text(json.dumps(dict(source='fit_reference.py --attack3', chain_from_attack2=CHAIN2_T,
                                                              length=ATTACK3_SECONDS, keys=keys), indent=1), encoding='utf-8')


def fit_keys(F, x_prev, theta_prev, ref, keys, seeds=None):
    bounds = [(8, 60), (-45, 55), (-50, 15), (-200, 200), (-260, 320), (-25, 40), (-55, 50), (-12, 28), (-16, 12)]
    for t, target in ref:
        target = dict(target, _t=t)
        best = None
        starts = [x_prev]
        for st, sx in (seeds or {}).items():
            if abs(st - t) < 1e-3:
                starts.append(np.array(sx, float))   # known-good basin from an earlier accepted fit
        rng = np.random.default_rng(int(t * 1000))
        for k in range(10):
            s = np.array(x_prev, float) + rng.normal(0, 1, 9) * np.array([6, 8, 6, 30, 40, 8, 10, 4, 3])
            starts.append(s)
        for s in starts:
            s = np.clip(s, [b[0] for b in bounds], [b[1] for b in bounds])
            res = minimize(F.cost, s, args=(target, x_prev, theta_prev), method='Powell', bounds=bounds,
                           options=dict(maxiter=3000, xtol=1e-2, ftol=1e-4))
            if best is None or res.fun < best.fun:
                best = res
        x = best.x
        o = F.evaluate(x, theta_prev)
        r = o['r']
        theta_prev = r['theta']
        keys.append(dict(t=t, x=list(map(float, x)), cost=float(best.fun), theta=math.degrees(r['theta']),
                         g=list(map(float, o['g'])), tip=list(map(float, o['tip'])), pom=list(map(float, o['pom'])),
                         target={k: v for k, v in target.items() if not k.startswith('_')}))
        print('t %.3f cost %6.2f | g %s tip %s pom %s | theta %6.1f ext %5.1f uln %5.1f rollU %6.1f reach %.2f | W %s phi %.0f psi %.0f du %.0f de %.0f C %.0f/%.0f'
              % (t, best.fun, np.round(o['g'], 2), np.round(o['tip'], 2), np.round(o['pom'], 2), math.degrees(r['theta']),
                 r['ext'], r['uln'], r['roll_u'], r['reach'], np.round(x[:3], 1), x[3], x[4], x[5], x[6], x[7], x[8]), flush=True)
        x_prev = x
    return keys


if __name__ == '__main__':
    main_attack3() if '--attack3' in sys.argv else main_attack2() if '--attack2' in sys.argv else main()
