"""Reference crouch melee #5 戳 (one-handed stab), BV1CeYUeSE7b 1:34.77-1:35.97.

Dumps every frame 94.0-98.0 s to Saved/Reference/KukriBV1CeYUeSE7b20261020/atk3_frames and writes NDC-gridded reading
sheets (grid_atk3_a..e.jpg, 9-12 frames each, t = 0 at frame 2843 = 94.767 s, the last still stance frame) and full-size
crops of the contact (big_atk3_a..c.jpg).  Used for the V12 third hit (Attack3, fit_reference.py REF_STAB) and by
track_atk3.py / contact_atk3.py for the camera."""
import os

import cv2
import numpy as np

d = r"D:\FPS3D\FPSGAME\Saved\Reference\KukriBV1CeYUeSE7b20261020"
out = os.path.join(d, "atk3_frames")
T0 = 2843


def dump():
    os.makedirs(out, exist_ok=True)
    c = cv2.VideoCapture(os.path.join(d, "ref.f100024.mp4"))
    fps = c.get(cv2.CAP_PROP_FPS)
    f0, f1 = int(94.0 * fps), int(98.0 * fps)
    c.set(cv2.CAP_PROP_POS_FRAMES, f0)
    for i in range(f0, f1):
        ok, f = c.read()
        if not ok:
            break
        cv2.imwrite(os.path.join(out, "f%05d.png" % i), f)


def grid(im):
    h, w = im.shape[:2]
    for k in range(-4, 5):
        x = int((k / 4 * 0.5 + 0.5) * w)
        y = int((k / 4 * 0.5 + 0.5) * h)
        col = (0, 255, 255) if k == 0 else (160, 160, 160)
        cv2.line(im, (x, 0), (x, h), col, 1)
        cv2.line(im, (0, y), (w, y), col, 1)
        cv2.putText(im, "%.2f" % (k / 4), (x + 2, h - 6), cv2.FONT_HERSHEY_SIMPLEX, .4, (0, 255, 0), 1)
        cv2.putText(im, "%.2f" % (k / 4), (2, y - 2), cv2.FONT_HERSHEY_SIMPLEX, .4, (0, 255, 0), 1)
    return im


def sheet(idx, name, cols=3, w=640):
    ims = []
    for i in idx:
        im = grid(cv2.resize(cv2.imread(os.path.join(out, "f%05d.png" % i)), (w, w * 9 // 16)))
        cv2.putText(im, "%d t=%.3f" % (i, (i - T0) / 30), (200, 22), cv2.FONT_HERSHEY_SIMPLEX, .7, (0, 0, 255), 2)
        ims.append(im)
    while len(ims) % cols:
        ims.append(np.zeros_like(ims[0]))
    cv2.imwrite(os.path.join(d, "sheets", name), np.vstack([np.hstack(ims[k:k + cols]) for k in range(0, len(ims), cols)]))


def big(idx, name, cols, w):
    ims = []
    for i in idx:
        im = cv2.resize(cv2.imread(os.path.join(out, "f%05d.png" % i)), (w, w * 9 // 16))
        cv2.putText(im, str(i), (10, 40), 0, 1.2, (0, 0, 255), 3)
        ims.append(im)
    cv2.imwrite(os.path.join(d, "sheets", name), np.vstack([np.hstack(ims[k:k + cols]) for k in range(0, len(ims), cols)]))


if __name__ == "__main__":
    dump()
    os.makedirs(os.path.join(d, "sheets"), exist_ok=True)
    sheet(range(2836, 2845), "grid_atk3_a.jpg")
    sheet(range(2845, 2854), "grid_atk3_b.jpg")
    sheet(range(2854, 2863), "grid_atk3_c.jpg")
    sheet(range(2863, 2872), "grid_atk3_d.jpg")
    sheet(range(2872, 2884), "grid_atk3_e.jpg")
    big((2848, 2852, 2855, 2858), "big_atk3_a.jpg", 2, 800)
    big((2872, 2876, 2878, 2880), "big_atk3_b.jpg", 2, 800)
    big((2853, 2854, 2856, 2857, 2859, 2860, 2861, 2862, 2863), "big_atk3_c.jpg", 3, 640)
