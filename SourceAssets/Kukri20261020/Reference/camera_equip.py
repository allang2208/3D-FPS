"""Camera motion of the reference toss-and-catch draw (切刀 #5, BV1CeYUeSE7b 52.13-52.83) by background registration.

Same method as camera_atk1.py / camera_atk2.py: ORB features on the background band (logos and the lower viewmodel
area masked; the flying knife is rejected by RANSAC), a partial affine per frame against the still frame before the
draw, then the screen-centre displacement, rotation and scale converted to this game's camera (75 deg vertical FOV,
16:9) so the on-screen motion matches:
  yaw   = atan(-dx / (W/2) * tan(hfov/2))     (+ right)
  pitch = atan( dy / (H/2) * tan(vfov/2))     (+ up: the background moves down)
  roll  = -rot                                (+ clockwise, UE)
  fov   = 2 atan(tan(vfov/2) / scale) - vfov  (scale > 1 = zoom in)
Writes Saved/Reference/.../equip_camera.json (raw + converted, 30 Hz, t = 0 at CLIP_START)."""
import json
import math
import os

import cv2
import numpy as np

d = r"D:\FPS3D\FPSGAME\Saved\Reference\KukriBV1CeYUeSE7b20261020"
CLIP_START = 1564          # 52.133 s: first frame of 切刀 #5 (the previous knife is gone, empty view)
REF = 1562                 # still frame before the draw
FIRST, LAST = 1558, 1610
VFOV = 75.0
TV = math.tan(math.radians(VFOV) / 2)
TH = TV * 16 / 9


def load(i):
    return cv2.imread(os.path.join(d, "equip_frames", "f%05d.png" % i), cv2.IMREAD_GRAYSCALE)


H, W = 720, 1280
mask = np.zeros((H, W), np.uint8)
mask[90:int(H * 0.56), :] = 255
mask[0:110, 0:260] = 0
mask[0:80, 1000:] = 0
orb = cv2.ORB_create(4000)
kr, dr = orb.detectAndCompute(load(REF), mask)
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
json.dump(dict(clip_start=CLIP_START, ref=REF, frames=out), open(os.path.join(d, "equip_camera.json"), "w"), indent=1)
