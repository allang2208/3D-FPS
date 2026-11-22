"""Measure the reference blade on screen per frame: py -3.11 measure_blade.py [first last] [--overlay DIR]

Reads Reference/frames/fNNNNN.jpg (index = file seconds x 60, YouTube NTrzxPIXer4 1080p60). The blade is the longest
pair of near-parallel straight edges; its centreline (angle, two end points) and the lower end of the bright blade
(where it meets the crossguard/ricasso) are written to Reference/blade_track.json in pixels of the 1920x1080 frame.
Author aid only: every key used by the author script is confirmed on the overlay sheet.
"""
import json
import math
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
FRAMES = HERE / 'frames'
W, H = 1920, 1080
TITLE_BOTTOM = 210          # burned-in title (two lines), ignore


def lines_of(img):
    grey = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    grey[:TITLE_BOTTOM] = 0
    edges = cv2.Canny(cv2.GaussianBlur(grey, (5, 5), 0), 40, 110)
    found = cv2.HoughLinesP(edges, 1, math.pi / 720, 120, minLineLength=260, maxLineGap=25)
    return [] if found is None else [tuple(float(v) for v in np.asarray(l).reshape(-1)[:4]) for l in found]


def angle(l):
    x1, y1, x2, y2 = l
    a = math.degrees(math.atan2(-(y2 - y1), x2 - x1)) % 180.0   # screen angle, 0 = horizontal, 90 = vertical up
    return a


def length(l):
    return math.hypot(l[2] - l[0], l[3] - l[1])


def offset(l, a):
    """Signed distance of the line from the image centre along the line normal (for pairing parallel edges)."""
    n = (math.sin(math.radians(a)), math.cos(math.radians(a)))
    cx, cy = (l[0] + l[2]) / 2 - W / 2, (l[1] + l[3]) / 2 - H / 2
    return cx * n[0] + cy * n[1]


def measure(img):
    ls = sorted(lines_of(img), key=length, reverse=True)
    if not ls:
        return None
    best = None
    for i, a in enumerate(ls[:40]):
        aa = angle(a)
        for b in ls[i + 1:40]:
            da = abs((angle(b) - aa + 90) % 180 - 90)
            if da > 4.0:
                continue
            gap = abs(offset(a, aa) - offset(b, aa))
            if not 12 <= gap <= 140:            # blade width on screen
                continue
            score = length(a) + length(b) - 3 * da
            if best is None or score > best[0]:
                best = (score, a, b, gap)
    if best is None:
        return None
    _, a, b, gap = best
    aa = angle(a)
    d = np.array([math.cos(math.radians(aa)), -math.sin(math.radians(aa))])     # along the blade, screen y down
    pts = np.array([[a[0], a[1]], [a[2], a[3]], [b[0], b[1]], [b[2], b[3]]])
    centre = pts.mean(axis=0)
    s = (pts - centre) @ d
    lo, hi = centre + d * s.min(), centre + d * s.max()
    if lo[1] < hi[1]:                    # 'low' end = towards the bottom of the screen (hilt side)
        lo, hi = hi, lo
    return {'angle_deg': round(aa, 2), 'width_px': round(gap, 1), 'low': [round(float(v), 1) for v in lo],
            'high': [round(float(v), 1) for v in hi]}


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    files = sorted(FRAMES.glob('f*.jpg'))
    if len(args) >= 2:
        first, last = int(args[0]), int(args[1])
        files = [f for f in files if first <= int(f.stem[1:]) <= last]
    out, overlay = {}, None
    if '--overlay' in sys.argv:
        overlay = Path(sys.argv[sys.argv.index('--overlay') + 1])
        overlay.mkdir(parents=True, exist_ok=True)
    for f in files:
        img = cv2.imread(str(f))
        m = measure(img)
        out[f.stem] = m
        if overlay is not None and m:
            cv2.line(img, tuple(map(int, m['low'])), tuple(map(int, m['high'])), (0, 0, 255), 4)
            cv2.circle(img, tuple(map(int, m['low'])), 14, (0, 255, 255), 4)
            cv2.putText(img, '%s %.1fdeg' % (f.stem, m['angle_deg']), (30, 1050), cv2.FONT_HERSHEY_SIMPLEX, 1.6,
                        (0, 255, 255), 3)
            cv2.imwrite(str(overlay / (f.stem + '.jpg')), cv2.resize(img, (640, 360)))
    (HERE / 'blade_track.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
    print('BLADE_TRACK', len(out), 'frames,', sum(1 for v in out.values() if v), 'measured')


if __name__ == '__main__':
    main()
