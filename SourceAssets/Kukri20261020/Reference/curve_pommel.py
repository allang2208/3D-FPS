"""pommel_camera.json (camera_pommel.py) -> KukriQuickRhythm.h quick-melee camera curve (30 Hz, degrees).

Same screen-equivalent scaling as the accepted swing curves (curve_atk1.py: yaw x0.75, pitch x0.92, roll x1, fov x0.75).
The measured curve (t = 0 at frame 2692):
  0.10-0.40  the view tilts up (+3.8 deg) and rolls clockwise (+4.2) while the left jab goes out and the right arm cocks;
  0.43-0.53  the drive pulls it down (pitch +4.3 -> +0.9) and turns it left (-2.5 deg yaw);
  0.53-0.67  the impact: the reference's roll rattles frame to frame (+6.6 / -8.8 / +2.6 deg) -- smoothed here (5-tap),
             the confirmed hit adds its own damped shake (KukriRhythm::HitShake);
  0.70-0.80  the view widens ~+4.7 deg (direct fits 0.70-0.77) and settles; 0.83-1.0 a small dip (-1.6 deg) back to rest.
FOV between 0.43 and 0.67: the striking forearm covers half the frame and the chained registration reports a 9-11 deg
widening that the direct fits on both sides do not support.  FOV there is rebuilt as a smooth rise from the last
direct fit before the strike to the first one after it (peak just after the impact), not taken from the chain.
The curve starts and ends at zero (stance) and fades over the last 0.15 s.
"""
import json
import os

import numpy as np

d = r"D:\FPS3D\FPSGAME\Saved\Reference\KukriBV1CeYUeSE7b20261020"
data = json.load(open(os.path.join(d, "pommel_camera.json")))
start = data['clip_start']
frames = {f['frame']: f for f in data['frames']}
N = 39                       # 0 .. 38 (1.267 s)
SCALE = dict(yaw=.75, pitch=.92, roll=1.0, fov=.75)
t = np.arange(N) / 30.0
raw = {k: np.array([frames[start + i][k] if (start + i) in frames else 0.0 for i in range(N)]) for k in SCALE}
direct = np.array([str(frames[start + i]['inl']).startswith('direct') if (start + i) in frames else False for i in range(N)])
# FOV in the covered gap: smooth rise between the direct fits around it (0.40 and 0.70), peak at 0.63
a, b = 12, 21
fa, fb = raw['fov'][a], raw['fov'][b]
for i in range(a + 1, b):
    u = (t[i] - t[a]) / (t[b] - t[a])
    rise = np.sin(np.pi * 0.5 * min(1.0, u / 0.77))           # reaches 1 at 0.633
    raw['fov'][i] = fa + (max(fb, 5.0) - fa) * rise if t[i] <= 0.634 else 5.0 + (fb - 5.0) * (t[i] - 0.633) / (t[b] - 0.633)
# roll rattle on the impact
r = raw['roll'].copy()
w = np.array([1, 2, 3, 2, 1], float); w /= w.sum()
for i in range(13, 21):
    r[i] = float(np.dot(w, raw['roll'][i - 2:i + 3]))
raw['roll'] = r
fade = np.clip((t[-1] - t) / 0.15, 0.0, 1.0)
out = {}
for k, s in SCALE.items():
    c = raw[k] * s * fade
    c[0] = 0.0
    c[-1] = 0.0
    out[k] = c
names = dict(yaw='QuickYaw', pitch='QuickPitch', roll='QuickRoll', fov='QuickFov')
print('// reference time (V1, 38/30 s):')
for k, n in names.items():
    print('//  %s={%s};' % (n, ','.join('%.2ff' % v for v in out[k])))
print('// direct fits at', ', '.join('%.3f' % x for x in t[direct]))
# V2: the clip plays the reference on author_kukri_quick.TIME_MAP (1.0 s); the camera follows the same clock.
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from author_kukri_quick import ref_time, LENGTH
n2 = int(round(LENGTH * 30)) + 1
s2 = np.arange(n2) / 30.0
tr = np.array([ref_time(v) for v in s2])
print('    inline constexpr int32 QuickSamples=%d;' % n2)
for k, n in names.items():
    c = np.interp(tr, t, out[k])
    c[0] = 0.0
    c[-1] = 0.0
    out[k + '_clip'] = c
    print('    inline constexpr float %s[QuickSamples]={%s};' % (n, ','.join('%.2ff' % v for v in c)))
for k in names:
    c = out[k + '_clip']
    i = int(np.argmax(c)); j = int(np.argmin(c))
    print('// %s max %.2f at %.3f s, min %.2f at %.3f s' % (k, c[i], s2[i], c[j], s2[j]))
