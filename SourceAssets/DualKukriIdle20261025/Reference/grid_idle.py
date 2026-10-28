"""NDC grid overlay on a reference frame (x right, y down, -1..1) for reading screen targets.

python -I Reference/grid_idle.py <frame.png> <out.jpg> [x0 y0 x1 y1 crop in px] [scale]
"""
import sys
import cv2

src, out = sys.argv[1], sys.argv[2]
im = cv2.imread(src)
h, w = im.shape[:2]
for i in range(-10, 11):
    x = int(round((i / 10 + 1) * w / 2))
    y = int(round((i / 10 + 1) * h / 2))
    major = i % 5 == 0
    col = (0, 255, 255) if major else (0, 160, 255)
    cv2.line(im, (x, 0), (x, h), col, 2 if major else 1)
    cv2.line(im, (0, y), (w, y), col, 2 if major else 1)
    cv2.putText(im, '%.1f' % (i / 10), (x + 3, 22), cv2.FONT_HERSHEY_SIMPLEX, .55, col, 2)
    cv2.putText(im, '%.1f' % (i / 10), (4, y - 4), cv2.FONT_HERSHEY_SIMPLEX, .55, col, 2)
if len(sys.argv) >= 7:
    x0, y0, x1, y1 = map(int, sys.argv[3:7])
    im = im[y0:y1, x0:x1]
    s = float(sys.argv[7]) if len(sys.argv) > 7 else 1.0
    im = cv2.resize(im, None, fx=s, fy=s, interpolation=cv2.INTER_CUBIC)
cv2.imwrite(out, im, [cv2.IMWRITE_JPEG_QUALITY, 92])
