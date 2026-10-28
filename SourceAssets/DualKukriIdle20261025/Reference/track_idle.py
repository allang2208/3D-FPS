"""Track the idle sway on the reference stills: template patches from f00105 (3.50 s) matched every 3 frames.

python -I Reference/track_idle.py
Prints per-frame pixel offsets (1080p) of the left fist, right hand/forearm, both blade tips, the left guard and two
background patches.  Read-out used by author_idle.py: 2.0-2.3 s is the end of the draw; 2.3-4.1 s the fists and
blades move rigidly (left x -15..+7, right +10..-4, both y +6..-6 px) while the background stays within 1 px.
"""
from pathlib import Path

import cv2

FRAMES = Path(r"D:\FPS3D\FPSGAME\Saved\Reference\DualKukriBV19dUqBJECT20261025\idle_frames")
PATCHES = {'Lfist': (470, 880, 140, 110), 'Rhand': (1120, 880, 140, 110), 'Rforearm': (1400, 960, 140, 100),
           'bladeBtip': (1500, 760, 140, 70), 'bladeAtip': (300, 550, 140, 80), 'guardB': (700, 880, 140, 90),
           'bg_top': (800, 150, 200, 120), 'bg_left': (60, 300, 200, 150)}


def load(f):
    return cv2.imread(str(FRAMES / ('f%05d.png' % f)), cv2.IMREAD_GRAYSCALE)


def main():
    ref = load(105)
    print('frame   t  ' + ' '.join(PATCHES))
    for f in range(60, 124, 3):
        a = load(f)
        row = []
        for x, y, w, h in PATCHES.values():
            x0, y0 = max(0, x - 60), max(0, y - 60)
            r = cv2.matchTemplate(a[y0:y + h + 60, x0:x + w + 60], ref[y:y + h, x:x + w], cv2.TM_CCOEFF_NORMED)
            _, score, _, loc = cv2.minMaxLoc(r)
            row.append('%+5.1f,%+5.1f(%.2f)' % (loc[0] + x0 - x, loc[1] + y0 - y, score))
        print(f, round(f / 30, 2), ' '.join(row))


if __name__ == '__main__':
    main()
