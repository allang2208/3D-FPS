"""Kukri quick melee (F): fit the right-arm keys to the reference pommel strike.

Reference: BV1CeYUeSE7b 89.73-90.97 s ("近战动作 #3 刀把"), t = 0 at frame 2692 (the last stance frame).  Read on the NDC
grid sheets (Reference/extract_pommel.py, grid_pommel.py; x right, y down):
  0.07-0.13  the right fist eases down-right, the blade turns to point left; the left fist rises from the bottom left;
  0.17       the right fist leaves the frame to the right (blade horizontal, pointing left); the left forearm comes in;
  0.20-0.30  left jab: the left fist punches into the centre; the right arm cocks up out of the right side;
  0.33-0.37  the left arm swings up and out to the left;
  0.37-0.40  the right forearm comes in from the upper right, the fist coming down from above the frame;
  0.43       the fist drops just below the centre (0.03, 0.15); 0.47-0.53 it drives forward-up into the target;
  0.53       impact (hit flash just left of the fist at (0.25, -0.17)); 0.53-0.60 held there;
  0.67-0.77  the fist settles a little lower (0.3, 0.05-0.22), blade still pointing back up-right at the lens;
  0.80-0.83  the fist drops to the lower right while the blade swings over and points away; 0.87-1.03 below the frame;
  1.07-1.23  the fist rises from the bottom into the stance (the first hit's re-raise, 38/30 s).
Blade direction (V2, user 10-23): through the strike the blade points BACK at the player, up and a little right -- it
widens towards the top edge in the reference, i.e. its far end is near the lens -- and the pommel, at the bottom of the
hammer fist, leads forward into the target.  V1 read the foreshortened blade as pointing straight up (bdir UP), which
left the pommel pointing down at the floor.  The left jab is keyed in author_kukri_quick.py, not fitted here.

Run:  python fit_pommel.py [--accept] [--resume[=t]]   -> Work/quick/fit_pommel.json (quick_keys.json with --accept)
      V2: python fit_pommel.py --resume --accept   (keeps the V1 keys up to RESUME_T)
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

from fit_reference import Fitter, idle_x, REF, _tip
from fit_sprint import fit

P = Path(__file__).resolve().parent
WORK = P / 'Work' / 'quick'
LENGTH = 38 / 30            # back on the stance at 1.267 s (reference ~1.23-1.27 s)
CONTACT_AT = 16 / 30        # 0.533: impact frame (hit flash)
WIDE = (-120.0, 120.0)
UP = (0.08, 0.12, 0.99)
UP_RIGHT = (0.05, 0.32, 0.95)
REF_POMMEL = [
    (0.067, dict(g=(0.38, 0.74), tip=_tip((0.38, 0.74), (-0.38, 0.02)), w=0.6, cw=6, mind=26.0, lens=True, th=WIDE)),
    (0.100, dict(g=(0.46, 0.75), tip=_tip((0.46, 0.75), (-0.40, 0.10)), w=0.6, cw=5, mind=26.0, lens=True, th=WIDE)),
    (0.133, dict(g=(0.62, 0.78), tip=_tip((0.62, 0.78), (-0.05, 0.30)), w=0.6, cw=4, mind=26.0, lens=True, th=WIDE)),
    (0.167, dict(g=(1.12, 0.72), tip=_tip((1.12, 0.72), (0.15, 0.48)), w=0.5, cw=3, mind=24.0, lens=True, th=WIDE)),
    # cock: out of the right side and up (blade hidden)
    (0.233, dict(g=(1.35, 0.50), off=True, hide=2, w=0.4, cw=3, mind=22.0, th=WIDE)),
    (0.300, dict(g=(1.35, -0.05), off=True, hide=2, w=0.4, cw=3, mind=22.0, th=WIDE)),
    # V2 (user 10-23: "the blade must point at the player, the pommel out at the enemy"): from the cock on, the blade
    # points back over the right shoulder towards the lens (it widens towards the top edge in the reference) and the
    # pommel leads into the target.  Fist positions re-read on 0.1-NDC grids (Work/quick/v2/ref_ndc_*.jpg, the red disc
    # on the back of the glove).
    (0.367, dict(g=(1.15, -0.80), bdir=(-0.55, 0.30, 0.78), hide=2, w=0.4, cw=3, mind=20.0, th=WIDE)),
    (0.400, dict(g=(0.32, -0.60), bdir=(-0.50, 0.25, 0.83), fm=(0.62, -0.05), lens=True, w=0.5, cw=3, mind=24.0, th=WIDE)),
    # drive: the fist drops just below the centre, then drives forward-up into the target, pommel first
    (0.433, dict(flat=0.5, g=(0.03, 0.15), bdir=(-0.55, 0.05, 0.83), fm=(0.30, 0.62), lens=True, w=0.8, gw=2.0, mind=30.0, maxd=44.0, cw=2, th=WIDE)),
    (0.467, dict(flat=0.5, g=(0.07, 0.08), bdir=(-0.58, 0.10, 0.81), fm=(0.34, 0.58), lens=True, w=0.8, gw=2.0, mind=31.0, maxd=45.0, cw=3, th=WIDE)),
    (0.500, dict(flat=0.5, g=(0.18, -0.04), bdir=(-0.60, 0.15, 0.79), fm=(0.40, 0.55), lens=True, w=0.8, gw=2.0, mind=33.0, maxd=46.0, cw=4, th=WIDE)),
    (CONTACT_AT, dict(flat=0.5, g=(0.25, -0.17), bdir=(-0.62, 0.20, 0.76), fm=(0.45, 0.50), lens=True, w=0.8, gw=2.0, mind=34.0, maxd=46.0, cw=5, th=WIDE)),
    (0.600, dict(flat=0.5, g=(0.28, -0.17), bdir=(-0.60, 0.28, 0.75), fm=(0.47, 0.52), lens=True, w=0.7, mind=33.0, maxd=45.0, cw=6, th=WIDE)),
    (0.667, dict(flat=0.5, g=(0.29, 0.03), bdir=(-0.55, 0.38, 0.74), lens=True, w=0.7, mind=31.0, maxd=44.0, cw=6, th=WIDE)),
    (0.733, dict(flat=0.5, g=(0.30, 0.10), bdir=(-0.52, 0.40, 0.75), lens=True, w=0.6, mind=30.0, maxd=42.0, cw=5, th=WIDE)),
    (0.767, dict(flat=0.5, g=(0.32, 0.22), bdir=(-0.42, 0.25, 0.87), lens=True, w=0.6, mind=29.0, cw=4, th=WIDE)),
    # the blade swings over the top and points away, thin, as the fist drops to the lower right
    (0.800, dict(g=(0.40, 0.48), tip=_tip((0.40, 0.48), (0.28, -0.72)), fwd=5.0, w=0.6, mind=27.0, cw=3, lens=True, th=WIDE)),
    (0.833, dict(g=(0.53, 0.85), tip=_tip((0.53, 0.85), (0.15, -0.19)), fwd=7.0, w=0.6, mind=26.0, cw=3, lens=True, th=WIDE)),
    # below the frame, then the first hit's re-raise into the stance
    # V2: one key just below the frame at a natural depth (V1's 0.867/0.933 keys were 0.99 reach, 46 cm out and 45-50 cm
    # down -- after the V2 strike that became a 1.7 m/s straight-arm swing with the blade tip crossing the bottom edge;
    # a second hidden key at 0.967 could not keep the blade hidden and is left to the spline)
    (0.900, dict(g=(0.50, 1.30), off=True, hide=2, elbowoff=1.3, mind=26.0, maxd=40.0, w=0.5, cw=3, th=(-40.0, 60.0))),
] + [(t, dict(k, th=(15.0, 50.0), lens=True, mind=max(k.get('mind', 0.0), 27.0))) for t, k in REF[-4:]]
RESUME_T = 0.300               # V2: keep the accepted V1 keys up to the hidden cock, refit from 0.367 on
TAIL_FROM = 1.000              # V2: --resume also keeps the accepted keys after this (the first hit's re-raise)


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    F = Fitter()
    x0 = idle_x(F)
    o = F.evaluate(x0)
    keys = [dict(t=0.0, x=list(map(float, x0)), theta=math.degrees(o['r']['theta']), note='stance')]
    theta, x_start, ref = o['r']['theta'], x0, REF_POMMEL
    resume = next((a for a in sys.argv if a.startswith('--resume')), None)
    if resume:
        t_keep = float(resume.split('=')[1]) if '=' in resume else RESUME_T
        old = json.loads((P / 'quick_keys.json').read_text('utf-8'))['keys']      # the accepted keys
        keep = [k for k in old if 0.0 < k['t'] <= t_keep + 1e-6]
        tail = [k for k in old if k['t'] > TAIL_FROM]
        for k in keep:
            theta = F.evaluate(np.array(k['x'], float), theta)['r']['theta']
        keys += keep
        x_start = np.array(keep[-1]['x'], float)
        ref = [k for k in ref if t_keep + 1e-6 < k[0] <= TAIL_FROM]
        print('resume after %.3f s with %d kept keys, %d tail keys after %.3f s' % (t_keep, len(keep), len(tail), TAIL_FROM))
    else:
        tail = []
    fit(F, x_start, theta, ref, keys)
    keys += tail
    out = dict(source='fit_pommel.py', reference='BV1CeYUeSE7b 89.733-90.967 (近战动作 #3 刀把)', start='stance',
               length=LENGTH, contact_at=CONTACT_AT, keys=keys)
    (WORK / 'fit_pommel.json').write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding='utf-8')
    if '--accept' in sys.argv:
        (P / 'quick_keys.json').write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding='utf-8')
        print('accepted -> quick_keys.json')


if __name__ == '__main__':
    main()
