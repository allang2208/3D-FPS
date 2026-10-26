"""melee_camera.json (camera_melee.py) -> thrust_curve.json: camera curve of the single quick-melee thrust (30 Hz, deg).

Window = reference frames 1210-1230 (file 40.33-41.00 s), author t = (frame - 1210) / 30, the second knife cycle of
the flourish that the retired curve_melee.py measured (trash/dual-pistol-kukri-20261026): roll/yaw kick on the hold swinging out (1213-1214), yaw whip on the
drive-in (1216), pitch nod into the full extension (1218-1219), settle by 1229. Same screen-equivalent scaling as
that flourish curve (yaw x0.75, pitch x0.92, roll x1, fov x0.75); ends faded to zero over 0.07 s / 0.15 s. The blur envelope
is the camera angular speed normalised against the whole flourish (same strength scale as before), clipped to 0.85.
"""
import json
import os

import numpy as np

d = r"D:\FPS3D\FPSGAME\Saved\Reference\DualPistolKukriBV1hQnh6hEio20261025"
data = json.load(open(os.path.join(d, "melee_camera.json")))
frames = {f['frame']: f for f in data['frames']}
START, N = 1210, 21
SCALE = dict(yaw=.75, pitch=.92, roll=1.0, fov=.75)
t = np.arange(N) / 30.0
fade = np.clip(t / 0.07, 0, 1) * np.clip((t[-1] - t) / 0.15, 0.0, 1.0)
out = {}
for k, s in SCALE.items():
    raw = np.array([frames[START + i][k] if (START + i) in frames else 0.0 for i in range(N)])
    c = raw * s * fade
    c[0] = c[-1] = 0.0
    out[k] = c


def speed_of(o):
    sp = sum(np.abs(np.diff(o[k], prepend=0)) for k in ('yaw', 'pitch', 'roll'))
    w = np.array([1, 2, 1], float) / 4
    return np.convolve(sp, w, mode='same')


# Normaliser: the whole flourish (frames 1177-1268), as the retired flourish curve did.
whole = {k: np.array([frames[1177 + i][k] * s if (1177 + i) in frames else 0.0 for i in range(92)]) for k, s in SCALE.items()}
peak = speed_of(whole).max()
blur = np.clip(speed_of(out) / peak * .85, 0.0, .85) * fade
json.dump(dict(samples=int(N), seconds=float(t[-1]), start_frame=START,
               yaw=np.round(out['yaw'], 2).tolist(), pitch=np.round(out['pitch'], 2).tolist(),
               roll=np.round(out['roll'], 2).tolist(), fov=np.round(out['fov'], 2).tolist(),
               blur=np.round(blur, 3).tolist()),
          open(os.path.join(d, 'thrust_curve.json'), 'w'), indent=1)
for k in ('yaw', 'pitch', 'roll', 'fov', ):
    c = out[k]
    i, j = int(np.argmax(c)), int(np.argmin(c))
    print('%5s max %+.2f @%.3f  min %+.2f @%.3f' % (k, c[i], t[i], c[j], t[j]))
print('blur', np.round(blur, 2).tolist())
