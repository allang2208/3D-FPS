"""Kukri whirlwind (active skill whirlwind, 2026-10-24): fit the right-arm keys of the one-handed spin.

No reference video: an original design on the sword whirlwind's contract (A_RuneSword_WhirlwindV5, knots of
SourceAssets/Whirlwind20260920/ImpactV5/whirlwind_motion.py).  The runtime turns the camera -720 deg (two turns to the
left) and sweeps the damage on the right side of the view (yaw + 90); the clip only carries the arms.  Author phases
15/30 s ready, 32/30 s spin, 16/30 s recover (2.1 s); the runtime maps its own ready/spin/recover onto them.
  0.00-0.34  coil: from the stance the fist sinks to the right hip, the forearm rolls palm-up and the blade swings round to
             point back-right past the frame (the body loads against the turn -- the camera coil of WhirlwindFeel);
  0.34-0.50  release: the arm swings out in front, the blade levels out to the right with the edge leading forward;
  0.50-1.57  two turns held at chest height: a first reach forward-left (0.67), a small pull-back (1.02) and a second
             send (1.20), drooping a little at the end (1.57) -- never a frozen pose;
  1.57-1.66  brake: the fist runs on to the left of centre and the blade swings forward with the turn's momentum;
  1.66-2.10  the wrist rolls back and the fist rises into the stance.
The hammer grip puts the edge on the knuckle side: palm-up with the forearm forward points the blade right and the edge
forward, which is the side that leads when the body turns left (Work/whirl/probe_hold.py: twist ~-6, ext 15, uln 15).

Run:  python fit_whirl.py [--accept]   -> Work/whirl/fit_whirl.json (whirl_keys.json with --accept)
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

from fit_reference import Fitter, idle_x
from fit_sprint import fit

P = Path(__file__).resolve().parent
WORK = P / 'Work' / 'whirl'
READY, SPIN, RECOVER = 15 / 30, 32 / 30, 16 / 30
LENGTH = READY + SPIN + RECOVER          # 63/30 s
SPIN_END = READY + SPIN
WIDE = (-150.0, 150.0)
EDGE_FWD = (0.95, -0.15, 0.25)           # edge leading forward (slightly up: the flat shows a little from above)
REF_WHIRL = [
    # coil: the blade swings round to point right and a little back, out past the right edge (fwd keeps its far end from
    # coming back at the lens -- V1 of this fit pointed it back-right and the blade filled the right half of the frame)
    (0.067, dict(g=(0.35, 0.76), bdir=(-0.40, -0.25, 0.88), w=0.6, cw=6, mind=27.0, lens=True, th=WIDE)),
    (0.140, dict(g=(0.46, 0.86), bdir=(-0.15, 0.62, 0.77), fwd=-4.0, w=0.6, cw=5, mind=27.0, maxd=33.0, lens=True, th=WIDE)),
    (0.240, dict(g=(0.56, 0.92), bdir=(-0.20, 0.93, 0.30), fwd=-6.0, w=0.6, cw=5, mind=28.0, maxd=33.0, lens=True, th=WIDE)),
    (0.340, dict(g=(0.60, 0.95), bdir=(-0.22, 0.95, 0.20), fwd=-6.0, w=0.6, cw=6, mind=28.0, maxd=33.0, lens=True, th=WIDE)),
    # release into the hold
    (0.420, dict(g=(0.42, 0.68), bdir=(-0.05, 0.98, 0.15), w=0.7, cw=3, mind=31.0, lens=True, th=WIDE)),
    (READY, dict(g=(0.27, 0.52), bdir=(0.05, 0.99, 0.08), edge=EDGE_FWD, w=0.8, gw=1.5, cw=3, mind=34.0, maxd=40.0, th=WIDE)),
    # two turns at chest height
    (READY + SPIN * 0.16, dict(g=(0.14, 0.47), bdir=(0.22, 0.97, 0.06), edge=EDGE_FWD, w=0.8, gw=1.5, cw=4, mind=37.0, maxd=42.0, th=WIDE)),
    (READY + SPIN * 0.33, dict(g=(0.17, 0.49), bdir=(0.15, 0.98, 0.04), edge=EDGE_FWD, w=0.8, gw=1.5, cw=5, mind=36.0, maxd=41.0, th=WIDE)),
    (READY + SPIN * 0.49, dict(g=(0.23, 0.53), bdir=(0.08, 0.99, 0.00), edge=EDGE_FWD, w=0.8, gw=1.5, cw=5, mind=34.0, maxd=39.0, th=WIDE)),
    (READY + SPIN * 0.66, dict(g=(0.11, 0.48), bdir=(0.22, 0.97, -0.02), edge=EDGE_FWD, w=0.8, gw=1.5, cw=4, mind=37.0, maxd=42.0, th=WIDE)),
    (READY + SPIN * 0.84, dict(g=(0.14, 0.52), bdir=(0.15, 0.98, -0.08), edge=EDGE_FWD, w=0.8, gw=1.5, cw=5, mind=36.0, maxd=41.0, th=WIDE)),
    (SPIN_END, dict(g=(0.18, 0.58), bdir=(0.10, 0.98, -0.15), edge=EDGE_FWD, w=0.8, gw=1.5, cw=5, mind=35.0, maxd=41.0, th=WIDE)),
    # brake (the fist runs on left of centre, the blade swings forward with the turn) and return
    (SPIN_END + RECOVER * 0.18, dict(g=(0.00, 0.64), bdir=(0.62, 0.70, 0.35), w=0.7, cw=3, mind=36.0, maxd=44.0, th=WIDE)),
    (SPIN_END + RECOVER * 0.44, dict(g=(0.12, 0.72), bdir=(0.10, 0.40, 0.91), w=0.6, cw=3, mind=32.0, lens=True, th=WIDE)),
    (SPIN_END + RECOVER * 0.70, dict(g=(0.27, 0.76), bdir=(-0.42, -0.38, 0.83), w=0.6, cw=4, mind=29.0, lens=True, th=(0.0, 60.0))),
]


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    F = Fitter()
    x0 = idle_x(F)
    o = F.evaluate(x0)
    keys = [dict(t=0.0, x=list(map(float, x0)), theta=math.degrees(o['r']['theta']), note='stance')]
    fit(F, x0, o['r']['theta'], REF_WHIRL, keys)
    out = dict(source='fit_whirl.py', design='original (no reference video); sword whirlwind V5 contract', start='stance',
               length=LENGTH, ready=READY, spin=SPIN, recover=RECOVER, keys=keys)
    (WORK / 'fit_whirl.json').write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding='utf-8')
    if '--accept' in sys.argv:
        (P / 'whirl_keys.json').write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding='utf-8')
        print('accepted -> whirl_keys.json')


if __name__ == '__main__':
    main()
