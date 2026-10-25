"""Kukri heavy strike (heavyStrike skill): fit the right-arm keys of the charge and the release to the reference.

Reference: BV1CeYUeSE7b 115.60-117.00 s ("近战动作（跳跃）#12 ↙"), t = 0 at frame 3468 (the last stance frame).  Read on the
labelled NDC sheets (Reference/extract_heavy.py: heavy_px_*.jpg; x right, y down):
  0.067      the fist rises and opens out to the right (0.38, 0.55), blade up-left, forearm up to the right edge;
             the left forearm comes in from the bottom left;
  0.100      fist (0.42, 0.42); the left forearm crosses the lower left, hand at (-0.05, 0.55);
  0.133      fist (0.60, -0.05), blade pointing left; left hand reaching to (0.08, 0.15);
  0.167      fist (0.65, -0.35) at the upper right, blade up-left (tip (0.25, -0.65)); left hand (-0.05, 0.05);
  0.20-0.33  the right hand is above the frame; the open left hand sweeps out to the lower left (gone at 0.30);
  0.367      the cocked forearm stands at the right edge, fist (0.68, -0.45), the blade laid back over the shoulder (not seen);
  0.400      one-frame diagonal cut: the fist ends at the bottom centre (-0.05, 0.92), the trail runs from the top right
             through the crosshair to the bottom left; hit flash at the centre on 0.433;
  0.43-1.03  both hands below the frame;
  1.067      the fist comes back in at the bottom right; 1.20 fist (0.35, 0.28) blade down-left; 1.233 (0.38, 0.37) blade
             left; 1.30 (0.25, 0.70) blade up-left; 1.40 the stance.

V2 (2026-10-24, user): "during the charge the blade should point back behind the player with the handle forward, then a
回砍 from the upper right to the lower left; now the blade points forward.  The release should be faster, with more impact."
V1 (run 1, Work/heavy/fit_heavy_run1.json) held the fist at the upper right with the blade pointing up-left into the frame
(the 0.167 reference read held for the whole charge) and hitched up out of the frame before the cut.  V2 reads the reference
cock (0.367) as the user describes it: a cocked hammer -- forearm upright along the right edge, wrist extended, the blade laid
back over the right shoulder behind the player, the pommel pointing forward at the target.
  HeavyCharge  0.00-0.167 the raise as V1 (kept keys); 0.20-0.40 the wrist cocks back and the blade swings up and over
               behind the shoulder into the cocked pose; 0.40-2.00 the load draws the fist back and the blade further down
               behind the back.  The runtime holds the end of the raise until the load starts and retimes the load over the
               skill's charge seconds.
  HeavyRelease from the cocked pose straight into the back-chop: 0.033 the blade comes up over the top (edge forward),
               0.067 the blade crosses the crosshair edge first, 0.100 the fist at the bottom centre (ref 0.400), out at the
               lower left 0.133, below the frame to 0.80, re-raise 0.833-1.067 (ref 1.067-1.30), the stance at 35/30 s.
Terms on top of fit_sprint.SprintFitter: bladeabove (the blade above the top edge, the fist in view), headclear (blade and
pommel samples at least HEAD_CLEAR cm from the head centre behind the eyes) and lensband (a sample in front of the lens but
closer than 10 cm must be outside the frame) -- the lens term cannot be used once the blade points back past the eyes.
The left hand is keyed in author_kukri_heavy.py (left_arm), not fitted here.

Run:  python fit_heavy.py [--accept] [--full] [--release] -> Work/heavy/fit_heavy.json (heavy_keys.json with --accept)
      default keeps the raise keys <= KEEP_RAISE of run 1; --full refits the whole charge; --release keeps the charge of
      Work/heavy/fit_heavy.json and refits only the release.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

from fit_reference import idle_x, _tip
from fit_sprint import SprintFitter, fit
from kukri_rig import ndc, TIP, POMMEL
from kmath import mesh_to_cam

P = Path(__file__).resolve().parent
WORK = P / 'Work' / 'heavy'
CHARGE_LENGTH = 2.0         # raise 0-0.40 + load 0.40-2.00 (RuneSwordHeavyRhythm::ChargeSeconds)
RAISE_END = 0.40
KEEP_RAISE = 0.167          # V2 keeps run 1's raise up to here (it follows the reference frames)
RELEASE_LENGTH = 35 / 30    # back on the stance (reference 1.40 s from the stance, 1.03 s from the cock)
CONTACT = (0.033, 0.133)    # from the blade coming over the top until the fist leaves the bottom
CUT_KEY = 0.067             # fitted key: the blade crosses the crosshair
STRIKE_AT = 0.075           # impact moment (author_kukri_heavy prints the edge lead around it)
WIDE = (-150.0, 150.0)
HEAD_CENTRE = (-7.0, 0.0, -3.0)   # camera cm: the head centre sits behind the eyes
HEAD_CLEAR = 16.0
# Camera: x forward, y right, z up.
EDGE_DIAG = (0.25, -0.55, -0.80)  # edge leading down-left along the cut
EDGE_OVER = (0.90, -0.35, 0.10)   # blade upright coming over the top: the edge leads forward
BACK = lambda d: tuple(np.asarray(d, float) / np.linalg.norm(d))


def edge_up(b, n=(0.5, -0.1, 0.86)):
    """Cocked edge: the part of forward-up across the blade -- the face that leads once the forearm drives the blade up over
    the top (run 2 left it free and needed -84..-114 deg of forearm twist to bring the edge round for the cut)."""
    b = np.asarray(b, float); n = np.asarray(n, float)
    e = n - b * np.dot(n, b)
    return tuple(e / np.linalg.norm(e))


COCK = dict(headclear=True, lensband=True, th=WIDE)

REF_CHARGE = [
    # The raise: fist out to the right and up, blade up-left, the forearm up to the right edge (kept from run 1).
    (0.067, dict(g=(0.38, 0.55), tip=_tip((0.38, 0.55), (-0.08, 0.12)), w=0.6, cw=6, mind=26.0, lens=True, th=(-30.0, 90.0))),
    (0.100, dict(g=(0.42, 0.42), tip=_tip((0.42, 0.42), (0.00, 0.05)), w=0.6, cw=5, mind=26.0, lens=True, th=(-30.0, 90.0))),
    (0.133, dict(g=(0.60, -0.05), tip=_tip((0.60, -0.05), (0.10, -0.30)), w=0.6, cw=4, mind=25.0, lens=True, th=(-40.0, 90.0))),
    (0.167, dict(g=(0.65, -0.35), tip=_tip((0.65, -0.35), (0.25, -0.65)), w=0.6, cw=4, mind=24.0, lens=True, th=(-40.0, 90.0))),
    # The cock: the wrist rolls the blade up and over (tip above the frame) and lays it back behind the right shoulder.
    (0.200, dict(g=(0.70, -0.55), bdir=BACK((0.10, -0.10, 1.0)), bladeabove=1.02, w=0.6, cw=4, mind=22.0, **COCK)),
    (0.267, dict(g=(0.72, -0.55), bdir=BACK((-0.55, 0.10, 0.83)), edge=edge_up(BACK((-0.55, 0.10, 0.83))), w=0.6, cw=4,
                 mind=20.0, maxd=32.0, **COCK)),
    # Cocked (= the reference 0.367 frame): forearm upright along the right edge, the pommel forward, the blade behind.
    (RAISE_END, dict(g=(0.70, -0.48), fm=(0.76, 0.28), bdir=BACK((-0.78, 0.15, 0.60)), edge=edge_up(BACK((-0.78, 0.15, 0.60))),
                     w=0.6, cw=6, mind=19.0, maxd=28.0, **COCK)),
    # The load: the fist draws back towards the shoulder and the blade sinks further behind the back.
    (1.200, dict(g=(0.71, -0.51), fm=(0.77, 0.30), bdir=BACK((-0.86, 0.18, 0.47)), edge=edge_up(BACK((-0.86, 0.18, 0.47))),
                 w=0.6, cw=10, mind=18.0, maxd=26.0, **COCK)),
    (CHARGE_LENGTH, dict(g=(0.72, -0.54), fm=(0.78, 0.32), bdir=BACK((-0.92, 0.20, 0.34)), edge=edge_up(BACK((-0.92, 0.20, 0.34))),
                         w=0.6, cw=10, mind=17.0, maxd=25.0, **COCK)),
]

REF_RELEASE = [
    # The back-chop starts at once: the blade swings up over the top, edge first, as the forearm drives forward.
    (0.033, dict(g=(0.60, -0.40), bdir=BACK((0.15, -0.20, 0.97)), edge=EDGE_OVER, bladeabove=1.0, w=0.6, cw=1.5, mind=22.0,
                 **COCK)),
    # Through the crosshair edge first, the fist running from the upper right to the bottom.
    # Run 2 reached the cut with -84 deg of forearm twist and the wrist at the ulnar limit: the twist is kept in the
    # combo's palm-up corridor (the first hit's cut runs at -70).
    (CUT_KEY, dict(g=(0.36, 0.30), tip=(0.05, -0.05), edge=EDGE_DIAG, edgeout=-0.2, w=0.7, gw=1.5, cw=1.5, mind=27.0,
                   maxd=38.0, lens=True, th=(-75.0, 45.0))),
    (0.100, dict(g=(-0.05, 0.92), tip=_tip((-0.05, 0.92), (-0.40, 0.50)), edge=EDGE_DIAG, edgeout=-0.2, w=0.7, gw=1.5, cw=1.5,
                 mind=25.0, maxd=38.0, lens=True, th=(-80.0, 40.0))),
    # Follow-through below the frame to the lower left, then under the frame back to the right.
    (0.133, dict(g=(-0.45, 1.25), off=True, hide=2, elbowoff=1.3, w=0.5, cw=3, lens=True, th=(-85.0, 40.0))),
    (0.233, dict(g=(-0.40, 1.45), off=True, hide=2, elbowoff=1.3, w=0.5, cw=4, lens=True, th=(-85.0, 40.0))),
    # Run 3 held the cut's pronation (-70/-50 at the corridor edge) under the frame and reached the re-raise with the arm
    # straight 52-59 cm out (cost 5-8): the forearm now rolls back while it is out of view.
    (0.500, dict(g=(0.05, 1.50), off=True, hide=2, elbowoff=1.3, w=0.5, cw=4, lens=True, th=(-40.0, 40.0))),
    (0.700, dict(g=(0.40, 1.45), off=True, hide=2, elbowoff=1.3, w=0.5, cw=4, lens=True, th=(-5.0, 50.0))),
    # Re-raise from the bottom right (ref 1.067-1.30): blade down-left, then left, then up-left into the stance.
    (0.833, dict(g=(0.55, 0.98), tip=(0.05, 1.12), w=0.5, cw=3, mind=20.0, lens=True, th=(-60.0, 70.0))),
    (0.967, dict(g=(0.35, 0.28), tip=_tip((0.35, 0.28), (-0.35, 0.60)), w=0.6, cw=3, mind=24.0, lens=True, th=(-40.0, 60.0))),
    (1.000, dict(g=(0.38, 0.37), tip=_tip((0.38, 0.37), (-0.12, 0.30)), w=0.6, cw=4, mind=24.0, lens=True, th=(-20.0, 60.0))),
    (1.067, dict(g=(0.25, 0.70), tip=_tip((0.25, 0.70), (-0.50, 0.25)), w=0.6, cw=4, mind=24.0, lens=True, th=(0.0, 55.0))),
]


class HeavyFitter(SprintFitter):
    """SprintFitter + bladeabove / headclear / lensband (see the module docstring)."""
    def cost(self, x, target, prev_x, prev_theta):
        c = super().cost(x, target, prev_x, prev_theta)
        if c >= 1e5 or not any(k in target for k in ('bladeabove', 'headclear', 'lensband')):
            return c
        o = self.evaluate(x, prev_theta)
        K = o['K']
        if 'bladeabove' in target:
            m = float(target['bladeabove'])
            for f in np.linspace(0.35, 1.0, 7):
                pc = mesh_to_cam(K.point(np.asarray(TIP) * f))
                if pc[0] > 3.0:
                    tx, ty = ndc(pc)
                    c += 15.0 * max(0.0, ty + m) ** 2 if abs(tx) < 1.05 else 0.0
        pts = [mesh_to_cam(K.point(np.asarray(TIP) * f)) for f in np.linspace(0.15, 1.0, 9)] + [mesh_to_cam(K.point(POMMEL))]
        if target.get('headclear'):
            for pc in pts:
                d = float(np.linalg.norm(pc - np.asarray(HEAD_CENTRE)))
                c += 2.0 * max(0.0, HEAD_CLEAR - d) ** 2
        if target.get('lensband'):
            for pc in pts:
                if 1.0 < pc[0] < 10.0:
                    tx, ty = ndc(pc)
                    if abs(tx) < 1.15 and abs(ty) < 1.15:
                        c += 0.5 * (10.0 - pc[0]) ** 2
        return c


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    F = HeavyFitter()
    x0 = idle_x(F)
    o = F.evaluate(x0)
    if '--release' in sys.argv:
        charge = json.loads((WORK / 'fit_heavy.json').read_text('utf-8'))['charge']
        print('kept %d charge keys' % len(charge))
    else:
        charge = [dict(t=0.0, x=list(map(float, x0)), theta=math.degrees(o['r']['theta']), note='stance')]
        ref, x_prev, theta = REF_CHARGE, x0, o['r']['theta']
        if '--full' not in sys.argv:
            run1 = json.loads((WORK / 'fit_heavy_run1.json').read_text('utf-8'))['charge']
            keep = [k for k in run1 if 0.0 < k['t'] <= KEEP_RAISE + 1e-6]
            for k in keep:
                theta = F.evaluate(np.array(k['x'], float), theta)['r']['theta']
            charge += keep
            x_prev = np.array(keep[-1]['x'], float)
            ref = [(t, k) for t, k in REF_CHARGE if t > KEEP_RAISE + 1e-6]
            print('kept %d raise keys of run 1' % len(keep))
        fit(F, x_prev, theta, ref, charge)
    theta = None
    for k in charge:
        theta = F.evaluate(np.array(k['x'], float), theta)['r']['theta']
    loaded = charge[-1]
    release = [dict(t=0.0, x=list(loaded['x']), theta=loaded['theta'], note='cocked pose (end of HeavyCharge)')]
    fit(F, np.array(loaded['x'], float), theta, REF_RELEASE, release)
    out = dict(source='fit_heavy.py', variant='V2 cocked hammer (blade back, pommel forward) + back-chop',
               reference='BV1CeYUeSE7b 115.60-117.00 s (近战动作（跳跃）#12 ↙)',
               charge_length=CHARGE_LENGTH, raise_end=RAISE_END, release_length=RELEASE_LENGTH, contact=CONTACT,
               strike_at=STRIKE_AT, charge=charge, release=release)
    (WORK / 'fit_heavy.json').write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding='utf-8')
    if '--accept' in sys.argv:
        (P / 'heavy_keys.json').write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding='utf-8')


if __name__ == '__main__':
    main()
