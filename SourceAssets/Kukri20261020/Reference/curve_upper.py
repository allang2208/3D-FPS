"""Uppercut camera curve (KukriUpperRhythm::Upper*, 30 Hz, 39 samples) from the reference slide uppercut.

Measured (camera_upper.py far band; the cut frames 3193-3200 re-run on the top band only, upper_camera_cut.json):
  0.03-0.27  wind-up: yaw drifts right to ~+0.7 deg, pitch down to ~-1.4, roll clockwise to ~+1.7, FOV ~+0.9;
  0.30       pitch back to 0, roll +2.0;
  0.33-0.37  the cut: yaw -2.0/-2.5, pitch +2.8/+3.8, FOV +6.3/+10.6, roll +12.6 then -2.6 (one-frame hit rattle);
  0.40       pitch ~+10 (the view follows the blade up), correlation 0.65;
  0.43-0.70  the raised forearm covers most of the frame: registration unusable (correlation 0.4-0.5);
  0.73-1.30  settles at yaw +3.3 / pitch -5 / FOV +4.8: the slide carried the player forward, not a camera return.
The curve keys below follow the reliable frames and replace the unusable ones by a smooth return:
  the one-frame +12.6/-2.6 roll rattle becomes a +5.5 peak (a confirmed hit adds HitShake x HitRoll like the stab);
  the look-up after the cut is kept at +4.5 (measured +10 at low confidence, and our cut is shorter than the Apex blade);
  the end offset is the slide's displacement and returns to zero by 1.1 s.
Then the same screen-equivalent scaling as the combo curves (yaw x0.75, pitch x0.92, roll x1, FOV x0.75).
Prints the C++ arrays."""
import numpy as np
from scipy.interpolate import PchipInterpolator

N = 39
SCALE = dict(yaw=.75, pitch=.92, roll=1.0, fov=.75)
KEYS = dict(
    yaw=[(0, 0), (.10, .6), (.267, .7), (.30, .2), (.333, -1.9), (.367, -2.5), (.433, -1.5), (.567, -.6), (.80, 0), (1.267, 0)],
    pitch=[(0, 0), (.10, -.8), (.233, -1.4), (.267, -1.0), (.30, 0), (.333, 2.8), (.367, 3.8), (.40, 4.5), (.50, 3.0), (.633, 1.2),
           (.733, -.8), (.90, -.4), (1.10, 0), (1.267, 0)],
    roll=[(0, 0), (.10, .8), (.267, 1.7), (.30, 2.0), (.333, 5.5), (.367, 3.0), (.433, 1.0), (.60, .3), (.80, 0), (1.267, 0)],
    fov=[(0, 0), (.233, .4), (.30, .7), (.333, 4.5), (.367, 6.5), (.433, 4.0), (.567, 1.5), (.75, 0), (1.267, 0)],
)
NAMES = dict(yaw='UpperYaw', pitch='UpperPitch', roll='UpperRoll', fov='UpperFov')
for k, keys in KEYS.items():
    f = PchipInterpolator([t for t, _ in keys], [v * SCALE[k] for _, v in keys])
    vals = [float(f(i / 30)) for i in range(N)]
    vals[0] = vals[-1] = 0.0
    print('    inline constexpr float %s[CameraSamples]={%s};' % (NAMES[k], ','.join('%.2ff' % v for v in vals)))
