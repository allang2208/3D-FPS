"""sprint_camera.json (camera_sprint.py) -> KukriDashRhythm.h sprint-attack camera curve (30 Hz, degrees).

Same screen-equivalent scaling as the accepted swing curves (curve_atk1.py: yaw x0.75, pitch x0.92, roll x1), FOV x0.5
(the jump's height change leaks into the registration scale).  The measured curve:
  0.03-0.10  the view tilts up as the arms go overhead; 0.17-0.30 held up ~+9 deg at the top of the jump;
  0.33-0.40  the chop pulls it down through the horizon; 0.43-0.53 bottomed at ~-9 deg on the landing;
After 0.55 s the chained registration drifts with the landing position (and the player turning), so the curve fades
to zero by RETURN_END and stays at the stance.  The reference's one-frame roll rattle on the hit (-10 / +4 / -4 deg)
is smoothed (5-tap) between 0.37 and 0.67 s: the confirmed hit adds its own damped shake (KukriRhythm::HitShake).
"""
import json
import os

import numpy as np

d = r"D:\FPS3D\FPSGAME\Saved\Reference\KukriBV1CeYUeSE7b20261020"
data = json.load(open(os.path.join(d, "sprint_camera.json")))
start = data['clip_start']
frames = {f['frame']: f for f in data['frames']}
N = 41                       # 0 .. 40 (1.333 s)
SCALE = dict(yaw=.75, pitch=.92, roll=1.0, fov=.5)
RETURN = (0.55, 1.10)
t = np.arange(N) / 30.0
fade = np.where(t <= RETURN[0], 1.0, 1.0 - np.clip((t - RETURN[0]) / (RETURN[1] - RETURN[0]), 0, 1) ** 2 * (3 - 2 * np.clip((t - RETURN[0]) / (RETURN[1] - RETURN[0]), 0, 1)))
out = {}
for k, s in SCALE.items():
    raw = np.array([frames[start + i][k] * s if (start + i) in frames else 0.0 for i in range(N)])
    if k == 'roll':
        sm = raw.copy()
        w = np.array([1, 2, 3, 2, 1], float); w /= w.sum()
        for i in range(11, 21):
            sm[i] = float(np.dot(w, raw[i - 2:i + 3]))
        raw = sm
    c = raw * fade
    c[0] = 0.0
    c[-1] = 0.0
    out[k] = c
names = dict(yaw='DashYaw', pitch='DashPitch', roll='DashRoll', fov='DashFov')
for k, n in names.items():
    print('    inline constexpr float %s[DashSamples]={%s};' % (n, ','.join('%.2ff' % v for v in out[k])))
for k in names:
    i = int(np.argmax(out[k])); j = int(np.argmin(out[k]))
    print('// %s max %.2f at %.3f s, min %.2f at %.3f s' % (k, out[k][i], t[i], out[k][j], t[j]))
