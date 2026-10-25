"""Track the tossed knife and the catching hand in the 抛刀 reference (BV1CeYUeSE7b 52.13-52.93).

Foreground = frame minus the empty-view frame (EMPTY, aligned by the background affine), then the knife pixels are
the saturated green/teal ones and the hand the rest of the foreground.  Per frame: knife centroid, principal axis
(angle, length) and its two extreme points, hand centroid and topmost point, all in NDC (x right, y down, [-1, 1]).
Writes Saved/Reference/.../equip_track.json and an overlay sheet sheets/equip_track_*.jpg for reading the result.
"""
import json
import math
import os

import cv2
import numpy as np

d = r"D:\FPS3D\FPSGAME\Saved\Reference\KukriBV1CeYUeSE7b20261020"
CLIP_START = 1564
EMPTY = 1567
FRAMES = range(1566, 1592)
H, W = 720, 1280


def load(i):
    return cv2.imread(os.path.join(d, "equip_frames", "f%05d.png" % i))


def ndc(x, y):
    return (round(2 * x / W - 1, 3), round(2 * y / H - 1, 3))


mask_bg = np.zeros((H, W), np.uint8)
mask_bg[90:int(H * 0.56), :] = 255
mask_bg[0:110, 0:260] = 0
mask_bg[0:80, 1000:] = 0
orb = cv2.ORB_create(4000)
bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
empty = load(EMPTY)
ke, de = orb.detectAndCompute(cv2.cvtColor(empty, cv2.COLOR_BGR2GRAY), mask_bg)
out, overlays = [], []
for i in FRAMES:
    im = load(i)
    g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
    k, dsc = orb.detectAndCompute(g, mask_bg)
    m = sorted(bf.match(de, dsc), key=lambda x: x.distance)[:500]
    A, _ = cv2.estimateAffinePartial2D(np.float32([ke[x.queryIdx].pt for x in m]),
                                       np.float32([k[x.trainIdx].pt for x in m]), method=cv2.RANSAC,
                                       ransacReprojThreshold=2)
    bg = cv2.warpAffine(empty, A, (W, H), borderMode=cv2.BORDER_REPLICATE)
    diff = cv2.absdiff(im, bg).max(axis=2)
    fg = (diff > 38).astype(np.uint8) * 255
    fg[0:110, 0:270] = 0
    fg[0:80, 1000:] = 0
    fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV)
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    knife = ((h >= 55) & (h <= 100) & (s >= 70) & (v >= 60)).astype(np.uint8) * 255
    # the blade's bright steel edge is unsaturated but very bright and inside the foreground
    knife |= ((s < 60) & (v > 200)).astype(np.uint8) * 255
    knife &= fg
    knife = cv2.morphologyEx(knife, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    hand = cv2.bitwise_and(fg, cv2.bitwise_not(cv2.dilate(knife, np.ones((5, 5), np.uint8))))
    rec = dict(frame=i, t=round((i - CLIP_START) / 30, 4))
    vis = im.copy()
    n, lab, stats, cent = cv2.connectedComponentsWithStats(knife)
    if n > 1:
        big = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        if stats[big, cv2.CC_STAT_AREA] > 150:
            # keep components close to the biggest one (the blade can split at the handle wrap)
            keep = np.zeros_like(knife)
            for c in range(1, n):
                if stats[c, cv2.CC_STAT_AREA] > 40 and np.linalg.norm(cent[c] - cent[big]) < 260:
                    keep[lab == c] = 255
            ys, xs = np.nonzero(keep)
            pts = np.column_stack([xs, ys]).astype(np.float64)
            c = pts.mean(axis=0)
            u, sv, vt = np.linalg.svd(pts - c, full_matrices=False)
            ax = vt[0]
            proj = (pts - c) @ ax
            p0, p1 = c + ax * proj.min(), c + ax * proj.max()
            ang = math.degrees(math.atan2(ax[1], ax[0]))
            rec.update(knife=dict(c=ndc(*c), a=ndc(*p0), b=ndc(*p1), angle=round(ang, 1),
                                  length_px=round(float(proj.max() - proj.min()), 1),
                                  width_px=round(float(2 * sv[1] / math.sqrt(len(pts)) * 2), 1),
                                  area=int(len(pts))))
            vis[keep > 0] = (0.4 * vis[keep > 0] + 0.6 * np.array([255, 255, 0])).astype(np.uint8)
            cv2.line(vis, tuple(map(int, p0)), tuple(map(int, p1)), (0, 0, 255), 2)
    n, lab, stats, cent = cv2.connectedComponentsWithStats(hand)
    if n > 1:
        big = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        if stats[big, cv2.CC_STAT_AREA] > 600:
            ys, xs = np.nonzero(lab == big)
            top = int(np.argmin(ys))
            rec.update(hand=dict(c=ndc(xs.mean(), ys.mean()), top=ndc(xs[top], ys[top]),
                                 left=ndc(xs.min(), ys[int(np.argmin(xs))]), area=int(len(xs))))
            vis[lab == big] = (0.5 * vis[lab == big] + 0.5 * np.array([255, 0, 255])).astype(np.uint8)
    out.append(rec)
    for kx in range(-4, 5):
        x = int((kx / 4 * .5 + .5) * W); y = int((kx / 4 * .5 + .5) * H)
        col = (0, 255, 255) if kx == 0 else (180, 180, 180)
        cv2.line(vis, (x, 0), (x, H), col, 1); cv2.line(vis, (0, y), (W, y), col, 1)
    cv2.putText(vis, "%d t=%.3f" % (i, rec['t']), (420, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)
    overlays.append(cv2.resize(vis, (640, 360)))
    print(json.dumps(rec))
json.dump(out, open(os.path.join(d, "equip_track.json"), "w"), indent=1)
for s in range(0, len(overlays), 9):
    chunk = overlays[s:s + 9]
    while len(chunk) % 3:
        chunk.append(np.zeros_like(chunk[0]))
    cv2.imwrite(os.path.join(d, "sheets", "equip_track_%d.jpg" % (s // 9)),
                np.vstack([np.hstack(chunk[r:r + 3]) for r in range(0, len(chunk), 3)]), [cv2.IMWRITE_JPEG_QUALITY, 82])
