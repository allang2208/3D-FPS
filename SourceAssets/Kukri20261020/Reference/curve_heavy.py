"""Heavy-strike camera curves (KukriHeavyRhythm::Charge* 13 samples, KukriRhythm::Heavy* 39 samples, 30 Hz).

Measured (camera_heavy.py far band, t = 0 at frame 3468):
  0.07-0.17  the raise: roll counter-clockwise to -6.3 deg, yaw +0.6, pitch -0.8;
  0.20-0.30  the right hand above the frame: roll back to +0.7, pitch up to +4.7, FOV +2..+6 (the jump carries the
             player up and forward -- partly translation);
  0.33-0.37  the cock: pitch +6.3/+5.3, yaw +1.8, roll -2.5;
  0.40       the cut frame: roll +14.5 (one-frame rattle), pitch -1.3, FOV +7.7;
  0.43-0.53  the view follows the cut down: pitch -9.4..-10, FOV +11..+19 at low correlation (hit flash, landing);
  0.57-1.40  settles at pitch -5 / FOV +7: the jump's displacement, not a camera offset.
Game mapping: the raise is the charge clip's first 0.40 s; the charge then holds and loads for the skill's charge seconds,
so its tilt is kept smaller than the reference's quick bank (held for up to two seconds) and the view narrows a little while
loading (focus).  The release starts from the loaded camera (V1: a hitch up into the cock; V2: straight into the back-chop, see RELEASE).
Same screen-equivalent scaling as the combo curves (yaw x0.75, pitch x0.92, roll x1, FOV x0.75).  Prints the C++ arrays."""
import numpy as np
from scipy.interpolate import PchipInterpolator

SCALE = dict(yaw=.75, pitch=.92, roll=1.0, fov=.75)
LOADED = dict(yaw=.3, pitch=2.5, roll=-4.5, fov=-2.0)     # end of the load (charge clip 2.0 s) = release t = 0
CHARGE = dict(
    yaw=[(0, 0), (.133, .5), (.233, .3), (.40, .3)],
    pitch=[(0, 0), (.10, -.2), (.167, -.6), (.233, .6), (.40, 1.5)],
    roll=[(0, 0), (.067, -.8), (.10, -2.6), (.133, -4.2), (.167, -4.8), (.233, -4.0), (.40, -3.5)],
    fov=[(0, 0), (.167, -.4), (.40, -.8)],
)
# V2 (2026-10-24, user: the blade laid back during the charge, a faster back-chop with more impact): the release starts in
# the cut at once -- a short lift as the blade comes over the top (0.033), the roll slams clockwise through the crosshair
# (0.067, +9.5; the confirmed hit adds HitShake x HitRoll), the view follows the blade down (-7) and widens (+8).
RELEASE = dict(
    yaw=[(0, .3), (.033, .9), (.067, 0), (.10, -1.6), (.167, -2.4), (.33, -1.2), (.55, -.3), (.75, 0), (1.267, 0)],
    pitch=[(0, 2.5), (.033, 3.8), (.067, 1.0), (.10, -4.0), (.167, -6.8), (.233, -7.0), (.35, -5.0), (.50, -2.2), (.65, -.6),
           (.80, 0), (1.267, 0)],
    roll=[(0, -4.5), (.033, -3.0), (.067, 9.5), (.10, 6.5), (.133, 2.5), (.20, -1.0), (.35, -.5), (.55, 0), (1.267, 0)],
    fov=[(0, -2.0), (.033, 0.0), (.067, 5.5), (.10, 8.0), (.167, 7.0), (.30, 4.5), (.45, 2.0), (.65, .5), (.80, 0), (1.267, 0)],
)
CNAMES = dict(yaw='ChargeYaw', pitch='ChargePitch', roll='ChargeRoll', fov='ChargeFov')
RNAMES = dict(yaw='HeavyYaw', pitch='HeavyPitch', roll='HeavyRoll', fov='HeavyFov')


def arr(keys, k, n):
    f = PchipInterpolator([t for t, _ in keys], [v * SCALE[k] for _, v in keys])
    return [float(f(min(i / 30, keys[-1][0]))) for i in range(n)]


for k, keys in CHARGE.items():
    v = arr(keys, k, 13)
    v[0] = 0.0
    print('    inline constexpr float %s[ChargeSamples]={%s};' % (CNAMES[k], ','.join('%.2ff' % x for x in v)))
print('    inline constexpr float LoadedYaw=%.2ff, LoadedPitch=%.2ff, LoadedRoll=%.2ff, LoadedFov=%.2ff;'
      % tuple(LOADED[k] * SCALE[k] for k in ('yaw', 'pitch', 'roll', 'fov')))
for k, keys in RELEASE.items():
    v = arr(keys, k, 39)
    v[-1] = 0.0
    print('    inline constexpr float %s[CameraSamples]={%s};' % (RNAMES[k], ','.join('%.2ff' % x for x in v)))
