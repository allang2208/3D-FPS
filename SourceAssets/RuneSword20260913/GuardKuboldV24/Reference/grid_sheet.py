"""2x2 read-out sheet with a labelled 100 px grid: py -3.11 grid_sheet.py OUT.jpg F1 F2 F3 F4 (frame numbers).

Each tile is the full 1920x1080 reference frame at half size, so coordinates read off the grid are full-frame pixels.
"""
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent


def tile(n):
    im = cv2.imread(str(HERE / 'frames' / ('f%05d.jpg' % n)))
    for x in range(100, 1920, 100):
        cv2.line(im, (x, 0), (x, 1080), (0, 255, 255) if x % 500 == 0 else (0, 140, 140), 2 if x % 500 == 0 else 1)
        cv2.putText(im, str(x), (x + 4, 230), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2)
    for y in range(100, 1080, 100):
        cv2.line(im, (0, y), (1920, y), (0, 255, 255) if y % 500 == 0 else (0, 140, 140), 2 if y % 500 == 0 else 1)
        cv2.putText(im, str(y), (6, y - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2)
    cv2.putText(im, 'f%05d  %.3f s' % (n, n / 60.0), (1300, 1060), cv2.FONT_HERSHEY_SIMPLEX, 1.6, (0, 0, 255), 4)
    return cv2.resize(im, (960, 540))


out = sys.argv[1]
frames = [int(v) for v in sys.argv[2:6]]
tiles = [tile(n) for n in frames]
cv2.imwrite(out, np.vstack([np.hstack(tiles[0:2]), np.hstack(tiles[2:4])]), [cv2.IMWRITE_JPEG_QUALITY, 88])
print(out)
