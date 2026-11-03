"""Read-out sheets: reference frames with a 0.1 NDC grid (x right, y down) and tick labels every 0.2.

python -I Reference/grid_ref.py frame [frame ...]  -> sheets/grid_<first>_<last>.jpg (2 x 2 frames, 800 px each)
"""
import sys
from pathlib import Path

import cv2
import numpy as np

REF = Path(r"D:\FPS3D\FPSGAME\Saved\Reference\HatchetBV1pqkyYyEDY20261102")
W, H = 800, 450


def cell(i):
    im = cv2.resize(cv2.imread(str(REF / 'frames' / ('f%05d.png' % i))), (W, H), interpolation=cv2.INTER_AREA)
    for k in range(-10, 11):
        x = int(round((k / 10 + 1) / 2 * W))
        y = int(round((k / 10 + 1) / 2 * H))
        col = (0, 255, 255) if k == 0 else (0, 200, 0) if k % 2 == 0 else (60, 60, 60)
        cv2.line(im, (x, 0), (x, H), col, 1)
        cv2.line(im, (0, y), (W, y), col, 1)
        if k % 2 == 0:
            cv2.putText(im, '%.1f' % (k / 10), (x + 2, H - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 255, 0), 1)
            cv2.putText(im, '%.1f' % (k / 10), (2, y - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 255, 0), 1)
    cv2.putText(im, '%d  %.3f s' % (i, i / 30), (W - 170, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 255), 2)
    return im


def main():
    ids = [int(v) for v in sys.argv[1:]]
    cells = [cell(i) for i in ids]
    while len(cells) % 2:
        cells.append(np.zeros_like(cells[0]))
    rows = [np.hstack(cells[k:k + 2]) for k in range(0, len(cells), 2)]
    out = REF / 'sheets' / ('grid_%d_%d.jpg' % (ids[0], ids[-1]))
    cv2.imwrite(str(out), np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 85])
    print(out)


if __name__ == '__main__':
    main()
