"""equip_camera.json (camera_equip.py) -> KukriDrawRhythm.h draw camera curve (toss-and-catch Equip, V2).

The reference is spliced at the draw: frame 1564 opens a new recording whose rest aim sits 0.36 deg lower than the
frame before.  The curve is taken relative to that new rest (median of 0.77-0.93 s, where the view is still), so it
starts and ends at zero.  What remains, converted to this game's 75 deg vertical FOV (screen-equivalent, scale 1):
  0.00-0.10  switch kick: roll +1.7, pitch +0.5, yaw +0.3 deg, settled within three frames;
  0.13-0.40  the view lifts with the toss: pitch up to +1.5 deg at 0.27-0.30 s, FOV +0.5 deg;
  0.43-0.70  the catch pulls it down: pitch -1.3 deg at 0.53 s with roll -0.6 deg and FOV -0.6 deg, back by 0.73 s.
The curve is written at 60 Hz: sample 0 is the stance (0) and the measured switch-kick frame lands on sample 1
(1/60 s), so the kick rises within one 60 Hz step instead of popping; from there every 30 Hz reading maps to its own
time (a short interpolation for the odd samples).  FOV is 3-tap smoothed (scale-based FOV jitters by +-0.1 deg);
yaw/pitch/roll keep the registration as measured.  The last samples fade to zero at the clip end (0.80 s).
"""
import json
import os

import numpy as np

d = r"D:\FPS3D\FPSGAME\Saved\Reference\KukriBV1CeYUeSE7b20261020"
data = json.load(open(os.path.join(d, "equip_camera.json")))
start = data['clip_start']
frames = {f['frame']: f for f in data['frames'] if f.get('ok')}
LENGTH = 0.8
N30 = int(round(LENGTH * 30)) + 1                       # 0 .. 24
rest = {k: float(np.median([frames[start + i][k] for i in range(23, 29)])) for k in ('yaw', 'pitch', 'roll', 'fov')}
raw = {k: np.array([frames[start + i][k] - rest[k] for i in range(N30)]) for k in rest}
raw['fov'] = np.array([raw['fov'][0]] + [.25 * raw['fov'][i - 1] + .5 * raw['fov'][i] + .25 * raw['fov'][i + 1]
                                         for i in range(1, N30 - 1)] + [raw['fov'][-1]])
N60 = int(round(LENGTH * 60)) + 1                       # 0 .. 48
t60 = np.arange(N60) / 60.0
out = {}
for k, v in raw.items():
    t30 = np.arange(N30) / 30.0
    c = np.interp(t60, t30, v)
    c[1] = v[0]                                          # the switch-kick frame at 1/60 s
    c[0] = 0.0
    fade = np.clip((LENGTH - t60) / 0.1, 0.0, 1.0)       # last 0.1 s
    c = c * fade
    c[-1] = 0.0
    out[k] = c
names = dict(yaw='DrawYaw', pitch='DrawPitch', roll='DrawRoll', fov='DrawFov')
print('// rest (deg):', {k: round(v, 3) for k, v in rest.items()})
for k, n in names.items():
    print('    inline constexpr float %s[DrawSamples]={%s};' % (n, ','.join('%.2ff' % x for x in out[k])))
for k in names:
    i = int(np.argmax(np.abs(out[k])))
    print('// %s peak %.2f at %.3f s' % (k, out[k][i], t60[i]))
