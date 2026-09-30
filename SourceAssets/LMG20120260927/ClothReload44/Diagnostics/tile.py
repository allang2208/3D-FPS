"""Tile f_<t>.png previews into labelled 4x3 sheets (jpg)."""
import sys, re
from pathlib import Path
import cv2, numpy as np

src, prefix = Path(sys.argv[1]), sys.argv[2]
cols, rows = 4, 3
stamp = lambda p: re.findall(r'f_(\d+\.\d+)', p.name)[0]
files = sorted(src.glob('f_*.png'), key=lambda p: float(stamp(p)))
tiles = []
for f in files:
    im = cv2.imread(str(f))
    t = stamp(f)
    cv2.putText(im, t + 's', (8, 26), cv2.FONT_HERSHEY_SIMPLEX, .8, (0, 0, 0), 4)
    cv2.putText(im, t + 's', (8, 26), cv2.FONT_HERSHEY_SIMPLEX, .8, (255, 255, 255), 2)
    tiles.append(im)
h, w = tiles[0].shape[:2]
for s in range(0, len(tiles), cols * rows):
    chunk = tiles[s:s + cols * rows]
    sheet = np.zeros((h * rows, w * cols, 3), np.uint8)
    for i, im in enumerate(chunk):
        r, c = divmod(i, cols)
        sheet[r * h:(r + 1) * h, c * w:(c + 1) * w] = im
    out = src / ('%s_%02d.jpg' % (prefix, s // (cols * rows) + 1))
    cv2.imwrite(str(out), sheet, [cv2.IMWRITE_JPEG_QUALITY, 80])
    print('SHEET', out)
