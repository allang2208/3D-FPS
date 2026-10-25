"""Reference melee #1 (diagonal, upper-left -> lower-right), BV1CeYUeSE7b 1:24-1:26.

Dumps every frame 84.0-86.2 s to Saved/Reference/KukriBV1CeYUeSE7b20261020/atk1_frames and writes
NDC-gridded reading sheets (grid_atk1_*.jpg).  Used for the V11 second hit (Attack2)."""
import os

import cv2
import numpy as np

d = r"D:\FPS3D\FPSGAME\Saved\Reference\KukriBV1CeYUeSE7b20261020"
out = os.path.join(d, "atk1_frames")
os.makedirs(out, exist_ok=True)
c = cv2.VideoCapture(os.path.join(d, "ref.f100024.mp4"))
fps = c.get(cv2.CAP_PROP_FPS)
F0, F1 = int(84.0 * fps), int(86.2 * fps)
c.set(cv2.CAP_PROP_POS_FRAMES, F0)
for i in range(F0, F1):
    ok, f = c.read()
    if not ok:
        break
    cv2.imwrite(os.path.join(out, "f%05d.png" % i), f)


def grid(im):
    h, w = im.shape[:2]
    for k in range(-4, 5):
        x = int((k / 4 * 0.5 + 0.5) * w)
        y = int((k / 4 * 0.5 + 0.5) * h)
        col = (0, 255, 255) if k == 0 else (200, 200, 200)
        cv2.line(im, (x, 0), (x, h), col, 1)
        cv2.line(im, (0, y), (w, y), col, 1)
        cv2.putText(im, "%.2f" % (k / 4), (x + 2, h - 6), cv2.FONT_HERSHEY_SIMPLEX, .4, (0, 255, 0), 1)
        cv2.putText(im, "%.2f" % (k / 4), (2, y - 2), cv2.FONT_HERSHEY_SIMPLEX, .4, (0, 255, 0), 1)
    return im


def sheet(idx, name, cols=3, w=640, t0=None):
    ims = []
    for i in idx:
        im = cv2.imread(os.path.join(out, "f%05d.png" % i))
        im = grid(cv2.resize(im, (w, w * 9 // 16)))
        lab = "%d %.3f" % (i, i / fps) if t0 is None else "%d t=%.3f" % (i, (i - t0) / fps)
        cv2.putText(im, lab, (200, 20), cv2.FONT_HERSHEY_SIMPLEX, .6, (0, 0, 255), 2)
        ims.append(im)
    while len(ims) % cols:
        ims.append(np.zeros_like(ims[0]))
    cv2.imwrite(os.path.join(d, "sheets", name), np.vstack([np.hstack(ims[i:i + cols]) for i in range(0, len(ims), cols)]))


if __name__ == "__main__":
    import sys
    t0 = int(sys.argv[1]) if len(sys.argv) > 1 else None
    s = F0 + 9   # 84.30
    sheet(list(range(s, s + 9)), "grid_atk1_a.jpg", t0=t0)
    sheet(list(range(s + 9, s + 18)), "grid_atk1_b.jpg", t0=t0)
    sheet(list(range(s + 18, s + 27)), "grid_atk1_c.jpg", t0=t0)
    sheet(list(range(s + 27, s + 45, 2)), "grid_atk1_d.jpg", t0=t0)
    print(fps, F0, F1)
