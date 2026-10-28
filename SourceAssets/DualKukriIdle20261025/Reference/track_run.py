"""Track the sprint sway on the reference (握持姿势 奔跑, file 16.75-18.4 s): patches from f00525 (17.50 s) every 2 frames.

python -I Reference/track_run.py    (frames: Reference/extract_idle.py writes idle_frames; run frames 15.5-19.5 s are
                                     extracted with  ffmpeg -ss 15.5 -t 4 -i ref_1080.mp4 -vsync 0 -start_number 465
                                     run_frames/f%05d.png)
Read-out used by author_clips.py: the left fist swings right+down / left+up about 140 x 80 px peak to peak once per
~0.5 s stride (peaks right at 17.2, 17.67, 18.2 s); the raised right fist is motion-blurred, its blade moves less
and mostly against the left fist; the background moves <= 12 px (camera bob, not authored).  Offsets beyond the
+-90 px search window are clipped.
"""
from pathlib import Path

import cv2

FRAMES = Path(r"D:\FPS3D\FPSGAME\Saved\Reference\DualKukriBV19dUqBJECT20261025\run_frames")
PATCHES = {'Lfist': (760, 860, 180, 120), 'Lblade': (380, 780, 160, 80), 'Rfist': (1700, 180, 160, 160),
           'Rblade': (1300, 250, 160, 90), 'Rarm': (1800, 500, 110, 160), 'bg': (900, 100, 200, 150)}


def load(f):
    return cv2.imread(str(FRAMES / ('f%05d.png' % f)), cv2.IMREAD_GRAYSCALE)


def main():
    ref = load(525)
    print('frame    t   ' + ' '.join(PATCHES))
    for f in range(500, 556, 2):
        a = load(f)
        row = []
        for x, y, w, h in PATCHES.values():
            x0, y0 = max(0, x - 90), max(0, y - 90)
            r = cv2.matchTemplate(a[y0:min(1080, y + h + 90), x0:min(1920, x + w + 90)], ref[y:y + h, x:x + w], cv2.TM_CCOEFF_NORMED)
            _, score, _, loc = cv2.minMaxLoc(r)
            row.append('%+5.0f,%+5.0f(%.2f)' % (loc[0] + x0 - x, loc[1] + y0 - y, score))
        print(f, '%.3f' % (f / 30), ' '.join(row))


if __name__ == '__main__':
    main()
