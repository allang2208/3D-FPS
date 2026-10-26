"""Camera motion of the reference knife flourish (BV1hQnh6hEio, file 39.0-43.5 s, frames 1170-1305),
used for the pistol+offhand-kukri quick melee.

Same method as Kukri20261020/Reference/camera_pommel.py: direct fits against the stance frame where enough
features survive, frame-to-frame chained steps bridged across the blurred slashes, linearly corrected between
anchors. The mask keeps the scenery above the swinging arms and drops the chapter title (top left) and the
watermark (top right). During the slashes the left arm and knife cross the centre, so the centre band below
mid frame is masked too. Conversion to this game's camera (75 deg vertical FOV, 16:9), screen-equivalent:
  yaw   = atan(-dx / (W/2) * tan(hfov/2))     (+ right)
  pitch = atan( dy / (H/2) * tan(vfov/2))     (+ up: the background moves down)
  roll  = -rot                                (+ clockwise, UE)
  fov   = 2 atan(tan(vfov/2) / scale) - vfov  (scale > 1 = zoom in)
Writes Saved/Reference/.../melee_camera.json (t = 0 at CLIP_START)."""
import json
import math
import os

import cv2
import numpy as np

d = r"D:\FPS3D\FPSGAME\Saved\Reference\DualPistolKukriBV1hQnh6hEio20261025"
CLIP_START = 1177          # 39.233 s: last stance frame before the left arm starts the flourish
FIRST, LAST = 1155, 1305
VFOV = 75.0
TV = math.tan(math.radians(VFOV) / 2)
TH = TV * 16 / 9
H, W = 720, 1280


def load(i):
    return cv2.imread(os.path.join(d, "idle_frames", "f%05d.png" % i), cv2.IMREAD_GRAYSCALE)


def mask_for():
    m = np.zeros((H, W), np.uint8)
    m[0:int(H * 0.52), :] = 255      # scenery above the viewmodel / sweeping arm
    m[0:110, 0:420] = 0              # chapter title + move label
    m[0:80, 980:] = 0                # watermark
    m[int(H * 0.30):int(H * 0.52), 430:850] = 0   # the blade/hand crossing the centre band
    return m


orb = cv2.ORB_create(4000)
bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
M = mask_for()
ANCHOR_INLIERS = 200       # a direct fit against the stance frame is trusted from this many inliers


def fit(kp_a, d_a, kp_b, d_b):
    m = sorted(bf.match(d_a, d_b), key=lambda x: x.distance)[:600]
    if len(m) < 30:
        return None, 0
    A, inl = cv2.estimateAffinePartial2D(np.float32([kp_a[x.queryIdx].pt for x in m]), np.float32([kp_b[x.trainIdx].pt for x in m]),
                                         method=cv2.RANSAC, ransacReprojThreshold=2.5)
    return (None, 0) if A is None else (np.vstack([A, [0, 0, 1]]), int(inl.sum()))


def params(A):
    c = np.array([W / 2, H / 2, 1.0])
    cd = (A @ c)[:2] - c[:2]
    return np.array([cd[0], cd[1], math.degrees(math.atan2(A[1, 0], A[0, 0])), math.log(math.hypot(A[0, 0], A[1, 0]))])


feats = {i: orb.detectAndCompute(load(i), M) for i in range(FIRST, LAST + 1)}
kr, dr = feats[CLIP_START]
direct, chain, acc = {}, {}, np.eye(3)
for i in range(FIRST, LAST + 1):
    A, n = fit(kr, dr, *feats[i])
    if A is not None and n >= ANCHOR_INLIERS:
        direct[i] = (params(A), n)
    if i > FIRST:
        B, nb = fit(*feats[i - 1], *feats[i])
        acc = (B if B is not None else np.eye(3)) @ acc
    chain[i] = params(acc)
direct[CLIP_START] = (np.zeros(4), 9999)
anchors = sorted(direct)
value, source = {}, {}
for i in anchors:
    value[i], source[i] = direct[i][0], 'direct %d' % direct[i][1]
for a, b in zip(anchors, anchors[1:]):
    if b - a <= 1:
        continue
    err = (direct[b][0] - direct[a][0]) - (chain[b] - chain[a])
    for i in range(a + 1, b):
        f = (i - a) / (b - a)
        value[i] = direct[a][0] + (chain[i] - chain[a]) + err * f
        source[i] = 'chain %d-%d' % (a, b)
for i in range(anchors[-1] + 1, LAST + 1):
    value[i], source[i] = direct[anchors[-1]][0] + chain[i] - chain[anchors[-1]], 'chain from %d' % anchors[-1]
out = []
for i in range(anchors[0], LAST + 1):
    dx, dy, rot, lsc = value[i]
    out.append(dict(frame=i, ok=True, inl=source[i], dx=dx, dy=dy, rot=rot, scale=math.exp(lsc)))
res = []
for r in out:
    dx, dy, rot, sc = r['dx'], r['dy'], r['rot'], r['scale']
    e = dict(frame=r['frame'], t=round((r['frame'] - CLIP_START) / 30, 4), ok=r['ok'], inl=r['inl'],
             dx=round(dx, 2), dy=round(dy, 2), rot=round(rot, 3), scale=round(sc, 4),
             yaw=round(math.degrees(math.atan(-dx / (W / 2) * TH)), 3), pitch=round(math.degrees(math.atan(dy / (H / 2) * TV)), 3),
             roll=round(-rot, 3), fov=round(2 * math.degrees(math.atan(TV / sc)) - VFOV, 3))
    res.append(e)
    print("%d t=%+.3f yaw %+6.2f pitch %+6.2f roll %+6.2f fov %+6.2f | %s" % (
        e['frame'], e['t'], e['yaw'], e['pitch'], e['roll'], e['fov'], e['inl']))
json.dump(dict(clip_start=CLIP_START, method='direct fits to the stance frame, gaps bridged by corrected chained steps', frames=res),
          open(os.path.join(d, "melee_camera.json"), "w"), indent=1)
