"""Camera motion of reference crouch melee #5 戳 (stab), BV1CeYUeSE7b 1:34.77-1:36.0, by frame-to-frame optical flow.

camera_atk1.py's single-reference ORB registration fails on this clip: the firing range repeats identical target
boards, so a stance-frame descriptor matches the neighbouring board once the view lunges in (it reported a
9-12 deg FOV widening where the boards plainly grow ~10 %), and in the drive/contact frames RANSAC locked onto
static overlay text.  Here corners on the background band (dummy column, hit flash, title, watermark and the
viewmodel band masked) are tracked frame to frame with pyramidal LK and a forward-backward check, a similarity
transform is fitted per step (RANSAC) and the steps are chained back to the stance frame.  Consecutive frames move
little, so the repeated boards cannot be confused.  Where a step has too few points (contact blur), the step is
fitted against the frame before the previous one instead.
Conversion to this game's camera (75 deg vertical FOV, 16:9), same as camera_atk1.py:
  yaw   = atan(-dx / (W/2) * tan(hfov/2))     (+ right)
  pitch = atan( dy / (H/2) * tan(vfov/2))     (+ up: the background moves down)
  roll  = -rot                                (+ clockwise, UE)
  fov   = 2 atan(tan(vfov/2) / scale) - vfov  (scale > 1 = the view closes in: the lunge)
Writes Saved/Reference/.../atk3_camera.json (30 Hz, t = 0 at CLIP_START = frame 2843, 94.767 s)."""
import json
import math
import os

import cv2
import numpy as np

d = r"D:\FPS3D\FPSGAME\Saved\Reference\KukriBV1CeYUeSE7b20261020"
CLIP_START = 2843
FIRST, LAST = 2840, 2885      # 2838-2839 are still the previous chapter (#4)
VFOV = 75.0
TV = math.tan(math.radians(VFOV) / 2)
TH = TV * 16 / 9
W, H = 1280, 720


def load(i):
    return cv2.imread(os.path.join(d, "atk3_frames", "f%05d.png" % i), cv2.IMREAD_GRAYSCALE)


def mask_for(i):
    m = np.zeros((H, W), np.uint8)
    m[40:470, :] = 255
    m[0:140, 0:340] = 0                    # chapter title
    m[0:80, 1000:] = 0                     # watermark
    m[:, 500:800] = 0                      # dummy column (it lunges at the lens and is knocked away)
    if 2852 <= i <= 2860:
        m[:, 300:1000] = 0                 # contact: hit flash and the dummy fill the middle
        m[200:, 0:520] = 0                 # forearm from the lower left
    return m


def step(a, b, ia):
    """Similarity transform mapping frame a's pixels to frame b's (LK with forward-backward check)."""
    p0 = cv2.goodFeaturesToTrack(a, 1500, 0.01, 7, mask=mask_for(ia))
    if p0 is None:
        return None, 0
    lk = dict(winSize=(31, 31), maxLevel=4, criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 40, 0.01))
    p1, st, _ = cv2.calcOpticalFlowPyrLK(a, b, p0, None, **lk)
    p0r, st2, _ = cv2.calcOpticalFlowPyrLK(b, a, p1, None, **lk)
    fb = np.linalg.norm((p0 - p0r).reshape(-1, 2), axis=1)
    good = (st.ravel() == 1) & (st2.ravel() == 1) & (fb < 1.0)
    if good.sum() < 12:
        return None, int(good.sum())
    A, inl = cv2.estimateAffinePartial2D(p0[good], p1[good], method=cv2.RANSAC, ransacReprojThreshold=2.0)
    return A, int(inl.sum()) if inl is not None else 0


def h3(A):
    return np.vstack([A, [0, 0, 1]])


acc = {FIRST: np.eye(3)}
info = {}
for i in range(FIRST + 1, LAST + 1):
    A, n = step(load(i - 1), load(i), i - 1)
    src = i - 1
    if A is None or n < 25:
        A2, n2 = step(load(i - 2), load(i), i - 2)
        if A2 is not None and n2 > n:
            A, n, src = A2, n2, i - 2
    if A is None:
        acc[i] = acc[i - 1]
        info[i] = dict(n=n, src=src, held=True)
        continue
    acc[i] = h3(A) @ acc[src]
    info[i] = dict(n=n, src=src)

# Refinement: the chain drifts through the blurred contact frames (it does not come back to the stance, which the
# end frames plainly do).  Every frame is therefore aligned directly to the stance frame: a similarity is optimised
# for the normalised cross-correlation between the stance frame and the frame warped back, over the background
# band (blurred harder through the contact), seeded with the chain and with the previous frame's solution.
# Checked at 2849/2852: the free fit lands on the chain's rotation sign and scale (corr 0.86/0.77), a
# sign-flipped candidate scores 0.70/0.52.  Only the far background on the left is used: the player lunges ~2 m at
# the dummy (it grows ~2.5x in 0.3 s), and the near building on the right then parallaxes outwards -- a fit that
# includes it reads the lunge as a 5 % zoom-in, the far left shows the actual 3-4 deg FOV widening of the move.
# Rotation and FOV come from this file; the lunge is approximated by a short camera push (KukriRhythm::StabCamera).
from scipy.optimize import minimize


def blurred(i, sigma):
    return cv2.GaussianBlur(load(i).astype(np.float32) / 255, (0, 0), sigma)


def ncc_mask(i):
    m = np.zeros((H, W), bool)
    m[40:440, 0:470] = True                # far background on the left (rocks, far boards)
    m[0:140, 0:340] = False
    m[0:80, 1000:] = False
    if 2852 <= i <= 2857:
        m[:, 330:] = False                 # dummy, flash and forearm: left background only
    return m


def sim(v):
    rot, sc, dx, dy = v
    t = math.radians(rot)
    a, b = sc * math.cos(t), sc * math.sin(t)
    M = np.array([[a, -b, 0], [b, a, 0]], np.float64)
    cc = np.array([W / 2, H / 2])
    M[:, 2] = cc + np.array([dx, dy]) - M[:, :2] @ cc
    return M


def params(M):
    rot = math.degrees(math.atan2(M[1, 0], M[0, 0]))
    sc = math.hypot(M[0, 0], M[1, 0])
    cd = M[:2, :2] @ np.array([W / 2, H / 2]) + M[:2, 2] - np.array([W / 2, H / 2])
    return np.array([rot, sc, cd[0], cd[1]])


direct = {}
seed = np.array([0.0, 1.0, 0.0, 0.0])
for i in range(FIRST, LAST + 1):
    sigma = 4.0 if 2852 <= i <= 2857 else 2.0
    ref_b, fr_b, m = blurred(CLIP_START, sigma), blurred(i, sigma), ncc_mask(i)
    a = ref_b[m] - ref_b[m].mean()

    def cost(v):
        w = cv2.warpAffine(fr_b, cv2.invertAffineTransform(sim(v).astype(np.float32)), (W, H))
        b = w[m] - w[m].mean()
        return -float((a * b).sum() / math.sqrt((a * a).sum() * (b * b).sum() + 1e-12))
    best = None
    for s0 in (seed, params(acc[i] @ np.linalg.inv(acc[CLIP_START]))):
        for jitter in ((0, 0, 0, 0), (2, 0, 15, 0), (-2, 0, -15, 0), (0, .04, 0, 15), (0, -.04, 0, -15)):
            r = minimize(cost, np.asarray(s0) + jitter, method='Nelder-Mead',
                         options=dict(xatol=.02, fatol=1e-5, maxiter=600, initial_simplex=None))
            if best is None or r.fun < best.fun:
                best = r
    direct[i] = (sim(best.x), -best.fun)
    seed = best.x

out = []
c = np.array([W / 2, H / 2, 1.0])
for i in range(FIRST, LAST + 1):
    M = np.vstack([direct[i][0], [0, 0, 1]])
    info.setdefault(i, {})['corr'] = round(direct[i][1], 3)
    rot = math.degrees(math.atan2(M[1, 0], M[0, 0]))
    sc = math.hypot(M[0, 0], M[1, 0])
    cd = (M @ c)[:2] - c[:2]
    dx, dy = float(cd[0]), float(cd[1])
    r = dict(frame=i, t=round((i - CLIP_START) / 30, 4), ok=True, rot=round(rot, 3), scale=round(sc, 4),
             dx=round(dx, 1), dy=round(dy, 1), **info.get(i, dict(n=0, src=i)),
             yaw=round(math.degrees(math.atan(-dx / (W / 2) * TH)), 3),
             pitch=round(math.degrees(math.atan(dy / (H / 2) * TV)), 3),
             roll=round(-rot, 3),
             fov=round(2 * math.degrees(math.atan(TV / sc)) - VFOV, 3))
    out.append(r)
    print('%5d t=%6.3f yaw %6.2f pitch %6.2f roll %6.2f fov %6.2f scale %.3f corr %.3f' % (
        i, r['t'], r['yaw'], r['pitch'], r['roll'], r['fov'], sc, r['corr']), flush=True)
json.dump(dict(clip_start=CLIP_START, ref=FIRST, method='direct NCC to the stance frame, LK chain seed', frames=out), open(os.path.join(d, "atk3_camera.json"), "w"), indent=1)
