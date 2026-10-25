"""Camera motion of the reference heavy-strike source (近战动作（跳跃）#12 ↙), BV1CeYUeSE7b 115.50-117.20 s, t = 0 at frame
3468 (the last stance frame before the raise).

Same method as camera_upper.py / contact_atk3.py: each frame is aligned directly to the stance frame by a similarity
transform that maximises the normalised cross-correlation on the far band only (towers, sky line, far boards), with a
coarse multi-start search before the Nelder-Mead refinement.  Masks follow the arms and the effect:
  0.07-0.17  the right fist rises to the upper right, the left forearm comes in from the lower left;
  0.20-0.30  the open left hand reaches into the centre and sweeps out to the lower left;
  0.37       the cocked right forearm stands at the right edge;
  0.40-0.80  the green slash trail runs from the top right to the bottom left, hit flash at the centre;
  1.03-1.40  the right arm comes back from the bottom right into the stance.
The player jumps, so the near ground and side boxes parallax; only the upper band is used.
Writes Saved/Reference/.../heavy_camera.json; curve_heavy.py turns it into KukriRhythm::Heavy* curves.
Frames come from extract_heavy.py."""
import json
import math
import os

import cv2
import numpy as np
from scipy.optimize import minimize

d = r"D:\FPS3D\FPSGAME\Saved\Reference\KukriBV1CeYUeSE7b20261020"
T0 = 3468
W, H = 1280, 720
TV = math.tan(math.radians(75.0) / 2)
TH = TV * 16 / 9


def blurred(i, s):
    im = cv2.imread(os.path.join(d, "heavy_frames", "f%05d.png" % i), cv2.IMREAD_GRAYSCALE).astype(np.float32) / 255
    return cv2.GaussianBlur(im, (0, 0), s)


def mask_for(i):
    t = (i - T0) / 30
    m = np.zeros((H, W), bool)
    m[40:330, :] = True
    m[0:150, 0:340] = False          # chapter title
    m[0:80, 1000:] = False           # watermark
    m[:, 560:720] = False            # the dummy column
    if 0.05 <= t <= 0.40:
        m[:, 760:] = False           # the raised right fist / cocked forearm on the right
    if 0.18 <= t <= 0.32:
        m[150:, 0:640] = False       # the open left hand reaching into the centre
    if 0.39 <= t <= 0.85:
        m[:, 380:1000] = False       # slash trail and hit flash through the middle
        m[:, 1000:] = m[:, 1000:] & (np.arange(H)[:, None] > 200)   # the trail's top-right end
    return m


def sim(v):
    rot, sc, dx, dy = v
    a = math.radians(rot)
    A = np.array([[sc * math.cos(a), -sc * math.sin(a), 0], [sc * math.sin(a), sc * math.cos(a), 0]])
    c = np.array([W / 2, H / 2])
    A[:, 2] = c + np.array([dx, dy]) - A[:, :2] @ c
    return A


if __name__ == "__main__":
    ref = blurred(T0, 3.0)
    out = []
    seed = np.array([0.0, 1.0, 0.0, 0.0])
    for i in range(T0 - 3, T0 + 48):
        m = mask_for(i)
        a = ref[m] - ref[m].mean()
        fr = blurred(i, 3.0)

        def cost(v):
            w = cv2.warpAffine(fr, cv2.invertAffineTransform(sim(v).astype(np.float32)), (W, H))
            b = w[m] - w[m].mean()
            return -float((a * b).sum() / math.sqrt((a * a).sum() * (b * b).sum() + 1e-12))
        seeds = [seed] + [np.array(s) for s in ((r, s, x, y) for r in (-10, 0, 10) for s in (.92, 1.0, 1.08)
                                                 for x in (-50, 0, 50) for y in (-60, 0, 60))]
        scored = sorted(seeds, key=cost)[:5]
        best = min((minimize(cost, s0, method='Nelder-Mead', options=dict(xatol=.02, fatol=1e-5, maxiter=800)) for s0 in scored),
                   key=lambda r: r.fun)
        seed = best.x
        rot, sc, dx, dy = best.x
        r = dict(frame=i, t=round((i - T0) / 30, 4), corr=round(-best.fun, 3), rot=round(rot, 2), scale=round(sc, 4),
                 dx=round(dx, 1), dy=round(dy, 1), yaw=round(math.degrees(math.atan(-dx / (W / 2) * TH)), 2),
                 pitch=round(math.degrees(math.atan(dy / (H / 2) * TV)), 2), roll=round(-rot, 2),
                 fov=round(2 * math.degrees(math.atan(TV / sc)) - 75.0, 2))
        out.append(r)
        print('%d t=%.3f corr %.3f yaw %6.2f pitch %6.2f roll %6.2f fov %6.2f' % (i, r['t'], r['corr'], r['yaw'], r['pitch'], r['roll'], r['fov']), flush=True)
    json.dump(dict(clip_start=T0, method='far-band direct NCC', frames=out), open(os.path.join(d, "heavy_camera.json"), "w"), indent=1)
