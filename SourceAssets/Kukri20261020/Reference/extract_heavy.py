"""Extract the heavy-strike reference frames (BV1CeYUeSE7b 1:53.5-1:59.5, charge raised to the upper right, release
swinging from the upper right to the lower left) and the reading sheets.

Frames: Saved/Reference/KukriBV1CeYUeSE7b20261020/heavy_frames/fNNNNN.png (frame index at 30 fps).
Sheets: Saved/Reference/KukriBV1CeYUeSE7b20261020/sheets/heavy_*.jpg; --grid a b step name draws the 0.1 NDC grid
(x right, y down) used for the screen readings.
"""
import cv2, numpy as np, os, sys

D = r"D:\FPS3D\FPSGAME\Saved\Reference\KukriBV1CeYUeSE7b20261020"
OUT = os.path.join(D, "heavy_frames")
T0, T1 = 113.5, 119.5


def extract():
    os.makedirs(OUT, exist_ok=True)
    c = cv2.VideoCapture(os.path.join(D, "ref.f100024.mp4"))
    fps = c.get(cv2.CAP_PROP_FPS)
    a, b = int(round(T0 * fps)), int(round(T1 * fps))
    c.set(cv2.CAP_PROP_POS_FRAMES, a)
    for i in range(a, b):
        ok, f = c.read()
        if not ok:
            break
        cv2.imwrite(os.path.join(OUT, "f%05d.png" % i), f)
    print("fps", fps, "frames", a, b)


def grid(im):
    h, w = im.shape[:2]
    for k in range(-10, 11):
        x = int((k / 10 + 1) / 2 * w)
        y = int((k / 10 + 1) / 2 * h)
        c = (0, 200, 255) if k % 5 == 0 else (90, 90, 90)
        cv2.line(im, (x, 0), (x, h), c, 1)
        cv2.line(im, (0, y), (w, y), c, 1)
    return im


def sheets(a, b, step, name, cols=6, w=320, with_grid=False):
    ims = []
    for i in range(a, b, step):
        p = os.path.join(OUT, "f%05d.png" % i)
        if not os.path.exists(p):
            continue
        im = cv2.resize(cv2.imread(p), (w, w * 9 // 16))
        if with_grid:
            im = grid(im)
        cv2.putText(im, "%d %.3f" % (i, i / 30), (6, 22), cv2.FONT_HERSHEY_SIMPLEX, .6, (0, 255, 255), 2)
        ims.append(im)
    while len(ims) % cols:
        ims.append(np.zeros_like(ims[0]))
    os.makedirs(os.path.join(D, "sheets"), exist_ok=True)
    cv2.imwrite(os.path.join(D, "sheets", name), np.vstack([np.hstack(ims[i:i + cols]) for i in range(0, len(ims), cols)]),
                [cv2.IMWRITE_JPEG_QUALITY, 85])


if __name__ == "__main__":
    if "--grid" in sys.argv:
        k = sys.argv.index("--grid")
        a, b, step, name = int(sys.argv[k + 1]), int(sys.argv[k + 2]), int(sys.argv[k + 3]), sys.argv[k + 4]
        sheets(a, b, step, name, cols=4, w=480, with_grid=True)
    else:
        if "--sheets" not in sys.argv:
            extract()
        sheets(3405, 3540, 3, "heavy_overview.jpg")


def labelled(i, out):
    """Full-resolution frame with the 0.1 NDC grid and axis labels (the readings in fit_heavy.py)."""
    im = grid(cv2.imread(os.path.join(OUT, "f%05d.png" % i)))
    h, w = im.shape[:2]
    for k in range(-9, 10, 3):
        cv2.putText(im, "%.1f" % (k / 10), (int((k / 10 + 1) / 2 * w) + 2, h - 6), cv2.FONT_HERSHEY_SIMPLEX, .5, (0, 255, 0), 1)
        cv2.putText(im, "%.1f" % (k / 10), (4, int((k / 10 + 1) / 2 * h) - 3), cv2.FONT_HERSHEY_SIMPLEX, .5, (0, 255, 0), 1)
    cv2.putText(im, "%d t=%.3f" % (i, (i - 3468) / 30), (w // 2 - 80, 30), cv2.FONT_HERSHEY_SIMPLEX, .9, (0, 255, 255), 2)
    return im


def pairs(frames, name):
    ims = [labelled(i, None) for i in frames]
    cv2.imwrite(os.path.join(D, "sheets", name), np.vstack(ims), [cv2.IMWRITE_JPEG_QUALITY, 88])
