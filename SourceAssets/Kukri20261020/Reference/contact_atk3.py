"""Camera of the reference stab from the farthest background only.  track_atk3.py's far-left band is partly covered
by the forearm, the cocked blade and the hit flash in the contact frames (2852-2860, t 0.30-0.57), and its mid-depth
boards parallax with the ~2 m lunge, so every frame 2843-2885 is aligned to the stance frame on the upper
left only (rocks, small boards, beams: y 40-330 px, x 0-330 px, below the chapter title), with a coarse multi-start
search (rotation +-16 deg, vertical shift +-140 px) before the NCC refinement.  Output merged into atk3_camera.json
as 'far' entries (same conversion as track_atk3.py); curve_atk3.py reads them."""
import json
import math
import os

import cv2
import numpy as np
from scipy.optimize import minimize

d = r"D:\FPS3D\FPSGAME\Saved\Reference\KukriBV1CeYUeSE7b20261020"
W, H = 1280, 720
TV = math.tan(math.radians(75.0) / 2)
TH = TV * 16 / 9


def blurred(i, s):
    im = cv2.imread(os.path.join(d, "atk3_frames", "f%05d.png" % i), cv2.IMREAD_GRAYSCALE).astype(np.float32) / 255
    return cv2.GaussianBlur(im, (0, 0), s)


m = np.zeros((H, W), bool)
m[40:330, 0:330] = True
m[0:150, 0:340] = False
m[40:150, 340:470] = True
ref = blurred(2843, 3.0)
a = ref[m] - ref[m].mean()


def sim(v):
    rot, sc, dx, dy = v
    t = math.radians(rot)
    A = np.array([[sc * math.cos(t), -sc * math.sin(t), 0], [sc * math.sin(t), sc * math.cos(t), 0]])
    c = np.array([W / 2, H / 2])
    A[:, 2] = c + np.array([dx, dy]) - A[:, :2] @ c
    return A


out = {}
for i in range(2843, 2886):
    fr = blurred(i, 3.0)

    def cost(v):
        w = cv2.warpAffine(fr, cv2.invertAffineTransform(sim(v).astype(np.float32)), (W, H))
        b = w[m] - w[m].mean()
        return -float((a * b).sum() / math.sqrt((a * a).sum() * (b * b).sum() + 1e-12))
    seeds = [(r, s, x, y) for r in (-12, -6, 0, 6, 12) for s in (.85, .95, 1.05) for x in (-60, 0, 60) for y in (-80, 0, 80, 140)]
    scored = sorted(seeds, key=cost)[:6]
    best = min((minimize(cost, s0, method='Nelder-Mead', options=dict(xatol=.02, fatol=1e-5, maxiter=800)) for s0 in scored),
               key=lambda r: r.fun)
    rot, sc, dx, dy = best.x
    out[i] = dict(frame=i, t=round((i - 2843) / 30, 4), corr=round(-best.fun, 3), rot=round(rot, 2), scale=round(sc, 4),
                  dx=round(dx, 1), dy=round(dy, 1), yaw=round(math.degrees(math.atan(-dx / (W / 2) * TH)), 2),
                  pitch=round(math.degrees(math.atan(dy / (H / 2) * TV)), 2), roll=round(-rot, 2),
                  fov=round(2 * math.degrees(math.atan(TV / sc)) - 75.0, 2))
    r = out[i]
    print('%d t=%.3f corr %.3f yaw %6.2f pitch %6.2f roll %6.2f fov %6.2f' % (i, r['t'], r['corr'], r['yaw'], r['pitch'], r['roll'], r['fov']), flush=True)
p = os.path.join(d, "atk3_camera.json")
data = json.load(open(p))
data['far'] = list(out.values())
json.dump(data, open(p, "w"), indent=1)
