"""Contact sheets of reference frames with time labels and an NDC grid (x right, y down, 0.25 steps).

python -I Reference/sheet_ref.py first_frame last_frame [cols] [cell_width] [name] [crop x0,y0,x1,y1 in 0..1]
"""
import sys
from pathlib import Path

import cv2
import numpy as np

REF = Path(r"D:\FPS3D\FPSGAME\Saved\Reference\HatchetBV1pqkyYyEDY20261102")
FPS = 30


def main():
    a, b = int(sys.argv[1]), int(sys.argv[2])
    cols = int(sys.argv[3]) if len(sys.argv) > 3 else 6
    cw = int(sys.argv[4]) if len(sys.argv) > 4 else 320
    name = sys.argv[5] if len(sys.argv) > 5 else 'dense_%d_%d' % (a, b)
    crop = [float(v) for v in sys.argv[6].split(',')] if len(sys.argv) > 6 else (0.0, 0.0, 1.0, 1.0)
    cells = []
    for i in range(a, b + 1):
        im = cv2.imread(str(REF / 'frames' / ('f%05d.png' % i)))
        if im is None:
            continue
        h, w = im.shape[:2]
        x0, y0, x1, y1 = int(crop[0] * w), int(crop[1] * h), int(crop[2] * w), int(crop[3] * h)
        for k in range(1, 8):          # grid lines every 0.25 NDC
            cv2.line(im, (k * w // 8, 0), (k * w // 8, h), (0, 255, 255) if k == 4 else (90, 90, 90), 2 if k == 4 else 1)
            cv2.line(im, (0, k * h // 8), (w, k * h // 8), (0, 255, 255) if k == 4 else (90, 90, 90), 2 if k == 4 else 1)
        im = im[y0:y1, x0:x1]
        ch = int(round(cw * im.shape[0] / im.shape[1]))
        im = cv2.resize(im, (cw, ch), interpolation=cv2.INTER_AREA)
        cv2.putText(im, '%d %.3f' % (i, i / FPS), (4, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        cells.append(im)
    while len(cells) % cols:
        cells.append(np.zeros_like(cells[0]))
    rows = [np.hstack(cells[k:k + cols]) for k in range(0, len(cells), cols)]
    (REF / 'sheets').mkdir(exist_ok=True)
    out = REF / 'sheets' / (name + '.jpg')
    cv2.imwrite(str(out), np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 82])
    print(out)


if __name__ == '__main__':
    main()
