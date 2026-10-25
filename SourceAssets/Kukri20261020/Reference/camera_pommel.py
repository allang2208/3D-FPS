"""Camera motion of the reference pommel strike (近战动作 #3 刀把, BV1CeYUeSE7b 89.73-90.93), used for the
kukri quick melee.

The jump moves the view a lot and the hit flash covers the centre.  Frames that still share enough features with the
stance frame are fitted to it directly (camera_atk1/atk2/equip.py method); the frames in between are bridged with
frame-to-frame steps (ORB + partial affine, RANSAC), chained and linearly corrected so they meet both direct fits.  The mask keeps the scenery above the viewmodel and drops the chapter title (top
left, wider than in the earlier chapters), the watermark (top right) and a centre box where the hit flash and the
target dummy sit.  Conversion to this game's camera (75 deg vertical FOV, 16:9), screen-equivalent:
  yaw   = atan(-dx / (W/2) * tan(hfov/2))     (+ right)
  pitch = atan( dy / (H/2) * tan(vfov/2))     (+ up: the background moves down)
  roll  = -rot                                (+ clockwise, UE)
  fov   = 2 atan(tan(vfov/2) / scale) - vfov  (scale > 1 = zoom in)
Vertical camera travel of the jump shows up as pitch here (the background is 10-30 m away).
Writes Saved/Reference/.../pommel_camera.json (t = 0 at CLIP_START)."""
import json
import math
import os

import cv2
import numpy as np

d = r"D:\FPS3D\FPSGAME\Saved\Reference\KukriBV1CeYUeSE7b20261020"
CLIP_START = 2692          # 89.733 s: last stance frame before the pommel strike
FIRST, LAST = 2688, 2730
VFOV = 75.0
TV = math.tan(math.radians(VFOV) / 2)
TH = TV * 16 / 9
H, W = 720, 1280


def load(i):
    return cv2.imread(os.path.join(d, "pommel_frames", "f%05d.png" % i), cv2.IMREAD_GRAYSCALE)


def mask_for():
    m = np.zeros((H, W), np.uint8)
    m[0:int(H * 0.62), :] = 255
    m[0:130, 0:430] = 0        # chapter title + move label
    m[0:80, 980:] = 0          # watermark
    m[:, 500:780] = 0          # hit flash beam / target dummy (whole centre band)
    return m


orb = cv2.ORB_create(4000)
bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
M = mask_for()
ANCHOR_INLIERS = 220       # a direct fit against the stance frame is trusted from this many inliers


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
# Bridge every gap between trusted direct fits with the chained increments, linearly corrected to both anchors.
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
# After the last direct fit the chain carries on uncorrected (the player lands further forward, so the view never
# returns to the stance frame).
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
          open(os.path.join(d, "pommel_camera.json"), "w"), indent=1)
