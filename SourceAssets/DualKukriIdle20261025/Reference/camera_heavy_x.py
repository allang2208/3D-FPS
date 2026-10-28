"""Camera motion of the reference X double chop (近战动作 #3「X」, BV19dUqBJECT 78.20-79.30 s; the user said 1:19-1:20), used for
the dual kukri heavy release (DualHeavyRelease).  Same method and conversion as camera_thrust.py (the double thrust).

Method of SourceAssets/Kukri20261020/Reference/camera_sprint.py: ORB + partial affine (RANSAC) on the scenery above the
viewmodel; frames that still share enough features with the stance frame are fitted to it directly, the gaps are bridged
with chained frame-to-frame steps linearly corrected to both direct fits.  The mask drops the chapter title and move label
(top left), the watermark (top right) and a centre box (the target dummy and the hit burst).  The player lunges ~2 m at
the dummy (the thrust; the X chop stands still), so the scale change of the 15-30 m scenery is part dolly; conversion to
this game's camera (75 deg vertical
FOV, 16:9), screen-equivalent:
  yaw   = atan(-dx / (W/2) * tan(hfov/2))     (+ right)
  pitch = atan( dy / (H/2) * tan(vfov/2))     (+ up: the background moves down)
  roll  = -rot                                (+ clockwise, UE)
  fov   = 2 atan(tan(vfov/2) / scale) - vfov  (scale > 1 = zoom in)
Writes Saved/Reference/DualKukriBV19dUqBJECT20261025/heavy_x_camera.json (t = 0 at CLIP_START).
Frames: python -c "import imageio_ffmpeg" ... -ss 76.5 -t 5.0 -i ref_1080.mp4 -vsync 0 -start_number 2295 heavy_frames/f%05d.png
"""
import json
import math
import os

import cv2
import numpy as np

d = r"D:\FPS3D\FPSGAME\Saved\Reference\DualKukriBV19dUqBJECT20261025"
CLIP_START = 2345          # 78.167 s: last stance frame before the move
FIRST, LAST = 2338, 2385
VFOV = 75.0
TV = math.tan(math.radians(VFOV) / 2)
TH = TV * 16 / 9
H, W = 720, 1280


def load(i):
    im = cv2.imread(os.path.join(d, "heavy_frames", "f%05d.png" % i), cv2.IMREAD_GRAYSCALE)
    return cv2.resize(im, (W, H), interpolation=cv2.INTER_AREA)


def mask_for():
    m = np.zeros((H, W), np.uint8)
    m[0:int(H * 0.50), :] = 255
    m[0:150, 0:380] = 0        # chapter title + move label
    m[0:80, 980:] = 0          # watermark
    m[:, 500:780] = 0          # target dummy / hit burst (centre band)
    return m


orb = cv2.ORB_create(4000)
bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
M = mask_for()
ANCHOR_INLIERS = 200


def fit(kp_a, d_a, kp_b, d_b):
    if d_a is None or d_b is None:
        return None, 0
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
res = []
for i in range(anchors[0], LAST + 1):
    dx, dy, rot, lsc = value[i]
    sc = math.exp(lsc)
    e = dict(frame=i, t=round((i - CLIP_START) / 30, 4), inl=source[i], dx=round(dx, 2), dy=round(dy, 2), rot=round(rot, 3),
             scale=round(sc, 4), yaw=round(math.degrees(math.atan(-dx / (W / 2) * TH)), 3),
             pitch=round(math.degrees(math.atan(dy / (H / 2) * TV)), 3), roll=round(-rot, 3),
             fov=round(2 * math.degrees(math.atan(TV / sc)) - VFOV, 3))
    res.append(e)
    print("%d t=%+.3f yaw %+6.2f pitch %+6.2f roll %+6.2f fov %+6.2f scale %.3f | %s" % (
        e['frame'], e['t'], e['yaw'], e['pitch'], e['roll'], e['fov'], sc, e['inl']))
json.dump(dict(clip_start=CLIP_START, method='direct fits to the stance frame, gaps bridged by corrected chained steps', frames=res),
          open(os.path.join(d, "heavy_x_camera.json"), "w"), indent=1)
