"""Camera motion of the reference toss-and-catch (#2 抛, BV1pqkyYyEDY 38.70-39.60) by background registration.

Same method as Kukri20261020/Reference/camera_equip.py: ORB features on the background band (title card, watermark and
the lower viewmodel area masked; the axe and arm are rejected by RANSAC), a partial affine per frame against the still
frame before the draw, converted to this game's camera (75 deg vertical FOV, 16:9, screen-equivalent):
  yaw = atan(-dx / (W/2) * tan(hfov/2)) (+ right), pitch = atan(dy / (H/2) * tan(vfov/2)) (+ up),
  roll = -rot (+ clockwise), fov = 2 atan(tan(vfov/2) / scale) - vfov.
Writes Saved/Reference/HatchetBV1pqkyYyEDY20261102/camera.json (30 Hz, t = 0 at CLIP_START).
"""
import json
import math
from pathlib import Path

import cv2
import numpy as np

REF_DIR = Path(r"D:\FPS3D\FPSGAME\Saved\Reference\HatchetBV1pqkyYyEDY20261102")
CLIP_START = 1161          # 38.700 s: empty view, the right forearm comes in on the next frame
STILL = 1160
FIRST, LAST = 1150, 1205
VFOV = 75.0
TV = math.tan(math.radians(VFOV) / 2)
TH = TV * 16 / 9


def load(i):
    im = cv2.imread(str(REF_DIR / 'frames' / ('f%05d.png' % i)), cv2.IMREAD_GRAYSCALE)
    return None if im is None else cv2.resize(im, (1280, 720), interpolation=cv2.INTER_AREA)


H, W = 720, 1280
mask = np.zeros((H, W), np.uint8)
mask[60:int(H * 0.56), :] = 255
mask[0:110, 0:260] = 0          # title card
mask[0:80, 1000:] = 0           # watermark
orb = cv2.ORB_create(4000)
kr, dr = orb.detectAndCompute(load(STILL), mask)
bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
out = []
for i in range(FIRST, LAST + 1):
    img = load(i)
    if img is None:
        continue
    k, dsc = orb.detectAndCompute(img, mask)
    m = sorted(bf.match(dr, dsc), key=lambda x: x.distance)[:500]
    src = np.float32([kr[x.queryIdx].pt for x in m])
    dst = np.float32([k[x.trainIdx].pt for x in m])
    A, inl = cv2.estimateAffinePartial2D(src, dst, method=cv2.RANSAC, ransacReprojThreshold=2)
    if A is None:
        out.append(dict(frame=i, t=round((i - CLIP_START) / 30, 4), ok=False))
        continue
    rot = math.degrees(math.atan2(A[1, 0], A[0, 0]))
    sc = math.hypot(A[0, 0], A[1, 0])
    c = np.array([W / 2, H / 2, 1.0])
    cd = A @ c - c[:2]
    dx, dy = float(cd[0]), float(cd[1])
    out.append(dict(frame=i, t=round((i - CLIP_START) / 30, 4), ok=True, rot=round(rot, 3), scale=round(sc, 4),
                    dx=round(dx, 2), dy=round(dy, 2), inl=int(inl.sum()),
                    yaw=round(math.degrees(math.atan(-dx / (W / 2) * TH)), 3),
                    pitch=round(math.degrees(math.atan(dy / (H / 2) * TV)), 3),
                    roll=round(-rot, 3),
                    fov=round(2 * math.degrees(math.atan(TV / sc)) - VFOV, 3)))
for r in out:
    if r['ok']:
        print("%d t=%+.3f yaw %+6.2f pitch %+6.2f roll %+6.2f fov %+6.2f | dx %+6.1f dy %+6.1f inl %d" % (
            r['frame'], r['t'], r['yaw'], r['pitch'], r['roll'], r['fov'], r['dx'], r['dy'], r['inl']))
    else:
        print(r)
(REF_DIR / 'camera.json').write_text(json.dumps(dict(clip_start=CLIP_START, still=STILL, frames=out), indent=1), encoding='utf-8')
