"""Probe: segment the reference axe's cyan blade by colour; writes mask overlays for a few frames (sheets/mask_*.jpg)
and prints centroid / area / principal axis in NDC (x right, y down)."""
import sys
from pathlib import Path

import cv2
import numpy as np

REF = Path(r"D:\FPS3D\FPSGAME\Saved\Reference\HatchetBV1pqkyYyEDY20261102")
LO = np.array([int(v) for v in (sys.argv[3] if len(sys.argv) > 3 else '86,110,110').split(',')])
HI = np.array([int(v) for v in (sys.argv[4] if len(sys.argv) > 4 else '104,255,255').split(',')])


def blade(im):
    hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV)
    m = cv2.inRange(hsv, LO, HI)
    m[: int(im.shape[0] * 0.09), : int(im.shape[1] * 0.22)] = 0       # title card
    m[: int(im.shape[0] * 0.07), int(im.shape[1] * 0.78):] = 0          # watermark
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    n, lab, st, cen = cv2.connectedComponentsWithStats(m)
    if n <= 1:
        return m, None
    k = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    keep = (lab == k).astype(np.uint8) * 255
    return keep, st[k]


def main():
    a, b = int(sys.argv[1]), int(sys.argv[2])
    cells = []
    for i in range(a, b + 1):
        im = cv2.imread(str(REF / 'frames' / ('f%05d.png' % i)))
        h, w = im.shape[:2]
        m, st = blade(im)
        ys, xs = np.nonzero(m)
        if len(xs):
            cx, cy = xs.mean(), ys.mean()
            print('%d %.3f area %6d centroid ndc (%.3f, %.3f) bbox x %.2f..%.2f y %.2f..%.2f' % (
                i, i / 30, len(xs), cx / w * 2 - 1, cy / h * 2 - 1, xs.min() / w * 2 - 1, xs.max() / w * 2 - 1,
                ys.min() / h * 2 - 1, ys.max() / h * 2 - 1))
        ov = im.copy()
        ov[m > 0] = (0, 0, 255)
        cells.append(cv2.resize(cv2.addWeighted(im, 0.5, ov, 0.5, 0), (480, 270)))
    while len(cells) % 4:
        cells.append(np.zeros_like(cells[0]))
    cv2.imwrite(str(REF / 'sheets' / ('mask_%d_%d.jpg' % (a, b))),
                np.vstack([np.hstack(cells[k:k + 4]) for k in range(0, len(cells), 4)]), [cv2.IMWRITE_JPEG_QUALITY, 80])


if __name__ == '__main__':
    main()
