"""Kukri uppercut (swordUppercut skill): fit the right-arm keys to the reference slide uppercut.

Reference: BV1CeYUeSE7b 106.20-107.30 s ("近战动作（滑铲）#9 上撩"), t = 0 at frame 3186 (the last stance frame; the
player is already sliding).  Read on the NDC grid sheets (Reference/extract_upper.py: grid_up_a..d, big_up_a..b; x right,
y down):
  0.03-0.07  the blade turns to point left/up-left and the fist eases right and down (0.50,0.76) -> (0.68,0.84);
             the open left hand comes up from the bottom left, palm down, fingers spread forward-right;
  0.10-0.13  the fist drops to the bottom-right corner, the blade still pointing up-left over the floor;
  0.17-0.23  the right hand is below the frame at the lower right (wind-up); the left hand sweeps left (-0.4 -> -0.75);
  0.27       the fist comes back in at the lower right, blade down-left;
  0.30       the fist rises (0.55, 0.62) with the blade up-right -- the cut starts, motion trail on the right;
  0.33-0.37  through the centre (0.20, 0.18) -> (-0.06, 0.03), blade up, the forearm up from the lower right;
  0.40       the forearm sweeps up across the lens, the fist leaves the top left;
  0.43-0.67  follow-through: the raised forearm crosses the upper left close to the lens and drifts slowly down;
  0.70-0.77  the arm drops out of the bottom left; 0.80-0.97 below the frame;
  1.00-1.10  the blade rises from the bottom centre and lays left into the stance (the first hit's re-raise; 38/30 s).
The left hand is keyed in author_kukri_upper.py (left_arm), not fitted here.

Run:  python fit_upper.py [--accept] [--resume[=t]]   -> Work/upper/fit_upper.json (upper_keys.json with --accept)
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

from fit_reference import Fitter, idle_x, REF, _tip, fit_keys

P = Path(__file__).resolve().parent
WORK = P / 'Work' / 'upper'
LENGTH = 38 / 30            # back on the stance at 1.267 s (reference ~1.10 s; the first hit's re-raise timing)
CONTACT = (0.300, 0.433)    # the cut: from the rise at the lower right until the forearm crosses the lens
STRIKE_AT = 0.350           # the fist crosses the screen centre (impact moment, KukriUpperRhythm)
WIDE = (-120.0, 120.0)
REF_UPPER = [
    # Turn and drop: blade up-left over the floor, fist to the lower right.
    (0.033, dict(g=(0.50, 0.76), tip=_tip((0.50, 0.76), (0.20, 0.45)), w=0.6, cw=6, mind=26.0, lens=True, th=WIDE)),
    (0.067, dict(g=(0.68, 0.84), tip=_tip((0.68, 0.84), (0.00, 0.60)), w=0.6, cw=5, mind=25.0, lens=True, th=WIDE)),
    (0.100, dict(g=(0.78, 0.98), tip=_tip((0.78, 0.98), (0.05, 0.68)), w=0.6, cw=4, mind=24.0, lens=True, th=WIDE)),
    (0.133, dict(g=(0.86, 1.10), tip=_tip((0.86, 1.10), (0.28, 0.62)), w=0.5, cw=4, mind=24.0, lens=True, th=WIDE)),
    # Wind-up below the lower right: arm and blade out of the frame.
    (0.167, dict(g=(0.92, 1.25), off=True, hide=2, elbowoff=1.3, w=0.5, cw=4, lens=True, th=WIDE)),
    (0.200, dict(g=(0.95, 1.35), off=True, hide=2, elbowoff=1.3, w=0.5, cw=4, lens=True, th=WIDE)),
    (0.233, dict(g=(0.92, 1.35), off=True, hide=2, elbowoff=1.3, w=0.5, cw=4, lens=True, th=WIDE)),
    (0.267, dict(g=(0.76, 1.04), tip=(0.48, 1.00), w=0.5, cw=3, mind=24.0, lens=True, th=WIDE)),
    # The cut: up from the lower right through the centre, blade up-right then up, forearm from the lower right.
    # Run 1 reached the cut at 46-53 cm (fist small, the V3 'extended far arm' read); capped at 33-36 cm.
    (0.300, dict(g=(0.55, 0.62), tip=_tip((0.55, 0.62), (0.95, 0.05)), fm=(0.50, 0.95), w=0.7, gw=1.5, cw=2, mind=24.0, maxd=36.0,
                 edgeout=-0.2, lens=True, th=WIDE)),
    (0.333, dict(g=(0.20, 0.18), tip=_tip((0.20, 0.18), (0.35, -0.10)), fm=(0.38, 0.70), w=0.7, gw=2.0, cw=2, mind=24.0, maxd=34.0,
                 edgeout=-0.2, lens=True, th=WIDE)),
    (0.367, dict(g=(-0.06, 0.03), tip=_tip((-0.06, 0.03), (-0.10, -0.28)), fm=(0.22, 0.55), w=0.7, gw=2.0, cw=2, mind=22.0, maxd=33.0,
                 edgeout=-0.2, lens=True, th=WIDE)),
    # Follow-through: the fist leaves the top left, the raised forearm crosses the upper left close to the lens.
    # Runs 3-5 (rejected): a blade-up target on the cut wrung the forearm to 120 deg (the V1 "twisted arm"); blade-up/back
    # targets on the follow-through put the wrist 14 cm in front of the eye on the transition frame (cost 23-53).  Run 2
    # (accepted) leaves the blade free: it stays off the screen 0.42-0.80 s and 8-11 cm from the lens.
    (0.400, dict(g=(-0.75, -0.75), fm=(0.00, 0.25), fd=20.0, w=0.6, cw=2, hide=2, lens=True, th=WIDE)),
    (0.433, dict(g=(-1.05, -1.00), off=True, fm=(-0.25, 0.00), fd=16.0, w=0.6, cw=3, hide=2, lens=True, th=WIDE)),
    (0.500, dict(g=(-1.15, -1.05), off=True, fm=(-0.35, -0.12), fd=14.0, w=0.6, cw=5, hide=2, lens=True, th=WIDE)),
    (0.567, dict(g=(-1.15, -1.00), off=True, fm=(-0.38, -0.10), fd=14.0, w=0.6, cw=6, hide=2, lens=True, th=WIDE)),
    (0.633, dict(g=(-1.10, -0.85), off=True, fm=(-0.36, 0.00), fd=14.5, w=0.6, cw=6, hide=2, lens=True, th=WIDE)),
    (0.667, dict(g=(-1.10, -0.70), off=True, fm=(-0.40, 0.10), fd=15.0, w=0.6, cw=5, hide=2, lens=True, th=WIDE)),
    (0.700, dict(g=(-0.95, 0.20), fm=(-0.60, 0.55), fd=16.0, w=0.6, cw=4, hide=2, lens=True, th=WIDE)),
    (0.733, dict(g=(-1.10, 0.80), off=True, fm=(-0.85, 0.95), w=0.5, cw=4, hide=2, lens=True, th=WIDE)),
    (0.767, dict(g=(-0.90, 1.30), off=True, hide=2, elbowoff=1.4, w=0.5, cw=3, lens=True, th=WIDE)),
    (0.833, dict(g=(-0.30, 1.50), off=True, hide=2, elbowoff=1.4, phi=0.0, w=0.5, cw=3, th=WIDE)),
] + [(t, dict(k, th=(15.0, 50.0), lens=True, **(dict(elbowoff=1.4, hide=2, phi=40.0) if t < 1.0 else {}))) for t, k in REF[-5:]]


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    F = Fitter()
    x0 = idle_x(F)
    o = F.evaluate(x0)
    keys = [dict(t=0.0, x=list(map(float, x0)), theta=math.degrees(o['r']['theta']), note='stance')]
    ref = REF_UPPER
    resume = next((a for a in sys.argv if a.startswith('--resume')), None)
    if resume:
        t_keep = float(resume.split('=')[1]) if '=' in resume else 0.267
        old = json.loads((WORK / 'fit_upper.json').read_text('utf-8'))['keys']
        keep = [k for k in old if 0.0 < k['t'] <= t_keep + 1e-6]
        theta = o['r']['theta']
        for k in keep:
            theta = F.evaluate(np.array(k['x'], float), theta)['r']['theta']
        keys += keep
        x0 = np.array(keep[-1]['x'], float)
        o = dict(r=dict(theta=theta))
        ref = [(t, k) for t, k in REF_UPPER if t > t_keep + 1e-6]
        print('resume after %.3f s with %d kept keys' % (t_keep, len(keep)))
    fit_keys(F, x0, o['r']['theta'], ref, keys)
    out = dict(source='fit_upper.py', reference='BV1CeYUeSE7b 106.20-107.30 s (近战动作（滑铲）#9 上撩)', start='stance',
               length=LENGTH, contact=CONTACT, strike_at=STRIKE_AT, keys=keys)
    (WORK / 'fit_upper.json').write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding='utf-8')
    if '--accept' in sys.argv:
        (P / 'upper_keys.json').write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding='utf-8')


if __name__ == '__main__':
    main()
